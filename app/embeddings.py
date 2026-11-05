"""Turns text into numbers (vectors). Uses Ollama normally; a tiny offline
fallback ("hash") exists only so tests can run without Ollama."""
import hashlib
import math
import re

import httpx

from . import config


class EmbeddingError(Exception):
    pass


_STOP = set("a an the is are was were of in on at to for and or by with as it this that what which how why does do from be".split())


def _hash_embed(text: str, dim: int = 512) -> list[float]:
    vec = [0.0] * dim
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        if tok in _STOP:
            continue
        tok = tok.rstrip("s")
        vec[int(hashlib.md5(tok.encode()).hexdigest()[:8], 16) % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed(texts: list[str]) -> list[list[float]]:
    if config.EMBED_BACKEND == "hash":
        return [_hash_embed(t) for t in texts]
    out: list[list[float]] = []
    try:
        with httpx.Client(timeout=120) as client:
            for i in range(0, len(texts), 16):
                r = client.post(f"{config.OLLAMA_URL}/api/embed",
                                json={"model": config.EMBED_MODEL, "input": texts[i:i + 16]})
                r.raise_for_status()
                out.extend(r.json()["embeddings"])
    except (httpx.HTTPError, KeyError) as e:
        raise EmbeddingError(
            f"Could not create embeddings. Is Ollama running and is '{config.EMBED_MODEL}' pulled? ({e})") from e
    return out
