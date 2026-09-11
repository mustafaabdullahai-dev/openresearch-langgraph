"""Pydantic schemas used for structured LLM output and agent input packing.

Structured output keeps agents honest: the model either returns a valid
instance of the schema or the request fails loudly instead of silently
producing loosely-typed prose.
"""

from typing import Literal

from pydantic import BaseModel, Field


class QueryAnalysis(BaseModel):
    research_goal: str
    research_type: Literal[
        "comparative", "exploratory", "descriptive", "how-to", "evaluative"
    ]
    entities: list[str] = Field(default_factory=list)
    sub_questions: list[str] = Field(min_length=1)


class ResearchPlan(BaseModel):
    objective: str
    sub_questions: list[str] = Field(min_length=1)
    search_queries: list[str] = Field(min_length=1)
    min_sources: int = Field(default=3, ge=1)
    notes: str = ""


class SourceSummary(BaseModel):
    source_url: str
    key_facts: list[str] = Field(default_factory=list)
    relevance: str = ""
    credibility_notes: str = ""


ClaimStatus = Literal[
    "supported", "partially_supported", "contradicted", "unsupported", "uncertain"
]


class FactCheckItem(BaseModel):
    claim: str
    status: ClaimStatus
    evidence_urls: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = ""


class FactCheckResult(BaseModel):
    items: list[FactCheckItem]


class ResearchEvaluation(BaseModel):
    complete: bool
    coverage: float = Field(ge=0.0, le=1.0)
    source_quality: float = Field(ge=0.0, le=1.0)
    missing_topics: list[str] = Field(default_factory=list)
    additional_queries: list[str] = Field(default_factory=list)
    reason: str = ""


class ReportReview(BaseModel):
    acceptable: bool
    issues: list[str] = Field(default_factory=list)
    feedback: str = ""
