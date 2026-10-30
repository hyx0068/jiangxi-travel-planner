from __future__ import annotations

from collections.abc import Iterable


PROVINCE_NAME = "江西省"
PROVINCE_ADCODE = "360000"

# The eleven prefecture-level destinations currently permitted by the product.
JIANGXI_CITIES = {
    "nanchang": "南昌",
    "jiujiang": "九江",
    "jingdezhen": "景德镇",
    "pingxiang": "萍乡",
    "xinyu": "新余",
    "yingtan": "鹰潭",
    "ganzhou": "赣州",
    "jian": "吉安",
    "yichun": "宜春",
    "fuzhou": "抚州",
    "shangrao": "上饶",
}

_CITY_BY_NAME = {name: city_id for city_id, name in JIANGXI_CITIES.items()}

# County names and commonly requested scenic areas resolve to their
# prefecture-level city. This is used before any network lookup.
CITY_ALIASES = {
    "南昌市": "南昌",
    "九江市": "九江",
    "景德镇市": "景德镇",
    "萍乡市": "萍乡",
    "新余市": "新余",
    "鹰潭市": "鹰潭",
    "赣州市": "赣州",
    "吉安市": "吉安",
    "宜春市": "宜春",
    "抚州市": "抚州",
    "上饶市": "上饶",
    "滕王阁": "南昌",
    "万寿宫": "南昌",
    "海昏侯": "南昌",
    "庐山": "九江",
    "浔阳楼": "九江",
    "石钟山": "九江",
    "鄱阳湖": "九江",
    "陶阳里": "景德镇",
    "御窑": "景德镇",
    "瑶里": "景德镇",
    "三宝": "景德镇",
    "武功山": "萍乡",
    "安源": "萍乡",
    "仙女湖": "新余",
    "龙虎山": "鹰潭",
    "上清古镇": "鹰潭",
    "八境台": "赣州",
    "郁孤台": "赣州",
    "通天岩": "赣州",
    "井冈山": "吉安",
    "吉州窑": "吉安",
    "明月山": "宜春",
    "温汤": "宜春",
    "大觉山": "抚州",
    "文昌里": "抚州",
    "汤显祖": "抚州",
    "三清山": "上饶",
    "婺源": "上饶",
    "篁岭": "上饶",
    "望仙谷": "上饶",
    "葛仙村": "上饶",
    "灵山": "上饶",
}


def normalize_city_name(value: str) -> str:
    """Return a canonical Jiangxi city name, or an empty string."""
    text = "".join(str(value or "").strip().lower().split())
    if not text:
        return ""
    for prefix in ("江西省", "江西"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    text = text.removesuffix("市")

    if text in _CITY_BY_NAME:
        return text
    if text in JIANGXI_CITIES:
        return JIANGXI_CITIES[text]
    if text in CITY_ALIASES:
        return CITY_ALIASES[text]
    for alias, city_name in sorted(CITY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if alias and alias in text:
            return city_name
    return ""


def is_supported_city(value: str) -> bool:
    return bool(normalize_city_name(value))


def require_supported_city(value: str) -> str:
    city_name = normalize_city_name(value)
    if not city_name:
        supported = "、".join(JIANGXI_CITIES.values())
        raise ValueError(f"当前仅支持江西省内目的地。可用城市：{supported}。")
    return city_name


def city_id_for(value: str) -> str:
    city_name = require_supported_city(value)
    return _CITY_BY_NAME[city_name]


def supported_city_names() -> list[str]:
    return list(JIANGXI_CITIES.values())


def find_supported_city_in_text(text: str, cities: Iterable[str] | None = None) -> str:
    """Find the most specific Jiangxi place name mentioned in free text."""
    value = str(text or "")
    names = list(cities or supported_city_names())
    named = [name for name in names if name in value]
    if named:
        return max(named, key=len)

    aliases = [
        (alias, city_name)
        for alias, city_name in CITY_ALIASES.items()
        if alias in value and city_name in names
    ]
    if aliases:
        return max(aliases, key=lambda item: len(item[0]))[1]
    return ""


def is_jiangxi_province(value: str) -> bool:
    text = "".join(str(value or "").strip().split())
    return text in {"江西", "江西省"}
