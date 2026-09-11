"""Report Reviewer agent: gates the draft before delivery."""

from typing import Any

from app.services.llm import LLMProvider

from .prompts import load_prompt
from .schemas import ReportReview
from .utils import clip


async def review_report(
    provider: LLMProvider,
    question: str,
    draft_report: str,
    contradictions: list[dict[str, Any]],
) -> ReportReview:
    """Evaluate whether the draft report can be delivered."""
    contradiction_lines = "\n".join(
        f"- {c.get('description', c.get('claim', ''))}" for c in contradictions
    )
    user = (
        f"RESEARCH QUESTION:\n{question}\n\n"
        "KNOWN CONTRADICTIONS DETECTED DURING FACT CHECKING:\n"
        f"{contradiction_lines or '(none)'}\n\n"
        "DRAFT REPORT:\n"
        "--------------\n"
        f"{clip(draft_report, 3000)}"
    )
    return await provider.generate_structured(
        schema=ReportReview,
        system=load_prompt("reviewer"),
        user=user,
    )
