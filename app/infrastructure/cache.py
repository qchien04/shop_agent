"""
app/infrastructure/cache.py
────────────────────────────
In-memory LRU Cache với TTL.

Tại sao không dùng Redis?
  Scale < 100 req/phút → Redis là overkill.
  LRU in-process đủ dùng, không thêm external dependency.

Chỉ cache product search — đây là dữ liệu:
   Đọc nhiều, ghi ít
   Chấp nhận stale tối đa 5 phút
  ❌ KHÔNG cache orders/addresses (cần real-time)
"""

import asyncio
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Optional

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class _Entry:
    value:      Any
    expires_at: float


class LRUCache:
    """
    Async-safe LRU Cache với TTL.

    - LRU eviction khi đầy (xóa entry ít dùng nhất)
    - TTL eviction khi hết hạn (xóa khi đọc)
    - asyncio.Lock bảo vệ concurrent writes
    """

    def __init__(self, max_size: int, ttl_seconds: int):
        self._store:    OrderedDict[str, _Entry] = OrderedDict()
        self._max_size: int   = max_size
        self._ttl:      int   = ttl_seconds
        self._lock:     asyncio.Lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[key]
                log.debug("cache.expired", key=key)
                return None
            self._store.move_to_end(key)   # đánh dấu "mới dùng"
            log.debug("cache.hit", key=key)
            return entry.value

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._set_internal(key, value)

    def get_sync(self, key: str) -> Optional[Any]:
        """Bản sync dùng cho Tools (không lock, an toàn trong thread riêng)."""
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return entry.value

    def set_sync(self, key: str, value: Any) -> None:
        """Bản sync dùng cho Tools."""
        self._set_internal(key, value)

    def _set_internal(self, key: str, value: Any) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = _Entry(
            value      = value,
            expires_at = time.monotonic() + self._ttl,
        )
        if len(self._store) > self._max_size:
            evicted, _ = self._store.popitem(last=False)
            log.debug("cache.evicted", key=evicted)

    def stats(self) -> dict:
        return {
            "size":     len(self._store),
            "max_size": self._max_size,
            "ttl":      self._ttl,
        }


# Singleton — dùng cho product search
product_cache = LRUCache(
    max_size    = settings.cache_max_size,
    ttl_seconds = settings.cache_ttl,
)

# Singleton — dùng cho history hội thoại (lưu theo userId)
# Max 1000 session, mỗi session 1 tiếng (3600s)
history_cache = LRUCache(
    max_size    = 1000,
    ttl_seconds = 3600,
)