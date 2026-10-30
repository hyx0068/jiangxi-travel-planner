from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .config import GUIDES_DB, GUIDES_DIR

try:
    import jieba

    jieba.setLogLevel(20)
except Exception:  # pragma: no cover - jieba is optional for tiny deployments
    jieba = None


@dataclass
class GuideHit:
    doc_id: str
    doc_name: str
    heading: str
    content: str
    score: float = 0.0
    chunk_id: int = 0
    bm25_rank: int | None = None
    vector_rank: int | None = None
    bm25_score: float = 0.0
    vector_score: float = 0.0

    def snippet(self, limit: int = 180) -> str:
        text = re.sub(r"\s+", " ", self.content).strip()
        return text[:limit] + ("..." if len(text) > limit else "")

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "doc_name": self.doc_name,
            "heading": self.heading,
            "snippet": self.snippet(),
            "score": round(self.score, 4),
            "bm25_rank": self.bm25_rank,
            "vector_rank": self.vector_rank,
            "bm25_score": round(self.bm25_score, 4),
            "vector_score": round(self.vector_score, 4),
        }


def tokenize(text: str) -> list[str]:
    value = (text or "").strip()
    if not value:
        return []
    if jieba is not None:
        raw = jieba.lcut(value)
    else:
        raw = re.split(r"[\s,，。！？、;；/|]+", value)
    tokens = []
    for token in raw:
        token = token.strip().lower()
        if len(token) < 1:
            continue
        if re.fullmatch(r"[\W_]+", token):
            continue
        tokens.append(token)
    return tokens


def _chunks_from_markdown(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    title = path.stem
    chunks = []
    heading = "概览"
    buffer: list[str] = []
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip() or title
        elif line.startswith("## "):
            if buffer:
                chunks.append(
                    {"doc_id": path.stem, "doc_name": title, "heading": heading, "content": "\n".join(buffer).strip()}
                )
            heading = line[3:].strip()
            buffer = []
        elif line.strip():
            buffer.append(line.strip())
    if buffer:
        chunks.append(
            {"doc_id": path.stem, "doc_name": title, "heading": heading, "content": "\n".join(buffer).strip()}
        )
    return [chunk for chunk in chunks if chunk["content"]]


class GuideIndex:
    def __init__(self, db_path: str | Path = GUIDES_DB, guides_dir: str | Path = GUIDES_DIR):
        self.db_path = Path(db_path)
        self.guides_dir = Path(guides_dir)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.vector = None
        self.vector_error = ""
        self.ensure()
        self._ensure_vector_store()

    def ensure(self) -> None:
        if not self.db_path.exists():
            self.rebuild()
            return
        conn = sqlite3.connect(self.db_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        finally:
            conn.close()
        if count == 0:
            self.rebuild()

    def rebuild(self) -> None:
        if self.db_path.exists():
            self.db_path.unlink()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(
                """
                CREATE TABLE chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT NOT NULL,
                    doc_name TEXT NOT NULL,
                    heading TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tokens TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE chunks_fts USING fts5(
                    tokens, content, doc_name, heading, tokenize='unicode61'
                );
                """
            )
            for path in sorted(self.guides_dir.glob("*.md")):
                for chunk in _chunks_from_markdown(path):
                    tokens = " ".join(tokenize(chunk["content"] + " " + chunk["heading"]))
                    cur = conn.execute(
                        "INSERT INTO chunks (doc_id, doc_name, heading, content, tokens) VALUES (?, ?, ?, ?, ?)",
                        (chunk["doc_id"], chunk["doc_name"], chunk["heading"], chunk["content"], tokens),
                    )
                    conn.execute(
                        "INSERT INTO chunks_fts (rowid, tokens, content, doc_name, heading) VALUES (?, ?, ?, ?, ?)",
                        (cur.lastrowid, tokens, chunk["content"], chunk["doc_name"], chunk["heading"]),
                    )
            conn.commit()
        finally:
            conn.close()
        self.vector = None
        self._ensure_vector_store(force=True)

    def _ensure_vector_store(self, force: bool = False) -> None:
        if not force and self.vector is not None:
            return
        try:
            from .vector_rag import ChromaGuideRetriever

            self.vector = ChromaGuideRetriever(self.guides_dir)
            self.vector_error = self.vector.error
        except Exception as exc:
            self.vector = None
            self.vector_error = f"{type(exc).__name__}: {exc}"

    def search(self, city: str, query: str, limit: int = 5) -> list[GuideHit]:
        tokens = tokenize(query)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            if tokens:
                match = " OR ".join('"' + token.replace('"', "") + '"' for token in tokens[:8])
                rows = conn.execute(
                    """
                    SELECT c.*, bm25(chunks_fts) AS rank
                    FROM chunks_fts
                    JOIN chunks c ON c.id = chunks_fts.rowid
                    WHERE chunks_fts MATCH ? AND c.doc_id = ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (match, city, max(limit * 3, 10)),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT *, 0 AS rank FROM chunks WHERE doc_id = ? LIMIT ?",
                    (city, max(limit * 3, 10)),
                ).fetchall()
            bm25_hits = [
                GuideHit(
                    doc_id=row["doc_id"],
                    doc_name=row["doc_name"],
                    heading=row["heading"],
                    content=row["content"],
                    score=abs(float(row["rank"] or 0)),
                    chunk_id=int(row["id"]),
                    bm25_rank=index + 1,
                    bm25_score=abs(float(row["rank"] or 0)),
                )
                for index, row in enumerate(rows)
            ]
        finally:
            conn.close()

        if self.vector is None or not self.vector.enabled:
            return bm25_hits[:limit]

        combined: dict[tuple[str, str], GuideHit] = {
            (hit.doc_id, hit.heading): hit for hit in bm25_hits
        }
        for vector_rank, vector_hit in enumerate(
            self.vector.search(city, query, limit=max(limit * 3, 10)), start=1
        ):
            key = (vector_hit.doc_id, vector_hit.heading)
            current = combined.get(key)
            if current is None:
                current = GuideHit(
                    doc_id=vector_hit.doc_id,
                    doc_name=vector_hit.doc_name,
                    heading=vector_hit.heading,
                    content=vector_hit.content,
                    score=vector_hit.similarity,
                    vector_rank=vector_rank,
                    vector_score=vector_hit.similarity,
                )
                combined[key] = current
            else:
                current.vector_rank = vector_rank
                current.vector_score = vector_hit.similarity

        for hit in combined.values():
            rrf = 0.0
            if hit.bm25_rank:
                rrf += 0.7 / (60 + hit.bm25_rank)
            if hit.vector_rank:
                rrf += 0.3 / (60 + hit.vector_rank)
            hit.score = rrf
        return sorted(combined.values(), key=lambda hit: hit.score, reverse=True)[:limit]
