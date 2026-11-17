"""Fetch live JDs. Remotive needs no key; Adzuna needs a free app_id/app_key. Results are cached to disk."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from app.core.config import settings
from app.data.clean import clean_text, html_to_text

CACHE = Path(settings.data_dir) / "raw" / "live"
TIMEOUT = 20


def _cache(name: str, rows: list[dict]) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    (CACHE / f"{name}_{stamp}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))


def remotive(query: str, limit: int = 20) -> list[dict]:
    r = requests.get("https://remotive.com/api/remote-jobs",
                     params={"search": query, "limit": limit}, timeout=TIMEOUT)
    r.raise_for_status()
    rows = [{
        "source": "remotive", "job_id": f"remotive_{j['id']}", "title": j.get("title", ""),
        "company": j.get("company_name", ""), "url": j.get("url", ""),
        "text": clean_text(html_to_text(j.get("description", ""))),
    } for j in r.json().get("jobs", [])[:limit]]
    _cache("remotive", rows)
    return rows


def adzuna(query: str, limit: int = 20) -> list[dict]:
    if not (settings.adzuna_app_id and settings.adzuna_app_key):
        return []
    url = f"https://api.adzuna.com/v1/api/jobs/{settings.adzuna_country}/search/1"
    r = requests.get(url, params={
        "app_id": settings.adzuna_app_id, "app_key": settings.adzuna_app_key,
        "what": query, "results_per_page": min(limit, 50), "content-type": "application/json",
    }, timeout=TIMEOUT)
    r.raise_for_status()
    rows = [{
        "source": "adzuna", "job_id": f"adzuna_{j['id']}", "title": j.get("title", ""),
        "company": (j.get("company") or {}).get("display_name", ""), "url": j.get("redirect_url", ""),
        "text": clean_text(j.get("description", "")),  # Adzuna returns a snippet, not the full JD
    } for j in r.json().get("results", [])]
    _cache("adzuna", rows)
    return rows


def search(query: str, source: str = "remotive", limit: int = 20) -> list[dict]:
    t0 = time.time()
    rows = remotive(query, limit) if source == "remotive" else adzuna(query, limit)
    for row in rows:
        row["fetched_in_ms"] = int((time.time() - t0) * 1000)
    return rows
