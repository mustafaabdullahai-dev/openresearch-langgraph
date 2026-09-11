"""Pydantic schemas for model / LLM status endpoints."""

from pydantic import BaseModel


class ModelStatusResponse(BaseModel):
    provider: str
    model: str
    connected: bool
    message: str = ""
