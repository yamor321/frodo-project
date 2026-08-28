"""Tests for etl.enrich.store_directory. Uses a real temp file for CACHE_PATH
rather than mocking -- same reasoning as test_raw_snapshot_fallback.py."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import etl.enrich.store_directory as store_directory


class UpdateAndSaveTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_path = pathlib.Path(self.tmp_dir) / "store_directory.json"
        self._orig_cache_path = store_directory.CACHE_PATH
        store_directory.CACHE_PATH = self.tmp_path
        self.addCleanup(setattr, store_directory, "CACHE_PATH", self._orig_cache_path)

    def test_new_store_is_saved(self):
        directory = store_directory.update_and_save({"victory-079": "כפר סבא הירוקה"}, {"victory-079": "אנגל 78"})
        self.assertEqual(directory["victory-079"], {"name": "כפר סבא הירוקה", "address": "אנגל 78"})
        self.assertTrue(self.tmp_path.exists())

    def test_a_store_missing_from_todays_run_keeps_its_last_known_entry(self):
        """The whole point of this module: a store absent from today's live
        results (the raw-snapshot-fallback case) must not lose its
        name/address just because today's run didn't see it live."""
        store_directory.update_and_save({"victory-079": "כפר סבא הירוקה"}, {"victory-079": "אנגל 78"})

        directory = store_directory.update_and_save({}, {})
        self.assertEqual(directory["victory-079"], {"name": "כפר סבא הירוקה", "address": "אנגל 78"})

    def test_a_returning_store_overwrites_its_old_entry(self):
        store_directory.update_and_save({"victory-079": "Old Name"}, {"victory-079": "Old Address"})
        directory = store_directory.update_and_save({"victory-079": "New Name"}, {"victory-079": "New Address"})
        self.assertEqual(directory["victory-079"], {"name": "New Name", "address": "New Address"})


if __name__ == "__main__":
    unittest.main()
