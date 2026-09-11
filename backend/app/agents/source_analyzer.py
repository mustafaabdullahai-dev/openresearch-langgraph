"""Source Analyzer agent: extracts facts from a single untrusted web source."""

from typing import Any

from app.services.llm import LLMProvider

from .prompts import load_prompt
from .schemas import SourceSummary
from .utils import clip


async def analyze_source(
    provider: LLMProvider,
    question: str,
    source: dict[str, Any],
) -> SourceSummary:
    """Summarize one source's key facts with respect to the question."""
    content = source.get("content") or source.get("snippet") or ""
    user = (
        f"RESEARCH QUESTION:\n{question}\n\n"
        f"SOURCE URL:\n{source.get('url', '')}\n\n"
        f"SOURCE TITLE:\n{source.get('title', '')}\n\n"
        "[EXTERNAL SOURCE CONTENT]\n"
        f"{clip(content)}\n"
        "[/EXTERNAL SOURCE CONTENT]"
    )
    return await provider.generate_structured(
        schema=SourceSummary,
        system=load_prompt("source_analyzer"),
        user=user,
    )
