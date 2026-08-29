"""Groups comparable products by declared manufacturer, so a product page
can surface other products that share one -- the concrete case that
prompted this: dishwasher salt sold under both the Finish and Sno-Spark
brands turned out to share a declared manufacturer ("מלח הארץ") in some of
the source records.

The manufacturer field genuinely exists per item (PriceRecord.manufacturer_name,
etl/scrapers/shufersal.py), but it is NOT reliable: verified live against the
real raw catalogs (29.08.2026, 97 files across two days) that the exact same
barcode (Finish dishwasher salt, 8410104045111) carries different manufacturer
values across different chains -- "רקיט בנקיזר" (its real global parent,
Reckitt Benckiser, and the majority value), "מלח הארץ אילת בע"מ", "חברת
המלח", and "לא ידוע" all appear for the identical product. A first version
of this module picked one "canonical" (majority-vote) manufacturer per
product -- but that's exactly wrong for this feature's own motivating case:
the real signal linking Finish to Sno-Spark salt is a MINORITY value for
Finish (most records correctly say Reckitt Benckiser), so majority voting
would have hidden it. This version keeps every distinct value a product has
ever shown, and groups on ANY shared value.

So this is deliberately conservative in a different way:
- Exact string match only (after stripping whitespace) -- never fuzzy/
  similarity matching. Missing a real match is a much smaller problem than
  wrongly merging two different manufacturers.
- No majority requirement, but also no invented data: only values actually
  present in the source records are ever used to link two products.
- Every place this data is shown must carry a clear "unverified,
  self-reported, not majority-checked" warning -- see the flag-banner-style
  note in etl/render/product.py. This is the one case in the project where
  a displayed grouping is NOT a pure, fully-reliable arithmetic fact from
  official data, so it must never be presented as if it were.
"""
from __future__ import annotations

from collections import defaultdict

from etl.scrapers.shufersal import PriceRecord

# Values that mean "no real manufacturer was declared" -- seen verified live
# in real raw catalogs, not guessed (some surprisingly common: "," alone
# was the declared value for 5,071 different products in one snapshot).
_NON_SIGNAL_VALUES = {"", ",", "-", "--", "---", "לא ידוע", "כללי", "משתנה", "unknown", "n/a"}

# Above this many products, a shared manufacturer value is almost certainly
# a real conglomerate (Tnuva, Osem, Strauss, Reckitt Benckiser -- all
# observed live with 200-500+ products each) rather than a specific,
# useful "these are interchangeable" signal. "Same giant company" isn't a
# meaningful equivalence for a shopper; a small/niche shared manufacturer
# is far more likely to mean "same actual product, different label" --
# see module docstring for the real dishwasher-salt case this targets.
_MAX_USEFUL_GROUP_SIZE = 8


def manufacturer_values_by_code(catalogs_by_store: dict[str, list[PriceRecord]]) -> dict[str, set[str]]:
    """item_code -> every informative manufacturer_name value ever recorded
    for it, across all stores/chains. A product commonly carries more than
    one value here (different chains enter it differently, see module
    docstring) -- kept as a set on purpose, not collapsed to a single
    "canonical" pick."""
    values: dict[str, set[str]] = defaultdict(set)
    for records in catalogs_by_store.values():
        for r in records:
            name = (r.manufacturer_name or "").strip()
            if name.lower() in _NON_SIGNAL_VALUES:
                continue
            values[r.item_code].add(name)
    return dict(values)


def group_by_manufacturer_value(
    item_codes: set[str], values_by_code: dict[str, set[str]]
) -> dict[str, list[str]]:
    """manufacturer value (exact string) -> every item_code in `item_codes`
    (the same comparable-product universe as spreads/products.json) that
    has ever shown that value."""
    groups: dict[str, list[str]] = defaultdict(list)
    for code in item_codes:
        for value in values_by_code.get(code, ()):
            groups[value].append(code)
    return dict(groups)


def related_products(
    code: str,
    values_by_code: dict[str, set[str]],
    groups_by_value: dict[str, list[str]],
    min_group_size: int = 2,
    max_group_size: int = _MAX_USEFUL_GROUP_SIZE,
) -> list[str]:
    """Every other tracked product that shares at least one declared
    manufacturer value with `code`, skipping values shared by too few
    (nothing to compare against) or too many (a real conglomerate, not a
    specific "these are interchangeable" signal -- see
    _MAX_USEFUL_GROUP_SIZE) other products."""
    related: set[str] = set()
    for value in values_by_code.get(code, ()):
        group = groups_by_value.get(value, ())
        if min_group_size <= len(group) <= max_group_size:
            related.update(group)
    related.discard(code)
    return sorted(related)
