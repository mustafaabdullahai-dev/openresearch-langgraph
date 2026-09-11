"""Follow-up chat: answers a user message grounded in prior research."""

from typing import Any

from app.services.llm import LLMProvider

from .prompts import load_prompt


async def answer_follow_up(
    provider: LLMProvider,
    question: str,
    report: str,
    sources: list[dict[str, Any]],
    follow_up: str,
) -> str:
    """Answer a follow-up question using the completed research as context."""
    prompt = load_prompt("follow_up").replace("{question}", question)
    source_lines = "\n".join(
        f"- {s.get('title', 'Untitled')} — {s.get('url', '')}" for s in sources[:10]
    )
    user = (
        f"FINAL REPORT:\n{report}\n\n"
        "SOURCES GATHERED:\n"
        f"{source_lines if source_lines else '(none)'}\n\n"
        f"FOLLOW-UP QUESTION:\n{follow_up}"
    )
    return await provider.generate(
        system=prompt,
        user=user,
    )
