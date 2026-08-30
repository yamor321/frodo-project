"""Classifies a store's physical format for the map pin's shape (see
etl/render/map.py). The Hebrew UI labels follow the prevailing size
categories used in Israeli food retail (see docs/sources.md): מכולת / חנות
נוחות (up to ~200 sqm), סופרמרקט (~200-2,500 sqm), סופרמרקט ענק / היפרמרקט
(over ~2,500 sqm). No source in this project publishes real floor-area data
for any branch -- not Stores.xml, not anywhere else -- so classification is
still inferred from the chain's own format branding in the store name, the
same signal this used before this taxonomy existed, just split three ways
(hyper/supermarket/express) instead of two (hyper/neighborhood), plus two
signals that override the name entirely: is_pharm (set at the chain level,
never inferred from a name) and a sourced per-store override for the rare
case where even the improved default still gets a specific known branch
wrong (see format_overrides.py, same pattern as address_overrides.py).
"""
from __future__ import annotations

from etl.enrich.format_overrides import FORMAT_OVERRIDES

# "היפר" catches Carrefour's own hyper-format branches the same way
# "דיל"/"יוניברס" catches Shufersal's. Rami Levy/Osher Ad/Yohananof are
# matched by chain name directly (not an in-name sub-brand) -- all three are
# large discount/hypermarket chains, not neighborhood stores (see
# docs/sources.md for sourcing).
_HYPER_KEYWORDS = ("דיל", "יוניברס", "היפר", "רמי לוי", "אושר עד", "יוחננוף")

# The only real small-format brand keyword evidenced in this project's data
# (e.g. Shufersal's "שופרסל אקספרס תל חי"). A name matching neither this nor
# _HYPER_KEYWORDS is NOT assumed to be small -- see the "supermarket"
# default below, which is the fix for the real bug this taxonomy replaced.
_EXPRESS_KEYWORDS = ("אקספרס",)


def store_format(
    name: str,
    *,
    is_online: bool = False,
    is_pharm: bool = False,
    store_id: str | None = None,
) -> str:
    """Precedence: online > pharm > sourced per-store override > hyper
    keywords > express keywords > default "supermarket".

    The default changed from the old "neighborhood" (small-format) bucket to
    "supermarket": a branch whose name carries no format signal at all (e.g.
    "שוק העיר — כפר סבא מזרח", a large supermarket with no hyper-brand
    keyword in its name) is a regular supermarket far more often than it's a
    true small-format store, and the old default silently mislabeled real
    supermarkets as convenience stores on the map (see docs/sources.md).
    """
    if is_online:
        return "online"
    if is_pharm:
        return "pharm"
    if store_id is not None and store_id in FORMAT_OVERRIDES:
        return FORMAT_OVERRIDES[store_id]
    if any(kw in name for kw in _HYPER_KEYWORDS):
        return "hyper"
    if any(kw in name for kw in _EXPRESS_KEYWORDS):
        return "express"
    return "supermarket"
