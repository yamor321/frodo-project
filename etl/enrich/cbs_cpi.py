"""Fetches Israel's official food CPI sub-index (Central Bureau of
Statistics -- "index 110050, מזון כולל ירקות ופירות", verified live
29.08.2026 via api.cbs.gov.il) for the price-history benchmark line on
product pages (etl/render/product.py). This is a real, public, monthly
series going back decades -- unlike our own per-product price history
(etl/scoring/price_history.py, which only started 26.08.2026 since none of
the source chain portals expose historical files), it gives genuine
years-long context from day one. It's a national category index, not this
project's own per-barcode price -- shown as background context, not as a
substitute for the real (short, growing) per-product line.

Cached to disk (data/processed/cbs_food_cpi.json) since CBS only publishes
once a month, on the 15th -- refetching on every build would be pointless
network traffic. Never raises on a failed fetch: falls back to whatever is
cached (even if stale), or an empty series if nothing is cached yet, since
a benchmark line failing to load shouldn't break the whole page.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import asdict, dataclass

import requests

CBS_FOOD_CPI_URL = "https://api.cbs.gov.il/index/data/price?id=110050&format=json&download=false"
REQUEST_TIMEOUT = 20


@dataclass
class CpiPoint:
    year: int
    month: int
    value: float  # index level, 2024 average = 100 (CBS's "currBase" for this series)


def fetch_food_cpi_series() -> list[CpiPoint]:
    """Live fetch, oldest-first (the API itself returns newest-first)."""
    resp = requests.get(CBS_FOOD_CPI_URL, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    dates = resp.json()["month"][0]["date"]
    points = [
        CpiPoint(year=d["year"], month=d["month"], value=d["currBase"]["value"])
        for d in dates
        if d.get("currBase") and d["currBase"].get("value") is not None
    ]
    points.sort(key=lambda p: (p.year, p.month))
    return points


def load_cached_food_cpi(cache_path: pathlib.Path) -> list[CpiPoint]:
    """Read-only, no network -- for scripts/build_site.py's offline dev
    loop (its own docstring: "no network calls, fast to iterate on").
    Returns whatever's cached, or an empty list if nothing's been fetched
    yet (the homepage/product chart just shows no benchmark line)."""
    if not cache_path.exists():
        return []
    cached = json.loads(cache_path.read_text(encoding="utf-8"))
    return [CpiPoint(**p) for p in cached["points"]]


def load_or_fetch_food_cpi(cache_path: pathlib.Path, today_ym: str) -> list[CpiPoint]:
    """`today_ym` is the caller's "YYYY-MM" for today -- passed in rather
    than computed here so this stays deterministic/testable. Refetches only
    when the cache is missing or from an earlier month than today's."""
    if cache_path.exists():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if cached.get("fetched_month") == today_ym:
            return [CpiPoint(**p) for p in cached["points"]]

    try:
        points = fetch_food_cpi_series()
    except Exception:
        if cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            return [CpiPoint(**p) for p in cached["points"]]
        return []

    cache_path.write_text(
        json.dumps({"fetched_month": today_ym, "points": [asdict(p) for p in points]}, ensure_ascii=False),
        encoding="utf-8",
    )
    return points
