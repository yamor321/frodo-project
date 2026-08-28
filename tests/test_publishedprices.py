"""Tests for etl.scrapers.publishedprices. Offline filename-parsing tests
only, unlike tests/test_carrefour.py and tests/test_victory.py -- there is no
live-network test here yet because this dev sandbox cannot open an outbound
FTP data connection at all (confirmed against an unrelated public FTP host
too, so it's a sandbox limitation, not a claim about the real server -- see
the module docstring in etl/scrapers/publishedprices.py). Add the live
integration tests (matching test_carrefour.py's CarrefourLiveTests shape)
once this has actually run somewhere with FTP access, so they assert real
confirmed values instead of guessed ones.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scrapers.publishedprices import CHAINS, _parse_filename


class ParseFilenameTests(unittest.TestCase):
    def test_per_store_file_shape(self):
        parsed = _parse_filename("PriceFull7290058140886-001-010-20260828-051001.gz")
        self.assertEqual(
            parsed,
            {"category": "PriceFull", "chain_id": "7290058140886", "subchain_id": "001", "store_id": "010", "ext": "gz"},
        )

    def test_chain_wide_stores_file_shape(self):
        parsed = _parse_filename("Stores7290058140886-000-20260828-000100.xml")
        self.assertEqual(
            parsed,
            {"category": "Stores", "chain_id": "7290058140886", "subchain_id": "000", "store_id": "All", "ext": "xml"},
        )

    def test_unrecognized_filename_returns_none(self):
        self.assertIsNone(_parse_filename("not-a-price-file.txt"))


class ChainConfigTests(unittest.TestCase):
    def test_three_chains_configured(self):
        self.assertEqual(set(CHAINS), {"rami-levy", "yohananof", "osher-ad"})
        for chain in CHAINS.values():
            self.assertIn("ftp_username", chain)
            self.assertIn("chain_id", chain)


if __name__ == "__main__":
    unittest.main()
