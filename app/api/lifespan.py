"""
app/api/lifespan.py
────────────────────
Quản lý vòng đời ứng dụng: startup và shutdown.

Mọi resource cần khởi tạo một lần (connections, models...) đều đặt ở đây.
Thứ tự khởi tạo quan trọng — đừng đảo lộn:

  STARTUP:
    1. Logging       — cần thiết để log các bước sau
    2. Gemini config — phải trước khi tạo model
    3. BackendClient — HTTP client pool
    4. AgentService  — inject model + memory

  SHUTDOWN (ngược lại):
    1. BackendClient — đóng HTTP connections
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agent.service             import create_agent_service
from app.core.config               import settings
from app.core.logging              import get_logger, setup_logging
from app.infrastructure.backend_client import backend_client

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ════════════════════════════════════
    # STARTUP
    # ════════════════════════════════════
    setup_logging()
    log.info("app.starting", environment=settings.environment, model=settings.ai_engine)

    # 1. Khởi tạo HTTP client (connection pool)
    await backend_client.start()

    # 2. Khởi tạo AgentService (tạo genai.Client + memory pipeline bên trong factory)
    app.state.agent = create_agent_service()

    log.info("app.ready")
    yield

    # ════════════════════════════════════
    # SHUTDOWN
    # ════════════════════════════════════
    log.info("app.stopping")
    await backend_client.stop()
    log.info("app.stopped")