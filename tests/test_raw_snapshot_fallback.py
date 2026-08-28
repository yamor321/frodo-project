"""Tests for etl.raw_snapshot_fallback. Uses a real temp directory tree
mimicking data/raw/<date>/ rather than mocking the filesystem -- the whole
point of this module is walking real directories, so that's what's worth
proving works.
"""
import datetime as dt
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.raw_snapshot_fallback import find_fallback_catalogs

REAL_PRICE_XML = """<?xml version="1.0" encoding="utf-8"?>
<Root>
<ChainID>7290696200003</ChainID>
<SubChainID>001</SubChainID>
<StoreID>079</StoreID>
<Items Count="1">
<Item>
<PriceUpdateTime>2026-08-27 05:00:00</PriceUpdateTime>
<ItemCode>7290000000123</ItemCode>
<ItemName>Test Product</ItemName>
<ManufactureName>Test Mfr</ManufactureName>
<ManufactureCountry>IL</ManufactureCountry>
<UnitQty>1</UnitQty>
<Quantity>1</Quantity>
<UnitOfMeasure>יחידה</UnitOfMeasure>
<bIsWeighted>0</bIsWeighted>
<QtyInPackage>1</QtyInPackage>
<ItemPrice>9.90</ItemPrice>
<UnitOfMeasurePrice>9.90</UnitOfMeasurePrice>
</Item>
</Items>
</Root>""".encode("utf-8")


class FindFallbackCatalogsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_finds_yesterdays_file(self):
        yesterday_dir = self.tmp / "2026-08-27"
        yesterday_dir.mkdir()
        (yesterday_dir / "PriceFull7290696200003-001-079-20260827-050544.xml").write_bytes(REAL_PRICE_XML)

        catalogs, as_of = find_fallback_catalogs(
            self.tmp, "victory-", {"079"}, dt.date(2026, 8, 28)
        )
        self.assertIn("victory-079", catalogs)
        self.assertEqual(len(catalogs["victory-079"]), 1)
        self.assertEqual(as_of["victory-079"], "2026-08-27")

    def test_skips_backward_past_missing_days_to_find_an_older_one(self):
        """The chain was down for two days straight -- must still find the
        real snapshot from three days ago rather than giving up after one
        empty day."""
        three_days_ago = self.tmp / "2026-08-25"
        three_days_ago.mkdir()
        (three_days_ago / "PriceFull7290696200003-001-079-20260825-050544.xml").write_bytes(REAL_PRICE_XML)

        catalogs, as_of = find_fallback_catalogs(
            self.tmp, "victory-", {"079"}, dt.date(2026, 8, 28)
        )
        self.assertIn("victory-079", catalogs)
        self.assertEqual(as_of["victory-079"], "2026-08-25")

    def test_nothing_found_within_lookback_window_returns_empty(self):
        catalogs, as_of = find_fallback_catalogs(
            self.tmp, "victory-", {"079"}, dt.date(2026, 8, 28), max_lookback_days=3
        )
        self.assertEqual(catalogs, {})
        self.assertEqual(as_of, {})

    def test_finds_a_same_day_earlier_success(self):
        """The real case that caught the original bug: the daily workflow
        triggers on every push, so "today" can have multiple runs. An
        earlier run today succeeded and wrote today's own raw file; a later
        run today fails live -- must still find that same-day file rather
        than treating `before` as always-excluded. Confirmed live 2026-08-28:
        Victory's page vanished from the deployed site in exactly this
        scenario before this fix (see module docstring)."""
        today_dir = self.tmp / "2026-08-28"
        today_dir.mkdir()
        (today_dir / "PriceFull7290696200003-001-079-20260828-050544.xml").write_bytes(REAL_PRICE_XML)

        catalogs, as_of = find_fallback_catalogs(
            self.tmp, "victory-", {"079"}, dt.date(2026, 8, 28)
        )
        self.assertIn("victory-079", catalogs)
        self.assertEqual(as_of["victory-079"], "2026-08-28")

    def test_prefers_todays_own_snapshot_over_an_older_one(self):
        today_dir = self.tmp / "2026-08-28"
        today_dir.mkdir()
        (today_dir / "PriceFull7290696200003-001-079-20260828-050544.xml").write_bytes(REAL_PRICE_XML)
        yesterday_dir = self.tmp / "2026-08-27"
        yesterday_dir.mkdir()
        (yesterday_dir / "PriceFull7290696200003-001-079-20260827-050544.xml").write_bytes(REAL_PRICE_XML)

        _catalogs, as_of = find_fallback_catalogs(
            self.tmp, "victory-", {"079"}, dt.date(2026, 8, 28)
        )
        self.assertEqual(as_of["victory-079"], "2026-08-28")


if __name__ == "__main__":
    unittest.main()
