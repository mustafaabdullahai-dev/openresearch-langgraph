"""Document text extraction for PDF, DOCX, TXT, and Markdown files."""

from pathlib import Path


def extract_text(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(path)
    if ext == ".docx":
        return _extract_docx(path)
    if ext in (".txt", ".md"):
        return Path(path).read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {ext}")


def _extract_pdf(path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(path)
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def _extract_docx(path: str) -> str:
    from docx import Document as DocxDocument

    doc = DocxDocument(path)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
