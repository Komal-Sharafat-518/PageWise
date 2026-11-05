"""Document pipeline: read -> clean -> split into chunks -> embed -> store."""
import hashlib
import re
import shutil
from pathlib import Path

from pypdf import PdfReader

from . import config, embeddings, store


class IngestError(Exception):
    pass


def extract_pages(path: Path) -> list[tuple[int, str]]:
    ext = path.suffix.lower()
    if ext in (".txt", ".md"):
        return [(1, path.read_text(encoding="utf-8", errors="ignore"))]
    if ext == ".pdf":
        try:
            reader = PdfReader(str(path))
            if reader.is_encrypted:
                raise IngestError("PDF is password protected")
            return [(i + 1, p.extract_text() or "") for i, p in enumerate(reader.pages)]
        except IngestError:
            raise
        except Exception as e:
            raise IngestError(f"PDF could not be read (corrupt file?): {e}") from e
    raise IngestError(f"Unsupported file type '{ext}'. Allowed: {sorted(config.ALLOWED_EXT)}")


def _units(text: str, size: int) -> list[tuple[str, bool]]:
    """Split text into whole sentences. Returns (sentence, starts_new_paragraph)."""
    units = []
    for para in re.split(r"\n\s*\n", text):
        para = re.sub(r"\s+", " ", para).strip()
        if not para:
            continue
        first = True
        for sent in re.split(r"(?<=[.!?])\s+", para):
            while len(sent) > size:                      # very long sentence: cut at a space
                cut = sent.rfind(" ", 0, size)
                cut = cut if cut > 0 else size
                units.append((sent[:cut].strip(), first)); first = False
                sent = sent[cut:].strip()
            if sent:
                units.append((sent, first)); first = False
    return units


def _join(units: list[tuple[str, bool]]) -> str:
    out = ""
    for i, (sent, new_par) in enumerate(units):
        out += sent if i == 0 else (("\n\n" if new_par else " ") + sent)
    return out


def _is_heading(unit: tuple[str, bool]) -> bool:
    sent, new_par = unit
    return new_par and len(sent) < 100 and sent[-1] not in ".!?`)"


def chunk_text(text: str, size: int = None, overlap: int = None) -> list[str]:
    """Cut text into chunks made of WHOLE sentences. A heading is never left alone at the
    end of a chunk, so no passage starts or ends mid-sentence or on a dangling title."""
    size, overlap = size or config.CHUNK_SIZE, overlap or config.CHUNK_OVERLAP
    chunks, cur = [], []
    for unit in _units(text, size):
        if cur and len(_join(cur + [unit])) > size:
            carry = []
            while len(cur) > 1 and _is_heading(cur[-1]):   # move dangling heading to next chunk
                carry.insert(0, cur.pop())
            chunks.append(_join(cur))
            keep, total = [], 0                            # repeat the last sentence(s) for context
            for u in reversed(cur):
                if total + len(u[0]) > overlap:
                    break
                keep.insert(0, u); total += len(u[0]) + 1
            if not (keep and len(_join(keep + carry + [unit])) <= size):
                keep = []
            cur = keep + carry
        cur.append(unit)
    if cur:
        chunks.append(_join(cur))
    return chunks


def ingest_file(path: Path) -> dict:
    """Add one file to the knowledge base. Returns a small status dict."""
    data = path.read_bytes()
    doc_hash = hashlib.sha256(data).hexdigest()
    name = path.name

    if store.collection.get(where={"doc_hash": doc_hash}, limit=1)["ids"]:
        return {"file": name, "status": "duplicate", "chunks": 0}

    pages = extract_pages(path)
    ids, texts, metas = [], [], []
    for page_no, page_text in pages:
        for piece in chunk_text(page_text):
            ids.append(f"{doc_hash[:12]}-{len(ids)}")
            texts.append(piece)
            metas.append({"source": name, "page": page_no, "doc_hash": doc_hash})
    if not texts:
        raise IngestError("No readable text found (scanned PDF or empty file?)")

    vectors = embeddings.embed(texts)          # embed first, so a failure changes nothing
    replaced = store.delete_document(name)     # same name, new content -> replace
    store.collection.upsert(ids=ids, documents=texts, metadatas=metas, embeddings=vectors)
    return {"file": name, "status": "replaced" if replaced else "added", "chunks": len(texts)}


def process_file(path: Path) -> dict:
    """Ingest a file from the inbox, then move it to processed/ or failed/."""
    try:
        result = ingest_file(path)
        shutil.move(str(path), str(config.PROCESSED / path.name))
        return result
    except Exception as e:  # keep the pipeline alive whatever happens
        shutil.move(str(path), str(config.FAILED / path.name))
        (config.FAILED / f"{path.name}.error.txt").write_text(str(e))
        return {"file": path.name, "status": "failed", "error": str(e)}


def scan_inbox() -> dict:
    results = [process_file(p) for p in sorted(config.INBOX.iterdir())
               if p.is_file() and not p.name.startswith(".")]
    failed = [r for r in results if r["status"] == "failed"]
    return {"processed": len(results), "failed_count": len(failed),
            "results": results, "failed": failed}
