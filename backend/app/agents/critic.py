"""Research Critic agent: decides whether the evidence base is sufficient."""

from typing import Any

from app.services.llm import LLMProvider

from .prompts import load_prompt
from .schemas import ResearchEvaluation
from .utils import numbered


async def evaluate_research(
    provider: LLMProvider,
    question: str,
    sub_questions: list[str],
    sources: list[dict[str, Any]],
    gaps: list[str],
    contradictions: list[dict[str, Any]],
    iteration: int,
    max_iterations: int,
) -> ResearchEvaluation:
    """Ask the critic whether more research is needed."""
    source_lines = "\n".join(
        f"- {s.get('title', 'Untitled')} ({s.get('domain', s.get('url', ''))})"
        for s in sources
    )
    contradiction_lines = "\n".join(
        f"- {c.get('description', c.get('claim', ''))}" for c in contradictions
    )
    user = (
        f"RESEARCH QUESTION:\n{question}\n\n"
        f"SUB-QUESTIONS:\n{numbered(sub_questions)}\n\n"
        "COLLECTED SOURCES:\n"
        f"{source_lines or '(none yet)'}\n\n"
        "KNOWN GAPS:\n"
        f"{numbered(gaps) if gaps else '(none reported)'}\n\n"
        "CONTRADICTIONS:\n"
        f"{contradiction_lines or '(none detected)'}\n\n"
        f"RESEARCH ITERATION: {iteration} of {max_iterations}"
    )
    return await provider.generate_structured(
        schema=ResearchEvaluation,
        system=load_prompt("critic"),
        user=user,
    )
