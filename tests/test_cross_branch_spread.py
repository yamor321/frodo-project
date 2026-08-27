import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scoring.cross_branch_spread import compute_spreads
from etl.scrapers.shufersal import PriceRecord


def rec(item_code, item_name, price, store_id):
    return PriceRecord(
        chain_id="7290027600007", subchain_id="002", store_id=store_id,
        item_code=item_code, item_name=item_name, manufacturer_name="",
        manufacturer_country="", unit_qty="", quantity="0", unit_of_measure="",
        is_weighted=False, qty_in_package="0", item_price=price,
        unit_of_measure_price=0.0, price_update_time="",
    )


class ComputeSpreadsTests(unittest.TestCase):
    def test_finds_largest_spread_first(self):
        catalogs = {
            "144": [rec("1", "מים", 4.00, "144"), rec("2", "לחם", 5.00, "144")],
            "394": [rec("1", "מים", 6.00, "394"), rec("2", "לחם", 5.00, "394")],
            "615": [rec("1", "מים", 7.90, "615"), rec("2", "לחם", 5.10, "615")],
            "682": [rec("1", "מים", 5.00, "682"), rec("2", "לחם", 5.00, "682")],
        }
        results = compute_spreads(catalogs, {"144": "A", "615": "B"}, min_stores=4)
        self.assertEqual(results[0].item_code, "1")
        self.assertAlmostEqual(results[0].spread_pct, (7.90 - 4.00) / 4.00)
        self.assertEqual(results[0].cheap_store_name, "A")
        self.assertEqual(results[0].expensive_store_name, "B")

    def test_excludes_items_below_min_stores(self):
        catalogs = {
            "144": [rec("1", "נדיר", 4.00, "144")],
            "394": [rec("1", "נדיר", 8.00, "394")],
        }
        results = compute_spreads(catalogs, {}, min_stores=4)
        self.assertEqual(results, [])

    def test_zero_spread_item_included_with_zero_pct(self):
        catalogs = {
            "1": [rec("x", "קבוע", 3.00, "1")],
            "2": [rec("x", "קבוע", 3.00, "2")],
            "3": [rec("x", "קבוע", 3.00, "3")],
            "4": [rec("x", "קבוע", 3.00, "4")],
        }
        results = compute_spreads(catalogs, {}, min_stores=4)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].spread_pct, 0.0)


if __name__ == "__main__":
    unittest.main()
