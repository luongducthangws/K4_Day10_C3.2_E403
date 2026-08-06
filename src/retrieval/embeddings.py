from __future__ import annotations

from functools import lru_cache
import math
import re
from typing import Any

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


class _FallbackEmbeddingModel:
    def encode(self, texts: list[str], normalize_embeddings: bool = True) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            tokens = re.findall(r"\w+", text.lower())
            if not tokens:
                vectors.append([0.0] * 8)
                continue
            vector = [0.0] * 8
            for token in tokens:
                index = sum(ord(ch) for ch in token) % 8
                vector[index] += 1.0
            if normalize_embeddings:
                norm = math.sqrt(sum(value * value for value in vector)) or 1.0
                vector = [value / norm for value in vector]
            vectors.append(vector)
        return vectors


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> Any:
    try:
        return SentenceTransformer(model_name)
    except Exception:
        return _FallbackEmbeddingModel()


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model = _load_model(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()
