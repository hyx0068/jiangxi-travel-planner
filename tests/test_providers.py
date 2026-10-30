from __future__ import annotations

from trip_planner.providers import MockRouteProvider, MockWeatherProvider


def test_mock_route_positive() -> None:
    info = MockRouteProvider().route((28.68, 115.86), (28.78, 115.72))
    assert info.minutes > 0
    assert info.distance_km > 0
    assert info.provider == "mock"


def test_mock_weather(poi_repo) -> None:
    city = poi_repo.get_city("nanchang")
    info = MockWeatherProvider().weather(city, "2026-11-01")
    assert info.city == "南昌"
    assert info.temperature
