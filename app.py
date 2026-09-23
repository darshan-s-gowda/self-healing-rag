from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.config import DOCUMENT_DIR, MAX_UPLOAD_MB, SAFE_FALLBACK
from src.pdf import build_chunks
from src.store import reset_index, add_records
from src.graph import GRAPH

app = FastAPI(title="Self-Healing RAG", version="1.0.0")


class AskRequest(BaseModel):
    question: str


@app.get("/")
def home():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


async def _save_upload(upload: UploadFile) -> Path:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    safe_name = Path(upload.filename).name
    target = DOCUMENT_DIR / safe_name
    temp = DOCUMENT_DIR / f".{safe_name}.uploading"
    limit = MAX_UPLOAD_MB * 1024 * 1024
    written = 0

    try:
        with temp.open("wb") as output:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > limit:
                    raise HTTPException(413, f"{safe_name} exceeds the {MAX_UPLOAD_MB} MB upload limit")
                output.write(chunk)
        temp.replace(target)
        return target
    except Exception:
        temp.unlink(missing_ok=True)
        raise


@app.post("/ingest")
async def ingest(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(400, "Select at least one PDF")

    staged: list[Path] = []
    try:
        # Stage and parse everything first. The vector index is replaced only
        # after every selected file is valid, avoiding a half-updated index.
        for upload in files:
            path = await _save_upload(upload)
            records = build_chunks(path)
            if not records:
                raise HTTPException(400, f"No extractable text found in {path.name}")
            staged.append(path)

        reset_index()
        total = 0
        names = []
        for path in staged:
            records = build_chunks(path)
            total += add_records(records)
            names.append(path.name)

        return {"status": "success", "files": names, "chunks_created": total}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Ingestion failed: {exc}")
    finally:
        for upload in files:
            await upload.close()


@app.post("/ask")
def ask(payload: AskRequest):
    question = payload.question.strip()
    if not question:
        raise HTTPException(400, "Question cannot be empty")
    try:
        result = GRAPH.invoke({"question": question, "query": question, "retries": 0})
        answer = result.get("answer") or SAFE_FALLBACK
        return {"answer": answer}
    except Exception:
        return {"answer": SAFE_FALLBACK}
