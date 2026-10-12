# EZLove 社区管理看板 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 EZLove 家庭端基础上，新增社区管理 H5 后台，实现老人 A/B/C 分级管理、食堂数据 LLM 解析、社区看板和事件中心。

**Architecture:** 共享同一 FastAPI 后端，新增 `/api/v1/community/*` 路由。新建独立 H5 前端项目（Vue 3 + Element Plus）。数据库新增 5 张表，与现有 7 张表共存，通过 `users.id` 外键打通。

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async), PostgreSQL 16, Redis 7, Alembic, Vue 3, Element Plus, Pinia, Axios, openpyxl, Anthropic Claude API

## Global Constraints

- Python 3.12, async throughout (asyncpg driver)
- SQLAlchemy 2.0 style: `Mapped` + `mapped_column`, no `relationship()` definitions
- Pydantic v2: `BaseModel`, `model_config = {"from_attributes": True}`
- UUID primary keys with `uuid.uuid4` default
- Server-side timestamps: `server_default=func.now()`, `onupdate=func.now()`
- Enum fields stored as `String` (not SQLAlchemy `Enum` type)
- No tests directory currently has tests; new tests go to `backend/tests/` using pytest + pytest-asyncio
- H5 frontend: Vue 3 Composition API + `<script setup>`, Element Plus, SCSS
- All API error messages in Chinese
- JWT auth: HS256, same secret as existing family auth
- LLM API key/URL to be provided later; code must include offline fallback

---

## File Structure

### Backend (新增/修改)

```
backend/
  app/
    models/
      __init__.py              # MODIFY: 新增 community model imports
      community.py             # CREATE: Community, CommunityWorker, CommunityElder
      canteen.py               # CREATE: CanteenRecord
      community_event.py       # CREATE: CommunityEvent
    schemas/
      community.py             # CREATE: 社区相关所有 Pydantic schemas
    services/
      community.py             # CREATE: 社区管理业务逻辑
      canteen.py               # CREATE: 食堂数据 + LLM 解析
      community_event.py       # CREATE: 事件管理 + 自动生成
    api/v1/
      community_auth.py        # CREATE: 社区登录
      community.py             # CREATE: 看板 + 老人管理
      canteen.py               # CREATE: 食堂数据 API
      community_events.py      # CREATE: 事件 API
      router.py                # MODIFY: 注册新路由
    deps.py                    # MODIFY: 新增 get_current_worker 依赖
    config.py                  # MODIFY: 新增 LLM 配置项
    utils/
      llm_parser.py            # CREATE: LLM 解析封装
  alembic/
    versions/
      xxx_community_tables.py  # CREATE: 新增迁移
  tests/
    conftest.py                # CREATE: pytest fixtures
    test_community_auth.py     # CREATE
    test_community_elders.py   # CREATE
    test_canteen.py            # CREATE
```

### H5 Frontend (新建项目)

```
admin-frontend/
  index.html
  package.json
  vite.config.js
  .env.development
  .env.production
  src/
    main.js                    # App bootstrap
    App.vue                    # Root component
    router/
      index.js                 # Vue Router
    api/
      request.js               # Axios 封装
      auth.js                  # 登录 API
      community.js             # 社区 API
      canteen.js               # 食堂 API
      events.js                # 事件 API
    stores/
      user.js                  # 登录状态
      dashboard.js             # 看板数据
      elders.js                # 老人档案
      canteen.js               # 食堂记录
      events.js                # 事件中心
    views/
      login/
        index.vue              # 登录页
      layout/
        index.vue              # 侧边栏布局
      dashboard/
        index.vue              # 看板页
      elders/
        index.vue              # 老人列表
        detail.vue             # 老人详情
      canteen/
        index.vue              # 食堂管理
      events/
        index.vue              # 事件中心
    styles/
      variables.scss           # 设计变量
      global.scss              # 全局样式
```

---

## Task 1: Database Migration

**Files:**
- Create: `backend/alembic/versions/<timestamp>_add_community_tables.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/models/community.py`
- Create: `backend/app/models/canteen.py`
- Create: `backend/app/models/community_event.py`

**Interfaces:**
- Produces: `Community`, `CommunityWorker`, `CommunityElder`, `CanteenRecord`, `CommunityEvent` ORM classes (all inherit `Base`)
- These are consumed by all subsequent backend tasks

- [ ] **Step 1: Create community model file**

```python
# backend/app/models/community.py
import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Community(Base):
    __tablename__ = "communities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128))
    address: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class CommunityWorker(Base):
    __tablename__ = "community_workers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    community_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communities.id"))
    name: Mapped[str] = mapped_column(String(64))
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    role_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class CommunityElder(Base):
    __tablename__ = "community_elders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    community_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communities.id"))
    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    care_level: Mapped[str] = mapped_column(String(1))  # A / B / C
    address: Mapped[str | None] = mapped_column(String(128), nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    health_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_worker_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("community_workers.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 2: Create canteen model file**

```python
# backend/app/models/canteen.py
import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CanteenRecord(Base):
    __tablename__ = "canteen_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    community_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communities.id"))
    raw_text: Mapped[str] = mapped_column(Text)
    source_format: Mapped[str] = mapped_column(String(16), default="text")  # text / excel / other
    parsed_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    parse_status: Mapped[str] = mapped_column(String(16), default="pending")  # pending / success / failed
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("community_workers.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

- [ ] **Step 3: Create community_event model file**

```python
# backend/app/models/community_event.py
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CommunityEvent(Base):
    __tablename__ = "community_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    community_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communities.id"))
    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(16))  # fall / absent / emergency / visit / other
    source: Mapped[str] = mapped_column(String(16))  # canteen / alert / manual
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), default="info")  # info / warning / urgent
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("community_workers.id"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

- [ ] **Step 4: Update models __init__.py**

Add imports to `backend/app/models/__init__.py`:

```python
from app.models.community import Community, CommunityWorker, CommunityElder
from app.models.canteen import CanteenRecord
from app.models.community_event import CommunityEvent
```

- [ ] **Step 5: Generate Alembic migration**

```bash
cd /Users/yxguo/Desktop/ezlove/backend
alembic revision --autogenerate -m "add_community_tables"
alembic upgrade head
```

Verify: `psql` into the DB and confirm 5 new tables exist + `community_workers.phone` has unique index.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/ backend/alembic/versions/
git commit -m "feat(db): add community management tables

5 new tables: communities, community_workers, community_elders,
canteen_records, community_events. All follow existing patterns:
UUID PKs, server-side timestamps, no relationship() definitions."
```

---

## Task 2: Backend - Community Auth (Phone + Password Login)

**Files:**
- Create: `backend/app/api/v1/community_auth.py`
- Modify: `backend/app/deps.py` (add `get_current_worker`)
- Modify: `backend/app/api/v1/router.py` (register community routes)
- Create: `backend/tests/test_community_auth.py`

**Interfaces:**
- Consumes: `CommunityWorker` model (Task 1), existing JWT config from `config.py`
- Produces: `get_current_worker` dependency (returns `CommunityWorker`), auth router with `POST /community/auth/login`
- Token payload: `{"sub": str(worker.id), "type": "worker", "community_id": str(worker.community_id), "exp": ...}`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_community_auth.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import async_session
from app.models.community import Community, CommunityWorker
from app.models.user import User
import uuid
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"])

@pytest_asyncio.fixture
async def setup_worker():
    async with async_session() as db:
        # create community
        community = Community(id=uuid.uuid4(), name="测试社区", address="测试地址")
        db.add(community)
        # create user for worker
        user = User(id=uuid.uuid4(), openid=f"worker_{uuid.uuid4().hex[:8]}", role="worker")
        db.add(user)
        await db.flush()
        # create worker
        worker = CommunityWorker(
            id=uuid.uuid4(),
            user_id=user.id,
            community_id=community.id,
            name="测试员工",
            phone="13800138000",
            role_label="网格员",
            password_hash=pwd_ctx.hash("test123456"),
        )
        db.add(worker)
        await db.commit()
        yield {"phone": "13800138000", "password": "test123456", "community_id": community.id}
        # cleanup
        await db.delete(worker)
        await db.delete(user)
        await db.delete(community)
        await db.commit()


@pytest.mark.asyncio
async def test_login_success(setup_worker):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/community/auth/login", json={
            "phone": setup_worker["phone"],
            "password": setup_worker["password"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(setup_worker):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/community/auth/login", json={
            "phone": setup_worker["phone"],
            "password": "wrong",
        })
        assert resp.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/yxguo/Desktop/ezlove/backend
pytest tests/test_community_auth.py -v
```

Expected: FAIL — endpoint not found (404 or import error).

- [ ] **Step 3: Add bcrypt to dependencies**

Add `passlib[bcrypt]` to `backend/requirements.txt` (or `pyproject.toml`).

- [ ] **Step 4: Implement get_current_worker dependency**

Add to `backend/app/deps.py`:

```python
from app.models.community import CommunityWorker
from jose import jwt, JWTError

async def get_current_worker(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> CommunityWorker:
    """验证社区工作人员 JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "worker":
            raise HTTPException(status_code=401, detail="无效的社区工作人员凭证")
        worker_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="认证已过期或无效")

    stmt = select(CommunityWorker).where(CommunityWorker.id == worker_id)
    result = await db.execute(stmt)
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=401, detail="社区工作人员不存在")
    return worker
```

- [ ] **Step 5: Implement community auth endpoint**

```python
# backend/app/api/v1/community_auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from passlib.context import CryptContext

from app.database import get_db
from app.models.community import CommunityWorker
from app.services.auth import create_access_token, create_refresh_token

router = APIRouter(prefix="/community/auth", tags=["community-auth"])
pwd_ctx = CryptContext(schemes=["bcrypt"])


class LoginRequest(BaseModel):
    phone: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    worker: dict


@router.post("/login", response_model=TokenResponse)
async def community_login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(CommunityWorker).where(CommunityWorker.phone == data.phone)
    result = await db.execute(stmt)
    worker = result.scalar_one_or_none()

    if not worker or not pwd_ctx.verify(data.password, worker.password_hash):
        raise HTTPException(status_code=401, detail="手机号或密码错误")

    # 创建 token，type=worker 以区分家庭端
    token_data = {
        "sub": str(worker.id),
        "type": "worker",
        "community_id": str(worker.community_id),
    }
    access_token = create_access_token(worker.id, extra_claims=token_data)
    refresh_token = create_refresh_token(worker.id, extra_claims=token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        worker={
            "id": str(worker.id),
            "name": worker.name,
            "phone": worker.phone,
            "role_label": worker.role_label,
            "community_id": str(worker.community_id),
        },
    )
```

Note: Modify `backend/app/services/auth.py` to support extra claims:

```python
# 在 create_access_token 函数中添加 extra_claims 参数
def create_access_token(user_id, extra_claims: dict | None = None):
    payload = {"sub": str(user_id), "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

# create_refresh_token 同理
def create_refresh_token(user_id, extra_claims: dict | None = None):
    payload = {"sub": str(user_id), "type": "refresh", "exp": datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
```

- [ ] **Step 6: Register route in router.py**

Add to `backend/app/api/v1/router.py`:

```python
from app.api.v1.community_auth import router as community_auth_router
api_router.include_router(community_auth_router)
```

- [ ] **Step 7: Run test to verify it passes**

```bash
pytest tests/test_community_auth.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/v1/community_auth.py backend/app/deps.py backend/app/api/v1/router.py backend/tests/test_community_auth.py backend/requirements.txt
git commit -m "feat(auth): add community worker phone+password login

POST /api/v1/community/auth/login with phone+password, returns JWT
with type=worker claim. New get_current_worker dependency for
protecting community routes."
```

---

## Task 3: Backend - Elder Management (CRUD + A/B/C Grading)

**Files:**
- Create: `backend/app/schemas/community.py`
- Create: `backend/app/services/community.py`
- Create: `backend/app/api/v1/community.py`
- Create: `backend/tests/test_community_elders.py`

**Interfaces:**
- Consumes: `Community`, `CommunityWorker`, `CommunityElder` models (Task 1), `get_current_worker` dependency (Task 2)
- Produces: CRUD endpoints for elder management, `get_elder_today_status()` helper for dashboard

- [ ] **Step 1: Create community schemas**

```python
# backend/app/schemas/community.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ElderCreate(BaseModel):
    elder_id: UUID
    care_level: str  # A / B / C
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    health_notes: str | None = None
    assigned_worker_id: UUID | None = None


class ElderUpdate(BaseModel):
    care_level: str | None = None
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    health_notes: str | None = None
    assigned_worker_id: UUID | None = None


class ElderResponse(BaseModel):
    id: UUID
    community_id: UUID
    elder_id: UUID
    care_level: str
    address: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    health_notes: str | None
    assigned_worker_id: UUID | None
    created_at: datetime
    updated_at: datetime
    # joined fields (set manually)
    elder_name: str | None = None
    elder_phone: str | None = None
    today_active: bool = False
    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    total_elders: int
    level_a: int
    level_b: int
    level_c: int
    today_active_count: int
    today_active_rate: float
    pending_events: int
    canteen_today: dict | None = None
    heatmap: list[dict] = []
```

- [ ] **Step 2: Create community service**

```python
# backend/app/services/community.py
import uuid
from datetime import datetime, timezone, date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import Community, CommunityWorker, CommunityElder
from app.models.user import User
from app.models.view_event import ViewEvent


async def create_elder_record(
    db: AsyncSession,
    community_id: uuid.UUID,
    data: dict,
) -> CommunityElder:
    elder = CommunityElder(community_id=community_id, **data)
    db.add(elder)
    await db.commit()
    await db.refresh(elder)
    return elder


async def update_elder_record(
    db: AsyncSession,
    elder_record_id: uuid.UUID,
    updates: dict,
) -> CommunityElder:
    stmt = select(CommunityElder).where(CommunityElder.id == elder_record_id)
    result = await db.execute(stmt)
    elder = result.scalar_one_or_none()
    if not elder:
        raise ValueError("老人档案不存在")
    for key, value in updates.items():
        setattr(elder, key, value)
    await db.commit()
    await db.refresh(elder)
    return elder


async def list_elders(
    db: AsyncSession,
    community_id: uuid.UUID,
    care_level: str | None = None,
    search: str | None = None,
) -> list[dict]:
    stmt = (
        select(CommunityElder, User.nickname, User.phone)
        .join(User, CommunityElder.elder_id == User.id)
        .where(CommunityElder.community_id == community_id)
    )
    if care_level:
        stmt = stmt.where(CommunityElder.care_level == care_level)
    if search:
        stmt = stmt.where(User.nickname.ilike(f"%{search}%"))
    stmt = stmt.order_by(CommunityElder.created_at.desc())

    result = await db.execute(stmt)
    rows = result.all()

    # 查询今日活跃状态
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    elder_ids = [row[0].elder_id for row in rows]
    active_stmt = (
        select(ViewEvent.viewer_id)
        .where(ViewEvent.viewer_id.in_(elder_ids))
        .where(ViewEvent.viewed_at >= today_start)
        .distinct()
    )
    active_result = await db.execute(active_stmt)
    active_ids = set(active_result.scalars().all())

    return [
        {
            **row[0].__dict__,
            "elder_name": row[1],
            "elder_phone": row[2],
            "today_active": row[0].elder_id in active_ids,
        }
        for row in rows
    ]


async def get_elder_detail(
    db: AsyncSession,
    elder_record_id: uuid.UUID,
) -> dict | None:
    stmt = (
        select(CommunityElder, User.nickname, User.phone)
        .join(User, CommunityElder.elder_id == User.id)
        .where(CommunityElder.id == elder_record_id)
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if not row:
        return None
    return {**row[0].__dict__, "elder_name": row[1], "elder_phone": row[2]}
```

- [ ] **Step 3: Create community API routes**

```python
# backend/app/api/v1/community.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.deps import get_current_worker
from app.models.community import CommunityWorker
from app.schemas.community import ElderCreate, ElderUpdate, ElderResponse
from app.services import community as community_service

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/elders")
async def list_elders(
    care_level: str | None = None,
    search: str | None = None,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    elders = await community_service.list_elders(
        db, worker.community_id, care_level=care_level, search=search
    )
    return elders


@router.post("/elders", response_model=ElderResponse)
async def create_elder(
    data: ElderCreate,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    elder = await community_service.create_elder_record(
        db, worker.community_id, data.model_dump()
    )
    return elder


@router.put("/elders/{elder_id}", response_model=ElderResponse)
async def update_elder(
    elder_id: UUID,
    data: ElderUpdate,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    try:
        elder = await community_service.update_elder_record(
            db, elder_id, data.model_dump(exclude_unset=True)
        )
        return elder
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/elders/{elder_id}")
async def get_elder(
    elder_id: UUID,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    detail = await community_service.get_elder_detail(db, elder_id)
    if not detail:
        raise HTTPException(status_code=404, detail="老人档案不存在")
    return detail
```

- [ ] **Step 4: Register route**

Add to `backend/app/api/v1/router.py`:

```python
from app.api.v1.community import router as community_router
api_router.include_router(community_router)
```

- [ ] **Step 5: Write integration test**

Test create + list + update elder via API (similar pattern to Task 2 test, using `setup_worker` fixture).

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_community_elders.py -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/community.py backend/app/services/community.py backend/app/api/v1/community.py backend/tests/test_community_elders.py
git commit -m "feat(community): add elder CRUD with A/B/C grading

GET/POST/PUT /community/elders with care_level filter and search.
Today's active status derived from view_events."
```

---

## Task 4: Backend - Canteen Data + LLM Parsing

**Files:**
- Create: `backend/app/utils/llm_parser.py`
- Create: `backend/app/services/canteen.py`
- Create: `backend/app/api/v1/canteen.py`
- Create: `backend/tests/test_canteen.py`

**Interfaces:**
- Consumes: `CanteenRecord` model (Task 1), `CommunityElder` (Task 3), existing Anthropic client in `app/utils/wechat.py` or create new utility
- Produces: `POST /community/canteen/submit` (upload + parse in one call), `GET /community/canteen/records`, `PUT /community/canteen/records/{id}` for manual correction
- Auto-creates `CommunityEvent` for absent A/B elders after parsing

- [ ] **Step 1: Create LLM parser utility**

```python
# backend/app/utils/llm_parser.py
import json
from app.config import settings


async def parse_canteen_text(
    raw_text: str,
    elder_list: list[dict],  # [{"id": "uuid", "name": "张大爷", "care_level": "A"}, ...]
) -> dict:
    """
    调用 LLM 将非结构化食堂文本解析为结构化 JSON。
    失败时返回 {"error": "原因", "fallback": True}。
    """
    if not settings.ANTHROPIC_API_KEY:
        return {"error": "LLM API 未配置", "fallback": True}

    elder_context = "\n".join(
        f"- {e['name']} (id: {e['id']}, {e['care_level']}级)"
        for e in elder_list
    )

    system_prompt = f"""你是社区食堂就餐记录解析助手。
以下是该社区的老人名单：
{elder_context}

请将输入的就餐记录解析为以下 JSON 格式（只返回 JSON，不要其他文字）：
{{
  "date": "YYYY-MM-DD",
  "meal_type": "breakfast|lunch|dinner",
  "attendees": [
    {{"elder_id": "uuid", "elder_name": "姓名", "present": true, "notes": "备注"}}
  ],
  "parse_notes": "解析说明"
}}

规则：
1. present 为 true 表示就餐，false 表示未就餐
2. 如果无法判断，present 设为 null
3. elder_id 必须从名单中匹配，名字模糊匹配
4. 名单外的老人单独列出，elder_id 设为 null"""

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": raw_text}],
        )
        text = response.content[0].text
        # 提取 JSON（LLM 可能包裹在 ```json ... ``` 中）
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
    except Exception as e:
        return {"error": str(e), "fallback": True}
```

- [ ] **Step 2: Add config fields**

Add to `backend/app/config.py`:

```python
ANTHROPIC_API_KEY: str = ""  # 留空则使用离线降级模式
ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"  # 可选自定义 URL
```

- [ ] **Step 3: Create canteen service**

```python
# backend/app/services/canteen.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import openpyxl
import io

from app.models.canteen import CanteenRecord
from app.models.community import CommunityElder
from app.models.user import User
from app.models.community_event import CommunityEvent
from app.utils.llm_parser import parse_canteen_text


async def submit_canteen_record(
    db: AsyncSession,
    community_id: uuid.UUID,
    worker_id: uuid.UUID,
    raw_text: str | None = None,
    excel_bytes: bytes | None = None,
    source_format: str = "text",
) -> CanteenRecord:
    """提交食堂数据并触发 LLM 解析"""
    # 处理 Excel
    if excel_bytes:
        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes), data_only=True)
        lines = []
        for sheet in wb.sheetnames:
            ws = wb[sheet]
            for row in ws.iter_rows(values_only=True):
                lines.append("\t".join(str(c) for c in row if c is not None))
        raw_text = "\n".join(lines)
        source_format = "excel"

    record = CanteenRecord(
        community_id=community_id,
        raw_text=raw_text or "",
        source_format=source_format,
        parse_status="pending",
        recorded_by=worker_id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # 获取老人名单
    stmt = (
        select(CommunityElder, User.nickname)
        .join(User, CommunityElder.elder_id == User.id)
        .where(CommunityElder.community_id == community_id)
    )
    result = await db.execute(stmt)
    elder_rows = result.all()
    elder_list = [
        {"id": str(e.elder_id), "name": name, "care_level": e.care_level}
        for e, name in elder_rows
    ]

    # LLM 解析
    parsed = await parse_canteen_text(raw_text or "", elder_list)

    if parsed.get("fallback"):
        record.parse_status = "failed"
        await db.commit()
        await db.refresh(record)
        return record

    record.parsed_data = parsed
    record.parsed_at = datetime.now(timezone.utc)
    record.parse_status = "success"
    await db.commit()
    await db.refresh(record)

    # 自动生成缺勤事件
    await _generate_absent_events(db, community_id, parsed, elder_list)

    return record


async def _generate_absent_events(
    db: AsyncSession,
    community_id: uuid.UUID,
    parsed: dict,
    elder_list: list[dict],
):
    """为未就餐的 A/B 级老人自动创建事件"""
    care_map = {e["id"]: e["care_level"] for e in elder_list}
    attendees = parsed.get("attendees", [])

    for att in attendees:
        elder_id_str = att.get("elder_id")
        if not elder_id_str or att.get("present") is not False:
            continue

        care_level = care_map.get(elder_id_str, "C")
        severity = "urgent" if care_level == "A" else "warning" if care_level == "B" else "info"

        event = CommunityEvent(
            community_id=community_id,
            elder_id=uuid.UUID(elder_id_str),
            event_type="absent",
            source="canteen",
            description=f"{att.get('elder_name', '未知')} 今日{parsed.get('meal_type', '')}未就餐",
            severity=severity,
        )
        db.add(event)

    await db.commit()
```

- [ ] **Step 4: Create canteen API routes**

```python
# backend/app/api/v1/canteen.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.database import get_db
from app.deps import get_current_worker
from app.models.community import CommunityWorker
from app.models.canteen import CanteenRecord
from app.services.canteen import submit_canteen_record

router = APIRouter(prefix="/community/canteen", tags=["canteen"])


@router.post("/submit")
async def submit_canteen(
    raw_text: str | None = Form(None),
    file: UploadFile | None = File(None),
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    excel_bytes = None
    if file and file.filename.endswith((".xlsx", ".xls")):
        excel_bytes = await file.read()
    elif not raw_text:
        raise HTTPException(status_code=400, detail="请输入文本或上传 Excel 文件")

    record = await submit_canteen_record(
        db,
        worker.community_id,
        worker.id,
        raw_text=raw_text,
        excel_bytes=excel_bytes,
    )
    return {
        "id": str(record.id),
        "parse_status": record.parse_status,
        "parsed_data": record.parsed_data,
    }


@router.get("/records")
async def list_records(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(CanteenRecord)
        .where(CanteenRecord.community_id == worker.community_id)
        .order_by(CanteenRecord.created_at.desc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "raw_text": r.raw_text[:100],
            "source_format": r.source_format,
            "parse_status": r.parse_status,
            "parsed_data": r.parsed_data,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@router.get("/records/{record_id}")
async def get_record(
    record_id: UUID,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CanteenRecord).where(
        CanteenRecord.id == record_id,
        CanteenRecord.community_id == worker.community_id,
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="食堂记录不存在")
    return {
        "id": str(record.id),
        "raw_text": record.raw_text,
        "source_format": record.source_format,
        "parse_status": record.parse_status,
        "parsed_data": record.parsed_data,
        "parsed_at": record.parsed_at.isoformat() if record.parsed_at else None,
        "created_at": record.created_at.isoformat(),
    }


@router.put("/records/{record_id}")
async def correct_record(
    record_id: UUID,
    parsed_data: dict,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CanteenRecord).where(
        CanteenRecord.id == record_id,
        CanteenRecord.community_id == worker.community_id,
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="食堂记录不存在")
    record.parsed_data = parsed_data
    record.parse_status = "success"
    await db.commit()
    await db.refresh(record)
    return {"ok": True}
```

- [ ] **Step 5: Register route + install openpyxl**

```bash
pip install openpyxl
```

Add to `router.py`:

```python
from app.api.v1.canteen import router as canteen_router
api_router.include_router(canteen_router)
```

- [ ] **Step 6: Write test**

Test submit with text → verify parse_status and auto-event creation.

- [ ] **Step 7: Commit**

```bash
git add backend/app/utils/llm_parser.py backend/app/services/canteen.py backend/app/api/v1/canteen.py backend/tests/test_canteen.py backend/requirements.txt
git commit -m "feat(canteen): add canteen data submission with LLM parsing

POST /community/canteen/submit accepts text or Excel, triggers LLM
parsing, auto-creates absent events for A/B level elders."
```

---

## Task 5: Backend - Events + Dashboard

**Files:**
- Create: `backend/app/services/community_event.py`
- Create: `backend/app/api/v1/community_events.py`
- Modify: `backend/app/api/v1/community.py` (add dashboard endpoint)

**Interfaces:**
- Consumes: `CommunityEvent` model (Task 1), `get_current_worker` (Task 2), canteen service auto-creates events (Task 4)
- Produces: `GET /community/events`, `POST /community/events`, `PUT /community/events/{id}/resolve`, `GET /community/dashboard`

- [ ] **Step 1: Create event service**

```python
# backend/app/services/community_event.py
import uuid
from datetime import datetime, timezone, date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_event import CommunityEvent
from app.models.community import CommunityElder, CommunityWorker


async def list_events(
    db: AsyncSession,
    community_id: uuid.UUID,
    severity: str | None = None,
    event_type: str | None = None,
    is_resolved: bool | None = None,
) -> list[CommunityEvent]:
    stmt = select(CommunityEvent).where(CommunityEvent.community_id == community_id)
    if severity:
        stmt = stmt.where(CommunityEvent.severity == severity)
    if event_type:
        stmt = stmt.where(CommunityEvent.event_type == event_type)
    if is_resolved is not None:
        stmt = stmt.where(CommunityEvent.is_resolved == is_resolved)
    stmt = stmt.order_by(CommunityEvent.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_event(
    db: AsyncSession,
    community_id: uuid.UUID,
    data: dict,
) -> CommunityEvent:
    event = CommunityEvent(community_id=community_id, **data)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def resolve_event(
    db: AsyncSession,
    event_id: uuid.UUID,
    worker_id: uuid.UUID,
) -> CommunityEvent:
    stmt = select(CommunityEvent).where(CommunityEvent.id == event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if not event:
        raise ValueError("事件不存在")
    event.is_resolved = True
    event.resolved_by = worker_id
    event.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(event)
    return event


async def get_dashboard_data(
    db: AsyncSession,
    community_id: uuid.UUID,
) -> dict:
    # 分级统计
    stmt = select(
        CommunityElder.care_level,
        func.count(CommunityElder.id),
    ).where(
        CommunityElder.community_id == community_id
    ).group_by(CommunityElder.care_level)
    result = await db.execute(stmt)
    level_counts = {row[0]: row[1] for row in result.all()}

    total = sum(level_counts.values())

    # 今日活跃（view_events 今日有记录的老人数）
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    elder_stmt = select(CommunityElder.elder_id).where(
        CommunityElder.community_id == community_id
    )
    elder_result = await db.execute(elder_stmt)
    elder_ids = elder_result.scalars().all()

    from app.models.view_event import ViewEvent
    active_stmt = select(func.count(func.distinct(ViewEvent.viewer_id))).where(
        ViewEvent.viewer_id.in_(elder_ids),
        ViewEvent.viewed_at >= today_start,
    )
    active_result = await db.execute(active_stmt)
    today_active = active_result.scalar() or 0

    # 待处理事件
    pending_stmt = select(func.count(CommunityEvent.id)).where(
        CommunityEvent.community_id == community_id,
        CommunityEvent.is_resolved == False,
        CommunityEvent.severity.in_(["urgent", "warning"]),
    )
    pending_result = await db.execute(pending_stmt)
    pending_events = pending_result.scalar() or 0

    # 热力图数据
    heatmap = await _build_heatmap(db, community_id, today_start)

    return {
        "total_elders": total,
        "level_a": level_counts.get("A", 0),
        "level_b": level_counts.get("B", 0),
        "level_c": level_counts.get("C", 0),
        "today_active_count": today_active,
        "today_active_rate": round(today_active / total * 100, 1) if total > 0 else 0,
        "pending_events": pending_events,
        "heatmap": heatmap,
    }


async def _build_heatmap(
    db: AsyncSession,
    community_id: uuid.UUID,
    today_start: datetime,
) -> list[dict]:
    """构建热力图数据：按 address 分组，每个老人的今日状态"""
    from app.models.user import User
    from app.models.view_event import ViewEvent

    stmt = (
        select(CommunityElder, User.nickname)
        .join(User, CommunityElder.elder_id == User.id)
        .where(CommunityElder.community_id == community_id)
        .order_by(CommunityElder.address)
    )
    result = await db.execute(stmt)
    elders = result.all()

    elder_ids = [e[0].elder_id for e in elders]
    active_stmt = select(ViewEvent.viewer_id).where(
        ViewEvent.viewer_id.in_(elder_ids),
        ViewEvent.viewed_at >= today_start,
    ).distinct()
    active_result = await db.execute(active_stmt)
    active_ids = set(active_result.scalars().all())

    heatmap = []
    for elder, name in elders:
        heatmap.append({
            "elder_id": str(elder.elder_id),
            "name": name,
            "care_level": elder.care_level,
            "address": elder.address or "未分配",
            "today_active": elder.elder_id in active_ids,
        })
    return heatmap
```

- [ ] **Step 2: Create events API routes**

```python
# backend/app/api/v1/community_events.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_worker
from app.models.community import CommunityWorker
from app.services import community_event as event_service

router = APIRouter(prefix="/community/events", tags=["community-events"])


class EventCreate(BaseModel):
    elder_id: UUID
    event_type: str
    description: str | None = None
    severity: str = "info"


@router.get("")
async def list_events(
    severity: str | None = None,
    event_type: str | None = None,
    is_resolved: bool | None = None,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    events = await event_service.list_events(
        db, worker.community_id,
        severity=severity, event_type=event_type, is_resolved=is_resolved,
    )
    return [
        {
            "id": str(e.id),
            "elder_id": str(e.elder_id),
            "event_type": e.event_type,
            "source": e.source,
            "description": e.description,
            "severity": e.severity,
            "is_resolved": e.is_resolved,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.post("")
async def create_event(
    data: EventCreate,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    event = await event_service.create_event(
        db, worker.community_id,
        {**data.model_dump(), "source": "manual"},
    )
    return {"id": str(event.id)}


@router.put("/{event_id}/resolve")
async def resolve_event(
    event_id: UUID,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    try:
        event = await event_service.resolve_event(db, event_id, worker.id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

- [ ] **Step 3: Add dashboard endpoint to community.py**

Add to `backend/app/api/v1/community.py`:

```python
@router.get("/dashboard")
async def dashboard(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    from app.services import community_event as event_service
    data = await event_service.get_dashboard_data(db, worker.community_id)
    return data
```

- [ ] **Step 4: Register events route**

Add to `router.py`:

```python
from app.api.v1.community_events import router as events_router
api_router.include_router(events_router)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/community_event.py backend/app/api/v1/community_events.py backend/app/api/v1/community.py backend/app/api/v1/router.py
git commit -m "feat(events): add event management + dashboard API

GET/POST /community/events, PUT /events/{id}/resolve,
GET /community/dashboard with level stats, active count,
pending events, and heatmap data."
```

---

## Task 6: H5 Frontend - Project Scaffold + Login

**Files:**
- Create: entire `admin-frontend/` project

**Interfaces:**
- Consumes: all backend APIs from Tasks 2-5
- Produces: running H5 dev server at `http://localhost:5174`

- [ ] **Step 1: Create Vue 3 project**

```bash
cd /Users/yxguo/Desktop/ezlove
npm create vite@latest admin-frontend -- --template vue
cd admin-frontend
npm install
npm install element-plus @element-plus/icons-vue pinia vue-router@4 axios sass
```

- [ ] **Step 2: Configure vite**

```js
// admin-frontend/vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': resolve(__dirname, 'src') }
  },
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      }
    }
  }
})
```

- [ ] **Step 3: Create .env files**

```
# admin-frontend/.env.development
VITE_API_BASE_URL=/api/v1
```

```
# admin-frontend/.env.production
VITE_API_BASE_URL=https://yuxilab.cn/ezlove/api/v1
```

- [ ] **Step 4: Create API layer**

```js
// admin-frontend/src/api/request.js
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
})

request.interceptors.request.use(config => {
  const token = localStorage.getItem('community_access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('community_access_token')
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    } else {
      ElMessage.error(error.response?.data?.detail || '请求失败')
    }
    return Promise.reject(error)
  }
)

export const api = {
  get: (url, params) => request.get(url, { params }),
  post: (url, data) => request.post(url, data),
  put: (url, data) => request.put(url, data),
  delete: (url) => request.delete(url),
}

export default request
```

```js
// admin-frontend/src/api/auth.js
import { api } from './request'

export const login = (phone, password) =>
  api.post('/community/auth/login', { phone, password })
```

```js
// admin-frontend/src/api/community.js
import { api } from './request'

export const getDashboard = () => api.get('/community/dashboard')
export const getElders = (params) => api.get('/community/elders', params)
export const createElder = (data) => api.post('/community/elders', data)
export const updateElder = (id, data) => api.put(`/community/elders/${id}`, data)
export const getElder = (id) => api.get(`/community/elders/${id}`)
```

```js
// admin-frontend/src/api/canteen.js
import { api } from './request'
import request from './request'

export const submitCanteen = (formData) =>
  request.post('/community/canteen/submit', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
export const getCanteenRecords = () => api.get('/community/canteen/records')
export const getCanteenRecord = (id) => api.get(`/community/canteen/records/${id}`)
export const correctCanteenRecord = (id, data) =>
  api.put(`/community/canteen/records/${id}`, data)
```

```js
// admin-frontend/src/api/events.js
import { api } from './request'

export const getEvents = (params) => api.get('/community/events', params)
export const createEvent = (data) => api.post('/community/events', data)
export const resolveEvent = (id) => api.put(`/community/events/${id}/resolve`)
```

- [ ] **Step 5: Create stores**

```js
// admin-frontend/src/stores/user.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi } from '@/api/auth'
import router from '@/router'

export const useUserStore = defineStore('user', () => {
  const worker = ref(JSON.parse(localStorage.getItem('community_worker') || 'null'))
  const token = ref(localStorage.getItem('community_access_token') || '')

  const isLoggedIn = computed(() => !!token.value)

  async function login(phone, password) {
    const data = await loginApi(phone, password)
    token.value = data.access_token
    worker.value = data.worker
    localStorage.setItem('community_access_token', data.access_token)
    localStorage.setItem('community_worker', JSON.stringify(data.worker))
    router.push('/')
  }

  function logout() {
    token.value = ''
    worker.value = null
    localStorage.removeItem('community_access_token')
    localStorage.removeItem('community_worker')
    router.push('/login')
  }

  return { worker, token, isLoggedIn, login, logout }
})
```

- [ ] **Step 6: Create router**

```js
// admin-frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/login/index.vue') },
  {
    path: '/',
    component: () => import('@/views/layout/index.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/index.vue') },
      { path: 'elders', name: 'Elders', component: () => import('@/views/elders/index.vue') },
      { path: 'elders/:id', name: 'ElderDetail', component: () => import('@/views/elders/detail.vue') },
      { path: 'canteen', name: 'Canteen', component: () => import('@/views/canteen/index.vue') },
      { path: 'events', name: 'Events', component: () => import('@/views/events/index.vue') },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('community_access_token')
  if (to.path !== '/login' && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
```

- [ ] **Step 7: Create main.js and App.vue**

```js
// admin-frontend/src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import App from './App.vue'
import router from './router'
import './styles/global.scss'

const app = createApp(App)
app.use(createPinia())
app.use(ElementPlus, { locale: zhCn })
app.use(router)
app.mount('#app')
```

```vue
<!-- admin-frontend/src/App.vue -->
<template>
  <router-view />
</template>
```

- [ ] **Step 8: Create login page**

```vue
<!-- admin-frontend/src/views/login/index.vue -->
<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2 class="login-title">易挂念 · 社区管理</h2>
      <el-form :model="form" @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="form.phone" placeholder="手机号" prefix-icon="Phone" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" prefix-icon="Lock" size="large" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" @click="handleLogin" style="width:100%">
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const loading = ref(false)
const form = reactive({ phone: '', password: '' })

async function handleLogin() {
  if (!form.phone || !form.password) {
    ElMessage.warning('请输入手机号和密码')
    return
  }
  loading.value = true
  try {
    await userStore.login(form.phone, form.password)
  } catch (e) {
    // error handled in request interceptor
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 400px;
  padding: 20px;
}
.login-title {
  text-align: center;
  margin-bottom: 30px;
  color: #303133;
}
</style>
```

- [ ] **Step 9: Create layout with sidebar**

```vue
<!-- admin-frontend/src/views/layout/index.vue -->
<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="layout-aside">
      <div class="logo">易挂念 · 社区</div>
      <el-menu :default-active="route.path" router>
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon>
          <span>看板</span>
        </el-menu-item>
        <el-menu-item index="/elders">
          <el-icon><User /></el-icon>
          <span>老人档案</span>
        </el-menu-item>
        <el-menu-item index="/canteen">
          <el-icon><Food /></el-icon>
          <span>食堂管理</span>
        </el-menu-item>
        <el-menu-item index="/events">
          <el-icon><Bell /></el-icon>
          <span>事件中心</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="layout-header">
        <span>{{ userStore.worker?.name }} · {{ userStore.worker?.role_label }}</span>
        <el-button text @click="userStore.logout()">退出</el-button>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { DataBoard, User, Food, Bell } from '@element-plus/icons-vue'

const route = useRoute()
const userStore = useUserStore()
</script>

<style lang="scss" scoped>
.layout-container { min-height: 100vh; }
.layout-aside {
  background: #304156;
  .logo {
    height: 60px;
    line-height: 60px;
    text-align: center;
    color: #fff;
    font-size: 18px;
    font-weight: bold;
  }
  .el-menu { border-right: none; }
}
.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
}
</style>
```

- [ ] **Step 10: Create styles**

```scss
// admin-frontend/src/styles/variables.scss
$primary-color: #FF8C42;
$bg-color: #f5f7fa;
$sidebar-bg: #304156;
$text-primary: #303133;
$text-regular: #606266;
$level-a: #F56C6C;  // red
$level-b: #E6A23C;  // orange
$level-c: #67C23A;  // green
$severity-urgent: #F56C6C;
$severity-warning: #E6A23C;
$severity-info: #909399;
```

```scss
// admin-frontend/src/styles/global.scss
@use './variables.scss' as *;
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: $bg-color; }
.page-header { margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
```

- [ ] **Step 11: Start dev server and verify**

```bash
cd /Users/yxguo/Desktop/ezlove/admin-frontend
npm run dev
```

Verify: login page renders at `http://localhost:5174/login`.

- [ ] **Step 12: Commit**

```bash
cd /Users/yxguo/Desktop/ezlove
git add admin-frontend/
git commit -m "feat(admin): scaffold H5 admin frontend with Vue3 + Element Plus

Login page, sidebar layout, API layer, stores, router.
Dev server at localhost:5174."
```

---

## Task 7: H5 Frontend - Dashboard Page

**Files:**
- Create: `admin-frontend/src/stores/dashboard.js`
- Create: `admin-frontend/src/views/dashboard/index.vue`

- [ ] **Step 1: Create dashboard store**

```js
// admin-frontend/src/stores/dashboard.js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getDashboard } from '@/api/community'

export const useDashboardStore = defineStore('dashboard', () => {
  const data = ref(null)
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      data.value = await getDashboard()
    } finally {
      loading.value = false
    }
  }

  return { data, loading, load }
})
```

- [ ] **Step 2: Create dashboard page**

包含：统计卡片（总人数/A/B/C/活跃率）、待处理事件列表、今日食堂概览、热力图网格。

```vue
<!-- admin-frontend/src/views/dashboard/index.vue -->
<template>
  <div v-loading="store.loading">
    <div class="page-header">
      <h2>社区看板</h2>
      <el-button @click="store.load()">刷新</el-button>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="4" v-for="stat in stats" :key="stat.label">
        <el-card shadow="hover" class="stat-card" :style="{ borderTop: `3px solid ${stat.color}` }">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 热力图 -->
    <el-card class="section-card">
      <template #header><span>老人活跃热力图</span></template>
      <div class="heatmap">
        <div v-for="group in heatmapGroups" :key="group.address" class="heatmap-group">
          <div class="group-label">{{ group.address }}</div>
          <div class="heatmap-grid">
            <el-tooltip v-for="e in group.elders" :key="e.elder_id"
              :content="`${e.name} (${e.care_level}级) - ${e.today_active ? '今日活跃' : '今日未活跃'}`">
              <div class="heatmap-cell" :class="cellClass(e)">{{ e.name.charAt(0) }}</div>
            </el-tooltip>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'

const store = useDashboardStore()
onMounted(() => store.load())

const stats = computed(() => {
  const d = store.data
  if (!d) return []
  return [
    { label: '总人数', value: d.total_elders, color: '#409EFF' },
    { label: 'A级', value: d.level_a, color: '#F56C6C' },
    { label: 'B级', value: d.level_b, color: '#E6A23C' },
    { label: 'C级', value: d.level_c, color: '#67C23A' },
    { label: '今日活跃', value: d.today_active_count, color: '#409EFF' },
    { label: '活跃率', value: `${d.today_active_rate}%`, color: '#67C23A' },
  ]
})

const heatmapGroups = computed(() => {
  if (!store.data?.heatmap) return []
  const map = {}
  store.data.heatmap.forEach(e => {
    if (!map[e.address]) map[e.address] = []
    map[e.address].push(e)
  })
  return Object.entries(map).map(([address, elders]) => ({ address, elders }))
})

function cellClass(e) {
  if (e.today_active) return 'cell-active'
  if (e.care_level === 'A') return 'cell-urgent'
  return 'cell-inactive'
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;
.stat-row { margin-bottom: 20px; }
.stat-card {
  text-align: center;
  .stat-value { font-size: 28px; font-weight: bold; color: $text-primary; }
  .stat-label { font-size: 14px; color: $text-regular; margin-top: 4px; }
}
.section-card { margin-bottom: 20px; }
.heatmap-group { margin-bottom: 16px; }
.group-label { font-size: 14px; color: $text-regular; margin-bottom: 8px; }
.heatmap-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.heatmap-cell {
  width: 48px; height: 48px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 8px; font-size: 16px; font-weight: bold; color: #fff;
  cursor: pointer;
}
.cell-active { background: #67C23A; }
.cell-inactive { background: #C0C4CC; }
.cell-urgent { background: #F56C6C; }
</style>
```

- [ ] **Step 3: Verify + commit**

```bash
git add admin-frontend/src/stores/dashboard.js admin-frontend/src/views/dashboard/index.vue
git commit -m "feat(admin): add dashboard page with stats cards and heatmap"
```

---

## Task 8: H5 Frontend - Elder Management Pages

**Files:**
- Create: `admin-frontend/src/stores/elders.js`
- Create: `admin-frontend/src/views/elders/index.vue`
- Create: `admin-frontend/src/views/elders/detail.vue`

- [ ] **Step 1: Create elders store**

```js
// admin-frontend/src/stores/elders.js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getElders, createElder, updateElder, getElder } from '@/api/community'

export const useEldersStore = defineStore('elders', () => {
  const elders = ref([])
  const current = ref(null)
  const loading = ref(false)

  async function load(params) {
    loading.value = true
    try {
      elders.value = await getElders(params)
    } finally {
      loading.value = false
    }
  }

  async function loadDetail(id) {
    current.value = await getElder(id)
  }

  async function create(data) {
    await createElder(data)
    await load()
  }

  async function update(id, data) {
    await updateElder(id, data)
    await load()
  }

  return { elders, current, loading, load, loadDetail, create, update }
})
```

- [ ] **Step 2: Create elder list page**

包含：筛选栏（分级下拉 + 搜索框）、表格（姓名/分级/楼栋/网格员/今日状态）、新增按钮、新增弹窗。

- [ ] **Step 3: Create elder detail page**

包含：档案信息卡片、家庭端已读日历（从 family API 获取）、食堂出勤记录、事件时间线。

- [ ] **Step 4: Commit**

```bash
git add admin-frontend/src/stores/elders.js admin-frontend/src/views/elders/
git commit -m "feat(admin): add elder list and detail pages with A/B/C grading"
```

---

## Task 9: H5 Frontend - Canteen Management Page

**Files:**
- Create: `admin-frontend/src/stores/canteen.js`
- Create: `admin-frontend/src/views/canteen/index.vue`

- [ ] **Step 1: Create canteen store**

```js
// admin-frontend/src/stores/canteen.js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { submitCanteen, getCanteenRecords, correctCanteenRecord } from '@/api/canteen'

export const useCanteenStore = defineStore('canteen', () => {
  const records = ref([])
  const loading = ref(false)
  const submitting = ref(false)

  async function load() {
    loading.value = true
    try {
      records.value = await getCanteenRecords()
    } finally {
      loading.value = false
    }
  }

  async function submit(formData) {
    submitting.value = true
    try {
      const result = await submitCanteen(formData)
      await load()
      return result
    } finally {
      submitting.value = false
    }
  }

  async function correct(id, data) {
    await correctCanteenRecord(id, data)
    await load()
  }

  return { records, loading, submitting, load, submit, correct }
})
```

- [ ] **Step 2: Create canteen page**

包含：文本输入区 + Excel 上传按钮、"解析"按钮、解析结果表格（可编辑修正）、历史记录列表。

- [ ] **Step 3: Commit**

```bash
git add admin-frontend/src/stores/canteen.js admin-frontend/src/views/canteen/
git commit -m "feat(admin): add canteen management page with LLM parsing"
```

---

## Task 10: H5 Frontend - Events Center Page

**Files:**
- Create: `admin-frontend/src/stores/events.js`
- Create: `admin-frontend/src/views/events/index.vue`

- [ ] **Step 1: Create events store**

```js
// admin-frontend/src/stores/events.js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getEvents, createEvent, resolveEvent } from '@/api/events'

export const useEventsStore = defineStore('events', () => {
  const events = ref([])
  const loading = ref(false)

  async function load(params) {
    loading.value = true
    try {
      events.value = await getEvents(params)
    } finally {
      loading.value = false
    }
  }

  async function create(data) {
    await createEvent(data)
    await load()
  }

  async function resolve(id) {
    await resolveEvent(id)
    await load()
  }

  return { events, loading, load, create, resolve }
})
```

- [ ] **Step 2: Create events page**

包含：筛选栏（severity/type/is_resolved）、事件列表（severity 颜色标记）、手动新增事件弹窗、标记已处理按钮。

- [ ] **Step 3: Commit**

```bash
git add admin-frontend/src/stores/events.js admin-frontend/src/views/events/
git commit -m "feat(admin): add events center page with filters and resolve"
```

---

## Task 11: Docker Compose Extension + Integration Test

**Files:**
- Modify: `docker-compose.yml`
- Create: `admin-frontend/Dockerfile`
- Create: `admin-frontend/nginx.conf`

- [ ] **Step 1: Create Dockerfile for H5 frontend**

```dockerfile
# admin-frontend/Dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] **Step 2: Create nginx config**

```nginx
# admin-frontend/nginx.conf
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

- [ ] **Step 3: Add to docker-compose.yml**

```yaml
  admin-frontend:
    build: ./admin-frontend
    ports:
      - "5174:80"
    depends_on:
      - backend
    restart: unless-stopped
```

- [ ] **Step 4: End-to-end verification**

1. `docker-compose up --build`
2. Verify login at `http://localhost:5174`
3. Create an elder, submit canteen text, check dashboard, check events
4. All pages render, API calls succeed, data flows correctly

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml admin-frontend/Dockerfile admin-frontend/nginx.conf
git commit -m "feat(deploy): add admin frontend to docker-compose

Nginx container serves Vue build, proxies /api to backend."
```

---

## Task Dependencies

```
Task 1 (DB Migration)
  ├── Task 2 (Auth)
  │     ├── Task 3 (Elders)
  │     │     ├── Task 4 (Canteen + LLM)
  │     │     │     └── Task 5 (Events + Dashboard)
  │     │     │           └── Task 11 (Docker + Integration)
  │     │     │
  │     │     └── Task 8 (Elder Pages) ──┐
  │     │                                 ├── Task 11
  │     └── Task 6 (Scaffold + Login) ────┤
  │           ├── Task 7 (Dashboard) ─────┤
  │           ├── Task 9 (Canteen Page) ──┤
  │           └── Task 10 (Events Page) ──┘
  └────────────────────────────────────────
```

Backend tasks (1-5) are sequential (each depends on the previous).
Frontend tasks (6-10) can start after Task 2 is done (auth is needed for login page).
Tasks 7-10 are independent of each other and can run in parallel after Task 6.
Task 11 requires all other tasks to be complete.
