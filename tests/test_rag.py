from __future__ import annotations

from trip_planner.rag import GuideIndex


def test_guide_search_returns_citation(guide_index: GuideIndex) -> None:
    hits = guide_index.search("nanchang", "美食 拌粉", limit=3)
    assert hits
    assert hits[0].doc_id == "nanchang"
    assert hits[0].snippet()
    assert hits[0].heading


def test_guide_search_is_city_scoped(guide_index: GuideIndex) -> None:
    hits = guide_index.search("jingdezhen", "陶瓷", limit=3)
    assert all(hit.doc_id == "jingdezhen" for hit in hits)
