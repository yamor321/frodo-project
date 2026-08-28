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

DEFAULT_CITY = "כפר סבא"
DEFAULT_COUNTRY = "ישראל"

# Rough municipal extent of Kfar Saba, with a small margin. Used both to
# constrain the Nominatim search itself (viewbox+bounded) and as a
# defensive check on whatever it returns -- a bounded query can still
# return a same-city-but-wrong-street match, so this alone doesn't fix
# precision, but it stops a result from ever landing outside the town.
KFAR_SABA_BOUNDS = {"min_lat": 32.14, "max_lat": 32.21, "min_lon": 34.86, "max_lon": 34.95}

CACHE_PATH = pathlib.Path(__file__).resolve().parents[2] / "data" / "processed" / "geocode_cache.json"


def _within_kfar_saba_bounds(lat: float, lon: float) -> bool:
    b = KFAR_SABA_BOUNDS
    return b["min_lat"] <= lat <= b["max_lat"] and b["min_lon"] <= lon <= b["max_lon"]


def _is_specific_street(street: str) -> bool:
    """Reject an address that's really just the city name repeated -- the
    actual cause of two real stores (Shufersal 615 and 140) collapsing to
    Kfar Saba's city centroid: their Stores.xml Address field held the
    literal string "כפר סבא" with no street, which passed a bare
    truthiness check but isn't specific enough to geocode meaningfully."""
    normalized = street.strip()
    return bool(normalized) and normalized not in {"כפר סבא", "כפר-סבא"}


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


def geocode(
    street: str,
    city: str = DEFAULT_CITY,
    country: str = DEFAULT_COUNTRY,
    cache: dict[str, dict] | None = None,
) -> GeoPoint | None:
    """Geocode one street address via Nominatim's *structured* search
    (separate street/city/country fields) rather than one free-text blob --
    structured queries match the street field directly instead of fuzzy
    full-text matching across a concatenated string, which is what let
    genuinely wrong-street results ("close but not the real address")
    through before. The search is also bounded to Kfar Saba's extent, and
    the result is checked against that same box before being trusted.

    Pass a shared `cache` dict across calls in the same run to also skip
    in-memory duplicates before they hit the on-disk cache.
    """
    owns_cache = cache is None
    if cache is None:
        cache = _load_cache()

    display_query = f"{street}, {city}, {country}"
    if display_query in cache:
        entry = cache[display_query]
        if entry is None:
            return None
        if _is_specific_street(street) and _within_kfar_saba_bounds(entry["lat"], entry["lon"]):
            return GeoPoint(entry["lat"], entry["lon"])
        # A result cached before these checks existed -- re-validate against
        # current rules instead of trusting stale data forever; falls
        # through and re-resolves (or is rejected outright) below.

    if not _is_specific_street(street):
        cache[display_query] = None
        if owns_cache:
            _save_cache(cache)
        return None

    b = KFAR_SABA_BOUNDS
    resp = requests.get(
        NOMINATIM_URL,
        params={
            "street": street,
            "city": city,
            "country": country,
            "format": "json",
            "limit": 1,
            "viewbox": f"{b['min_lon']},{b['max_lat']},{b['max_lon']},{b['min_lat']}",
            "bounded": 1,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    results = resp.json()
    time.sleep(RATE_LIMIT_SECONDS)

    point = None
    if results:
        lat, lon = float(results[0]["lat"]), float(results[0]["lon"])
        if _within_kfar_saba_bounds(lat, lon):
            point = GeoPoint(lat, lon)

    cache[display_query] = {"lat": point.lat, "lon": point.lon} if point else None
    if owns_cache:
        _save_cache(cache)
    return point


def geocode_many(
    streets: list[str], city: str = DEFAULT_CITY, country: str = DEFAULT_COUNTRY
) -> dict[str, GeoPoint | None]:
    """Geocode several street addresses, sharing one cache load/save and one
    rate-limited session across all of them. Keyed by the raw street string.
    """
    cache = _load_cache()
    results = {}
    for street in streets:
        results[street] = geocode(street, city=city, country=country, cache=cache)
    _save_cache(cache)
    return results
