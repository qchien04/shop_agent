"""
app/core/context.py
────────────────────
Request-scoped context dùng ContextVar — thread-safe, không cần global.

Mỗi request có riêng:
  - trace_id  : ID để trace log xuyên suốt request
  - user_id   : Lấy từ JWT, dùng cho rate limiting và logging
  - auth_token: Raw JWT token, dùng khi gọi backend cần auth

Cách dùng:
  from app.core.context import ctx
  ctx.set_trace("abc123")
  ctx.user_id        # → "user-42"
  ctx.auth_token     # → "Bearer eyJ..."
"""

from contextvars import ContextVar
import structlog

_trace_id:   ContextVar[str] = ContextVar("trace_id",   default="")
_user_id:    ContextVar[str] = ContextVar("user_id",    default="anonymous")
_auth_token: ContextVar[str] = ContextVar("auth_token", default="")


class _RequestContext:
    """Thin wrapper quanh ContextVar để có API gọn hơn."""

    # ── Setters ──────────────────────────────────────────
    def set_trace(self, trace_id: str) -> None:
        _trace_id.set(trace_id)
        # Bind vào structlog để mọi log trong request này đều có trace_id
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

    def set_user(self, user_id: str) -> None:
        _user_id.set(user_id)
        structlog.contextvars.bind_contextvars(user_id=user_id)

    def set_auth(self, token: str) -> None:
        _auth_token.set(token)

    # ── Getters ──────────────────────────────────────────
    @property
    def trace_id(self) -> str:
        return _trace_id.get()

    @property
    def user_id(self) -> str:
        return _user_id.get()

    @property
    def auth_token(self) -> str:
        return _auth_token.get()

    @property
    def auth_headers(self) -> dict[str, str]:
        """Trả về dict header Authorization nếu có token."""
        token = _auth_token.get()
        return {"Authorization": token} if token else {}


# Singleton — import `ctx` ở mọi nơi
ctx = _RequestContext()