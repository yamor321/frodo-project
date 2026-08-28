"""Live tests against the real binaprojects.com platform (no mocking -- same
principle as tests/test_carrefour.py and tests/test_victory.py). Requires
network access. Only exercises Shuk HaIr -- the one Bina chain in CHAINS
with a confirmed live Kfar Saba branch (see etl/scrapers/bina.py docstring).
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scrapers.bina import CHAINS, _parse_filename, download, list_files
from etl.scrapers.shufersal import (
    kfar_saba_full_catalog_files,
    kfar_saba_stores,
    list_stores_file,
    parse_price_xml,
    parse_stores_xml,
)


class ParseFilenameTests(unittest.TestCase):
    def test_per_store_file_shape_uppercase_extension(self):
        """Bina's real filenames use uppercase .GZ, unlike Shufersal/
        Carrefour's lowercase -- must not silently fail to match."""
        parsed = _parse_filename("PriceFull7290058148776-000-311-20260828-050944.GZ")
        self.assertEqual(
            parsed,
            {"category": "PriceFull", "chain_id": "7290058148776", "subchain_id": "000", "store_id": "311", "ext": "GZ"},
        )

    def test_chain_wide_stores_file_shape(self):
        parsed = _parse_filename("Stores7290058148776-000-20260828-050944.GZ")
        self.assertEqual(
            parsed,
            {"category": "Stores", "chain_id": "7290058148776", "subchain_id": "000", "store_id": "All", "ext": "GZ"},
        )

    def test_unrecognized_filename_returns_none(self):
        self.assertIsNone(_parse_filename("not-a-price-file.txt"))


class BinaLiveTests(unittest.TestCase):
    def test_list_files_finds_the_real_kfar_saba_branch(self):
        chain = CHAINS["shuk-hair"]
        files = list_files(chain["url_perfix"], chain["chain_id"])
        self.assertGreater(len(files), 0)

        stores_file = list_stores_file(files)
        self.assertIsNotNone(stores_file)
        stores = parse_stores_xml(download(stores_file))
        self.assertGreater(len(stores), 0)

        kfar_saba_ids = kfar_saba_stores(stores)
        self.assertEqual(kfar_saba_ids, {"011"})

    def test_shufersal_parsers_work_unmodified_on_real_bina_files(self):
        chain = CHAINS["shuk-hair"]
        files = list_files(chain["url_perfix"], chain["chain_id"])
        stores = parse_stores_xml(download(list_stores_file(files)))
        kfar_saba_ids = kfar_saba_stores(stores)

        catalog_files = list(kfar_saba_full_catalog_files(files, kfar_saba_ids))
        self.assertEqual({f.store_id for f in catalog_files}, {"011"})

        records = parse_price_xml(download(catalog_files[0]))
        self.assertGreater(len(records), 0)
        self.assertTrue(all(r.item_price >= 0 for r in records))


if __name__ == "__main__":
    unittest.main()
