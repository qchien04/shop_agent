"""
app/agent/llm.py
─────────────────
Tạo LangChain ChatModel dựa trên AI_ENGINE trong .env.
"""

from langchain_core.language_models.chat_models import BaseChatModel
from app.core.config  import settings
from app.core.logging import get_logger

log = get_logger(__name__)


def create_llm() -> BaseChatModel:
    engine = (settings.ai_engine or "gemini").lower()

    if engine == "groq" and settings.groq_api_key:
        from langchain_groq import ChatGroq
        log.info("llm.using_groq", model=settings.groq_model)
        return ChatGroq(
            groq_api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0.0,
        )

    from langchain_google_genai import ChatGoogleGenerativeAI
    log.info("llm.using_gemini", model=settings.gemini_model)
    return ChatGoogleGenerativeAI(
        google_api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        temperature=0.0,
    )
