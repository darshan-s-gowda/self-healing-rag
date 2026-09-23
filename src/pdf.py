from pathlib import Path
from pypdf import PdfReader
from .config import CHUNK_OVERLAP, CHUNK_SIZE


def extract_pdf(path: Path) -> list[dict]:
    reader = PdfReader(str(path))
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append({"page": page_number, "text": text})
    return pages


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    if overlap >= size:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + size, length)
        if end < length:
            boundary = text.rfind(" ", start, end)
            if boundary > start + size // 2:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


def build_chunks(path: Path) -> list[dict]:
    records = []
    for page in extract_pdf(path):
        for part, chunk in enumerate(chunk_text(page["text"]), start=1):
            records.append({
                "id": f"{path.name}:{page['page']}:{part}",
                "text": chunk,
                "metadata": {"source": path.name, "page": page["page"], "part": part},
            })
    return records
