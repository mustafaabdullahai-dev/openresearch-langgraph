"""Query Analyst agent: understands intent and produces sub-questions."""

from app.services.llm import LLMProvider

from .prompts import load_prompt
from .schemas import QueryAnalysis


async def analyze_query(provider: LLMProvider, question: str) -> QueryAnalysis:
    """Break the user's question into a goal and focused sub-questions."""
    return await provider.generate_structured(
        schema=QueryAnalysis,
        system=load_prompt("query_analyzer"),
        user=f"USER QUESTION:\n{question}",
    )
