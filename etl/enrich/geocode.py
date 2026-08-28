"""Geocodes branch addresses to lat/lon using Nominatim (OpenStreetMap) --
free, no API key. Results are cached to disk since store addresses almost
never change; only new/uncached addresses trigger a network call, respecting
Nominatim's usage policy (max 1 request/second, identifying User-Agent).
"""
from __future__ import annotations

import json
import pathlib
import time
from dataclasses import dataclass

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "FrodoProject-price-transparency-pilot/0.1 (github.com/yamor321/frodo-project)"
REQUEST_TIMEOUT = 15
RATE_LIMIT_SECONDS = 1.1

CACHE_PATH = pathlib.Path(__file__).resolve().parents[2] / "data" / "processed" / "geocode_cache.json"


@dataclass
class GeoPoint:
    lat: float
    lon: float


def _load_cache() -> dict[str, dict]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache: dict[str, dict]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def geocode(query: str, cache: dict[str, dict] | None = None) -> GeoPoint | None:
    """Geocode one free-text address query. Pass a shared `cache` dict across
    calls in the same run to also skip in-memory duplicates before they hit
    the on-disk cache.
    """
    owns_cache = cache is None
    if cache is None:
        cache = _load_cache()

    if query in cache:
        entry = cache[query]
        return GeoPoint(entry["lat"], entry["lon"]) if entry else None

    resp = requests.get(
        NOMINATIM_URL,
        params={"q": query, "format": "json", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    results = resp.json()
    time.sleep(RATE_LIMIT_SECONDS)

    point = GeoPoint(float(results[0]["lat"]), float(results[0]["lon"])) if results else None
    cache[query] = {"lat": point.lat, "lon": point.lon} if point else None
    if owns_cache:
        _save_cache(cache)
    return point


def geocode_many(queries: list[str]) -> dict[str, GeoPoint | None]:
    """Geocode several addresses, sharing one cache load/save and one
    rate-limited session across all of them.
    """
    cache = _load_cache()
    results = {}
    for q in queries:
        results[q] = geocode(q, cache=cache)
    _save_cache(cache)
    return results
