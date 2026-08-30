"""Unit tests for etl.scrapers.shufersal, run against a real (trimmed) sample
file downloaded from the live Shufersal portal for a Kfar Saba branch
(store 144, "דיל שבירו כפר סבא") on 2026-08-26.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scrapers.shufersal import parse_price_xml, PriceRecord

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "shufersal_pricefull_sample.xml"


class ParsePriceXmlTests(unittest.TestCase):
    def setUp(self):
        self.records = parse_price_xml(FIXTURE.read_bytes())

    def test_parses_every_item(self):
        self.assertEqual(len(self.records), 15)
        self.assertTrue(all(isinstance(r, PriceRecord) for r in self.records))

    def test_store_and_chain_identity_propagated_to_every_row(self):
        self.assertTrue(all(r.chain_id == "7290027600007" for r in self.records))
        self.assertTrue(all(r.store_id == "144" for r in self.records))
        self.assertTrue(all(r.subchain_id == "002" for r in self.records))

    def test_prices_parsed_as_numbers(self):
        zipper_bags = next(r for r in self.records if r.item_code == "10900035187")
        self.assertEqual(zipper_bags.item_name, 'שקיות זיפר M 25 יחידות')
        self.assertAlmostEqual(zipper_bags.item_price, 16.90)
        self.assertAlmostEqual(zipper_bags.unit_of_measure_price, 16.90)

    def test_weighted_flag_parsed_as_bool(self):
        self.assertTrue(all(r.is_weighted is False for r in self.records))

    def test_naive_dairy_keyword_match_has_false_positives(self):
        """Real-data proof of the risk the brief flags in section 4: matching
        product names against a keyword like "שמנת" (cream) also catches
        "גלידת שמנת" (cream-*flavored ice cream*) -- not the regulated dairy
        category at all. Confirms category mapping needs the LLM
        classifier + closed category list from section 4, not a keyword scan.
        """
        naive_matches = [r for r in self.records if "שמנת" in r.item_name]
        actually_dairy = [r for r in naive_matches if "גלידה" not in r.item_name and "גלידת" not in r.item_name]
        self.assertGreater(len(naive_matches), len(actually_dairy))


_WOLT_SHAPED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Root>
  <ChainID>7290058249350</ChainID>
  <SubChainID>000</SubChainID>
  <StoreID>005</StoreID>
  <Items>
    <Item>
      <ItemCode>1234567890123</ItemCode>
      <ItemName>מוצר לדוגמה</ItemName>
      <ManufactureName></ManufactureName>
      <ManufactureCountry></ManufactureCountry>
      <UnitQty></UnitQty>
      <Quantity>1</Quantity>
      <UnitOfMeasure></UnitOfMeasure>
      <blsWeighted>1</blsWeighted>
      <QtyInPackage></QtyInPackage>
      <ItemPrice>9.90</ItemPrice>
      <UnitOfMeasurePrice>9.90</UnitOfMeasurePrice>
      <PriceUpdateTime></PriceUpdateTime>
    </Item>
  </Items>
</Root>"""


class WeightedFlagTagVariantTests(unittest.TestCase):
    """Regression for a real bug found live 2026-08-30: Wolt Market's own
    PriceFull files spell this flag <blsWeighted> (lowercase L), not
    <bIsWeighted> (capital I) like every other chain's schema. Synthetic,
    offline -- not dependent on live catalog content."""

    def test_reads_is_weighted_from_the_lowercase_l_tag_variant(self):
        records = parse_price_xml(_WOLT_SHAPED_XML.encode("utf-8"))
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0].is_weighted)


if __name__ == "__main__":
    unittest.main()
