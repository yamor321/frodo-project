import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scoring.item_code_filters import is_reliable_item_code


class IsReliableItemCodeTests(unittest.TestCase):
    def test_rejects_the_real_collision_found_live(self):
        self.assertFalse(is_reliable_item_code("7290000000145"))  # red cabbage / gift basket collision

    def test_rejects_the_pattern_generally(self):
        self.assertFalse(is_reliable_item_code("7290000000176"))
        self.assertFalse(is_reliable_item_code("7290000000114"))

    def test_accepts_real_looking_barcodes(self):
        self.assertTrue(is_reliable_item_code("7290107978460"))
        self.assertTrue(is_reliable_item_code("7290002331490"))
        self.assertTrue(is_reliable_item_code("4003790001420"))

    def test_accepts_a_real_ean8_barcode(self):
        self.assertTrue(is_reliable_item_code("72994818"))  # real, already a live cross-chain match

    def test_rejects_short_internal_plu_codes(self):
        """Real case found live comparing Victory and Carrefour: "2001"
        (yellow grapefruit at Victory) collided with an unrelated Carrefour
        product also coded "2001" -- a fake 832% spread, the next headline
        after the first collision was fixed."""
        self.assertFalse(is_reliable_item_code("2001"))
        self.assertFalse(is_reliable_item_code("2012"))

    def test_boundary_at_eight_digits(self):
        self.assertFalse(is_reliable_item_code("1234567"))  # 7 digits, rejected
        self.assertTrue(is_reliable_item_code("12345678"))  # 8 digits, accepted


if __name__ == "__main__":
    unittest.main()
