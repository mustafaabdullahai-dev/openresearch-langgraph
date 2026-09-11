"""Research Planner agent: converts analysis into an executable plan."""

from app.services.llm import LLMProvider

from .prompts import load_prompt
from .schemas import QueryAnalysis, ResearchPlan


async def create_research_plan(
    provider: LLMProvider,
    question: str,
    analysis: QueryAnalysis,
) -> ResearchPlan:
    """Produce search queries and coverage requirements from the analysis."""
    user = (
        f"RESEARCH QUESTION:\n{question}\n\n"
        f"RESEARCH GOAL:\n{analysis.research_goal}\n\n"
        f"RESEARCH TYPE:\n{analysis.research_type}\n\n"
        f"ENTITIES:\n{', '.join(analysis.entities)}\n\n"
        f"SUB-QUESTIONS:\n{'. '.join(analysis.sub_questions)}"
    )
    return await provider.generate_structured(
        schema=ResearchPlan,
        system=load_prompt("research_planner"),
        user=user,
    )
