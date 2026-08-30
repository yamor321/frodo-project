"""Unit tests for scripts/daily_snapshot.py's pure helpers -- no network,
no live chain data.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from daily_snapshot import store_format, usable_street_addresses


class UsableStreetAddressesTests(unittest.TestCase):
    def test_drops_the_literal_unknown_placeholder(self):
        """Real case found live 2026-08-29: Yohananof store 024's own
        Stores.xml publishes address=="unknown" -- the same data-quality bug
        that also breaks its City field. Showing that verbatim would read as
        a genuine street address to a Hebrew-reading visitor."""
        addrs = {"yohananof-024": "unknown", "rami-levy-033": "הרצל 10"}
        self.assertEqual(usable_street_addresses(addrs, {}), {"rami-levy-033": "הרצל 10"})

    def test_drops_other_known_placeholders_case_insensitively(self):
        addrs = {"a": "", "b": "0", "c": "-", "d": "UNKNOWN", "e": "  "}
        self.assertEqual(usable_street_addresses(addrs, {}), {})

    def test_an_override_can_rescue_an_otherwise_placeholder_address(self):
        addrs = {"keshet-019": "unknown"}
        overrides = {"keshet-019": 'מרכז מסחרי "שרונה", דרך השרון 12'}
        self.assertEqual(
            usable_street_addresses(addrs, overrides),
            {"keshet-019": 'מרכז מסחרי "שרונה", דרך השרון 12'},
        )

    def test_a_real_address_passes_through_unchanged(self):
        addrs = {"1": "הרצל 10"}
        self.assertEqual(usable_street_addresses(addrs, {}), {"1": "הרצל 10"})


class StoreFormatTests(unittest.TestCase):
    def test_is_online_wins_over_name_heuristics(self):
        """StoreType (is_online) is a sourced, verified signal -- it must
        take priority over the name-keyword heuristic, not the other way
        around, even for a name that would otherwise say "hyper" (e.g. a
        chain's own "online"/"quick" branding still containing a hyper-
        format keyword by coincidence)."""
        self.assertEqual(store_format("שופרסל דיל אונליין", is_online=True), "online")

    def test_falls_back_to_name_heuristics_when_not_online(self):
        self.assertEqual(store_format("שופרסל דיל שבירו", is_online=False), "hyper")
        self.assertEqual(store_format("שופרסל אקספרס תל חי", is_online=False), "neighborhood")


if __name__ == "__main__":
    unittest.main()
