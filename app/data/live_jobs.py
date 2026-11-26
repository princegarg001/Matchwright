"""Fetch live JDs. Remotive needs no key; Adzuna needs a free app_id/app_key. Results are cached to disk."""
import json
import logging
import time
from datetime import datetime, timezone
from itertools import zip_longest
from pathlib import Path

import requests

from app.core.config import settings
from app.data.clean import clean_text, html_to_text

log = logging.getLogger(__name__)
CACHE = Path(settings.data_dir) / "raw" / "live"
TIMEOUT = 20


def _cache(name: str, rows: list[dict]) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    (CACHE / f"{name}_{stamp}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))


def remotive(query: str, limit: int = 20) -> list[dict]:
    """Remotive's free `/remote-jobs` endpoint now silently ignores `search`/`category` and
    always returns the same fixed small batch of recent jobs (confirmed live: identical results
    for different search terms, `limit` included) — search appears to be a paid-tier feature now.
    We filter client-side instead, on whatever Remotive currently exposes for free, so the result
    is at least honestly related to the query rather than a plausible-looking but unrelated job."""
    r = requests.get("https://remotive.com/api/remote-jobs", params={"search": query}, timeout=TIMEOUT)
    r.raise_for_status()
    jobs = r.json().get("jobs", [])
    terms = [t for t in query.lower().split() if t]
    if terms:
        jobs = [j for j in jobs if any(t in (j.get("title", "") + " " + j.get("description", "")).lower()
                                        for t in terms)]
    rows = [{
        "source": "remotive", "job_id": f"remotive_{j['id']}", "title": j.get("title", ""),
        "company": j.get("company_name", ""), "url": j.get("url", ""),
        "text": clean_text(html_to_text(j.get("description", ""))),
    } for j in jobs[:limit]]
    _cache("remotive", rows)
    return rows


def adzuna(query: str, limit: int = 20) -> list[dict]:
    if not (settings.adzuna_app_id and settings.adzuna_app_key):
        return []
    url = f"https://api.adzuna.com/v1/api/jobs/{settings.adzuna_country}/search/1"
    params: dict[str, str | int] = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "results_per_page": min(limit, 50),
        "content-type": "application/json",
    }
    if query.strip():
        params["what"] = query.strip()
    r = requests.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    rows = [{
        "source": "adzuna", "job_id": f"adzuna_{j['id']}", "title": j.get("title", ""),
        "company": (j.get("company") or {}).get("display_name", ""), "url": j.get("redirect_url", ""),
        "text": clean_text(html_to_text(j.get("description", ""))),  # Adzuna returns a snippet, not the full JD
    } for j in r.json().get("results", [])]
    _cache("adzuna", rows)
    return rows


def _search_all(query: str, limit: int) -> list[dict]:
    buckets: list[list[dict]] = []
    errors: list[Exception] = []
    for name, fn in (("adzuna", adzuna), ("remotive", remotive)):
        try:
            items = fn(query, limit)
            if items:
                buckets.append(items)
        except Exception as e:
            log.warning("%s job search failed: %s", name, e)
            errors.append(e)
    if not buckets and errors:
        raise errors[0]
    merged = [item for pair in zip_longest(*buckets) for item in pair if item is not None]
    return merged[:limit]


def search(query: str, source: str = "remotive", limit: int = 20) -> list[dict]:
    t0 = time.time()
    if source == "all":
        rows = _search_all(query, limit)
    elif source == "adzuna":
        rows = adzuna(query, limit)
    else:
        rows = remotive(query, limit)
    for row in rows:
        row["fetched_in_ms"] = int((time.time() - t0) * 1000)
    return rows
