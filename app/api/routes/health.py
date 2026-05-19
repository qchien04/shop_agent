"""
app/api/routes/health.py
─────────────────────────
GET /health — kiểm tra trạng thái các thành phần hệ thống.

Dùng để:
  - Load balancer / Docker healthcheck
  - Monitoring (Prometheus, Grafana, Uptime Robot...)
  - Debug nhanh khi có sự cố

Trả về HTTP 200 nếu healthy, 503 nếu degraded.
"""

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config             import settings
from app.infrastructure.cache           import product_cache
from app.infrastructure.backend_client  import backend_client

router = APIRouter()


@router.get(
    "/health",
    summary     = "Kiểm tra trạng thái hệ thống",
    description = "Trả về trạng thái của backend và cache.",
)
async def health() -> JSONResponse:
    checks: dict = {}

    # Kiểm tra Java backend
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{settings.backend_url}/health")
            checks["java_backend"] = "ok" if r.status_code == 200 else f"http_{r.status_code}"
    except Exception:
        checks["java_backend"] = "unreachable"



    # Cache stats
    checks["product_cache"] = product_cache.stats()

    is_healthy = checks["java_backend"] == "ok"
    return JSONResponse(
        status_code = 200 if is_healthy else 503,
        content     = {
            "status":  "healthy" if is_healthy else "degraded",
            "version": "3.0.0",
            "checks":  checks,
        },
    )