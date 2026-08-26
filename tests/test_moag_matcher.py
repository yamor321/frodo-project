"""Unit tests for etl.category_mapping.moag_matcher.

Most cases below use REAL items pulled from the live Shufersal full-catalog
download for Kfar Saba store 144 (2026-08-26/27) -- see
scratchpad research in this session; exact field values reproduced here.
Two milk cases are constructed (not from a real sample) to exercise the
carton/bag ambiguity logic, since no real 1%/3% milk item with an explicit
"קרטון"/"שקית" word turned up in that particular store's catalog; they're
marked accordingly.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.category_mapping.moag_matcher import match_item
from etl.scrapers.shufersal import PriceRecord


def make_record(item_name, unit_qty, quantity, item_price=0.0) -> PriceRecord:
    return PriceRecord(
        chain_id="7290027600007",
        subchain_id="002",
        store_id="144",
        item_code="0000000000000",
        item_name=item_name,
        manufacturer_name="",
        manufacturer_country="",
        unit_qty=unit_qty,
        quantity=str(quantity),
        unit_of_measure="",
        is_weighted=False,
        qty_in_package="0",
        item_price=item_price,
        unit_of_measure_price=0.0,
        price_update_time="",
    )


class RealItemMatchTests(unittest.TestCase):
    """Real items from the live download -- verified 2026-08-27."""

    def test_white_cheese_matches(self):
        rec = make_record("גבינה לבנה 5% 250ג תנובה", "גרם", "250.00", item_price=5.87)
        self.assertEqual(match_item(rec), ["גבינה לבנה 5%"])

    def test_eshel_matches(self):
        rec = make_record('אשל מהדרין 4.5% 200 מ"ל', "מיליליטר", "200.00", item_price=1.99)
        self.assertEqual(match_item(rec), ["אשל 4.5% שומן"])

    def test_fortified_sour_cream_excluded(self):
        """'מועשרת' (fortified) -- real item priced 12.7% above the plain
        controlled benchmark on the first live demo run. Treated as a
        different, non-regulated product tier rather than a real gap."""
        rec = make_record("שמנת חמוצה15% מועשרת200", "מיליליטר", "200.00")
        self.assertEqual(match_item(rec), [])

    def test_goat_cheese_excluded_from_cows_milk_benchmark(self):
        """Real item from the first live demo run: matched the (cow's milk)
        white-cheese benchmark on category+fat%+package alone and produced
        a fabricated +307% gap. Different product."""
        rec = make_record("גבינה לבנה 5% עיזים 250ג", "גרם", "250.00", item_price=23.90)
        self.assertEqual(match_item(rec), [])

    def test_uht_milk_excluded_from_fresh_milk_benchmark(self):
        """'עמיד' (UHT/long-life) vs the controlled item's 'טרי' (fresh)."""
        rec = make_record("חלב עמיד הומוגני 3% 1 ל", "ליטר", "1.00")
        self.assertEqual(match_item(rec), [])

    def test_2pct_milk_does_not_match_1_or_3pct_controlled(self):
        rec = make_record("חלב טרי 2% דל לקטוז 1 ל", "ליטר", "1.00")
        self.assertEqual(match_item(rec), [])

    def test_32pct_cream_does_not_match_38pct_controlled(self):
        rec = make_record("שמנת מתוקה להקצפה32% 250", "מיליליטר", "250.00")
        self.assertEqual(match_item(rec), [])

    def test_gil_word_boundary_excludes_regil(self):
        """'רגיל' (regular) contains the substring 'גיל' -- must not match Gil."""
        rec = make_record("קרפרי לונג רגיל 40יח", "יחידות", "1.00")
        self.assertEqual(match_item(rec), [])

    def test_milk_chocolate_false_positive_excluded(self):
        rec = make_record("שוקולד חלב אגוז שלם100", "גרם", "100.00")
        self.assertEqual(match_item(rec), [])

    def test_cream_flavored_ice_cream_false_positive_excluded(self):
        rec = make_record("גלידת שמנת וניל קרמל330ג", "גרם", "330.00")
        self.assertEqual(match_item(rec), [])


class ConstructedPositiveMatchTests(unittest.TestCase):
    """Constructed (not from a real sample) plain-variant case, since every
    real sour-cream item found in the sample catalog happened to be the
    excluded fortified variant -- this checks the base spec still matches
    when the product isn't a premium tier."""

    def test_plain_sour_cream_matches(self):
        rec = make_record('שמנת חמוצה 15% שומן רגילה 200 מ"ל', "מיליליטר", "200.00")
        self.assertEqual(match_item(rec), ["שמנת חמוצה 15% שומן רגילה"])


class ConstructedMilkAmbiguityTests(unittest.TestCase):
    """Constructed cases (not from a real sample) exercising the
    carton/bag disambiguation logic on structurally-real field shapes."""

    def test_milk_with_explicit_carton_word_matches_single_variant(self):
        rec = make_record("חלב טרי בקרטון 3% שומן", "ליטר", "1.00")
        self.assertEqual(match_item(rec), ["חלב טרי בקרטון 3% שומן (רגיל)"])

    def test_milk_with_explicit_bag_word_matches_single_variant(self):
        rec = make_record("חלב טרי בשקית 1% שומן", "ליטר", "1.00")
        self.assertEqual(match_item(rec), ["חלב טרי בשקית 1% שומן (רגיל)"])

    def test_milk_without_package_word_is_ambiguous(self):
        rec = make_record("חלב טרי 3% שומן 1 ליטר", "ליטר", "1.00")
        result = match_item(rec)
        self.assertEqual(
            set(result),
            {"חלב טרי בקרטון 3% שומן (רגיל)", "חלב טרי בשקית 3% שומן (רגיל)"},
        )


if __name__ == "__main__":
    unittest.main()
