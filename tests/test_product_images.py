"""Live tests against the real Open Food Facts API (no mocking -- same
principle as tests/test_moag_benchmark.py and tests/test_geocode.py).
Requires network access.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.enrich.product_images import get_image_url, get_image_urls


class ProductImagesLiveTests(unittest.TestCase):
    def test_finds_a_real_known_barcode(self):
        """Verified during research: real Tnuva low-lactose milk, present
        in our own Shufersal catalog."""
        url = get_image_url("7290000040974")
        self.assertIsNotNone(url)
        self.assertTrue(url.startswith("https://"))

    def test_returns_none_for_a_nonexistent_barcode(self):
        self.assertIsNone(get_image_url("0000000000000"))

    def test_returns_none_for_a_real_barcode_off_returns_404_for(self):
        """Open Food Facts is inconsistent: most unknown barcodes come back
        200 with status:0, but some (this one, hit during a real build)
        come back a plain HTTP 404 -- both must resolve to None, not a
        crash that takes down the whole batch."""
        self.assertIsNone(get_image_url("7290013128324"))

    def test_get_image_urls_handles_a_mix_of_found_and_missing(self):
        results = get_image_urls(["7290000040974", "0000000000000"])
        self.assertIsNotNone(results["7290000040974"])
        self.assertIsNone(results["0000000000000"])


if __name__ == "__main__":
    unittest.main()
