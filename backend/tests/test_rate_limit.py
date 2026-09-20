"""限流中间件独立测试（P4-iter1 评审指令 D3）：直调原始 dispatch 判定逻辑。

conftest 对 RateLimitMiddleware.dispatch 做了类级旁路（RATE_LIMIT_BYPASSED=True），
本模块通过 conftest 保存的原始引用 _ORIGINAL_RATE_LIMIT_DISPATCH 直调生产实现——
不恢复、不触碰类属性旁路态（旁路对其余用例持续生效）。每个用例独立构造中间件
实例（计数器为实例级 defaultdict），天然隔离 60s 窗口的计数残留，无 flaky。

覆盖两条路径（D3 验收）：超限触发 429 + 窗口内未超限放行（另含窗口过期清理回归）。
"""
import time

import pytest
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.main import RateLimitMiddleware
from tests.conftest import _ORIGINAL_RATE_LIMIT_DISPATCH

pytestmark = pytest.mark.asyncio(loop_scope="session")

SENSITIVE_PATH = "/api/v1/auth/dev-login"  # 含 "/auth/" → 敏感路径（sensitive_limit=10）
GENERAL_PATH = "/api/v1/moments"  # 非敏感路径（general_limit=100）


def _make_request(path: str) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": ("10.0.0.1", 12345),
        "scheme": "http",
        "server": ("testserver", 80),
        "http_version": "1.1",
    }
    return Request(scope)


def _new_middleware() -> RateLimitMiddleware:
    # app 参数仅占位（BaseHTTPMiddleware.__init__ 只存 self.app，直调 dispatch 不经过）
    return RateLimitMiddleware(app=PlainTextResponse("dummy"))


class _CallNext:
    """记录放行次数的 call_next 桩——放行路径每次调用返回 200。"""

    def __init__(self):
        self.count = 0

    async def __call__(self, request):
        self.count += 1
        return PlainTextResponse("ok")


async def test_sensitive_path_over_limit_returns_429():
    """/auth/ 敏感路径默认 10 次/60s：前 10 次放行，第 11 次触发 429 且不再放行。"""
    mw = _new_middleware()
    call_next = _CallNext()
    for _ in range(10):
        resp = await _ORIGINAL_RATE_LIMIT_DISPATCH(mw, _make_request(SENSITIVE_PATH), call_next)
        assert resp.status_code == 200
    assert call_next.count == 10

    resp11 = await _ORIGINAL_RATE_LIMIT_DISPATCH(mw, _make_request(SENSITIVE_PATH), call_next)
    assert resp11.status_code == 429
    assert "请求过于频繁" in resp11.body.decode()  # 与 main.py 生产文案一致
    assert call_next.count == 10  # 第 11 次被拦截，未到达 call_next


async def test_general_path_under_limit_passes():
    """非敏感路径默认 100 次/60s：窗口内 50 次连续请求全部放行（未超限路径）。"""
    mw = _new_middleware()
    call_next = _CallNext()
    for _ in range(50):
        resp = await _ORIGINAL_RATE_LIMIT_DISPATCH(mw, _make_request(GENERAL_PATH), call_next)
        assert resp.status_code == 200
    assert call_next.count == 50


async def test_window_expiry_cleans_stale_counts():
    """窗口过期清理：60s 前的过期计数在下一请求时被清除并恢复放行（滑动窗口回归）。"""
    mw = _new_middleware()
    call_next = _CallNext()
    # 预置 10 条已过期（61s 前）的敏感路径计数——模拟上一窗口已打满
    mw._sensitive_requests["10.0.0.1"] = [time.time() - 61] * 10

    resp = await _ORIGINAL_RATE_LIMIT_DISPATCH(mw, _make_request(SENSITIVE_PATH), call_next)
    assert resp.status_code == 200  # 过期计数不阻断
    assert call_next.count == 1
    # 旧记录已被清理，窗口内仅剩本次请求的 1 条记录
    assert len(mw._sensitive_requests["10.0.0.1"]) == 1
