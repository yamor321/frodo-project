"""Live test against the real data.gov.il CKAN API (no mocking -- this
project's principle is arithmetic on real official data, so the benchmark
client is tested against the actual source, same as the Shufersal demo
script). Requires network access.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.benchmarks.moag_controlled_prices import (
    DAIRY_PRODUCT_NAMES,
    current_controlled_prices,
    current_dairy_controlled_prices,
)


class MoagBenchmarkLiveTests(unittest.TestCase):
    def test_fetches_more_than_just_the_current_snapshot(self):
        """391 records verified live 2026-08-27 -- one row per price change
        per product, not just 21-22 current values."""
        from etl.benchmarks.moag_controlled_prices import fetch_all_records

        records = list(fetch_all_records())
        self.assertGreater(len(records), 100)

    def test_current_prices_cover_all_dairy_products(self):
        current = {r.product for r in current_controlled_prices()}
        missing = DAIRY_PRODUCT_NAMES - current
        self.assertEqual(missing, set(), f"dairy products not found in live data: {missing}")

    def test_dairy_filter_returns_only_dairy_products(self):
        dairy = current_dairy_controlled_prices()
        self.assertEqual({r.product for r in dairy}, DAIRY_PRODUCT_NAMES)
        for r in dairy:
            self.assertGreater(r.consumer_price, 0)


if __name__ == "__main__":
    unittest.main()
