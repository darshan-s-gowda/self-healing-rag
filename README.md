# Self-Healing RAG — Senior Reference Build

A clean document-grounded RAG application with a LangGraph control loop:

`Retrieve → Generate → Critique → Rewrite → Retrieve`

The system fails closed when evidence is insufficient. The public API returns only the final answer; internal retrieval/critic details are not exposed by the UI.

## Design goals

- No structured-output/tool-calling dependency for the critic.
- No stale Chroma documents after a new UI ingestion; every ingestion replaces the active index.
- Batched embeddings for larger PDFs.
- Configurable upload, chunk, embedding-batch, top-k, and retry limits.
- Exact safe fallback for unsupported questions.
- Frontend intentionally avoids gradients, neon colors, glassmorphism, decorative icon packs, excessive rounded cards, drop shadows, bento grids, pricing sections, testimonials, animated arrows, radial ornaments, emoji UI, and raw JSON/debug traces.
- UI displays only the answer after a question is submitted.

## Windows setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Put your Groq key in `.env`:

```text
GROQ_API_KEY=...
GROQ_MODEL=openai/gpt-oss-20b
```

Run:

```powershell
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000`.

## Important usage rule

Use the web UI to index the current document set. Uploading through the UI replaces the previous vector index, preventing old resumes/documents from leaking into a new session.

Do not run a separate bulk-ingestion script against the same persistent collection.

## Large PDF behavior

PDFs are extracted page by page and split into overlapping chunks. Embeddings are created in batches rather than sending the whole document to the model at once. Retrieval sends only the top relevant chunks to the LLM.

The default upload limit is 100 MB. Adjust `MAX_UPLOAD_MB` if required.

## Validation

The project includes a small test suite for chunking and JSON parsing. Syntax can be checked with:

```powershell
python -m compileall app.py src
```
