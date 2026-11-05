"""Tests run fully offline: a simple built-in embedder replaces Ollama."""
import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="rag_test_")
os.environ["EMBED_BACKEND"] = "hash"
os.environ["MIN_SIM"] = "0.12"

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config, rag, store
from app.main import app

SAMPLES = Path(__file__).resolve().parent.parent / "sample_docs"


@pytest.fixture(scope="session")
def client():
    c = TestClient(app)
    for f in SAMPLES.iterdir():
        r = c.post("/documents/upload", files={"file": (f.name, f.read_bytes())})
        assert r.status_code == 200, r.text
    return c


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    """Echo the first context passage so tests never need a real model."""
    monkeypatch.setattr(rag, "generate", lambda msgs: "ANSWER FROM CONTEXT: " + msgs[-1]["content"][:300])
