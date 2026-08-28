"""Live tests against the real laibcatalog.co.il API (no mocking -- same
principle as tests/test_carrefour.py and friends). Requires network access.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scrapers.victory import VICTORY_CHAIN_IDS, download, list_files
from etl.scrapers.shufersal import (
    kfar_saba_full_catalog_files,
    kfar_saba_stores,
    list_stores_file,
    parse_price_xml,
    parse_stores_xml,
)


class VictoryLiveTests(unittest.TestCase):
    def test_list_files_finds_the_real_kfar_saba_branch(self):
        files = list_files(VICTORY_CHAIN_IDS)
        self.assertGreater(len(files), 0)

        stores_file = list_stores_file(files)
        self.assertIsNotNone(stores_file)
        stores = parse_stores_xml(download(stores_file))
        self.assertGreater(len(stores), 0)

        kfar_saba_ids = kfar_saba_stores(stores)
        self.assertEqual(kfar_saba_ids, {"079"})

    def test_shufersal_parsers_work_unmodified_on_real_victory_files(self):
        files = list_files(VICTORY_CHAIN_IDS)
        stores = parse_stores_xml(download(list_stores_file(files)))
        kfar_saba_ids = kfar_saba_stores(stores)

        catalog_files = list(kfar_saba_full_catalog_files(files, kfar_saba_ids))
        self.assertEqual({f.store_id for f in catalog_files}, {"079"})

        records = parse_price_xml(download(catalog_files[0]))
        self.assertGreater(len(records), 0)
        self.assertTrue(all(r.item_price >= 0 for r in records))


if __name__ == "__main__":
    unittest.main()
