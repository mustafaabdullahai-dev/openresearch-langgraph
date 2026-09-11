"""Fact Checker agent: verifies extracted claims against collected evidence."""

from typing import Any

from app.services.llm import LLMProvider

from .prompts import load_prompt
from .schemas import FactCheckItem, FactCheckResult


def _serialize_claims(claims: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, claim in enumerate(claims, start=1):
        lines.append(f"{index}. {claim.get('claim_text', '')}")
        urls = claim.get("source_urls", [])
        if urls:
            lines.append(f"   Evidence URLs: {', '.join(urls)}")
    return "\n".join(lines)


async def fact_check(
    provider: LLMProvider,
    question: str,
    claims: list[dict[str, Any]],
) -> list[FactCheckItem]:
    """Verify a batch of claims against the collected evidence only."""
    user = (
        f"RESEARCH QUESTION:\n{question}\n\n"
        "CLAIMS WITH EVIDENCE:\n"
        f"{_serialize_claims(claims)}"
    )
    result = await provider.generate_structured(
        schema=FactCheckResult,
        system=load_prompt("fact_checker"),
        user=user,
    )
    return result.items
