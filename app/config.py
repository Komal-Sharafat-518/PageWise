"""All settings in one place. Change them with environment variables."""
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = Path(os.getenv("DATA_DIR", BASE / "data"))
INBOX, PROCESSED, FAILED = DATA / "inbox", DATA / "processed", DATA / "failed"
CHROMA_DIR = DATA / "chroma"
HISTORY_DB = DATA / "history.sqlite"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:1b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
EMBED_BACKEND = os.getenv("EMBED_BACKEND", "ollama")  # "ollama" or "hash" (offline tests only)

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K = int(os.getenv("TOP_K", "4"))
MIN_SIM = float(os.getenv("MIN_SIM", "0.30"))  # below this, we say "not found"
HISTORY_TURNS = int(os.getenv("HISTORY_TURNS", "4"))
ALLOWED_EXT = {".pdf", ".txt", ".md"}
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))

for _d in (INBOX, PROCESSED, FAILED, CHROMA_DIR):
    _d.mkdir(parents=True, exist_ok=True)
