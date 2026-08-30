"""Unit tests for scripts/daily_snapshot.py's pure helpers -- no network,
no live chain data.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from daily_snapshot import usable_street_addresses


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


if __name__ == "__main__":
    unittest.main()
