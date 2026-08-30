"""Unit tests for etl/enrich/store_format.py -- no network, no live data."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.enrich.store_format import store_format


class StoreFormatTests(unittest.TestCase):
    def test_is_online_wins_over_name_heuristics(self):
        """StoreType (is_online) is a sourced, verified signal -- it must
        take priority over the name-keyword heuristic, not the other way
        around, even for a name that would otherwise say "hyper" (e.g. a
        chain's own "online"/"quick" branding still containing a hyper-
        format keyword by coincidence)."""
        self.assertEqual(store_format("שופרסל דיל אונליין", is_online=True), "online")

    def test_is_pharm_wins_over_name_heuristics(self):
        """is_pharm is set at the chain level (see daily_snapshot.py's
        ChainCollection.is_pharm_chain), never inferred from a name -- it
        must win even over a name that happens to contain a hyper/express
        keyword, the same way is_online already does."""
        self.assertEqual(store_format("היפר פארם כפר סבא", is_pharm=True), "pharm")

    def test_falls_back_to_name_heuristics_when_not_online_or_pharm(self):
        self.assertEqual(store_format("שופרסל דיל שבירו"), "hyper")
        self.assertEqual(store_format("שופרסל אקספרס תל חי"), "express")

    def test_default_is_supermarket_not_the_old_small_format_bucket(self):
        """Regression test for the reported bug: a name with no format
        signal at all used to silently default to the small "neighborhood"
        bucket, mislabeling real supermarkets (like שוק העיר, a large
        industrial-zone supermarket) as convenience stores on the map."""
        self.assertEqual(store_format("שוק העיר — כפר סבא מזרח"), "supermarket")
        self.assertEqual(store_format('שופרסל — שלי כ"ס- רוטשילד'), "supermarket")

    def test_manual_override_wins_over_the_name_heuristic(self):
        """A sourced per-store override (etl/enrich/format_overrides.py) must
        win over whatever the name-keyword heuristic would otherwise say --
        it exists specifically for the case where the heuristic is known,
        with an independent source, to be wrong for one branch."""
        import etl.enrich.store_format as store_format_module

        original = dict(store_format_module.FORMAT_OVERRIDES)
        store_format_module.FORMAT_OVERRIDES["999"] = "express"
        try:
            self.assertEqual(
                store_format("שופרסל דיל שבירו", store_id="999"), "express"
            )
        finally:
            store_format_module.FORMAT_OVERRIDES.clear()
            store_format_module.FORMAT_OVERRIDES.update(original)

    def test_override_is_ignored_without_a_matching_store_id(self):
        self.assertEqual(store_format("שופרסל דיל שבירו", store_id="not-in-overrides"), "hyper")


if __name__ == "__main__":
    unittest.main()
