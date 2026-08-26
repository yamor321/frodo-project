"""Deterministic matcher: Shufersal catalog items -> MoAg controlled dairy
products. No LLM, no external classifier project (checked -- see
docs/sources.md; the OpenIsraeliSupermarkets ecosystem has no product-category
classifier, only file-type parsing and a separate cross-chain entity-matching
experiment).

Signature per product: a required-word set (Hebrew, word-boundary matched so
"רגיל" doesn't false-match "גיל"), a fat percentage parsed from the item
name, and (where verified) an expected package size compared against the
catalog item's *structured* Quantity/UnitQty fields -- not a regex over the
free-text name. A global exclusion list blocks the two false-positive
patterns already proven on real data: "שוקולד חלב" (milk chocolate) and
"גלידת שמנת" (cream-flavored ice cream).

Package size is enforced only where actually verified against the live
gov.il page on 2026-08-27 (milk, both cheeses, Eshel): weight_and_package
wasn't available from data.gov.il's CKAN dataset (no such field there), so
cream's package size is left unenforced -- documented gap, not a guess.

Milk is a known ambiguous case: the real Shufersal catalog does not
reliably state "קרטון" (carton) vs "שקית" (bag) in the item name, but the
carton and bag controlled prices differ. When the package type isn't
stated, both candidates are returned rather than silently picking one.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from etl.scrapers.shufersal import PriceRecord

FAT_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
FAT_TOLERANCE = 0.01  # exact match expected; percentages are discrete labels
QTY_TOLERANCE = 0.05  # 5% slack on package size comparisons


def _hebrew_word_re(word: str) -> re.Pattern:
    """Word-boundary match tuned for Hebrew product names.

    Python's \\b treats digits as word characters, so plain \\b fails on
    real names like "חמוצה15%" (no boundary between ה and 1) -- verified
    failing on real data. It also can't tell a real different word ("רגיל")
    from a grammatical single-letter prefix ("ב-" in "בקרטון"). For this
    matcher's actual vocabulary (Hebrew nouns/adjectives, never legitimately
    prefixed with ב/ל/מ/ו/כ/ש/ה in these names), the practical rule is:
    match unless directly adjacent to another Hebrew letter on either side.
    Digits, punctuation, spaces, and string edges all count as boundaries.
    """
    return re.compile(rf"(?<![א-ת]){re.escape(word)}(?![א-ת])")


# Proven false-positive patterns (see tests/test_moag_matcher.py, the
# earlier tests/test_shufersal_parser.py fixture, and the first live run of
# scripts/demo_dairy_gap.py against store 144's real catalog):
#   - שוקולד/גלידה/גלידת/עוגה/עוגת/ממתק/וופל/עוגיות/ביסקוויט/קינוח: flavor
#     descriptors ("milk chocolate"), not the product itself.
#   - מרוכז: sweetened condensed milk -- a different product, not "fresh".
#   - עיזים: goat's milk/cheese -- matched "גבינה לבנה 5% עיזים 250ג" against
#     the (cow's milk) white-cheese benchmark and produced a fabricated
#     +307% gap on the first live run. Different product, wrong to compare.
#   - מועשר/מועשרת (fortified/enriched), עמיד (UHT/long-life, vs the
#     controlled item's "טרי" = fresh): premium variants that priced 15-30%
#     above the benchmark on the first live run -- plausibly a different,
#     non-regulated product tier rather than a real gap. Excluded rather
#     than reported as a gap we can't actually stand behind.
GLOBAL_EXCLUSIONS = [
    _hebrew_word_re(w)
    for w in [
        "שוקולד", "גלידה", "גלידת", "עוגה", "עוגת", "ממתק", "וופל", "עוגיות",
        "ביסקוויט", "קינוח", "מרוכז", "עיזים", "מועשר", "מועשרת", "עמיד",
    ]
]

_GRAMS_PER = {"גרם": 1.0, "קילוגרם": 1000.0}
_ML_PER = {"מיליליטר": 1.0, "ליטר": 1000.0}


@dataclass
class ControlledSpec:
    group: str
    controlled_product_name: str
    required_words: tuple[str, ...]  # ALL must appear, word-boundary matched
    excluded_words: tuple[str, ...]  # NONE may appear (beyond GLOBAL_EXCLUSIONS)
    fat_pct: float
    package_grams: float | None = None
    package_ml: float | None = None
    package_type_word: str | None = None  # e.g. "קרטון" / "שקית", for disambiguation only


CONTROLLED_SPECS: list[ControlledSpec] = [
    ControlledSpec("milk_1pct", "חלב טרי בקרטון 1% שומן (רגיל)", ("חלב",), (), 1.0, package_ml=1000.0, package_type_word="קרטון"),
    ControlledSpec("milk_1pct", "חלב טרי בשקית 1% שומן (רגיל)", ("חלב",), (), 1.0, package_ml=1000.0, package_type_word="שקית"),
    ControlledSpec("milk_3pct", "חלב טרי בקרטון 3% שומן (רגיל)", ("חלב",), (), 3.0, package_ml=1000.0, package_type_word="קרטון"),
    ControlledSpec("milk_3pct", "חלב טרי בשקית 3% שומן (רגיל)", ("חלב",), (), 3.0, package_ml=1000.0, package_type_word="שקית"),
    ControlledSpec("white_cheese", "גבינה לבנה 5%", ("גבינה", "לבנה"), (), 5.0, package_grams=250.0),
    ControlledSpec("hard_cheese_emek", "גבינה חצי קשה עמק (רגילה) 28% שומן", ("גבינה",), ("לבנה",), 28.0, package_grams=1000.0),
    ControlledSpec("hard_cheese_gilboa", "גבינה חצי קשה גלבוע 22% שומן", ("גבינה",), ("לבנה",), 22.0, package_grams=1000.0),
    ControlledSpec("eshel", "אשל 4.5% שומן", ("אשל",), (), 4.5, package_ml=200.0),
    ControlledSpec("gil", "גיל 3% שומן", ("גיל",), (), 3.0, package_ml=200.0),
    ControlledSpec("sour_cream", "שמנת חמוצה 15% שומן רגילה", ("שמנת", "חמוצה"), (), 15.0),
    ControlledSpec("sweet_cream", "שמנת מתוקה 38% שומן", ("שמנת", "מתוקה"), (), 38.0),
]


def match_item(record: PriceRecord) -> list[str]:
    """Return the controlled product name(s) this catalog item matches.

    Usually 0 or 1. Can be 2 only for milk, when the item name states
    neither "קרטון" nor "שקית" -- both candidates are returned rather than
    guessing, since their controlled prices differ.
    """
    name = record.item_name
    if any(p.search(name) for p in GLOBAL_EXCLUSIONS):
        return []

    fat_pct = _extract_fat_pct(name)
    if fat_pct is None:
        return []

    item_dimension, item_value = _normalize_quantity(record.quantity, record.unit_qty)

    candidates: list[ControlledSpec] = []
    for spec in CONTROLLED_SPECS:
        if abs(spec.fat_pct - fat_pct) > FAT_TOLERANCE:
            continue
        if not all(_hebrew_word_re(w).search(name) for w in spec.required_words):
            continue
        if any(_hebrew_word_re(w).search(name) for w in spec.excluded_words):
            continue
        if not _package_matches(spec, item_dimension, item_value):
            continue
        candidates.append(spec)

    if len(candidates) <= 1:
        return [c.controlled_product_name for c in candidates]

    # Ambiguous case (expected only for milk): if the name states the
    # package type explicitly, narrow to it. Plain substring here (not the
    # Hebrew word-boundary helper) since these names attach the grammatical
    # prefix "ב" directly: "בקרטון" ("in a carton") should still count.
    stated = [c for c in candidates if c.package_type_word and c.package_type_word in name]
    return [c.controlled_product_name for c in (stated or candidates)]


def _extract_fat_pct(name: str) -> float | None:
    m = FAT_PCT_RE.search(name)
    return float(m.group(1)) if m else None


def _normalize_quantity(quantity_str: str, unit_qty: str) -> tuple[str, float] | tuple[None, None]:
    try:
        qty = float(quantity_str)
    except (TypeError, ValueError):
        return (None, None)
    if unit_qty in _GRAMS_PER:
        return ("grams", qty * _GRAMS_PER[unit_qty])
    if unit_qty in _ML_PER:
        return ("ml", qty * _ML_PER[unit_qty])
    return (None, None)


def _package_matches(spec: ControlledSpec, dimension: str | None, value: float | None) -> bool:
    if spec.package_grams is None and spec.package_ml is None:
        return True  # not enforced for this product (e.g. cream -- see module docstring)
    if dimension is None:
        return False
    expected = spec.package_grams if dimension == "grams" else spec.package_ml if dimension == "ml" else None
    if expected is None:
        return False
    return abs(value - expected) <= expected * QTY_TOLERANCE
