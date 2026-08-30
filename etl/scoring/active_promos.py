"""Which currently-active promotions are simple enough (no coupon, no club
card, no bundle) that any shopper can actually get them -- and, critically,
confirmed to actually be cheaper than the item's own regular price in that
store, not just labeled as a discount in the promo file's own metadata.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from etl.scrapers.shufersal import (
    PriceRecord,
    PromoRecord,
    is_simple_active_promo,
    simple_promo_item_prices,
)


@dataclass
class ActivePromo:
    item_code: str
    store_id: str
    discounted_price: float
    description: str
    end_datetime: str


def compute_active_promos(
    promos_by_store: dict[str, list[PromoRecord]],
    catalogs_by_store: dict[str, list[PriceRecord]],
    today: dt.date,
) -> dict[str, dict[str, ActivePromo]]:
    """store_id -> item_code -> ActivePromo.

    Two conditions must both hold, not just the first: (a) the promotion
    passes is_simple_active_promo() (no coupon/club/bundle, date-active),
    and (b) simple_promo_item_prices()'s discounted_price is confirmed
    strictly lower than that item's own regular PriceFull price in the
    same store. Verified live 2026-08-30 (5,284 real promotions, 5 Kfar
    Saba Shufersal stores): skipping the price cross-check would show
    ~30% of "simple" promos as a discount when they aren't one in
    practice -- stale promo metadata vs. an already-updated shelf price,
    not a rare edge case. See docs/sources.md for the real numbers behind
    this.

    A store with no live catalog today (no PriceFull to cross-check
    against) contributes nothing here -- there is no regular price to
    confirm a real discount against, so its promos are silently dropped
    rather than shown unverified.

    When more than one simple, confirmed-cheaper promo targets the same
    item_code in the same store, keeps the cheapest.
    """
    result: dict[str, dict[str, ActivePromo]] = {}
    for store_id, promos in promos_by_store.items():
        catalog = catalogs_by_store.get(store_id)
        if not catalog:
            continue
        regular_price = {r.item_code: r.item_price for r in catalog}

        store_result: dict[str, ActivePromo] = {}
        for promo in promos:
            if not is_simple_active_promo(promo, today):
                continue
            for item_code, discounted_price in simple_promo_item_prices(promo).items():
                regular = regular_price.get(item_code)
                if regular is None or discounted_price >= regular:
                    continue
                existing = store_result.get(item_code)
                if existing is not None and existing.discounted_price <= discounted_price:
                    continue
                store_result[item_code] = ActivePromo(
                    item_code=item_code,
                    store_id=store_id,
                    discounted_price=discounted_price,
                    description=promo.description,
                    end_datetime=promo.end_datetime,
                )

        if store_result:
            result[store_id] = store_result
    return result


def format_promo_end_date(end_datetime: str) -> str:
    """"2028-05-01T00:00:00.000" -> "01.05.2028", or "" if unparseable --
    shown next to a promo badge so a shopper can see how long the price
    holds, per explicit user request. Shown as-is even for a far-future
    "standing" discount (some real ones run to 2031, see docs/sources.md)
    -- honesty over trimming, not every promo is this week's flyer deal."""
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return dt.datetime.strptime(end_datetime, fmt).strftime("%d.%m.%Y")
        except ValueError:
            continue
    return ""
