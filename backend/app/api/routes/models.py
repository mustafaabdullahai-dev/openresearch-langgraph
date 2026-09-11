"""Endpoints that surface local model / runtime status."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_llm_provider
from app.config.settings import settings
from app.schemas.models import ModelStatusResponse
from app.services.llm import LLMProvider, LLMUnavailableError

router = APIRouter(tags=["models"])


@router.get("/api/models/status", response_model=ModelStatusResponse)
async def model_status(
    provider: LLMProvider = Depends(get_llm_provider),
) -> ModelStatusResponse:
    """Report whether the configured model endpoint is reachable."""
    try:
        await provider.check_connection()
    except LLMUnavailableError as exc:
        return ModelStatusResponse(
            provider="hf",
            model=settings.HF_MODEL,
            connected=False,
            message=str(exc),
        )
    return ModelStatusResponse(
        provider="hf",
        model=settings.HF_MODEL,
        connected=True,
        message="Model endpoint is reachable.",
    )
