"""Accuracy + speed report.

  python -m tests.evaluate --offline   # retrieval only, no Ollama needed
  python -m tests.evaluate --live      # full answers from a running server (needs Ollama)
"""
import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = json.loads((ROOT / "tests" / "questions.json").read_text())
SAMPLES = ROOT / "sample_docs"


def offline():
    os.environ.update(DATA_DIR=tempfile.mkdtemp(), EMBED_BACKEND="hash", MIN_SIM="0.12")
    from app import ingest, rag
    from app.config import INBOX
    t = time.perf_counter()
    for f in SAMPLES.iterdir():
        (INBOX / f.name).write_bytes(f.read_bytes())
    summary = ingest.scan_inbox()
    ingest_s = time.perf_counter() - t
    rows, times = [], []
    for item in QUESTIONS:
        t = time.perf_counter()
        hits = rag.retrieve(item["q"])
        dt = time.perf_counter() - t
        times.append(dt)
        top = hits[0]["source"] if hits else None
        ok = (top == item["source"])
        rows.append((item["q"], item["source"] or "(not in docs)", top or "(none)", ok, dt))
    return summary, ingest_s, rows, times


def live(base="http://localhost:8000"):
    import httpx
    rows, times = [], []
    with httpx.Client(timeout=300) as c:
        for item in QUESTIONS:
            t = time.perf_counter()
            r = c.post(f"{base}/chat", json={"question": item["q"]}).json()
            dt = time.perf_counter() - t
            times.append(dt)
            top = r["sources"][0]["source"] if r.get("sources") else None
            src_ok = (top == item["source"])
            kw_ok = all(k.lower() in r["answer"].lower() for k in item["keywords"][:1]) if item["keywords"] else r["answer"].startswith("I could not find")
            rows.append((item["q"], item["source"] or "(not in docs)", top or "(none)", src_ok and kw_ok, dt))
    return None, None, rows, times


def report(summary, ingest_s, rows, times, title):
    print(f"## {title}\n")
    if summary:
        print(f"Ingested {summary['processed']} files in {ingest_s:.2f}s, failures: {summary['failed_count']}\n")
    print("| # | Question | Expected source | Top source found | Result | Time (s) |")
    print("|---|----------|-----------------|------------------|--------|----------|")
    for i, (q, exp, got, ok, dt) in enumerate(rows, 1):
        print(f"| {i} | {q} | {exp} | {got} | {'PASS' if ok else 'FAIL'} | {dt:.3f} |")
    passed = sum(r[3] for r in rows)
    print(f"\n**Accuracy: {passed}/{len(rows)} ({100 * passed / len(rows):.0f}%)**  ")
    print(f"**Average time: {statistics.mean(times):.3f}s, slowest: {max(times):.3f}s**")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    if "--live" in sys.argv:
        report(*live(), "Live test (full answers with Ollama)")
    else:
        report(*offline(), "Offline retrieval test (built-in embedder, no LLM)")
