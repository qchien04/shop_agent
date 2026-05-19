"""
app/api/app.py
───────────────
Factory function tạo FastAPI app.

Dùng pattern factory (không dùng module-level singleton) để:
  - Dễ test: tạo app với config khác nhau cho từng test
  - Tránh side-effect khi import
  - Tách biệt cấu hình với khởi tạo

Cách dùng:
  # main.py
  from app.api.app import create_app
  app = create_app()
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.lifespan        import lifespan
from app.api.middleware      import trace_middleware
from app.api.routes          import chat_router, health_router
from app.core.config         import settings
from app.core.context        import ctx


# ── Rate limit key: theo user_id nếu đã login, fallback IP ──

def _rate_limit_key(request: Request) -> str:
    uid = ctx.user_id
    return f"uid:{uid}" if uid != "anonymous" else get_remote_address(request)


def create_app() -> FastAPI:
    app = FastAPI(
        title       = "Shop Agent API",
        version     = "3.0.0",
        description = "AI-powered shopping assistant backend",
        lifespan    = lifespan,
        # Chỉ bật docs ở môi trường không phải production
        docs_url    = "/docs"  if settings.environment != "production" else None,
        redoc_url   = "/redoc" if settings.environment != "production" else None,
    )

    # ── Middleware ────────────────────────────────────────
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins     = ["*"],   # ← thay bằng domain cụ thể trên production
        allow_credentials = True,
        allow_methods     = ["GET", "POST"],
        allow_headers     = ["*"],
    )
    # Trace + timing
    app.middleware("http")(trace_middleware)

    # ── Rate Limiting ─────────────────────────────────────
    limiter = Limiter(key_func=_rate_limit_key, default_limits=[settings.rate_limit])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Routes ────────────────────────────────────────────
    app.include_router(chat_router)
    app.include_router(health_router)

    return app