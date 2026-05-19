"""
app/api/auth.py
────────────────
Xử lý authentication từ JWT header.

Trách nhiệm:
  - Lấy token từ Authorization header
  - Decode payload để extract user_id (KHÔNG verify signature)
  - Lưu vào request context để các layer sau dùng

Tại sao không verify signature ở đây?
  Java backend đã verify rồi — làm lại ở Python là redundant.
  Mục đích duy nhất của decode ở đây là lấy user_id cho logging và rate limiting.
"""

import base64
import json
from typing import Optional

from fastapi import Header

from app.core.context import ctx
from app.core.logging import get_logger

log = get_logger(__name__)


def _decode_user_id(token: str) -> str:
    """
    Decode JWT payload để lấy user_id.
    Trả về "anonymous" nếu token invalid hoặc không có.
    """
    if not token:
        return "anonymous"
    try:
        # Bỏ prefix "Bearer "
        raw = token.removeprefix("Bearer ").strip()

        # JWT gồm 3 phần: header.payload.signature
        parts = raw.split(".")
        if len(parts) != 3:
            return "anonymous"

        # Decode base64url (thêm padding nếu thiếu)
        padding = 4 - len(parts[1]) % 4
        padded  = parts[1] + "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(padded))

        # Thử các field phổ biến
        uid = payload.get("sub") or payload.get("userId") or payload.get("id")
        return str(uid) if uid else "anonymous"

    except Exception:
        return "anonymous"


async def extract_auth(authorization: Optional[str] = Header(None)) -> None:
    """
    FastAPI dependency: tự động chạy trước mỗi endpoint có inject dependency này.

    Lưu token và user_id vào request context.
    Không raise exception — unauthenticated request vẫn được xử lý
    (backend sẽ trả 401 nếu endpoint đó cần auth).
    """
    token   = authorization or ""
    user_id = _decode_user_id(token)

    ctx.set_auth(token)
    ctx.set_user(user_id)

    log.debug("auth.extracted", user_id=user_id, has_token=bool(token))