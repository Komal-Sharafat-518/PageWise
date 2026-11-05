"""RAG: find the most relevant chunks, then ask the LLM to answer from them only."""
import re
import time

import httpx

from . import config, embeddings, history, store

NOT_FOUND = "I could not find this in the uploaded documents."

SYSTEM = (
    "You are a helpful study assistant. Answer the question using ONLY the numbered "
    "context passages provided. Write a short, clear answer in your own words. "
    "Do NOT repeat the passage labels or file names at the start of your answer. "
    "Cite the passages you used with their number in square brackets, like [1], at the end of a sentence. "
    "If the context does not contain the answer, reply exactly: "
    f"\"{NOT_FOUND}\" Keep answers clear and simple."
)

_HEADER = re.compile(r"^\s*(\[\d+\]\s*\([^)\n]*\)\s*:?\s*)+", re.I)


class LLMError(Exception):
    pass


def retrieve(question: str, k: int = None) -> list[dict]:
    total = store.collection.count()
    if total == 0:
        return []
    k = min(k or config.TOP_K, total)
    res = store.collection.query(query_embeddings=embeddings.embed([question]),
                                 n_results=k, include=["documents", "metadatas", "distances"])
    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        hits.append({"text": doc, "source": meta["source"], "page": meta["page"],
                     "score": round(1 - dist, 3)})
    return [h for h in hits if h["score"] >= config.MIN_SIM]


def generate(messages: list[dict]) -> str:
    try:
        with httpx.Client(timeout=180) as c:
            r = c.post(f"{config.OLLAMA_URL}/api/chat",
                       json={"model": config.LLM_MODEL, "messages": messages, "stream": False,
                             "options": {"temperature": 0.2}})
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
    except (httpx.HTTPError, KeyError) as e:
        raise LLMError(f"The language model is not reachable. Is Ollama running with '{config.LLM_MODEL}'? ({e})") from e


def ask(session_id: str, question: str) -> dict:
    t0 = time.perf_counter()
    past = history.get(session_id)
    last_users = [m["content"] for m in past if m["role"] == "user"]
    # Short follow-ups like "why?" need the previous question to be searchable.
    search_q = f"{last_users[-1]} {question}" if last_users and len(question.split()) < 6 else question

    hits = retrieve(search_q)
    sources = [{"id": i + 1, "source": h["source"], "page": h["page"], "score": h["score"],
                "snippet": h["text"]}for i, h in enumerate(hits)]

    if not hits:
        answer = NOT_FOUND
    else:
        context = "\n\n".join(f"[{i + 1}] ({h['source']}, p.{h['page']})\n{h['text']}"
                              for i, h in enumerate(hits))
        msgs = [{"role": "system", "content": SYSTEM}]
        msgs += [{"role": m["role"], "content": m["content"]}
                 for m in past[-2 * config.HISTORY_TURNS:]]
        msgs.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"})
        answer = _HEADER.sub("", generate(msgs)).strip() or NOT_FOUND

    history.add(session_id, "user", question)
    history.add(session_id, "assistant", answer, sources)
    return {"answer": answer, "sources": sources, "seconds": round(time.perf_counter() - t0, 2)}
