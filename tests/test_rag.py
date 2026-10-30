from __future__ import annotations

from trip_planner.rag import GuideIndex


def test_guide_search_returns_citation(guide_index: GuideIndex) -> None:
    hits = guide_index.search("nanchang", "美食 拌粉", limit=3)
    assert hits
    assert hits[0].doc_id == "nanchang"
    assert hits[0].snippet()
    assert hits[0].heading
    assert hits[0].bm25_rank is not None
    assert hits[0].vector_rank is not None


def test_guide_search_is_city_scoped(guide_index: GuideIndex) -> None:
    hits = guide_index.search("jingdezhen", "陶瓷", limit=3)
    assert all(hit.doc_id == "jingdezhen" for hit in hits)


def test_hybrid_search_exposes_rank_fusion(guide_index: GuideIndex) -> None:
    assert guide_index.vector is not None
    assert guide_index.vector.enabled
    hits = guide_index.search("shangrao", "婺源古村和夜游", limit=4)
    assert hits
    assert any(hit.vector_rank is not None for hit in hits)
    assert hits == sorted(hits, key=lambda hit: hit.score, reverse=True)


def test_guide_search_falls_back_to_bm25(guide_index: GuideIndex) -> None:
    guide_index.vector = None
    hits = guide_index.search("nanchang", "美食", limit=3)
    assert hits
    assert all(hit.vector_rank is None for hit in hits)
