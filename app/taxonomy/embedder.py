"""Optional semantic similarity (sentence-transformers). Returns None when unavailable."""
import logging
from functools import lru_cache

import numpy as np

from app.core.config import settings

log = logging.getLogger(__name__)


class Embedder:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self._cache: dict[str, np.ndarray] = {}

    def vec(self, text: str) -> np.ndarray:
        key = text[:2000]
        if key not in self._cache:
            self._cache[key] = self.model.encode(key, normalize_embeddings=True)
        return self._cache[key]

    def sim(self, a: str, b: str) -> float:
        return float(np.dot(self.vec(a), self.vec(b)))


@lru_cache
def get_embedder() -> Embedder | None:
    if settings.offline_mode or not settings.use_embeddings:
        return None
    try:
        return Embedder(settings.embed_model)
    except Exception as e:  # not installed / no network on first download
        log.warning("embeddings disabled: %s", e)
        return None
