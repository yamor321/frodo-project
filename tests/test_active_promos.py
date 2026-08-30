"""Unit tests for etl.scoring.active_promos.compute_active_promos, using
synthetic PromoRecord/PriceRecord data -- no network.
"""
import datetime as dt
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scoring.active_promos import compute_active_promos
from etl.scrapers.shufersal import PriceRecord, PromoItem, PromoRecord

TODAY = dt.date(2026, 8, 30)


def price(item_code, item_price, store_id="1"):
    return PriceRecord(
        chain_id="1", subchain_id="1", store_id=store_id, item_code=item_code,
        item_name="x", manufacturer_name="", manufacturer_country="", unit_qty="",
        quantity="1", unit_of_measure="", is_weighted=False, qty_in_package="",
        item_price=item_price, unit_of_measure_price=item_price, price_update_time="",
    )


def promo(
    item_code,
    discounted_price,
    store_id="1",
    club_id="0 - כלל הלקוחות",
    is_coupon=False,
    is_gift_item=False,
    min_qty=1.0,
    start="2026-01-01T00:00:00.000",
    end="2027-01-01T00:00:00.000",
    description="מבצע",
):
    return PromoRecord(
        chain_id="1", subchain_id="1", store_id=store_id, promotion_id="p1",
        description=description, start_datetime=start, end_datetime=end,
        club_id=club_id, is_coupon=is_coupon, is_gift_item=is_gift_item,
        items=[PromoItem(item_code=item_code, min_qty=min_qty, discount_rate=0, discounted_price=discounted_price)],
    )


class ComputeActivePromosTests(unittest.TestCase):
    def test_simple_confirmed_cheaper_promo_is_kept(self):
        promos_by_store = {"1": [promo("A", 8.0)]}
        catalogs_by_store = {"1": [price("A", 10.0)]}
        result = compute_active_promos(promos_by_store, catalogs_by_store, TODAY)
        self.assertEqual(result["1"]["A"].discounted_price, 8.0)

    def test_promo_not_actually_cheaper_than_regular_price_is_dropped(self):
        """Real live finding, 2026-08-30: ~30% of "simple" promos aren't
        actually cheaper once cross-checked -- must be dropped, not shown."""
        promos_by_store = {"1": [promo("A", 12.0)]}
        catalogs_by_store = {"1": [price("A", 10.0)]}
        result = compute_active_promos(promos_by_store, catalogs_by_store, TODAY)
        self.assertNotIn("1", result)

    def test_item_missing_from_regular_catalog_is_dropped(self):
        """No regular price to confirm a real discount against -- can't
        verify, so don't show it, rather than trusting the promo alone."""
        promos_by_store = {"1": [promo("A", 8.0)]}
        catalogs_by_store = {"1": [price("B", 10.0)]}
        result = compute_active_promos(promos_by_store, catalogs_by_store, TODAY)
        self.assertNotIn("1", result)

    def test_coupon_gated_promo_excluded(self):
        promos_by_store = {"1": [promo("A", 8.0, is_coupon=True)]}
        catalogs_by_store = {"1": [price("A", 10.0)]}
        result = compute_active_promos(promos_by_store, catalogs_by_store, TODAY)
        self.assertNotIn("1", result)

    def test_club_gated_promo_excluded(self):
        promos_by_store = {"1": [promo("A", 8.0, club_id="3 - מועדון ספציפי")]}
        catalogs_by_store = {"1": [price("A", 10.0)]}
        result = compute_active_promos(promos_by_store, catalogs_by_store, TODAY)
        self.assertNotIn("1", result)

    def test_gift_item_promo_excluded(self):
        promos_by_store = {"1": [promo("A", 0.0, is_gift_item=True)]}
        catalogs_by_store = {"1": [price("A", 10.0)]}
        result = compute_active_promos(promos_by_store, catalogs_by_store, TODAY)
        self.assertNotIn("1", result)

    def test_expired_promo_excluded(self):
        promos_by_store = {"1": [promo("A", 8.0, start="2020-01-01T00:00:00.000", end="2020-12-31T00:00:00.000")]}
        catalogs_by_store = {"1": [price("A", 10.0)]}
        result = compute_active_promos(promos_by_store, catalogs_by_store, TODAY)
        self.assertNotIn("1", result)

    def test_not_yet_started_promo_excluded(self):
        promos_by_store = {"1": [promo("A", 8.0, start="2030-01-01T00:00:00.000", end="2031-12-31T00:00:00.000")]}
        catalogs_by_store = {"1": [price("A", 10.0)]}
        result = compute_active_promos(promos_by_store, catalogs_by_store, TODAY)
        self.assertNotIn("1", result)

    def test_bundle_min_qty_promo_excluded(self):
        promos_by_store = {"1": [promo("A", 8.0, min_qty=3.0)]}
        catalogs_by_store = {"1": [price("A", 10.0)]}
        result = compute_active_promos(promos_by_store, catalogs_by_store, TODAY)
        self.assertNotIn("1", result)

    def test_cheapest_of_multiple_promos_on_same_item_wins(self):
        promos_by_store = {"1": [promo("A", 9.0), promo("A", 7.0)]}
        catalogs_by_store = {"1": [price("A", 10.0)]}
        result = compute_active_promos(promos_by_store, catalogs_by_store, TODAY)
        self.assertEqual(result["1"]["A"].discounted_price, 7.0)

    def test_store_with_no_catalog_contributes_nothing(self):
        promos_by_store = {"1": [promo("A", 8.0)]}
        catalogs_by_store = {}
        result = compute_active_promos(promos_by_store, catalogs_by_store, TODAY)
        self.assertEqual(result, {})

    def test_end_datetime_and_description_carried_through(self):
        promos_by_store = {"1": [promo("A", 8.0, end="2028-05-01T00:00:00.000", description="5% הנחה")]}
        catalogs_by_store = {"1": [price("A", 10.0)]}
        result = compute_active_promos(promos_by_store, catalogs_by_store, TODAY)
        active = result["1"]["A"]
        self.assertEqual(active.end_datetime, "2028-05-01T00:00:00.000")
        self.assertEqual(active.description, "5% הנחה")


if __name__ == "__main__":
    unittest.main()
