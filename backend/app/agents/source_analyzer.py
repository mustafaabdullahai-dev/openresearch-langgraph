"""Source Analyzer agent: extracts facts from untrusted web sources.

Provides both single-source and batched analysis. The batched variant is the
default path for the research graph so that N sources cost exactly ONE LLM
call instead of N (which is important on low-quota inference endpoints).
"""

from typing import Any

from app.services.llm import LLMProvider

from .prompts import load_prompt
from .schemas import SourceSummary, SourceSummaryList
from .utils import clip


async def analyze_source(
    provider: LLMProvider,
    question: str,
    source: dict[str, Any],
) -> SourceSummary:
    """Summarize a single source's key facts with respect to the question."""
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


async def analyze_sources_batch(
    provider: LLMProvider,
    question: str,
    sources: list[dict[str, Any]],
) -> list[SourceSummary]:
    """Analyze many sources in a single LLM call (1 call total)."""
    if not sources:
        return []
    blocks: list[str] = []
    for index, source in enumerate(sources, start=1):
        content = source.get("content") or source.get("snippet") or ""
        blocks.append(
            f"SOURCE {index}\n"
            f"- URL: {source.get('url', '')}\n"
            f"- TITLE: {source.get('title', '')}\n"
            "[EXTERNAL SOURCE CONTENT]\n"
            f"{clip(content, 1500)}\n"
            "[/EXTERNAL SOURCE CONTENT]"
        )
    user = f"RESEARCH QUESTION:\n{question}\n\nSOURCES TO ANALYZE:\n\n" + "\n\n".join(
        blocks
    )
    result = await provider.generate_structured(
        schema=SourceSummaryList,
        system=load_prompt("source_analyzer_batch"),
        user=user,
    )
    paired: list[SourceSummary] = []
    for source, parsed in zip(sources, result.summaries, strict=False):
        if parsed.source_url == source.get("url", ""):
            paired.append(parsed)
        else:
            paired.append(
                parsed.model_copy(update={"source_url": source.get("url", "")})
            )
    return paired
