import json
from pathlib import Path

from app import config, ingest, store

QUESTIONS = json.loads((Path(__file__).parent / "questions.json").read_text())


# ---------- document processing ----------
def test_chunking_respects_size_and_overlap():
    text = ". ".join(f"Sentence number {i} about learning" for i in range(200))
    chunks = ingest.chunk_text(text, size=400, overlap=80)
    assert len(chunks) > 5
    assert all(len(c) <= 400 for c in chunks)


def test_documents_are_listed(client):
    names = {d["name"] for d in client.get("/documents").json()}
    assert {"newtons_laws.txt", "photosynthesis.txt", "python_basics.md"} <= names


def test_duplicate_upload_is_skipped(client):
    f = Path(__file__).parent.parent / "sample_docs" / "newtons_laws.txt"
    r = client.post("/documents/upload", files={"file": ("copy_of_newton.txt", f.read_bytes())})
    assert r.json()["status"] == "duplicate"


def test_inbox_scan_moves_files(client):
    (config.INBOX / "extra.txt").write_text("The mitochondria is the powerhouse of the cell. " * 20)
    (config.INBOX / "empty.txt").write_text("   ")
    res = client.post("/ingest/scan").json()
    assert res["processed"] == 2 and res["failed_count"] == 1
    assert (config.PROCESSED / "extra.txt").exists()
    assert (config.FAILED / "empty.txt").exists()
    assert (config.FAILED / "empty.txt.error.txt").exists()
    store.delete_document("extra.txt")  # keep the shared knowledge base clean for other tests


# ---------- error handling ----------
def test_unsupported_file_type_rejected(client):
    r = client.post("/documents/upload", files={"file": ("virus.exe", b"abc")})
    assert r.status_code == 415


def test_empty_file_rejected(client):
    assert client.post("/documents/upload", files={"file": ("a.txt", b"")}).status_code == 400


def test_corrupt_pdf_goes_to_failed(client):
    r = client.post("/documents/upload", files={"file": ("broken.pdf", b"this is not a pdf")})
    assert r.status_code == 422
    assert (config.FAILED / "broken.pdf").exists()


def test_empty_question_rejected(client):
    assert client.post("/chat", json={"question": "   "}).status_code == 422


def test_model_down_returns_friendly_503(client, monkeypatch):
    from app import rag
    def boom(msgs):
        raise rag.LLMError("Ollama is not reachable")
    monkeypatch.setattr(rag, "generate", boom)
    r = client.post("/chat", json={"question": "What is Newton's second law?"})
    assert r.status_code == 503 and "Ollama" in r.json()["detail"]


# ---------- question answering ----------
def test_retrieval_finds_correct_source(client):
    for item in QUESTIONS:
        if item["source"]:
            r = client.post("/chat", json={"question": item["q"]}).json()
            assert r["sources"], item["q"]
            assert r["sources"][0]["source"] == item["source"], item["q"]


def test_unrelated_question_says_not_found(client):
    r = client.post("/chat", json={"question": "Who won the 2018 football world cup?"}).json()
    assert r["answer"].startswith("I could not find")
    assert r["sources"] == []


def test_history_is_kept_and_sources_saved(client):
    a = client.post("/chat", json={"question": "Which pigment absorbs sunlight in leaves?"}).json()
    sid = a["session_id"]
    client.post("/chat", json={"question": "Why does it look green?", "session_id": sid})
    h = client.get(f"/history/{sid}").json()
    assert [m["role"] for m in h] == ["user", "assistant", "user", "assistant"]
    assert h[1]["sources"][0]["source"] == "photosynthesis.txt"
    client.delete(f"/history/{sid}")
    assert client.get(f"/history/{sid}").json() == []


def test_delete_document(client):
    client.post("/documents/upload", files={"file": ("temp.txt", b"Temporary note about rivers and lakes. " * 10)})
    assert client.delete("/documents/temp.txt").status_code == 200
    assert client.delete("/documents/temp.txt").status_code == 404
