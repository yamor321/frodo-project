import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scoring.store_ranking import compute_store_scores
from etl.scrapers.shufersal import PriceRecord


def rec(item_code, price, store_id):
    return PriceRecord(
        chain_id="7290027600007", subchain_id="002", store_id=store_id,
        item_code=item_code, item_name="x", manufacturer_name="",
        manufacturer_country="", unit_qty="", quantity="0", unit_of_measure="",
        is_weighted=False, qty_in_package="0", item_price=price,
        unit_of_measure_price=0.0, price_update_time="",
    )


class ComputeStoreScoresTests(unittest.TestCase):
    def test_consistently_cheapest_store_scores_near_zero(self):
        # Realistic-length codes: is_reliable_item_code() rejects anything
        # under 8 digits, and these fixtures should reflect real barcode
        # shapes, not trip that filter by accident.
        catalogs = {
            "A": [rec("11111111", 1.0, "A"), rec("22222222", 1.0, "A")],
            "B": [rec("11111111", 2.0, "B"), rec("22222222", 2.0, "B")],
            "C": [rec("11111111", 3.0, "C"), rec("22222222", 3.0, "C")],
            "D": [rec("11111111", 4.0, "D"), rec("22222222", 4.0, "D")],
        }
        scores = {s.store_id: s for s in compute_store_scores(catalogs, {}, min_stores=4)}
        self.assertAlmostEqual(scores["A"].avg_percentile, 0.0)
        self.assertAlmostEqual(scores["D"].avg_percentile, 1.0)
        self.assertAlmostEqual(scores["B"].avg_percentile, 1 / 3)
        self.assertEqual(scores["A"].items_compared, 2)

    def test_below_min_stores_excluded(self):
        catalogs = {
            "A": [rec("11111111", 1.0, "A")],
            "B": [rec("11111111", 2.0, "B")],
        }
        scores = compute_store_scores(catalogs, {}, min_stores=4)
        self.assertEqual(scores, [])

    def test_scores_sorted_cheapest_first(self):
        catalogs = {
            "A": [rec("11111111", 5.0, "A")],
            "B": [rec("11111111", 1.0, "B")],
            "C": [rec("11111111", 3.0, "C")],
            "D": [rec("11111111", 2.0, "D")],
        }
        scores = compute_store_scores(catalogs, {}, min_stores=4)
        self.assertEqual([s.store_id for s in scores], ["B", "D", "C", "A"])


if __name__ == "__main__":
    unittest.main()
