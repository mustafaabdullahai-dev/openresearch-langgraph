"""Report Writer agent: turns the evidence base into a cited Markdown report."""

from typing import Any

from app.services.llm import LLMProvider

from .prompts import load_prompt
from .utils import numbered


def _evidence_pack(sources: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, source in enumerate(sources, start=1):
        excerpt = (
            source.get("key_facts")
            or source.get("snippet")
            or source.get("content")
            or ""
        )
        if isinstance(excerpt, list):
            excerpt = "\n".join(f"  - {item}" for item in excerpt[:6])
        lines.append(
            f"[S{index}] {source.get('title', 'Untitled')} | "
            f"{source.get('url', '')} | domain: {source.get('domain', '')}\n"
            f"    Excerpt: {excerpt}"
        )
    return "\n\n".join(lines)


def _fact_check_summary(fact_checks: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"- {fc.get('claim', '')} [{fc.get('status', 'unknown')}] "
        f"(confidence {fc.get('confidence', 0):.2f})"
        for fc in fact_checks
    )


async def write_report(
    provider: LLMProvider,
    question: str,
    sub_questions: list[str],
    sources: list[dict[str, Any]],
    fact_checks: list[dict[str, Any]],
    revision_feedback: str | None = None,
    previous_draft: str | None = None,
) -> str:
    """Generate the draft report grounded strictly in the evidence pack.

    When ``revision_feedback`` is provided, the model revises ``previous_draft``
    to address the reviewer findings. Feedback and draft are input only — they
    never become part of the returned report.
    """
    user = (
        f"RESEARCH QUESTION:\n{question}\n\n"
        f"SUB-QUESTIONS:\n{numbered(sub_questions)}\n\n"
        "EVIDENCE PACK (plain text)\n"
        "=======================\n"
        f"{_evidence_pack(sources)}\n\n"
        "FACT CHECK RESULTS\n"
        "==================\n"
        f"{_fact_check_summary(fact_checks)}"
    )
    if revision_feedback:
        user = (
            f"{user}\n\n--- REVISION REQUEST FROM REVIEWER ---\n"
            f"REVIEWER FEEDBACK:\n{revision_feedback}\n\n"
            f"PREVIOUS DRAFT:\n{previous_draft or '(no previous draft)'}"
        )
    return await provider.generate(
        system=load_prompt("report_writer"),
        user=user,
    )
