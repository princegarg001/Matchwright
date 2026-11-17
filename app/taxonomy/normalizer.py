"""Map raw skill strings to canonical names; answer 'are these two skills related?'."""
import re
from functools import lru_cache
from pathlib import Path

import yaml

from app.core.config import settings

_STRIP = re.compile(r"\(.*?\)|\b(v?\d+(\.\d+)*)\b$|[\"'`]")


def snippet(text: str, start: int, end: int, pad: int = 50) -> str:
    """Evidence quote around a match, cut at word boundaries, with ellipses when trimmed."""
    s, e = max(0, start - pad), min(len(text), end + pad)
    if s > 0:
        sp = text.find(" ", s, start)
        s = sp + 1 if sp != -1 else s
    if e < len(text):
        sp = text.rfind(" ", end, e)
        e = sp if sp != -1 else e
    body = " ".join(text[s:e].split())
    return ("…" if s > 0 else "") + body + ("…" if e < len(text) else "")


class Normalizer:
    def __init__(self, path: str | Path):
        data = yaml.safe_load(Path(path).read_text())
        self.alias_to_canon: dict[str, str] = {}
        for canon, aliases in (data.get("aliases") or {}).items():
            canon = canon.lower()
            self.alias_to_canon[canon] = canon
            for a in aliases or []:
                self.alias_to_canon[a.lower()] = canon
        self.groups: list[set[str]] = [{self.canon(s) for s in g} for g in data.get("related") or []]
        # longest first so 'machine learning' wins over 'learning'
        self.vocabulary = sorted(self.alias_to_canon, key=len, reverse=True)

    @staticmethod
    def clean(name: str) -> str:
        n = name.lower().strip().strip(".,;:-•*")
        n = _STRIP.sub("", n).strip()
        return re.sub(r"\s+", " ", n)

    def canon(self, name: str) -> str:
        n = self.clean(name)
        return self.alias_to_canon.get(n, n)

    def related(self, a: str, b: str) -> bool:
        return self.related_strength(a, b) is not None

    def related_strength(self, a: str, b: str) -> int | None:
        """Size of the smallest group holding both skills (smaller = closer), or None if unrelated."""
        sizes = [len(g) for g in self.groups if a != b and a in g and b in g]
        return min(sizes) if sizes else None

    def keyword_scan(self, text: str) -> dict[str, str]:
        """Deterministic extractor: {canonical: evidence snippet} for every vocabulary term in text."""
        found: dict[str, str] = {}
        low = text.lower()
        for term in self.vocabulary:
            pat = r"(?<![\w+#])" + re.escape(term) + r"(?![\w+#])"
            m = re.search(pat, low)
            if m:
                canon = self.alias_to_canon[term]
                if canon not in found:
                    found[canon] = snippet(text, m.start(), m.end())
        return found


@lru_cache
def get_normalizer() -> Normalizer:
    return Normalizer(settings.aliases_path)
