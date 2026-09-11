"""Pydantic schemas for research-related API requests and responses."""

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class ResearchResponse(BaseModel):
    thread_id: str
    question: str
    status: str
    message: str = ""


class ResearchResultResponse(BaseModel):
    thread_id: str
    question: str
    status: str
    final_report: str
    sources: list[dict]
    citations: list[dict]
    iterations: int
    duration_seconds: float


class SourceResponse(BaseModel):
    url: str
    title: str
    domain: str
    quality_score: float
    quality_tier: str
    snippet: str
