"""
app/infrastructure/backend_client.py
──────────────────────────────────────
HTTP client giao tiếp với Java backend.

Tính năng:
  - Async (httpx) — không block event loop
  - Connection pooling — tái sử dụng TCP connection
  - Retry tự động — 3 lần, exponential backoff, chỉ retry network errors
  - Auth header — tự lấy từ request context

Lifecycle:
  - Gọi start() khi app khởi động
  - Gọi stop() khi app tắt
  (Được quản lý bởi app/api/lifespan.py)
"""

from typing import Any, Optional

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from fastapi import HTTPException

from app.core.config  import settings
from app.core.context import ctx
from app.core.logging import get_logger


log = get_logger(__name__)


class BackendClient:
    """
    Async HTTP client với retry.

    Singleton — khởi tạo 1 lần lúc app start, dùng xuyên suốt.
    """

    def __init__(self):
        self._client:      Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client]      = None

    # ── Lifecycle ─────────────────────────────────────────

    async def start(self) -> None:
        # Client cho các request từ Agent (async)
        base_url = settings.backend_url
        if not base_url.endswith("/"):
            base_url += "/"
            
        self._client = httpx.AsyncClient(
            base_url = base_url,
            timeout  = settings.backend_timeout,
            limits   = httpx.Limits(
                max_connections           = 10,
                max_keepalive_connections  = 5,
            ),
        )
        # Client cho các Tool (Gemini SDK yêu cầu sync function)
        self._sync_client = httpx.Client(
            base_url = base_url,
            timeout  = settings.backend_timeout,
        )
        log.info("backend_client.started", url=base_url)

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
        if self._sync_client:
            self._sync_client.close()
        log.info("backend_client.stopped")

    # ── Internal ──────────────────────────────────────────

    def _assert_ready(self) -> None:
        if self._client is None or self._sync_client is None:
            raise RuntimeError("BackendClient chưa được khởi tạo — gọi start() trước.")

    async def _get_with_retry(
        self,
        path:    str,
        params:  Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> httpx.Response:
        """
        Gửi GET request, tự retry khi gặp lỗi network.

        Chỉ retry: ConnectError, TimeoutException (lỗi hạ tầng)
        KHÔNG retry: HTTP 4xx, 5xx (lỗi logic — retry vô nghĩa)
        """
        async for attempt in AsyncRetrying(
            stop    = stop_after_attempt(3),
            wait    = wait_exponential(multiplier=0.5, min=0.5, max=4.0),
            retry   = retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
            reraise = True,
        ):
            with attempt:
                response = await self._client.get(path, params=params, headers=headers)
                response.raise_for_status()
                return response

    # ── Public API ────────────────────────────────────────

    async def get(
        self,
        path:   str,
        params: Optional[dict] = None,
        auth:   bool = False,
    ) -> Any:
        """
        GET endpoint Java backend (Async).

        Args:
          path   : Đường dẫn relative (vd: "/search-products")
          params : Query parameters
          auth   : True → đính kèm JWT từ request context

        Returns:
          dict nếu response là JSON, str nếu là plain text
        """
        self._assert_ready()
        path = path.lstrip("/")
        headers = ctx.auth_headers if auth else {}

        try:
            response = await self._get_with_retry(path, params=params, headers=headers)
            try:
                return response.json()
            except Exception:
                return response.text
        except RetryError:
            log.error("backend_client.retry_exhausted", path=path)
            raise HTTPException(status_code=502, detail="Backend không phản hồi sau nhiều lần thử.")
        except httpx.HTTPStatusError as e:
            log.error("backend_client.http_error", path=path, status=e.response.status_code)
            raise HTTPException(status_code=502, detail=f"Lỗi từ backend: HTTP {e.response.status_code}.")

    def get_sync(
        self,
        path:   str,
        params: Optional[dict] = None,
        auth:   bool = False,
    ) -> Any:
        """GET endpoint Java backend (Sync) — dùng cho Tools."""
        self._assert_ready()
        path = path.lstrip("/")
        headers = ctx.auth_headers if auth else {}
        
        try:
            response = self._sync_client.get(path, params=params, headers=headers)
            response.raise_for_status()
            try: return response.json()
            except: return response.text
        except Exception as e:
            log.error("backend_client.sync_get_error", path=path, error=str(e))
            raise RuntimeError(f"Lỗi kết nối backend: {str(e)}")

    def post_sync(
        self,
        path:   str,
        data:   Optional[dict] = None,
        auth:   bool = False,
    ) -> Any:
        self._assert_ready()
        path = path.lstrip("/")
        headers = ctx.auth_headers if auth else {}
        try:
            response = self._sync_client.post(path, json=data, headers=headers)
            response.raise_for_status()
            try: return response.json()
            except: return response.text
        except Exception as e:
            log.error("backend_client.sync_post_error", path=path, error=str(e))
            raise RuntimeError(f"Lỗi kết nối backend: {str(e)}")

    async def post(
        self,
        path:   str,
        data:   Optional[dict] = None,
        auth:   bool = False,
    ) -> Any:
        """
        POST endpoint Java backend (Async).

        Args:
          path : Đường dẫn relative (vd: "/orders")
          data : JSON body
          auth : True → đính kèm JWT từ request context

        Returns:
          dict nếu response là JSON, str nếu là plain text
        """
        self._assert_ready()
        path = path.lstrip("/")
        headers = ctx.auth_headers if auth else {}

        try:
            # Không retry POST vì có thể gây duplicate
            response = await self._client.post(path, json=data, headers=headers)
            response.raise_for_status()
            try:
                return response.json()
            except Exception:
                return response.text
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            log.error("backend_client.network_error", path=path, error=str(e))
            raise HTTPException(status_code=502, detail="Backend không phản hồi.")
        except httpx.HTTPStatusError as e:
            log.error("backend_client.http_error", path=path, status=e.response.status_code)
            raise HTTPException(status_code=502, detail=f"Lỗi từ backend: HTTP {e.response.status_code}.")




# Singleton
backend_client = BackendClient()