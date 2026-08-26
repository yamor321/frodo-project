"""Layer 3 (brief section 3): gap between a chain's actual price and the
official controlled price, for the subset of catalog items matched against
MoAg's regulated dairy products.

gap_pct = (actual_price - controlled_consumer_price) / controlled_consumer_price
A positive gap means the store is charging above the regulated maximum
consumer price; per the brief's section 2 principles this is reported as a
number only, with no judgmental label attached.
"""
from __future__ import annotations

from dataclasses import dataclass

from etl.benchmarks.moag_controlled_prices import ControlledPriceRecord
from etl.category_mapping.moag_matcher import match_item
from etl.scrapers.shufersal import PriceRecord


@dataclass
class GapResult:
    item_code: str
    item_name: str
    store_id: str
    actual_price: float
    controlled_product_names: list[str]
    controlled_consumer_price: float | None  # None when ambiguous (see below)
    gap_pct: float | None
    ambiguous: bool  # True only for milk items where carton/bag isn't stated


def compute_gaps(
    catalog: list[PriceRecord], controlled: list[ControlledPriceRecord]
) -> list[GapResult]:
    controlled_by_name = {c.product: c for c in controlled}
    results: list[GapResult] = []

    for item in catalog:
        matched_names = match_item(item)
        matched_records = [controlled_by_name[n] for n in matched_names if n in controlled_by_name]
        if not matched_records:
            continue

        if len(matched_records) == 1:
            cp = matched_records[0].consumer_price
            results.append(
                GapResult(
                    item_code=item.item_code,
                    item_name=item.item_name,
                    store_id=item.store_id,
                    actual_price=item.item_price,
                    controlled_product_names=matched_names,
                    controlled_consumer_price=cp,
                    gap_pct=(item.item_price - cp) / cp,
                    ambiguous=False,
                )
            )
        else:
            # Ambiguous milk match: package type (carton/bag) not stated in
            # the item name, and the two controlled prices differ -- report
            # the range rather than silently picking one (brief section 2.1:
            # no field stands in for a judgment call).
            results.append(
                GapResult(
                    item_code=item.item_code,
                    item_name=item.item_name,
                    store_id=item.store_id,
                    actual_price=item.item_price,
                    controlled_product_names=matched_names,
                    controlled_consumer_price=None,
                    gap_pct=None,
                    ambiguous=True,
                )
            )

    return results
