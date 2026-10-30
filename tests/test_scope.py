from __future__ import annotations

import pytest

from trip_planner.scope import (
    find_supported_city_in_text,
    normalize_city_name,
    require_supported_city,
    supported_city_names,
)


def test_all_supported_cities_are_in_jiangxi() -> None:
    assert supported_city_names() == [
        "南昌",
        "九江",
        "景德镇",
        "萍乡",
        "新余",
        "鹰潭",
        "赣州",
        "吉安",
        "宜春",
        "抚州",
        "上饶",
    ]


def test_scenic_alias_resolves_to_prefecture_city() -> None:
    assert normalize_city_name("婺源篁岭") == "上饶"
    assert normalize_city_name("庐山") == "九江"
    assert find_supported_city_in_text("去婺源看晒秋") == "上饶"
    assert find_supported_city_in_text("去成都看熊猫") == ""


def test_outside_province_is_rejected(poi_repo) -> None:
    with pytest.raises(ValueError, match="仅支持江西省内目的地"):
        require_supported_city("成都")
    with pytest.raises(ValueError, match="仅支持江西省内目的地"):
        poi_repo.get_city("成都")


def test_only_jiangxi_cities_are_listed(poi_repo) -> None:
    assert {city.name for city in poi_repo.list_cities()} == {
        "南昌",
        "九江",
        "景德镇",
        "上饶",
    }
    assert poi_repo.get_city("庐山").id == "jiujiang"
    assert poi_repo.get_city("婺源").id == "shangrao"


def test_cross_province_dynamic_poi_is_rejected(poi_repo) -> None:
    raw = {
        "name": "省外示例地点",
        "location": "104.0668,30.5728",
        "pname": "四川省",
        "cityname": "成都市",
        "type": "风景名胜",
    }
    assert poi_repo._parse_dynamic_poi(raw, "南昌") is None


def test_uncurated_jiangxi_city_requires_amap(poi_repo) -> None:
    if poi_repo.amap_key:
        pytest.skip("A real Amap key is configured")
    with pytest.raises(ValueError, match="配置高德 API Key"):
        poi_repo.get_city("赣州")
