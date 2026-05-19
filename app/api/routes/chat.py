"""
app/api/routes/chat.py
───────────────────────
POST /chat — Sales Advisor AI endpoint.
"""

import time
from fastapi import APIRouter, Depends, Request

from app.agent.service  import AgentService
from app.api.auth       import extract_auth
from app.api.schemas    import ChatRequest, ChatResponse
from app.core.context   import ctx
from app.core.logging   import get_logger

log    = get_logger(__name__)
router = APIRouter()


def _get_agent(request: Request) -> AgentService:
    return request.app.state.agent


@router.post("/chat", response_model=ChatResponse, summary="Tư vấn mua sắm AI")
async def chat(
    request: Request,
    body:    ChatRequest,
    _auth:   None         = Depends(extract_auth),
    agent:   AgentService = Depends(_get_agent),
) -> ChatResponse:
    t0 = time.monotonic()
    log.info("chat.request", user_id=ctx.user_id, q_len=len(body.question))

    history = [{"role": h.role, "content": h.content} for h in body.history]
    result  = await agent.chat(question=body.question, history=history)

    latency = round((time.monotonic() - t0) * 1000)
    log.info("chat.done", latency_ms=latency, has_products=bool(result.products), has_cta=result.cta is not None)

    return ChatResponse(
        message     = result.message,
        products    = result.products,
        cta         = result.cta.model_dump() if result.cta else None,
        suggestions = result.suggestions,
        note        = result.note,
        trace_id    = ctx.trace_id,
        latency_ms  = latency,
    )