"""Accumulates a compact daily price-history rollup per product, appended
(never overwritten) to sharded JSON files under site/price-history/ -- next
to site/products/, since this needs to be both git-committed (like the rest
of data/processed) AND servable to the client (like products.json's shards),
and site/ already gets both from the daily workflow's own commit step.

This is the only way to build a genuine multi-year price trend: none of the
source chain portals expose historical files (verified live, 29.08.2026 --
the Shufersal transparency portal's listing shows only the current file per
store/category, no date filter, no archive to browse). So there is no way
to backfill real per-product history from before this project started
(26.08.2026) -- the series here starts near-empty and grows by one point
per daily run, forever. See etl/enrich/cbs_cpi.py for the complementary
multi-year *context* line (official food CPI) that's real from day one,
just not per-product.

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
        for code, entry in entries.items():
            series = existing.setdefault(code, [])
            if series and series[-1]["date"] == entry["date"]:
                series[-1] = entry
            else:
                series.append(entry)
        path.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")
