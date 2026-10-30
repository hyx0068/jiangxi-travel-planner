from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import httpx

from .config import (
    CHROMA_DIR,
    EMBEDDING_API_KEY,
    EMBEDDING_BASE_URL,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    GUIDES_DIR,
)


HASH_DIMENSION = 384


@dataclass
class VectorHit:
    doc_id: str
    doc_name: str
    heading: str
    content: str
    similarity: float


class HashingEmbedding:
    """Lightweight deterministic n-gram embedding that needs no model download."""

    name = "hash"

    def __init__(self, dimension: int = HASH_DIMENSION):
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        value = re.sub(r"\s+", "", (text or "").lower())
        counts: Counter[str] = Counter()
        for width in (2, 3, 4):
            for index in range(max(0, len(value) - width + 1)):
                counts[value[index : index + width]] += 1
        vector = [0.0] * self.dimension
        for token, count in counts.items():
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest, "big") % self.dimension
            vector[bucket] += math.log1p(count)
        norm = math.sqrt(sum(item * item for item in vector))
        if norm:
            vector = [item / norm for item in vector]
        return vector


class OpenAICompatibleEmbedding:
    """Use an OpenAI-compatible /embeddings endpoint, for example Qwen."""

    name = "openai_compatible"

    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 20.0):
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.configured:
            raise RuntimeError("Embedding API is not configured")
        response = httpx.post(
            f"{self.base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={"model": self.model, "input": texts},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        rows = sorted(payload["data"], key=lambda row: row.get("index", 0))
        return [row["embedding"] for row in rows]


def make_embedding_provider():
    if EMBEDDING_PROVIDER != "hash" and EMBEDDING_API_KEY:
        provider = OpenAICompatibleEmbedding(
            EMBEDDING_API_KEY, EMBEDDING_BASE_URL, EMBEDDING_MODEL
        )
        if provider.configured:
            return provider
    return HashingEmbedding()


def _chunks_from_guides(guides_dir: Path) -> list[dict]:
    chunks: list[dict] = []
    for path in sorted(guides_dir.glob("*.md")):
        title = path.stem
        heading = "概览"
        buffer: list[str] = []
        file_chunks: list[dict] = []

        def flush() -> None:
            content = "\n".join(buffer).strip()
            if content:
                file_chunks.append(
                    {
                        "doc_id": path.stem,
                        "doc_name": title,
                        "heading": heading,
                        "content": content,
                    }
                )

        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                title = line[2:].strip() or title
            elif line.startswith("## "):
                flush()
                buffer = []
                heading = line[3:].strip()
            elif line.strip():
                buffer.append(line.strip())
        flush()
        for index, item in enumerate(file_chunks):
            chunks.append({**item, "id": f"{path.stem}:{index}"})
    return chunks


class ChromaGuideRetriever:
    def __init__(self, guides_dir: str | Path = GUIDES_DIR, persist_dir: str | Path = CHROMA_DIR):
        self.guides_dir = Path(guides_dir)
        self.persist_dir = Path(persist_dir)
        self.embedder = make_embedding_provider()
        self.error = ""
        self.collection = None

        try:
            import chromadb
            from chromadb.config import Settings

            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False),
            )
            self.chunks = _chunks_from_guides(self.guides_dir)
            self.collection = self._ensure_collection()
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"

    @property
    def enabled(self) -> bool:
        return self.collection is not None

    @property
    def label(self) -> str:
        return self.embedder.name if self.enabled else "unavailable"

    def _ensure_collection(self):
        if not self.chunks:
            return None
        corpus = "\n".join(
            f"{item['id']}|{item['heading']}|{item['content']}" for item in self.chunks
        )
        digest = hashlib.sha256(
            f"{self.embedder.name}:{EMBEDDING_MODEL}:{corpus}".encode("utf-8")
        ).hexdigest()[:12]
        name = f"jiangxi_guides_v1_{digest}"
        collection = self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine", "embedding": self.embedder.name},
        )
        if collection.count() < len(self.chunks):
            embeddings = self.embedder.embed([item["content"] for item in self.chunks])
            collection.upsert(
                ids=[item["id"] for item in self.chunks],
                documents=[item["content"] for item in self.chunks],
                metadatas=[
                    {
                        "doc_id": item["doc_id"],
                        "doc_name": item["doc_name"],
                        "heading": item["heading"],
                    }
                    for item in self.chunks
                ],
                embeddings=embeddings,
            )
        return collection

    def search(self, city: str, query: str, limit: int = 6) -> list[VectorHit]:
        if not self.enabled:
            return []
        try:
            embedding = self.embedder.embed([query])[0]
            result = self.collection.query(
                query_embeddings=[embedding],
                n_results=min(max(limit, 1), max(1, self.collection.count())),
                where={"doc_id": city},
                include=["documents", "metadatas", "distances"],
            )
            ids = (result.get("ids") or [[]])[0]
            documents = (result.get("documents") or [[]])[0]
            metadatas = (result.get("metadatas") or [[]])[0]
            distances = (result.get("distances") or [[]])[0]
            return [
                VectorHit(
                    doc_id=meta["doc_id"],
                    doc_name=meta["doc_name"],
                    heading=meta["heading"],
                    content=document,
                    similarity=max(0.0, 1.0 - float(distance)),
                )
                for _, document, meta, distance in zip(
                    ids, documents, metadatas, distances
                )
            ]
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            return []
