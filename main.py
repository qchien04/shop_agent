"""
main.py
────────
Entrypoint duy nhất của ứng dụng.

Chỉ có 2 việc:
  1. Tạo FastAPI app
  2. Chạy uvicorn

Mọi logic đều nằm trong app/ — không đặt gì ở đây.a
"""

import uvicorn
from app.api.app    import create_app
from app.core.config import settings

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host      = "0.0.0.0",
        port      = 8000,
        reload    = settings.environment == "development",
        log_level = "warning",   # structlog tự xử lý log
    )