"""Local deterministic embeddings for model-independent Phase 1 retrieval."""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


class LocalLexicalEmbedder:
    """Tiny stable embedding that requires no external model provider.

    It hashes tokens into a fixed-size vector. This is not a model-weight system;
    it is a portable retrieval primitive and can be replaced by any provider.
    """

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
        counts = Counter(tokens)
        vector = [0.0] * self.dimensions
        for token, count in counts.items():
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [round(v / norm, 6) for v in vector]

    @staticmethod
    def cosine(left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        size = min(len(left), len(right))
        return sum(left[i] * right[i] for i in range(size))
