"""Chat (follow-up) endpoint grounded in prior research."""

from fastapi import APIRouter, HTTPException

from app.agents.chat import answer_follow_up
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm import LLMUnavailableError, create_provider
from app.services.sessions import repository as sessions

router = APIRouter(tags=["chat"])


@router.post("/api/research/{thread_id}/chat", response_model=ChatResponse)
async def chat_follow_up(thread_id: str, req: ChatRequest) -> ChatResponse:
    session = sessions.get_session(thread_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.get("status") not in ("completed",):
        raise HTTPException(status_code=409, detail="Research is not completed yet.")

    try:
        config = {"configurable": {"thread_id": thread_id}}
        from app.graph import get_research_graph

        state = get_research_graph().get_state(config)
        values = state.values if state else {}
    except Exception:
        values = {}

    provider = create_provider()
    try:
        response = await answer_follow_up(
            provider,
            session["question"],
            values.get("final_report", ""),
            values.get("sources", []),
            req.message,
        )
    except LLMUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail="The model backend is not reachable. Check HF_TOKEN and retry.",
        ) from exc
    return ChatResponse(thread_id=thread_id, message=req.message, response=response)
