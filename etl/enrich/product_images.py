"""Product images from Open Food Facts -- free, no API key. Coverage is
partial (verified: 2/2 real Tnuva barcodes from our own catalog matched
with a real image; 2/5 random non-dairy barcodes matched, both non-Israeli
brands), so every caller must handle `None` with a real UI fallback, not
assume every product has a picture. Results are cached permanently to disk
since a product's image essentially never changes.
"""
from __future__ import annotations

import json
import pathlib
import time

import requests

OFF_API_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
USER_AGENT = "FrodoProject-price-transparency-pilot/0.1 (github.com/yamor321/frodo-project)"
REQUEST_TIMEOUT = 15
RATE_LIMIT_SECONDS = 0.6
MAX_RETRIES = 3

CACHE_PATH = pathlib.Path(__file__).resolve().parents[2] / "data" / "processed" / "image_cache.json"


def _load_cache() -> dict[str, str | None]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache: dict[str, str | None]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def get_image_url(barcode: str, cache: dict[str, str | None] | None = None) -> str | None:
    """Look up one barcode's product image. Pass a shared `cache` dict
    across calls in the same run to also skip in-memory duplicates before
    they hit the on-disk cache.
    """
    owns_cache = cache is None
    if cache is None:
        cache = _load_cache()

    if barcode in cache:
        return cache[barcode]

    resp = None
    for attempt in range(MAX_RETRIES):
        resp = requests.get(
            OFF_API_URL.format(barcode=barcode),
            params={"fields": "image_front_url,image_front_small_url"},
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 429:
            # A batch of ~170+ lookups with no pacing hit Open Food Facts'
            # rate limit in practice -- back off (honoring Retry-After when
            # given) and retry instead of failing the whole batch.
            wait = float(resp.headers.get("Retry-After", 2 * (attempt + 1)))
            time.sleep(wait)
            continue
        break
    time.sleep(RATE_LIMIT_SECONDS)

    # Open Food Facts is inconsistent about "not found": some barcodes come
    # back 200 with status:0, others come back a plain 404 -- both mean the
    # same thing here (no product on file), not an error worth failing the
    # whole batch over.
    if resp.status_code == 404:
        cache[barcode] = None
        if owns_cache:
            _save_cache(cache)
        return None
    resp.raise_for_status()
    data = resp.json()

    url = None
    if data.get("status") == 1:
        product = data.get("product", {})
        # Prefer the ~400px "display" resolution over the ~100px small one
        # (a bit bigger than CHP's own 23x23 thumbnails, per the request) --
        # coverage of the two fields isn't confirmed identical per-product,
        # so fall back rather than assume the bigger one is always present.
        url = product.get("image_front_url") or product.get("image_front_small_url") or None

    cache[barcode] = url
    if owns_cache:
        _save_cache(cache)
    return url


def get_image_urls(barcodes: list[str]) -> dict[str, str | None]:
    """Look up several barcodes, sharing one cache load/save across all of
    them. Only barcodes not already cached hit the network.
    """
    cache = _load_cache()
    results = {}
    for barcode in barcodes:
        results[barcode] = get_image_url(barcode, cache=cache)
    _save_cache(cache)
    return results
