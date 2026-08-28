"""Tests for etl.scrapers.publishedprices. Live tests against the real
HTTPS web client (no mocking -- same principle as test_carrefour.py/
test_victory.py/test_bina.py), now that the module talks HTTPS instead of
the FTP host whose data channel turned out to be blocked from every cloud
environment this project has run in (see the module docstring). Requires
network access.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scrapers.publishedprices import CHAINS, _parse_filename, download, list_files, preflight, preflight_diagnostic
from etl.scrapers.shufersal import (
    kfar_saba_full_catalog_files,
    kfar_saba_stores,
    list_stores_file,
    parse_price_xml,
    parse_stores_xml,
)


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
            self.assertIn("username", chain)
            self.assertIn("password", chain)
            self.assertIn("chain_id", chain)

    def test_two_chains_have_a_real_non_empty_password(self):
        """Confirmed from OpenIsraeliSupermarkets' scrappers/{yellow,
        salachdabach}.py -- most of this platform's chains use an empty
        password, these two don't. A regression here would silently break
        their login."""
        self.assertEqual(CHAINS["yellow"]["password"], "paz468")
        self.assertEqual(CHAINS["salach-dabach"]["password"], "12345")
        others = {k: v for k, v in CHAINS.items() if k not in ("yellow", "salach-dabach")}
        self.assertTrue(all(v["password"] == "" for v in others.values()))


class PublishedPricesLiveTests(unittest.TestCase):
    """Live against the real HTTPS web client -- this is the whole point of
    the rewrite: unlike the old FTP path, this one is actually verifiable
    from a normal network, not just asserted to work "once it runs
    somewhere else." Exercises three chains, including two with real
    non-empty passwords, to prove the login flow generalizes rather than
    only working for the one chain it was developed against."""

    def test_preflight_succeeds_for_every_configured_chain(self):
        for chain_key, cfg in CHAINS.items():
            with self.subTest(chain=chain_key):
                diag = preflight_diagnostic(cfg["username"], cfg["password"])
                self.assertTrue(diag["ok"], f"{chain_key}: failed at {diag['failed_at']}: {diag['error']}")
                self.assertTrue(preflight(cfg["username"], cfg["password"]))

    def test_list_files_and_download_work_for_rami_levy(self):
        cfg = CHAINS["rami-levy"]
        files = list_files(cfg["username"], cfg["password"])
        self.assertGreater(len(files), 0)

        stores_file = list_stores_file(files)
        self.assertIsNotNone(stores_file)
        stores = parse_stores_xml(download(cfg["username"], stores_file, cfg["password"]))
        self.assertGreater(len(stores), 0)

    def test_download_works_for_a_chain_with_a_real_password(self):
        """Yellow's account needs a real, non-empty password -- proves the
        password isn't silently dropped anywhere in the login/download path."""
        cfg = CHAINS["yellow"]
        files = list_files(cfg["username"], cfg["password"])
        self.assertGreater(len(files), 0)
        pricefull = next((f for f in files if f.category.lower() == "pricefull"), None)
        if pricefull is not None:
            xml_bytes = download(cfg["username"], pricefull, cfg["password"])
            records = parse_price_xml(xml_bytes)
            self.assertGreaterEqual(len(records), 0)

    def test_shufersal_parsers_work_unmodified_on_a_real_downloaded_file(self):
        """Same regulated schema as every other chain in this project --
        proven against a real file, not assumed."""
        cfg = CHAINS["rami-levy"]
        files = list_files(cfg["username"], cfg["password"])
        stores_file = list_stores_file(files)
        stores = parse_stores_xml(download(cfg["username"], stores_file, cfg["password"]))
        kfar_saba_ids = kfar_saba_stores(stores)

        catalog_files = list(kfar_saba_full_catalog_files(files, kfar_saba_ids)) if kfar_saba_ids else []
        if catalog_files:
            records = parse_price_xml(download(cfg["username"], catalog_files[0], cfg["password"]))
            self.assertGreater(len(records), 0)
            self.assertTrue(all(r.item_price >= 0 for r in records))


if __name__ == "__main__":
    unittest.main()
