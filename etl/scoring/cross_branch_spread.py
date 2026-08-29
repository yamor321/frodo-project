"""Layer-2-at-city-scale: how much does the SAME product (same barcode)
vary in price across a chain's own branches in one city? Doesn't need a
second chain to be meaningful -- Shufersal alone runs different formats
(Deal/Sheli budget, BE convenience, Express mini) in the same city, and the
price differences between them are real and large (see docs/sources.md).

This is arithmetic on official data only (brief section 2.1): min price,
max price, and the percentage between them, grouped by barcode. No judgment
field, no "which store is bad" -- just the numbers and which branches they
came from.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from etl.scoring.item_code_filters import is_reliable_item_code
from etl.scrapers.shufersal import PriceRecord


# Above this spread, the cheap price is under a quarter of the expensive
# one -- past the point normal chain-format pricing explains (see
# docs/sources.md: a real case, "משקה שיבולת שועל בטע", had cheap_price
# under 1/8th of expensive_price with no promo/discount field anywhere in
# the source data to confirm it's a sale rather than a data-quality issue).
# Flagging instead of dropping: nothing here proves it's wrong, so it stays
# in the full data, just excluded from the homepage headline/top spreads.
FLAG_SPREAD_PCT = 3.0


@dataclass
class SpreadResult:
    item_code: str
    item_name: str
    num_stores: int
    cheap_store_id: str
    cheap_store_name: str
    cheap_price: float
    expensive_store_id: str
    expensive_store_name: str
    expensive_price: float
    spread_pct: float
    flagged: bool


def compute_spreads(
    catalogs_by_store: dict[str, list[PriceRecord]],
    store_names: dict[str, str],
    min_stores: int = 4,
) -> list[SpreadResult]:
    """Group items by barcode across stores; return those seen in at least
    `min_stores` branches, sorted by largest spread first.
    """
    by_item: dict[str, dict[str, tuple[str, float]]] = defaultdict(dict)
    for store_id, records in catalogs_by_store.items():
        for r in records:
            if r.item_price > 0 and is_reliable_item_code(r.item_code):
                by_item[r.item_code][store_id] = (r.item_name, r.item_price)

    results: list[SpreadResult] = []
    for code, store_prices in by_item.items():
        if len(store_prices) < min_stores:
            continue
        ordered = sorted(store_prices.items(), key=lambda kv: kv[1][1])
        cheap_store, (name, cheap_price) = ordered[0]
        expensive_store, (_name2, expensive_price) = ordered[-1]
        if cheap_price <= 0:
            continue
        spread_pct = (expensive_price - cheap_price) / cheap_price
        results.append(
            SpreadResult(
                item_code=code,
                item_name=name,
                num_stores=len(store_prices),
                cheap_store_id=cheap_store,
                cheap_store_name=store_names.get(cheap_store, cheap_store),
                cheap_price=cheap_price,
                expensive_store_id=expensive_store,
                expensive_store_name=store_names.get(expensive_store, expensive_store),
                expensive_price=expensive_price,
                spread_pct=spread_pct,
                flagged=spread_pct > FLAG_SPREAD_PCT,
            )
        )

    results.sort(key=lambda r: -r.spread_pct)
    return results
