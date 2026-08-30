"""Live tests against the real Nominatim API (no mocking -- same principle
as tests/test_moag_benchmark.py: this project verifies against the actual
source, not a stand-in). Requires network access.

Regression coverage for two real bugs a user found on the live map: (1)
stores 615 and 140 both geocoded to Kfar Saba's city centroid because their
Address field was literally just the city name, and (2) a store whose real
address is on one street rendered near a different street entirely, because
free-text geocoding matched loosely across a concatenated blob instead of
the street field specifically.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.enrich.geocode import _is_specific_street, _within_kfar_saba_bounds, geocode


class SpecificStreetTests(unittest.TestCase):
    def test_rejects_bare_city_name(self):
        """This is the exact bug: Address == "כפר סבא" with no street --
        truthy, so the old `if addr` filter let it through."""
        self.assertFalse(_is_specific_street("כפר סבא"))
        self.assertFalse(_is_specific_street("כפר-סבא"))
        self.assertFalse(_is_specific_street("  "))
        self.assertFalse(_is_specific_street(""))

    def test_accepts_a_real_street_address(self):
        self.assertTrue(_is_specific_street("רוטשילד 65"))

    def test_rejects_a_url_instead_of_a_street(self):
        """Real case: Carrefour's online-only branches (471, 473) carry
        their website as the Stores.xml Address field, since there's no
        physical storefront to place a pin for."""
        self.assertFalse(_is_specific_street("https://www.quik.co.il"))
        self.assertFalse(_is_specific_street("https://www.carrefour.co.il"))

    def test_rejects_an_uppercase_url_without_a_protocol(self):
        """Real case, found live 2026-08-30: Shufersal's own online store
        (413) publishes its Address as "WWW.SHUFERSAL.CO.IL" -- uppercase,
        no http(s):// prefix. The original check was case-sensitive and
        would have sent this straight to Nominatim as if it were a real
        street; latent until StoreType-based inclusion made store 413
        reachable at all."""
        self.assertFalse(_is_specific_street("WWW.SHUFERSAL.CO.IL"))


class BoundsCheckTests(unittest.TestCase):
    def test_accepts_a_known_real_kfar_saba_point(self):
        self.assertTrue(_within_kfar_saba_bounds(32.1755487, 34.9071512))  # Weizmann 29

    def test_rejects_a_point_clearly_outside_the_city(self):
        self.assertFalse(_within_kfar_saba_bounds(32.0853, 34.7818))  # central Tel Aviv


class GeocodeLiveTests(unittest.TestCase):
    def test_bare_city_name_short_circuits_without_a_result(self):
        """Same scenario that produced the 615/140 bug -- must now return
        None instead of the city centroid."""
        self.assertIsNone(geocode("כפר סבא"))

    def test_finds_a_real_known_kfar_saba_address(self):
        point = geocode("ויצמן 29")
        self.assertIsNotNone(point)
        self.assertAlmostEqual(point.lat, 32.1755487, delta=0.01)
        self.assertAlmostEqual(point.lon, 34.9071512, delta=0.01)

    def test_rejects_a_real_result_outside_kfar_saba(self):
        """Rothschild St, Tel Aviv is a real, well-known address Nominatim
        will happily resolve -- proves the Kfar-Saba-only bounding box
        rejects an out-of-town match instead of trusting it."""
        point = geocode("רוטשילד", city="תל אביב יפו")
        self.assertIsNone(point)


if __name__ == "__main__":
    unittest.main()
