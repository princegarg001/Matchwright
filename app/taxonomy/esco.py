"""ESCO lookup with a disk cache. Free API, no key. Pin the version for reproducibility."""
import json
from pathlib import Path

import requests

CACHE = Path("data/esco_cache.json")
URL = "https://ec.europa.eu/esco/api/search"


def esco_skill(name: str) -> dict | None:
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    if name in cache:
        return cache[name]
    try:
        r = requests.get(URL, params={"text": name, "type": "skill", "language": "en", "limit": 1,
                                      "selectedVersion": "v1.2.0"}, timeout=10)
        r.raise_for_status()
        hits = r.json().get("_embedded", {}).get("results", [])
        hit = {"uri": hits[0]["uri"], "title": hits[0]["title"]} if hits else None
    except Exception:
        return None
    cache[name] = hit
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1))
    return hit
