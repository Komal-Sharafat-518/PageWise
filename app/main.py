"""FastAPI server: chat, uploads, document management, history."""
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, history, ingest, rag, store
from .embeddings import EmbeddingError

app = FastAPI(title="Educational Document Assistant")
STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None


@app.exception_handler(rag.LLMError)
@app.exception_handler(EmbeddingError)
async def model_down(_, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "chunks": store.collection.count(), "documents": len(store.list_documents())}


@app.post("/chat")
def chat(body: ChatIn):
    if not body.question.strip():
        raise HTTPException(422, "Question cannot be empty")
    sid = body.session_id or uuid.uuid4().hex[:12]
    return {"session_id": sid, **rag.ask(sid, body.question.strip())}

@app.get("/sessions")
def sessions():
    return history.list_sessions()
@app.get("/sessions")
def sessions():
    return history.list_sessions()
@app.get("/history/{session_id}")
def get_history(session_id: str):
    return history.get(session_id)


@app.delete("/history/{session_id}")
def clear_history(session_id: str):
    history.clear(session_id)
    return {"cleared": True}


@app.post("/documents/upload")
async def upload(file: UploadFile = File(...)):
    name = Path(file.filename or "").name
    if Path(name).suffix.lower() not in config.ALLOWED_EXT:
        raise HTTPException(415, f"Unsupported file type. Allowed: {sorted(config.ALLOWED_EXT)}")
    data = await file.read()
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File larger than {config.MAX_UPLOAD_MB} MB")
    if not data:
        raise HTTPException(400, "File is empty")
    dest = config.INBOX / name
    dest.write_bytes(data)
    result = ingest.process_file(dest)
    if result["status"] == "failed":
        raise HTTPException(422, result["error"])
    return result


@app.post("/ingest/scan")
def scan():
    """Called by n8n: processes every file waiting in data/inbox."""
    return ingest.scan_inbox()


@app.get("/documents")
def documents():
    return store.list_documents()


@app.delete("/documents/{name}")
def delete_document(name: str):
    n = store.delete_document(name)
    if not n:
        raise HTTPException(404, "Document not found")
    return {"deleted_chunks": n}
