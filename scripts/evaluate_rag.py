"""Evaluate city-scoped BM25 and hybrid retrieval on a small labelled set."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trip_planner.rag import GuideIndex  # noqa: E402


def run(index: GuideIndex, mode: str, cases: list[dict], k: int = 3) -> dict:
    rows = []
    reciprocal_ranks = []
    for case in cases:
        hits = index.search(case["city"], case["query"], limit=k)
        rank = None
        for position, hit in enumerate(hits, start=1):
            if case["expected"] in hit.heading or case["expected"] in hit.content:
                rank = position
                break
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
        rows.append(
            {
                "city": case["city"],
                "query": case["query"],
                "expected": case["expected"],
                "rank": rank,
                "headings": [hit.heading for hit in hits],
            }
        )
    return {
        "mode": mode,
        "recall_at_3": round(
            sum(row["rank"] is not None for row in rows) / len(rows), 4
        ),
        "mrr": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4),
        "rows": rows,
    }


def main() -> None:
    cases = json.loads((ROOT / "evals" / "rag_cases.json").read_text(encoding="utf-8"))
    index = GuideIndex()

    hybrid = run(index, "bm25+chroma", cases)
    vector_hit_count = sum(
        1
        for hit in index.search("nanchang", "历史 美食 夜景", limit=8)
        if hit.vector_rank is not None
    )
    vector_available = bool(
        index.vector is not None and index.vector.enabled and vector_hit_count
    )
    index.vector = None
    bm25 = run(index, "bm25", cases)

    report = {
        "cases": len(cases),
        "vector_available": vector_available,
        "hybrid": hybrid,
        "bm25_only": bm25,
    }
    out = ROOT / "reports" / "rag_eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(
        {
            "cases": report["cases"],
            "hybrid_recall_at_3": hybrid["recall_at_3"],
            "hybrid_mrr": hybrid["mrr"],
            "bm25_recall_at_3": bm25["recall_at_3"],
            "bm25_mrr": bm25["mrr"],
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
