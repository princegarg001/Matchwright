"""Tiny SQLite store for results + audit (input hashes, model, weights)."""
import hashlib
import json
import sqlite3
from pathlib import Path

from app.core.config import settings


def _conn() -> sqlite3.Connection:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(settings.db_path)
    c.execute("CREATE TABLE IF NOT EXISTS results (match_id TEXT PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP,"
              " resume_hash TEXT, jd_hash TEXT, body TEXT)")
    return c


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def save(match_id: str, resume_text: str, jd_text: str, body: dict) -> None:
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO results (match_id, resume_hash, jd_hash, body) VALUES (?,?,?,?)",
                  (match_id, sha(resume_text), sha(jd_text), json.dumps(body)))


def get(match_id: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT body FROM results WHERE match_id=?", (match_id,)).fetchone()
    return json.loads(row[0]) if row else None


def find_cached(resume_text: str, jd_text: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT body FROM results WHERE resume_hash=? AND jd_hash=? ORDER BY created DESC LIMIT 1",
                        (sha(resume_text), sha(jd_text))).fetchone()
    return json.loads(row[0]) if row else None
