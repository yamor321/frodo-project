"""Tests for etl.scrapers.wolt. The pure filename-parsing logic is tested
offline; the portal integration tests are live (no mocking -- same principle
as tests/test_carrefour.py and tests/test_geocode.py). Requires network
access for the live tests.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scrapers.wolt import KFAR_SABA_STORE_IDS, _parse_filename, download, list_files
from etl.scrapers.shufersal import (
    kfar_saba_full_catalog_files,
    kfar_saba_stores,
    list_stores_file,
    parse_price_xml,
    parse_stores_xml,
)


class ParseFilenameTests(unittest.TestCase):
    def test_per_store_file_shape(self):
        parsed = _parse_filename("PriceFull7290058249350-000-005-20260830-000033.gz")
        self.assertEqual(
            parsed,
            {"category": "PriceFull", "chain_id": "7290058249350", "subchain_id": "000", "store_id": "005", "ext": "gz"},
        )

    def test_chain_wide_stores_file_shape(self):
        """The Stores file has one fewer dash-separated segment than a
        per-store file (no store id) -- store_id normalizes to "All", same
        convention as every other chain's Stores file."""
        parsed = _parse_filename("Stores7290058249350-000-20260830-000009.gz")
        self.assertEqual(
            parsed,
            {"category": "Stores", "chain_id": "7290058249350", "subchain_id": "000", "store_id": "All", "ext": "gz"},
        )

    def test_unrecognized_filename_returns_none(self):
        self.assertIsNone(_parse_filename("not-a-price-file.txt"))


class WoltLiveTests(unittest.TestCase):
    def test_list_files_finds_the_kfar_saba_branch_and_excludes_noise_rows(self):
        """Confirms live: store 005 is the only Kfar Saba branch, and the
        two known non-production rows (038 "Test Venue", 041 "(CLOSED)")
        never show up here -- neither carries Kfar Saba's city, so the
        ordinary city filter already excludes them without any extra
        denylist (see wolt.py's module docstring)."""
        files = list_files()
        self.assertGreater(len(files), 0)
        found_store_ids = {f.store_id for f in files if f.store_id in KFAR_SABA_STORE_IDS}
        self.assertEqual(found_store_ids, KFAR_SABA_STORE_IDS)

    def test_shufersal_parsers_work_on_real_wolt_files(self):
        """The whole point of reusing shufersal.py's parse functions instead
        of writing new ones: Wolt publishes under the same regulation, same
        XML schema (aside from the blsWeighted tag-name quirk, handled by
        shufersal._text()'s multi-tag support). Proves it against real,
        live files, not a fixture."""
        files = list_files()

        stores_file = list_stores_file(files)
        self.assertIsNotNone(stores_file)
        stores = parse_stores_xml(download(stores_file))
        self.assertGreater(len(stores), 0)

        dynamic_kfar_saba = kfar_saba_stores(stores)
        self.assertEqual(dynamic_kfar_saba, KFAR_SABA_STORE_IDS)

        catalog_files = list(kfar_saba_full_catalog_files(files, dynamic_kfar_saba))
        self.assertEqual({f.store_id for f in catalog_files}, KFAR_SABA_STORE_IDS)

        records = parse_price_xml(download(catalog_files[0]))
        self.assertGreater(len(records), 0)
        self.assertTrue(all(r.item_price >= 0 for r in records))

    def test_all_wolt_stores_nationally_are_online_store_type(self):
        """Regression for the live finding this project's inclusion is
        built on: Wolt Market is a fully online/dark-store chain, not an
        online branch of an otherwise-physical chain -- every single store
        it publishes nationally is StoreType=="2", not a minority."""
        files = list_files()
        stores_file = list_stores_file(files)
        stores = parse_stores_xml(download(stores_file))
        self.assertGreater(len(stores), 0)
        self.assertTrue(all(s.store_type == "2" for s in stores))


if __name__ == "__main__":
    unittest.main()
