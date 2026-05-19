"""
app/api/middleware.py
──────────────────────
HTTP Middleware chạy cho MỌI request.

Thứ tự chạy:
  request → [middleware] → endpoint → [middleware] → response

Nhiệm vụ:
  1. Tạo/đọc trace_id từ header X-Trace-Id
  2. Lưu trace_id vào request context (để log + response)
  3. Đo thời gian xử lý
  4. Log mỗi request sau khi hoàn thành
"""

import time
import uuid

import structlog
from fastapi import Request

from app.core.context import ctx
from app.core.logging import get_logger

log = get_logger(__name__)


async def trace_middleware(request: Request, call_next):
    """
    Middleware inject trace_id và log timing cho mỗi HTTP request.

    - Nếu client gửi X-Trace-Id → dùng luôn (để correlate với client log)
    - Nếu không → tự sinh UUID ngắn
    """
    trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex[:8]
    ctx.set_trace(trace_id)

    t0       = time.monotonic()
    response = await call_next(request)
    elapsed  = round((time.monotonic() - t0) * 1000)

    log.info(
        "http.request",
        method     = request.method,
        path       = request.url.path,
        status     = response.status_code,
        elapsed_ms = elapsed,
    )

    # Echo trace_id về client để debug
    response.headers["X-Trace-Id"] = trace_id
    return response