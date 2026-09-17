import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from jose import jwt, JWTError
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.api.v1.router import api_router

access_logger = logging.getLogger("ezlove.access")
logger = logging.getLogger("ezlove")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.DEBUG and not settings.JWT_SECRET:
        raise RuntimeError("JWT_SECRET must be set in production (DEBUG=False)")
    # SQLite 模式：自动建表（开发演示用，生产环境应使用 Alembic 迁移）
    if settings.DATABASE_URL.startswith("sqlite"):
        from app.database import engine, Base
        import app.models  # noqa: F401 确保所有模型注册
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    from app.tasks.alert_checker import start_scheduler
    start_scheduler()
    yield
    from app.tasks.alert_checker import shutdown_scheduler
    shutdown_scheduler()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        user_id = self._extract_user_id(request)
        access_logger.info(
            "%s %s %d uid=%s %.1fms",
            request.method, request.url.path, response.status_code,
            user_id or "-", duration_ms,
        )
        return response

    @staticmethod
    def _extract_user_id(request: Request) -> str | None:
        auth = request.headers.get("authorization")
        if not auth or not auth.lower().startswith("bearer "):
            return None
        try:
            payload = jwt.decode(auth[7:], settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM], options={"verify_exp": False})
            return payload.get("sub")
        except JWTError:
            return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于滑动窗口的简易速率限制器（内存存储）"""

    def __init__(self, app, general_limit: int = 100, sensitive_limit: int = 10, window: int = 60):
        super().__init__(app)
        self.general_limit = general_limit
        self.sensitive_limit = sensitive_limit
        self.window = window  # 秒
        # 存储结构：{ip: [(timestamp, ...), ...]}
        self._general_requests: dict[str, list[float]] = defaultdict(list)
        self._sensitive_requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - self.window

        path = request.url.path
        is_sensitive = "/auth/" in path or "/ai/" in path

        store = self._sensitive_requests if is_sensitive else self._general_requests
        limit = self.sensitive_limit if is_sensitive else self.general_limit

        # 清除过期记录
        timestamps = store[client_ip]
        store[client_ip] = [t for t in timestamps if t > cutoff]

        if len(store[client_ip]) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后再试"},
            )

        store[client_ip].append(now)
        return await call_next(request)


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请稍后再试"})


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AccessLogMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else settings.CORS_ORIGINS,
    allow_credentials=False if settings.DEBUG else True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"] if settings.DEBUG else ["Authorization", "Content-Type"],
)

app.include_router(api_router, prefix="/api/v1")

static_dir = Path(__file__).resolve().parents[1] / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


_start_time = time.time()


@app.get("/health")
async def health_check():
    uptime_s = int(time.time() - _start_time)
    h, rem = divmod(uptime_s, 3600)
    m, s = divmod(rem, 60)
    return {
        "status": "ok",
        "version": "1.0.0",
        "uptime": f"{h}h{m}m{s}s",
        "features": {
            "ai": bool(settings.ANTHROPIC_API_KEY),
            "wechat": bool(settings.WECHAT_APP_ID),
        },
    }
