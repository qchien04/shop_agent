"""
app/api/schemas.py
───────────────────
Pydantic schemas cho API layer.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator
from app.core.config import settings


# ── Request ───────────────────────────────────────────────────────────────────

class HistoryItem(BaseModel):
    role:    str = Field(..., pattern="^(user|model|assistant)$")
    content: str = Field(..., min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    question: str               = Field(..., min_length=1, max_length=500)
    history:  list[HistoryItem] = Field(default_factory=list)

    @field_validator("question")
    @classmethod
    def clean_question(cls, v: str) -> str:
        return " ".join(v.split())

    @field_validator("history")
    @classmethod
    def cap_history(cls, v: list[HistoryItem]) -> list[HistoryItem]:
        return v[-settings.max_history_items:]


# ── Response ──────────────────────────────────────────────────────────────────

class VariantSchema(BaseModel):
    variantId: int
    name:      str
    price:     float = 0.0
    stock:     int   = 0


class ProductSchema(BaseModel):
    productId:     int
    productName:   str
    price:         float
    originalPrice: float = 0.0
    imageUrl:      str   = ""
    description:   str   = ""
    variants:      list[VariantSchema] = []


class CtaSchema(BaseModel):
    label: str
    url:   str


class ChatResponse(BaseModel):
    """Response trả về cho FE."""
    message:     str
    products:    list[dict]    = []
    cta:         Optional[dict] = None          # { label, url }
    suggestions: list[str]    = []              # Quick reply buttons
    note:        Optional[str] = None
    trace_id:    str = ""
    latency_ms:  int = 0