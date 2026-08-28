"""Tests for etl.scrapers.carrefour. The pure filename-parsing logic is
tested offline; the portal integration tests are live (no mocking -- same
principle as tests/test_geocode.py and tests/test_product_images.py: this
project verifies against the actual source). Requires network access for
the live tests.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scrapers.carrefour import KFAR_SABA_STORE_IDS, _parse_filename, download, list_files
from etl.scrapers.shufersal import (
    kfar_saba_full_catalog_files,
    kfar_saba_stores,
    list_stores_file,
    parse_price_xml,
    parse_stores_xml,
)


class ParseFilenameTests(unittest.TestCase):
    def test_per_store_file_shape(self):
        parsed = _parse_filename("PriceFull7290055700007-001-010-20260828-051001.gz")
        self.assertEqual(
            parsed,
            {"category": "PriceFull", "chain_id": "7290055700007", "subchain_id": "001", "store_id": "010", "ext": "gz"},
        )

    def test_chain_wide_stores_file_shape(self):
        """The Stores file has one fewer dash-separated segment than a
        per-store file (no store id) -- store_id normalizes to "All", same
        convention as Shufersal's own Stores file."""
        parsed = _parse_filename("Stores7290055700007-000-20260828-000100.xml")
        self.assertEqual(
            parsed,
            {"category": "Stores", "chain_id": "7290055700007", "subchain_id": "000", "store_id": "All", "ext": "xml"},
        )

    def test_unrecognized_filename_returns_none(self):
        self.assertIsNone(_parse_filename("not-a-price-file.txt"))


class CarrefourLiveTests(unittest.TestCase):
    def test_list_files_finds_kfar_saba_stores(self):
        files = list_files()
        self.assertGreater(len(files), 0)
        found_store_ids = {f.store_id for f in files if f.store_id in KFAR_SABA_STORE_IDS}
        self.assertEqual(found_store_ids, KFAR_SABA_STORE_IDS)

    def test_shufersal_parsers_work_unmodified_on_real_carrefour_files(self):
        """The whole point of reusing shufersal.py's parse functions instead
        of writing new ones: both chains publish under the same regulation,
        same XML schema. Proves it against real, live files, not a fixture."""
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


if __name__ == "__main__":
    unittest.main()
