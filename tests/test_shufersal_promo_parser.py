"""Unit tests for etl.scrapers.shufersal's promo parsing/filtering
(parse_promo_xml, is_simple_active_promo, simple_promo_item_prices) --
synthetic XML, no network. See tests/test_active_promos.py for the
cross-check-against-regular-price logic these feed into.
"""
import datetime as dt
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scrapers.shufersal import (
    PromoRecord,
    is_simple_active_promo,
    parse_promo_xml,
    simple_promo_item_prices,
)

TODAY = dt.date(2026, 8, 30)

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "shufersal_promofull_sample.xml"

_NESTED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Root>
  <ChainID>7290027600007</ChainID>
  <SubChainID>002</SubChainID>
  <StoreID>144</StoreID>
  <Promotions>
    <Promotion>
      <PromotionID>111</PromotionID>
      <PromotionDescription>מבצע פשוט</PromotionDescription>
      <PromotionStartDateTime>2026-01-01T00:00:00.000</PromotionStartDateTime>
      <PromotionEndDateTime>2027-01-01T00:00:00.000</PromotionEndDateTime>
      <ClubID>0 - כלל הלקוחות</ClubID>
      <AdditionalIsCoupon>0</AdditionalIsCoupon>
      <IsGiftItem></IsGiftItem>
      <Groups>
        <Group>
          <DiscountType>0</DiscountType>
          <PromotionItems>
            <PromotionItem>
              <ItemCode>111111</ItemCode>
              <MinQty>1.00</MinQty>
              <DiscountRate>10</DiscountRate>
              <DiscountedPrice>9.00</DiscountedPrice>
            </PromotionItem>
          </PromotionItems>
        </Group>
        <Group>
          <DiscountType>0</DiscountType>
          <PromotionItems>
            <PromotionItem>
              <ItemCode>222222</ItemCode>
              <MinQty>1.00</MinQty>
              <DiscountRate>10</DiscountRate>
              <DiscountedPrice>18.00</DiscountedPrice>
            </PromotionItem>
          </PromotionItems>
        </Group>
      </Groups>
    </Promotion>
    <Promotion>
      <PromotionID>222</PromotionID>
      <PromotionDescription>קופון דבש - מתנה</PromotionDescription>
      <PromotionStartDateTime>2014-07-16T00:00:00.000</PromotionStartDateTime>
      <PromotionEndDateTime>2031-01-01T02:59:00.000</PromotionEndDateTime>
      <ClubID>0 - כלל הלקוחות</ClubID>
      <AdditionalIsCoupon>1</AdditionalIsCoupon>
      <IsGiftItem></IsGiftItem>
      <Groups>
        <Group>
          <DiscountType>0</DiscountType>
          <PromotionItems>
            <PromotionItem>
              <ItemCode>333333</ItemCode>
              <MinQty>1.00</MinQty>
              <DiscountRate>100</DiscountRate>
              <DiscountedPrice>0.00</DiscountedPrice>
            </PromotionItem>
          </PromotionItems>
        </Group>
      </Groups>
    </Promotion>
  </Promotions>
</Root>"""


class ParsePromoXmlTests(unittest.TestCase):
    def test_parses_both_promotions(self):
        records = parse_promo_xml(_NESTED_XML.encode("utf-8"))
        self.assertEqual(len(records), 2)
        self.assertTrue(all(isinstance(r, PromoRecord) for r in records))

    def test_flattens_items_across_multiple_groups(self):
        """Real schema quirk: one Promotion can have several Groups, each
        with their own PromotionItems -- all items must end up in the
        same PromoRecord.items list."""
        records = parse_promo_xml(_NESTED_XML.encode("utf-8"))
        simple = next(r for r in records if r.promotion_id == "111")
        self.assertEqual({i.item_code for i in simple.items}, {"111111", "222222"})

    def test_coupon_flag_parsed(self):
        records = parse_promo_xml(_NESTED_XML.encode("utf-8"))
        coupon = next(r for r in records if r.promotion_id == "222")
        self.assertTrue(coupon.is_coupon)
        simple = next(r for r in records if r.promotion_id == "111")
        self.assertFalse(simple.is_coupon)

    def test_empty_is_gift_item_element_parses_as_false(self):
        """<IsGiftItem></IsGiftItem> (empty, but present) must not be
        treated as truthy -- only a real "1" (or similar non-empty/non-zero
        value) counts."""
        records = parse_promo_xml(_NESTED_XML.encode("utf-8"))
        self.assertTrue(all(not r.is_gift_item for r in records))

    def test_store_and_chain_identity_propagated(self):
        records = parse_promo_xml(_NESTED_XML.encode("utf-8"))
        self.assertTrue(all(r.store_id == "144" for r in records))
        self.assertTrue(all(r.chain_id == "7290027600007" for r in records))

    def test_missing_promotions_element_returns_empty_list(self):
        xml = b'<?xml version="1.0"?><Root><ChainID>1</ChainID></Root>'
        self.assertEqual(parse_promo_xml(xml), [])


class IsSimpleActivePromoTests(unittest.TestCase):
    def setUp(self):
        self.records = parse_promo_xml(_NESTED_XML.encode("utf-8"))
        self.simple = next(r for r in self.records if r.promotion_id == "111")
        self.coupon = next(r for r in self.records if r.promotion_id == "222")

    def test_accepts_the_real_simple_shape(self):
        self.assertTrue(is_simple_active_promo(self.simple, TODAY))

    def test_excludes_coupon_gated(self):
        """Real live finding, 2026-08-30: the coupon-gift shape is common
        (7.0% of all real promotions sampled) -- must be excluded."""
        self.assertFalse(is_simple_active_promo(self.coupon, TODAY))

    def test_excludes_club_gated(self):
        gated = parse_promo_xml(
            _NESTED_XML.replace("0 - כלל הלקוחות", "3 - מועדון ספציפי", 1).encode("utf-8")
        )[0]
        self.assertFalse(is_simple_active_promo(gated, TODAY))

    def test_excludes_expired(self):
        self.assertFalse(is_simple_active_promo(self.simple, dt.date(2028, 1, 1)))

    def test_excludes_not_yet_started(self):
        self.assertFalse(is_simple_active_promo(self.simple, dt.date(2025, 1, 1)))

    def test_excludes_malformed_dates(self):
        broken = PromoRecord(
            chain_id="1", subchain_id="1", store_id="1", promotion_id="x",
            description="", start_datetime="not-a-date", end_datetime="not-a-date",
            club_id="0 - כלל הלקוחות", is_coupon=False, is_gift_item=False, items=[],
        )
        self.assertFalse(is_simple_active_promo(broken, TODAY))


class SimplePromoItemPricesTests(unittest.TestCase):
    def test_returns_item_code_to_discounted_price(self):
        records = parse_promo_xml(_NESTED_XML.encode("utf-8"))
        simple = next(r for r in records if r.promotion_id == "111")
        self.assertEqual(simple_promo_item_prices(simple), {"111111": 9.0, "222222": 18.0})

    def test_excludes_bundle_min_qty_items(self):
        records = parse_promo_xml(
            _NESTED_XML.replace("<MinQty>1.00</MinQty>\n              <DiscountRate>10</DiscountRate>\n              <DiscountedPrice>9.00</DiscountedPrice>", "<MinQty>3.00</MinQty>\n              <DiscountRate>10</DiscountRate>\n              <DiscountedPrice>9.00</DiscountedPrice>", 1).encode("utf-8")
        )
        simple = next(r for r in records if r.promotion_id == "111")
        prices = simple_promo_item_prices(simple)
        self.assertNotIn("111111", prices)
        self.assertIn("222222", prices)

    def test_excludes_zero_price_items(self):
        records = parse_promo_xml(_NESTED_XML.encode("utf-8"))
        coupon = next(r for r in records if r.promotion_id == "222")
        self.assertEqual(simple_promo_item_prices(coupon), {})


class RealFixtureRegressionTests(unittest.TestCase):
    """Real sample downloaded live 2026-08-30 (store 682) -- three real
    <Promotion> entries covering the three shapes the live shape survey
    found (see docs/sources.md): simple/universal, coupon-gated, and
    club-gated. Not synthetic -- a regression against the real schema,
    same pattern as test_shufersal_parser.py's own PriceFull fixture."""

    def setUp(self):
        self.records = parse_promo_xml(FIXTURE.read_bytes())

    def test_parses_all_three_real_promotions(self):
        self.assertEqual(len(self.records), 3)

    def test_real_simple_universal_discount_is_accepted(self):
        promo = next(r for r in self.records if r.promotion_id == "3246581")
        self.assertEqual(promo.description, "תו זהב 5% הנחה מותג שופרסל")
        self.assertFalse(promo.is_coupon)
        self.assertFalse(promo.is_gift_item)
        self.assertTrue(is_simple_active_promo(promo, TODAY))
        self.assertEqual(
            simple_promo_item_prices(promo),
            {"7290103706982": 18.91, "7296073277255": 22.71},
        )

    def test_real_coupon_gift_is_excluded(self):
        promo = next(r for r in self.records if r.promotion_id == "3406201")
        self.assertTrue(promo.is_coupon)
        self.assertFalse(is_simple_active_promo(promo, TODAY))

    def test_real_club_restricted_discount_is_excluded(self):
        promo = next(r for r in self.records if r.promotion_id == "1649969")
        self.assertFalse(promo.club_id.strip().startswith("0"))
        self.assertFalse(is_simple_active_promo(promo, TODAY))


if __name__ == "__main__":
    unittest.main()
