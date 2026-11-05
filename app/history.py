"""Conversation memory saved in SQLite, so chats survive a restart."""
import json
import sqlite3
import time

from . import config


def _conn():
    c = sqlite3.connect(config.HISTORY_DB)
    c.execute("""CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT,
        content TEXT, sources TEXT, ts REAL)""")
    return c


def add(session_id: str, role: str, content: str, sources: list | None = None):
    with _conn() as c:
        c.execute("INSERT INTO messages(session_id,role,content,sources,ts) VALUES(?,?,?,?,?)",
                  (session_id, role, content, json.dumps(sources or []), time.time()))


def get(session_id: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT role,content,sources,ts FROM messages WHERE session_id=? ORDER BY id",
                         (session_id,)).fetchall()
    return [{"role": r, "content": t, "sources": json.loads(s), "ts": ts} for r, t, s, ts in rows]


def clear(session_id: str):
    with _conn() as c:
        c.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
def list_sessions() -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT session_id, MAX(ts),
                   (SELECT content FROM messages m2
                    WHERE m2.session_id = m.session_id AND m2.role = 'user'
                    ORDER BY id LIMIT 1)
            FROM messages m GROUP BY session_id ORDER BY MAX(ts) DESC""").fetchall()
    return [{"session_id": s, "updated": ts, "title": (t or "New chat")[:50]} for s, ts, t in rows]
def list_sessions() -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT session_id, MAX(ts),
                   (SELECT content FROM messages m2
                    WHERE m2.session_id = m.session_id AND m2.role = 'user'
                    ORDER BY id LIMIT 1)
            FROM messages m GROUP BY session_id ORDER BY MAX(ts) DESC""").fetchall()
    return [{"session_id": s, "updated": ts, "title": (t or "New chat")[:50]} for s, ts, t in rows]