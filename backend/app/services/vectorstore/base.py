"""Vector store abstraction for RAG document retrieval."""

from typing import Any, Protocol

from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    content: str
    source_filename: str
    score: float = 0.0


class VectorStore(Protocol):
    async def add_documents(
        self,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Insert document chunks."""

    async def similarity_search(self, query: str, k: int = 5) -> list[RetrievedChunk]:
        """Return the top-k most relevant chunks for ``query``."""
