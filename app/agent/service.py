"""
app/agent/service.py
─────────────────────
AgentService — Sales Advisor AI.

Không xử lý đơn hàng. Tư vấn + dẫn khách đến trang web.
"""

import json
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.agent.llm    import create_llm
from app.agent.tools  import AGENT_TOOLS
from app.agent.prompt import SYSTEM_PROMPT
from app.core.context import ctx
from app.core.logging import get_logger
from app.infrastructure.cache import history_cache

log = get_logger(__name__)


# ── Response Model ────────────────────────────────────────────────────────────

class CtaSchema(BaseModel):
    label: str
    url: str

class AgentResponse(BaseModel):
    message: str
    products: List[Dict[str, Any]] = Field(default_factory=list)
    cta: Optional[CtaSchema] = None
    suggestions: List[str] = Field(default_factory=list)
    note: Optional[str] = None


# ── Service ───────────────────────────────────────────────────────────────────

class AgentService:
    def __init__(self, llm):
        self._llm = llm

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(self._llm, AGENT_TOOLS, prompt)
        self._executor = AgentExecutor(
            agent=agent,
            tools=AGENT_TOOLS,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
        )
        log.info("agent.ready", engine=type(llm).__name__)

    async def chat(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AgentResponse:
        user_id = ctx.user_id

        # Load history từ cache
        cached = await history_cache.get(user_id)
        history = cached if cached is not None else (history or [])

        # Chuyển sang LangChain messages
        lc_history = []
        for turn in history:
            if turn["role"] == "user":
                lc_history.append(HumanMessage(content=turn["content"]))
            else:
                lc_history.append(AIMessage(content=turn["content"]))

        try:
            result = await self._executor.ainvoke({
                "input": question,
                "chat_history": lc_history,
            })
            raw = result.get("output", "")
            response = _parse(raw)

            # Cập nhật và lưu history (tối đa 20 turns)
            history.append({"role": "user",  "content": question})
            history.append({"role": "model", "content": raw})
            await history_cache.set(user_id, history[-20:])

            return response

        except Exception as e:
            log.error("agent.error", error=str(e))
            return AgentResponse(
                message="Xin lỗi, mình đang gặp sự cố kỹ thuật. Bạn thử lại sau nhé! 🙏",
                suggestions=["Tìm sản phẩm", "Xem đơn hàng của tôi", "Kết nối nhân viên"],
            )


# ── Parser ────────────────────────────────────────────────────────────────────

def _parse(text: str) -> AgentResponse:
    """Parse JSON output từ LLM, fallback sang plain text."""
    text = text.strip()

    # Bóc markdown code block
    if "```" in text:
        for block in text.split("```"):
            block = block.removeprefix("json").strip()
            if block.startswith("{"):
                text = block
                break

    try:
        data = json.loads(text)
        cta_raw = data.get("cta")
        cta = CtaSchema(**cta_raw) if isinstance(cta_raw, dict) else None

        return AgentResponse(
            message     = data.get("message", ""),
            products    = data.get("products", []),
            cta         = cta,
            suggestions = data.get("suggestions", []),
            note        = data.get("note"),
        )
    except Exception:
        # Plain text fallback
        return AgentResponse(
            message=text,
            suggestions=["Tìm sản phẩm", "Xem đơn hàng", "Hỗ trợ khác"],
        )


def create_agent_service() -> AgentService:
    return AgentService(llm=create_llm())