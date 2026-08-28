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


if __name__ == "__main__":
    unittest.main()
