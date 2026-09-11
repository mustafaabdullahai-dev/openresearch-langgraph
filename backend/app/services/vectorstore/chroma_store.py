"""ChromaDB-backed vector store with a deterministic local embedding fallback.

Embeddings are generated via Hugging Face hosted inference when a token is
configured.  When the inference backend is unavailable (e.g. in CI without a
token), a hash-based embedding function provides stable, zero-dependency
vector storage so the rest of the system stays functional for non-semantic
retrieval.
"""

from __future__ import annotations

import asyncio
from hashlib import sha256
from typing import Any, cast

import chromadb
from app.config.settings import settings

from .base import RetrievedChunk

try:  # optional dependency guard
    from huggingface_hub import AsyncInferenceClient

    _HFClient: Any = AsyncInferenceClient
except Exception:  # noqa: BLE001
    _HFClient = None


class _LocalEmbeddingFunction:
    """Deterministic TF-hash embedding — no network, no model download.

    Duck-types chroma's ``EmbeddingFunction`` protocol: Chroma calls
    ``__call__`` to embed batches, ``embed_query`` for query embedding,
    and ``name()``/``get_config()`` when persisting configuration.
    """

    def __init__(self, dimensions: int = 128) -> None:
        self.dimensions = dimensions

    @staticmethod
    def name() -> str:
        return "openresearch-local-hash"

    def get_config(self) -> dict[str, Any]:
        return {}

    @classmethod
    def build_from_config(
        cls, configuration: dict[str, Any]
    ) -> _LocalEmbeddingFunction:
        return cls()

    def embed_query(self, input: str) -> list[list[float]]:
        return self.__call__([input])

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        vectors: list[list[float]] = []
        for text in input:
            if isinstance(text, (list, tuple)):
                text = " ".join(str(t) for t in text)
            vec = [0.0] * self.dimensions
            for token in str(text).lower().split():
                digest = sha256(token.encode("utf-8")).digest()
                index = int.from_bytes(digest[:8], "big") % self.dimensions
                sign = 1.0 if digest[0] % 2 == 0 else -1.0
                vec[index] += sign
            norm = float(sum(v * v for v in vec) ** 0.5)
            if norm > 0:
                vec = [v / norm for v in vec]
            vectors.append(vec)
        return vectors


_collection_name = "openresearch_docs"


class ChromaVectorStore:
    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)
        self._hash_fn = _LocalEmbeddingFunction()
        self._collection = self._client.get_or_create_collection(
            name=_collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=cast(Any, self._hash_fn),
        )

        # HF inference embeddings are tried first; when available they
        # override the local hash embeddings at add/query time (passing
        # explicit ``embeddings`` / ``query_embeddings``).
        self._external_embeds: list[Any] = []
        try:
            if _HFClient is not None:
                self._external_embeds.append(_HFClient(token=settings.HF_TOKEN or None))
        except Exception:
            pass

    async def _external_embed(
        self, texts: list[str], *, batch_size: int = 4
    ) -> list[list[float]] | None:
        """Embed via the HF inference server; hash fallback otherwise."""
        for engine in self._external_embeds:
            try:
                if not settings.HF_TOKEN:
                    continue
                vectors: list[list[float]] = []
                for i in range(0, len(texts), batch_size):
                    batch = texts[i : i + batch_size]
                    result = await engine.feature_extraction(batch)
                    for vec in result:
                        if isinstance(vec, (list, tuple)):
                            vectors.append([float(v) for v in vec])
                if len(vectors) == len(texts):
                    return vectors
            except Exception:
                continue
        return None

    async def add_documents(
        self,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        embeddings = await self._external_embed(documents)
        kwargs: dict[str, Any] = {
            "documents": documents,
            "metadatas": metadatas,
            "ids": ids,
        }
        if embeddings is not None:
            kwargs["embeddings"] = embeddings
        await asyncio.to_thread(self._collection.add, **kwargs)

    async def similarity_search(self, query: str, k: int = 5) -> list[RetrievedChunk]:
        embeddings = await self._external_embed([query])
        kwargs: dict[str, Any] = {"query_texts": [query], "n_results": k}
        if embeddings is not None:
            kwargs = {"query_embeddings": [embeddings[0]], "n_results": k}
        results: Any = await asyncio.to_thread(self._collection.query, **kwargs)
        chunks: list[RetrievedChunk] = []
        raw_docs = (results.get("documents") or [[]])[0]
        raw_metas = (results.get("metadatas") or [[]])[0]
        raw_dists = (results.get("distances") or [[]])[0]
        for idx, doc in enumerate(raw_docs):
            meta = raw_metas[idx] if idx < len(raw_metas) else {}
            dist = raw_dists[idx] if idx < len(raw_dists) else 0.0
            score = max(0.0, min(1.0, 1.0 - float(dist)))
            chunks.append(
                RetrievedChunk(
                    content=str(doc),
                    source_filename=str(meta.get("filename", "unknown")),
                    score=score,
                )
            )
        return chunks
