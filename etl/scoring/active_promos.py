"""Which currently-active promotions are simple enough (no coupon, no club
card, no bundle) that any shopper can actually get them -- and, critically,
confirmed to actually be cheaper than the item's own regular price in that
store, not just labeled as a discount in the promo file's own metadata.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
from dataclasses import dataclass

from etl.scrapers.shufersal import (
    PriceRecord,
    PromoRecord,
    is_simple_active_promo,
    simple_promo_item_prices,
)

_PROMO_DT_FORMATS = ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S")


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


@dataclass
class PromoHighlight:
    """A confirmed active promo enriched with display text -- ActivePromo
    itself only carries item_code/store_id (see compute_active_promos()),
    not the item's real name or the store's display name, since it's built
    from PromoRecord/PromoItem data alone. Used for the homepage's own
    "active promos now" section, added after a user report: the promo
    badge existed on product/store pages, but the homepage's other two
    sections (biggest cross-store gap, best-value leaderboard) select for
    signals that rarely overlap with "has a modest 5-10% promo today" --
    an extreme price GAP and a real SALE are different things, so a
    dedicated section is what actually makes the feature visible."""

    item_code: str
    item_name: str
    store_id: str
    store_name: str
    regular_price: float
    discounted_price: float
    end_datetime: str


def build_promo_highlights(
    active_promos: dict[str, dict[str, ActivePromo]],
    catalogs_by_store: dict[str, list[PriceRecord]],
    store_names: dict[str, str],
) -> list[PromoHighlight]:
    """Enriches every confirmed active promo with its real item/store
    names and sorts by discount percentage, steepest first."""
    highlights = []
    for store_id, promos in active_promos.items():
        catalog_by_code = {r.item_code: r for r in catalogs_by_store.get(store_id, [])}
        for item_code, promo in promos.items():
            record = catalog_by_code.get(item_code)
            if record is None:
                continue
            highlights.append(
                PromoHighlight(
                    item_code=item_code,
                    item_name=record.item_name,
                    store_id=store_id,
                    store_name=store_names.get(store_id, store_id),
                    regular_price=record.item_price,
                    discounted_price=promo.discounted_price,
                    end_datetime=promo.end_datetime,
                )
            )
    highlights.sort(key=lambda h: (h.discounted_price - h.regular_price) / h.regular_price)
    return highlights


def format_promo_end_date(end_datetime: str) -> str:
    """"2028-05-01T00:00:00.000" -> "01.05.2028", or "" if unparseable --
    shown next to a promo badge so a shopper can see how long the price
    holds, per explicit user request. Shown as-is even for a far-future
    "standing" discount (some real ones run to 2031, see docs/sources.md)
    -- honesty over trimming, not every promo is this week's flyer deal."""
    for fmt in _PROMO_DT_FORMATS:
        try:
            return dt.datetime.strptime(end_datetime, fmt).strftime("%d.%m.%Y")
        except ValueError:
            continue
    return ""


def find_fallback_active_promos(
    processed_root: pathlib.Path, before: dt.date, max_lookback_days: int = 7
) -> tuple[list[dict], str | None]:
    """Walk backward from `before` (inclusive -- same reasoning as
    etl/raw_snapshot_fallback.py's find_fallback_catalogs: the daily
    workflow can run more than once a day, so an earlier same-day success
    must be found before falling back further) for the most recent day's
    own active_promos.json. Returns its raw flat row list and the date it
    came from, or ([], None) if nothing usable was found.

    Unlike prices, promo data has no raw-XML fallback (see docs/sources.md
    -- PromoFull is deliberately never written to data/raw/, only the
    small already-filtered active_promos.json is committed). Confirmed
    live 2026-08-31: prices.shufersal.co.il timed out on every pagination
    request across two consecutive full runs -- a real, reproducible
    failure mode, not hypothetical -- which would otherwise make the whole
    promo feature silently vanish for a day even though the source data
    didn't actually change.
    """
    for days_back in range(0, max_lookback_days + 1):
        day = (before - dt.timedelta(days=days_back)).isoformat()
        path = processed_root / day / "active_promos.json"
        if not path.exists():
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if rows:
            return rows, day
    return [], None


def rebuild_active_promos_from_flat(
    flat_rows: list[dict],
    catalogs_by_store: dict[str, list[PriceRecord]],
    today: dt.date,
) -> dict[str, dict[str, ActivePromo]]:
    """Reconstructs the store_id -> item_code -> ActivePromo shape from a
    previous day's active_promos.json (see find_fallback_active_promos()),
    re-validating every row against TWO things only today's own context
    can confirm -- never trusted blindly from yesterday's file:
    (a) the promo's end_datetime hasn't already passed, and (b) its
    discounted_price is still actually lower than TODAY's real regular
    price for that item at that store (today's own catalog can be fresh
    even when only promo collection failed, so a stale promo price could
    have been overtaken by a real price change since).
    """
    regular_price_by_store = {
        store_id: {r.item_code: r.item_price for r in catalog} for store_id, catalog in catalogs_by_store.items()
    }

    result: dict[str, dict[str, ActivePromo]] = {}
    for row in flat_rows:
        end = None
        for fmt in _PROMO_DT_FORMATS:
            try:
                end = dt.datetime.strptime(row.get("end_datetime", ""), fmt)
                break
            except ValueError:
                continue
        if end is None or end.date() < today:
            continue

        store_id = row.get("store_id", "")
        regular = regular_price_by_store.get(store_id, {}).get(row.get("item_code", ""))
        discounted_price = row.get("discounted_price")
        if regular is None or discounted_price is None or discounted_price >= regular:
            continue

        result.setdefault(store_id, {})[row["item_code"]] = ActivePromo(
            item_code=row["item_code"],
            store_id=store_id,
            discounted_price=discounted_price,
            description=row.get("description", ""),
            end_datetime=row.get("end_datetime", ""),
        )
    return result
