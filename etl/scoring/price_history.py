"""Accumulates a compact daily price-history rollup per product, appended
(never overwritten) to sharded JSON files under site/price-history/ -- next
to site/products/, since this needs to be both git-committed (like the rest
of data/processed) AND servable to the client (like products.json's shards),
and site/ already gets both from the daily workflow's own commit step.

This is the only way to build a genuine multi-year price trend: none of the
source chain portals expose historical files. Verified repeatedly and from
multiple independent angles (29.08.2026-30.08.2026): the Shufersal portal's
listing table shows only the current file per store/category; direct,
unsigned requests to the Azure Blob Storage container behind it return
ResourceNotFound (the download links are single-use SAS-signed by the
portal, always pointing at the current file); the Wayback Machine has
archived the portal's *listing page* since 2015 (2,943 captures), but never
the actual price files themselves -- their storage domain has zero Wayback
captures, confirmed via the CDX API, because a generic web crawler never
followed the signed download links. There is no legal/free path to
backfill real per-product history from before this project started
(26.08.2026) -- the
series here starts near-empty and grows by one point per daily run,
forever. See compute_sitewide_index_point() below for the project's own
aggregate index, built from nothing but this same accumulated data --
replaced the earlier CBS food-CPI benchmark (etl/enrich/cbs_cpi.py, removed)
per explicit user preference for a number the project computes itself over
one borrowed from an external, non-reproducible source.

Sharded the same way as products.json (etl/render/product.py's
shard_key()) so a product page's history fetch is one small file.
"""
from __future__ import annotations

import json
import pathlib

from etl.render.product import StorePrice, shard_key


def compute_daily_rollup(all_store_prices: dict[str, list[StorePrice]], date: str) -> dict[str, dict]:
    """One compact entry per product for `date` -- cheap/avg/expensive price
    and store count, not every store's own price, so the accumulated file
    stays small as days add up."""
    rollup: dict[str, dict] = {}
    for code, prices in all_store_prices.items():
        if not prices:
            continue
        values = [p.price for p in prices]
        rollup[code] = {
            "date": date,
            "cheap": min(values),
            "avg": round(sum(values) / len(values), 2),
            "expensive": max(values),
            "n": len(values),
        }
    return rollup


def append_daily_rollup(rollup: dict[str, dict], history_dir: pathlib.Path) -> None:
    """Appends today's entry to each product's shard file. Reruns for the
    same date replace that date's entry instead of duplicating it, so the
    daily workflow can run more than once a day (it does, per
    daily_snapshot.py's own docstring) without the chart growing fake
    same-day points."""
    history_dir.mkdir(parents=True, exist_ok=True)
    by_shard: dict[str, dict[str, dict]] = {}
    for code, entry in rollup.items():
        by_shard.setdefault(shard_key(code), {})[code] = entry

    for shard, entries in by_shard.items():
        path = history_dir / f"{shard}.json"
        existing: dict[str, list[dict]] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        # Self-healing: collapses any duplicate dates already on disk (e.g.
        # from an interleaved local dev run using a fixed placeholder date)
        # down to one entry per date before appending today's, instead of
        # only ever guarding the entry this call is about to add.
        for code in existing:
            deduped: dict[str, dict] = {}
            for e in existing[code]:
                deduped[e["date"]] = e
            existing[code] = sorted(deduped.values(), key=lambda e: e["date"])

        for code, entry in entries.items():
            series = existing.setdefault(code, [])
            replaced = False
            for i, existing_entry in enumerate(series):
                if existing_entry["date"] == entry["date"]:
                    series[i] = entry
                    replaced = True
                    break
            if not replaced:
                series.append(entry)
                series.sort(key=lambda e: e["date"])
        path.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")


def compute_sitewide_index_point(history_dir: pathlib.Path, date: str) -> float | None:
    """The project's own price index for `date`: for every product with a
    recorded entry on `date` and at least one earlier entry, the ratio of
    `date`'s avg price to that product's first-ever recorded avg price
    (its baseline); the index is 100 * the median of those ratios. Same
    underlying idea as a consumer price index (relative movement across a
    basket of goods), but reproducible end to end from nothing but this
    project's own accumulated daily rollups -- no external, non-verifiable
    statistic. On the very first day a product is recorded, its own ratio
    is exactly 1.0 (today's entry IS the baseline), so the index reads
    100.0 while every product is brand new -- expected, not a bug.

    Call this AFTER append_daily_rollup() has already written `date`'s
    entry into every shard, so today's entry is actually there to find.
    Returns None if history_dir has no data at all yet.
    """
    ratios: list[float] = []
    for path in sorted(history_dir.glob("*.json")):
        shard = json.loads(path.read_text(encoding="utf-8"))
        for series in shard.values():
            if not series:
                continue
            baseline = series[0]["avg"]
            today_entry = next((e for e in series if e["date"] == date), None)
            if today_entry is None or baseline <= 0:
                continue
            ratios.append(today_entry["avg"] / baseline)

    if not ratios:
        return None
    ratios.sort()
    mid = len(ratios) // 2
    median = ratios[mid] if len(ratios) % 2 else (ratios[mid - 1] + ratios[mid]) / 2
    return round(median * 100, 2)


def append_sitewide_index_point(index_path: pathlib.Path, date: str, value: float) -> None:
    """Appends today's sitewide index value to a single flat series (not
    sharded -- one number a day, stays tiny). Self-heals duplicate dates
    the same way append_daily_rollup does for per-product series."""
    points: list[dict] = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    deduped = {p["date"]: p for p in points}
    deduped[date] = {"date": date, "value": value}
    index_path.write_text(
        json.dumps(sorted(deduped.values(), key=lambda p: p["date"]), ensure_ascii=False),
        encoding="utf-8",
    )
