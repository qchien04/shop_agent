"""
app/core/config.py
──────────────────
Toàn bộ cấu hình ứng dụng đọc từ biến môi trường / file .env.
Chỉ có DUY NHẤT một nơi khai báo config — không scatter khắp codebase.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Gemini AI ─────────────────────────────────────────────
    gemini_api_key: str   = Field(...,              alias="GEMINI_API_KEY")
    gemini_model:   str   = Field("gemini-1.5-flash", alias="GEMINI_MODEL")
    ai_timeout:     float = Field(30.0,             alias="AI_TIMEOUT_SECONDS")

    # ── Groq AI ───────────────────────────────────────────────
    groq_api_key:   str   = Field(None,             alias="GROQ_API_KEY")
    groq_model:     str   = Field("llama-3.3-70b-versatile", alias="GROQ_MODEL")

    # ── AI Engine Selection ──────────────────────────────────
    # "gemini" | "groq"
    ai_engine:      str   = Field("groq",           alias="AI_ENGINE")

    # ── Java Backend ──────────────────────────────────────────
    backend_url:     str   = Field("http://localhost:8080/api/ai/internal", alias="JAVA_BACKEND_URL")
    backend_timeout: float = Field(10.0, alias="BACKEND_TIMEOUT_SECONDS")

    # ── Memory Pipeline ───────────────────────────────────────
    # Khi history dài hơn `summarize_after` turns → kích hoạt summarize
    summarize_after: int = Field(12, alias="SUMMARIZE_AFTER")
    # Số turns GIỮ LẠI (không tóm tắt) để làm sliding window
    history_window:  int = Field(8,  alias="HISTORY_WINDOW")

    # ── In-memory Cache (product search) ─────────────────────
    cache_max_size: int = Field(200, alias="PRODUCT_CACHE_SIZE")
    cache_ttl:      int = Field(300, alias="PRODUCT_CACHE_TTL")   # giây

    # ── Rate Limiting ─────────────────────────────────────────
    rate_limit: str = Field("30/minute", alias="RATE_LIMIT")

    # ── Input Validation ──────────────────────────────────────
    max_question_len:  int = Field(500, alias="MAX_QUESTION_LEN")
    max_history_items: int = Field(40,  alias="MAX_HISTORY_ITEMS")

    # ── Application ───────────────────────────────────────────
    environment: str = Field("production", alias="ENVIRONMENT")
    log_level:   str = Field("INFO",       alias="LOG_LEVEL")

    model_config = {"env_file": ".env", "populate_by_name": True}


# Singleton — import `settings` ở mọi nơi cần dùng
settings = Settings()