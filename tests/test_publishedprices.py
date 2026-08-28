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
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scrapers.publishedprices import CHAINS, _parse_filename, preflight


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
    def test_ten_kfar_saba_chains_configured(self):
        """All ten confirmed live to have a real Kfar Saba branch (see
        docs/sources.md, 28.08.2026) -- not the platform's full ~30-chain
        roster, just the ones actually relevant to this pilot."""
        self.assertEqual(
            set(CHAINS),
            {
                "rami-levy", "yohananof", "osher-ad", "tiv-taam", "dor-alon", "yellow",
                "stop-market", "fresh-market", "keshet", "salach-dabach",
            },
        )
        for chain in CHAINS.values():
            self.assertIn("ftp_username", chain)
            self.assertIn("ftp_password", chain)
            self.assertIn("chain_id", chain)

    def test_two_chains_have_a_real_non_empty_password(self):
        """Confirmed from OpenIsraeliSupermarkets' scrappers/{yellow,
        salachdabach}.py -- most of this platform's chains use an empty
        password, these two don't. A regression here would silently break
        their login."""
        self.assertEqual(CHAINS["yellow"]["ftp_password"], "paz468")
        self.assertEqual(CHAINS["salach-dabach"]["ftp_password"], "12345")
        others = {k: v for k, v in CHAINS.items() if k not in ("yellow", "salach-dabach")}
        self.assertTrue(all(v["ftp_password"] == "" for v in others.values()))


class PreflightTests(unittest.TestCase):
    """preflight() wraps etl.health_check.ftp_preflight -- these just prove
    the wiring (right host/username/password passed through), not the FTP
    behavior itself, which health_check.py's own tests cover."""

    @patch("etl.scrapers.publishedprices.ftp_preflight")
    def test_delegates_to_health_check_with_the_right_host(self, mock_preflight):
        mock_preflight.return_value = True
        result = preflight("RamiLevi", "")
        self.assertTrue(result)
        mock_preflight.assert_called_once_with("url.retail.publishedprices.co.il", "RamiLevi", "")

    @patch("etl.scrapers.publishedprices.ftp_preflight")
    def test_unreachable_source_returns_false(self, mock_preflight):
        mock_preflight.return_value = False
        self.assertFalse(preflight("osherad", ""))


if __name__ == "__main__":
    unittest.main()
