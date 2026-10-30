from __future__ import annotations

from trip_planner.models import TripRequest
from trip_planner.planner import TripPlanner
from trip_planner.poi import POIRepository
from trip_planner.rag import GuideIndex


def _request(budget: float = 5000) -> TripRequest:
    return TripRequest(
        city="nanchang",
        start_date="2026-11-01",
        days=4,
        budget=budget,
        origin="上海",
        preferences="美食、人文、不赶",
        pace="relaxed",
    )


def test_builds_balanced_four_day_plan(poi_repo: POIRepository, guide_index: GuideIndex) -> None:
    planner = TripPlanner(poi_repo=poi_repo, guide_index=guide_index)
    plan = planner.build(_request())
    assert len(plan.days) == 4
    assert all(1 <= sum(1 for item in day.items if item.kind == "poi") <= 2 for day in plan.days)
    assert all(day.items[-1].end >= "18:00" for day in plan.days)
    assert plan.total_cost <= 5000
    assert plan.citations
    assert not [issue for issue in plan.issues if issue.severity == "high"]


def test_over_budget_is_reported(poi_repo: POIRepository, guide_index: GuideIndex) -> None:
    planner = TripPlanner(poi_repo=poi_repo, guide_index=guide_index)
    plan = planner.build(_request(budget=500))
    assert any(issue.code == "over_budget" for issue in plan.issues)


def test_closed_museum_is_not_scheduled_on_monday(poi_repo: POIRepository, guide_index: GuideIndex) -> None:
    planner = TripPlanner(poi_repo=poi_repo, guide_index=guide_index)
    request = TripRequest(
        city="nanchang",
        start_date="2026-11-02",  # Monday
        days=2,
        budget=4000,
        preferences="博物馆",
        pace="balanced",
    )
    plan = planner.build(request)
    for day in plan.days:
        if day.date == "2026-11-02":
            assert all(item.poi_id != "nc_aug1_museum" for item in day.items)


def test_budget_utilization_is_close_to_requested_budget(
    poi_repo: POIRepository, guide_index: GuideIndex
) -> None:
    planner = TripPlanner(poi_repo=poi_repo, guide_index=guide_index)
    plan = planner.build(
        TripRequest(
            city="nanchang",
            start_date="2026-11-06",
            days=3,
            budget=3000,
            travelers=2,
            preferences="美食、人文",
            pace="balanced",
        )
    )
    assert plan.total_cost <= 3000
    assert 0.90 <= plan.total_cost / 3000 <= 0.98
    assert any(item.category == "experience" for item in plan.budget_items)
