"""测试基建：独立 ezlove_test 库 + 每用例 TRUNCATE 清库 + ASGI 客户端（P3 §3.9 契约）。"""
import os

# ── 环境变量硬覆盖（必须在任何 import app.* 之前）──
# 不用 setdefault：本套件含全表 TRUNCATE 清库——若开发 shell 已 export DATABASE_URL，
# setdefault 不覆盖，pydantic-settings 环境变量优先于 backend/.env 的机制会使测试
# 连到 shell 指向的库并对其执行 TRUNCATE（误清非测试库的数据安全风险）。
# TRUNCATE 型测试套件的库指向必须不受外部环境变量影响。
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5433/ezlove_test"
os.environ["DEBUG"] = "true"  # 启用 dev-login（测试取小程序侧 user token 的途径）
os.environ["JWT_SECRET"] = "pytest-secret"
os.environ["SCHEDULER_ENABLED"] = "false"  # ASGITransport 不触发 lifespan，此处双保险
os.environ["ALERT_NOTIFY_ENABLED"] = "false"  # 防通知外呼双保险（模板未配置时本就早退）

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

import app.models  # noqa: F401  确保所有模型注册（与 alembic/env.py 同款注释）
from app.database import Base, async_session, engine
from app.main import RateLimitMiddleware, app

# ── 测试旁路：dev-login 速率限制（类级 patch，进程级 pytest 运行期生效）──
# RateLimitMiddleware 以 client_ip 计数（/auth/、/ai/ 路径 10 次/60s）。ASGITransport 下
# 所有请求 client.host 相同，全量套件集中调用 dev-login 必然触发 429。
# 限流器非本次 P0 修复对象，测试侧直通 dispatch（不改动生产代码）；
# 中间件实例在首次请求时才创建，此处类级 patch 一定先于实例化生效。
#
# 生命周期声明（P4-iter1 D5/D9）：本旁路为一次性类属性赋值，作用于整个 pytest 进程、
# 无自动还原——RATE_LIMIT_BYPASSED 标记当前旁路态；需要测限流器本体的用例不得依赖
# 已被旁路的 app 栈，应通过 _ORIGINAL_RATE_LIMIT_DISPATCH 直调原实现（见
# tests/test_rate_limit.py），或以该引用显式恢复类属性并在用后还原。
async def _bypass_rate_limit(self, request, call_next):
    return await call_next(request)


# 原始 dispatch 引用（模块级保存，可直调/可回退）——与旁路赋值一并定义，防漂移
_ORIGINAL_RATE_LIMIT_DISPATCH = RateLimitMiddleware.dispatch
RateLimitMiddleware.dispatch = _bypass_rate_limit
RATE_LIMIT_BYPASSED = True  # 旁路状态标记：True = 本 pytest 进程内限流已被类级旁路


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _prepare_database():
    """session 级建库：DROP + CREATE ezlove_test，再 Base.metadata.create_all。"""
    try:
        conn = await asyncpg.connect(
            host="localhost", port=5433,
            user="postgres", password="postgres", database="postgres",
        )
    except Exception as e:
        pytest.skip(f"PG 不可用（{e}）：请先 docker-compose up -d db")
        return
    try:
        await conn.execute("DROP DATABASE IF EXISTS ezlove_test")
        await conn.execute("CREATE DATABASE ezlove_test")
    finally:
        await conn.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _truncate_tables():
    """function 级清库：每用例开始前 TRUNCATE 全表（RESTART IDENTITY CASCADE）。"""
    async with async_session() as session:
        table_names = ", ".join(f'"{t}"' for t in Base.metadata.tables.keys())
        await session.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
        await session.commit()


@pytest_asyncio.fixture
async def db():
    """与被测代码同一 engine 的 session（测试可直读/构造数据）。"""
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    """httpx AsyncClient + ASGITransport——不触发 lifespan（调度器不会启动）。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
