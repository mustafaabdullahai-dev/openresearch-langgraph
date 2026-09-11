"""Document upload endpoint for RAG."""

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from app.schemas.documents import DocumentUploadResponse
from app.services.documents.extractor import extract_text
from app.services.security import is_allowed_upload

router = APIRouter(tags=["documents"])

UPLOAD_DIR = Path("data/uploads")


@router.post("/api/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile) -> DocumentUploadResponse:
    """Accept a file, extract text, chunk it, and store in the vector database."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    allowed, msg = is_allowed_upload(file.filename or "unknown", len(content))
    if not allowed:
        raise HTTPException(status_code=400, detail=msg)

    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    stored_path = UPLOAD_DIR / safe_name
    stored_path.write_bytes(content)

    try:
        text = extract_text(str(stored_path))
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Could not extract text: {exc}"
        ) from exc

    from app.services.vectorstore.chroma_store import ChromaVectorStore

    store = ChromaVectorStore()

    chunk_size = 1200
    chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)] or [
        text
    ]
    ids = [uuid.uuid4().hex for _ in chunks]
    metadatas = [
        {"filename": file.filename, "chunk_index": i} for i in range(len(chunks))
    ]

    await store.add_documents(ids=ids, documents=chunks, metadatas=metadatas)

    # Persist document row
    try:
        from app.database.engine import SessionLocal
        from app.models.document import Document as DocRow

        with SessionLocal() as db:
            row = DocRow(
                id=uuid.uuid4().hex,
                filename=file.filename or "unknown",
                stored_path=str(stored_path),
                chunk_count=len(chunks),
            )
            db.add(row)
            db.commit()
    except Exception:
        pass

    return DocumentUploadResponse(
        document_id=ids[0] if ids else "",
        filename=file.filename or "unknown",
        chunk_count=len(chunks),
        message="Document ingested successfully.",
    )
