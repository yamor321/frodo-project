"""Sticky store name/address directory, keyed by namespaced store id.

A store's name and physical address barely ever change day to day, unlike
its price catalog -- but daily_snapshot.py only ever learns them from a
chain's live Stores file, fetched fresh every run. When a chain's whole host
is unreachable (see etl/raw_snapshot_fallback.py), there's no live Stores
file that day either, so a store falling back to yesterday's prices would
otherwise have no name/address to render a page with. This directory is
updated with every successfully-seen store every run and read back only for
stores missing from that run's own live results -- same self-healing-cache
shape as etl/enrich/geocode.py and etl/enrich/product_images.py.
"""
from __future__ import annotations

import json
import pathlib

CACHE_PATH = pathlib.Path(__file__).resolve().parents[2] / "data" / "processed" / "store_directory.json"


def load_directory() -> dict[str, dict[str, str]]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_directory(directory: dict[str, dict[str, str]]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(directory, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def update_and_save(store_names: dict[str, str], store_addresses: dict[str, str]) -> dict[str, dict[str, str]]:
    """Merge today's live results into the persistent directory and save.
    Never removes an entry -- a store missing from today's live results
    (the exact case this exists for) should keep its last-known name/address,
    not lose it."""
    directory = load_directory()
    for store_id, name in store_names.items():
        entry = directory.setdefault(store_id, {})
        entry["name"] = name
        if store_id in store_addresses:
            entry["address"] = store_addresses[store_id]
    save_directory(directory)
    return directory
