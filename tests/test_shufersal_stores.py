"""Unit tests for etl.scrapers.shufersal's chain-agnostic Stores-file
helpers (kfar_saba_stores), using synthetic StoreRecord data -- no network.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scrapers.shufersal import StoreRecord, kfar_saba_stores


def store(store_id, city_code, name="x"):
    return StoreRecord(
        chain_id="1", subchain_id="1", store_id=store_id, store_name=name,
        address="", city_code=city_code, zip_code="",
    )


class KfarSabaStoresTests(unittest.TestCase):
    def test_matches_the_official_settlement_code(self):
        """Shufersal and Carrefour's convention -- verified live."""
        stores = [store("1", "6900"), store("2", "5000")]
        self.assertEqual(kfar_saba_stores(stores), {"1"})

    def test_matches_the_literal_city_name(self):
        """Real case found live: Victory's own Stores file puts the city
        NAME in this field instead of the settlement code -- silently
        returned zero matches before this was handled."""
        stores = [store("1", "כפר סבא"), store("2", "תל אביב")]
        self.assertEqual(kfar_saba_stores(stores), {"1"})

    def test_matches_the_hyphenated_city_name(self):
        stores = [store("1", "כפר-סבא")]
        self.assertEqual(kfar_saba_stores(stores), {"1"})

    def test_no_matches_returns_empty_set(self):
        stores = [store("1", "5000"), store("2", "תל אביב")]
        self.assertEqual(kfar_saba_stores(stores), set())


if __name__ == "__main__":
    unittest.main()
