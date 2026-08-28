"""Layer 2 (brief section 3): "for each chain/branch, average percentile
over a representative basket." Computed here at branch granularity within
one chain -- extends naturally to cross-chain once a second chain exists,
same math.

For every item seen in >=4 branches, each branch's price is converted to a
percentile within that item (0.0 = cheapest branch for this item, 1.0 =
priciest). A branch's score is the average of those percentiles across
every qualifying item it carries. This is a number and nothing else --
brief section 2.1/2.2: no judgment field, just arithmetic and (downstream)
color.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from etl.scrapers.shufersal import PriceRecord


@dataclass
class StoreScore:
    store_id: str
    store_name: str
    avg_percentile: float  # 0 = consistently cheapest, 1 = consistently priciest
    items_compared: int


def compute_store_scores(
    catalogs_by_store: dict[str, list[PriceRecord]],
    store_names: dict[str, str],
    min_stores: int = 4,
) -> list[StoreScore]:
    by_item: dict[str, dict[str, float]] = defaultdict(dict)
    for store_id, records in catalogs_by_store.items():
        for r in records:
            if r.item_price > 0:
                by_item[r.item_code][store_id] = r.item_price

    percentile_sums: dict[str, float] = defaultdict(float)
    percentile_counts: dict[str, int] = defaultdict(int)

    for store_prices in by_item.values():
        if len(store_prices) < min_stores:
            continue
        ordered = sorted(store_prices.items(), key=lambda kv: kv[1])
        n = len(ordered)
        denom = n - 1 if n > 1 else 1
        for rank, (store_id, _price) in enumerate(ordered):
            percentile_sums[store_id] += rank / denom
            percentile_counts[store_id] += 1

    scores = [
        StoreScore(
            store_id=store_id,
            store_name=store_names.get(store_id, store_id),
            avg_percentile=percentile_sums[store_id] / percentile_counts[store_id],
            items_compared=percentile_counts[store_id],
        )
        for store_id in percentile_counts
    ]
    scores.sort(key=lambda s: s.avg_percentile)
    return scores
