"""
app/agent/tools.py
───────────────────
Tools cho Sales Advisor AI.

Chỉ có 2 tools:
- search_products: Tìm sản phẩm để tư vấn
- get_order_status: Cho khách tra cứu đơn hàng

AI KHÔNG đặt hàng thay khách — dẫn khách đến trang web để tự thao tác.
"""

import hashlib
import json
from typing import Any

from langchain_core.tools import tool

from app.core.logging import get_logger
from app.infrastructure.backend_client import backend_client
from app.infrastructure.cache import product_cache

log = get_logger(__name__)


def _json(data: Any) -> str:
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return "Lỗi xử lý dữ liệu."


# ── Tool 1: Tìm kiếm & tư vấn sản phẩm ──────────────────────────────────────

@tool
def search_products(query: str) -> str:
    """
    Tìm kiếm sản phẩm phù hợp với nhu cầu khách hàng.
    Gọi khi khách hỏi về sản phẩm, giá cả, tính năng, so sánh, hoặc gợi ý mua gì.

    Trả về danh sách sản phẩm với productId, tên, giá, ảnh, mô tả và các variants.
    Dùng productId để tạo link /products/{productId} cho khách xem chi tiết.

    Args:
        query: Từ khóa tìm kiếm (tên sản phẩm, loại hàng, nhu cầu, ngân sách...)
    """
    try:
        key = hashlib.md5(query.lower().strip().encode()).hexdigest()
        cached = product_cache.get_sync(key)
        if cached:
            return cached

        data = backend_client.get_sync("/search-products", params={"q": query})
        result = _json(data)
        product_cache.set_sync(key, result)
        return result
    except Exception as e:
        log.error("tool.search_products.error", error=str(e))
        return f"Không thể tìm kiếm sản phẩm lúc này."


# ── Tool 2: Tra cứu đơn hàng ─────────────────────────────────────────────────

@tool
def get_order_status() -> str:
    """
    Tra cứu danh sách và trạng thái đơn hàng của khách.
    Gọi khi khách hỏi "đơn của tôi đâu", "đơn đã giao chưa", "hủy đơn được không".
    Chỉ dùng được khi khách đã đăng nhập.
    """
    try:
        data = backend_client.get_sync("/orders", auth=True)
        if isinstance(data, list):
            # Chỉ lấy tối đa 5 đơn hàng mới nhất để tối ưu token
            data = data[:5]
        return _json(data)
    except Exception as e:
        log.error("tool.get_orders.error", error=str(e))
        return "Không thể tra cứu đơn hàng. Vui lòng đăng nhập và thử lại."


# ── Tool 3: Lấy danh sách địa chỉ ────────────────────────────────────────────

@tool
def get_user_addresses() -> str:
    """
    Lấy danh sách các địa chỉ nhận hàng đã lưu của khách hàng.
    Gọi khi khách hỏi "tôi có địa chỉ nào chưa", "nhà tôi ở đâu", hoặc khi cần tham khảo địa chỉ giao hàng.
    Chỉ dùng được khi khách đã đăng nhập.
    """
    try:
        data = backend_client.get_sync("/addresses", auth=True)
        return _json(data)
    except Exception as e:
        log.error("tool.get_addresses.error", error=str(e))
        return "Không thể lấy danh sách địa chỉ. Vui lòng đăng nhập và thử lại."


# ── Tool 4: Lấy link thanh toán ──────────────────────────────────────────────

@tool
def get_payment_link(orderId: int) -> str:
    """
    Tạo hoặc lấy link thanh toán (VNPAY/PAYOS) cho một đơn hàng cụ thể.
    Gọi khi khách yêu cầu thanh toán hoặc xin link thanh toán cho đơn hàng của họ.

    Args:
        orderId: ID của đơn hàng cần lấy link thanh toán.
    """
    try:
        data = backend_client.get_sync("/payment-link", params={"orderId": orderId}, auth=True)
        if isinstance(data, dict):
            url = data.get("checkoutUrl", "")
            return url or "Không tìm thấy link thanh toán cho đơn hàng này."
        return str(data)
    except Exception as e:
        log.error("tool.get_payment_link.error", error=str(e))
        return f"Lỗi lấy link thanh toán: {e}"


# ── Danh sách tools ───────────────────────────────────────────────────────────

AGENT_TOOLS = [
    search_products,
    get_order_status,
    get_user_addresses,
    get_payment_link,
]