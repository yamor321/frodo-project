"""Exploratory analysis (throwaway, not wired into daily_snapshot.py): does
real, structured promo/sale data exist across the chains this project
already collects, and if so, what fraction of it is a "simple" promo any
shopper can actually get (no coupon, no club card, no minimum quantity) vs.
coupon/club/bundle-gated or already expired/not-yet-started?

Confirmed live before this script existed: Shufersal publishes a real
"promofull" category file per store (docs/sources.md already lists the
category name, but this project never fetched one until now). One real
14.2MB sample (store 144) showed a rich nested schema -- see the module
docstring context in the plan this script exists to validate.

Usage: python scripts/explore_promo_shape.py
"""
import datetime as dt
import pathlib
import sys
import xml.etree.ElementTree as ET
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scrapers import bina, carrefour, publishedprices, victory, wolt
from etl.scrapers.shufersal import (
    download,
    kfar_saba_full_catalog_files,
    kfar_saba_stores,
    list_files,
    list_stores_file,
    parse_price_xml,
    parse_stores_xml,
)

SAMPLE_STORE_IDS = ["144", "394", "615", "682", "752"]


def check_cross_chain_categories() -> None:
    print("=" * 70)
    print("PART A -- does each already-integrated chain publish a promo category?")
    print("=" * 70)

    checks = []

    try:
        files = carrefour.list_files()
        cats = {f.category.lower() for f in files}
        checks.append(("Carrefour", cats))
    except Exception as e:
        checks.append(("Carrefour", f"ERROR: {e}"))

    try:
        files = victory.list_files(victory.VICTORY_CHAIN_IDS)
        cats = {f.category.lower() for f in files}
        checks.append(("Victory", cats))
    except Exception as e:
        checks.append(("Victory", f"ERROR (expected if network-blocked): {e}"))

    try:
        chain = bina.CHAINS["shuk-hair"]
        files = bina.list_files(chain["url_perfix"], chain["chain_id"])
        cats = {f.category.lower() for f in files}
        checks.append(("Shuk HaIr (Bina)", cats))
    except Exception as e:
        checks.append(("Shuk HaIr (Bina)", f"ERROR: {e}"))

    try:
        files = wolt.list_files()
        cats = {f.category.lower() for f in files}
        checks.append(("Wolt Market", cats))
    except Exception as e:
        checks.append(("Wolt Market", f"ERROR: {e}"))

    for chain_key in ["rami-levy", "yohananof", "osher-ad", "tiv-taam"]:
        try:
            cfg = publishedprices.CHAINS[chain_key]
            username, password = cfg["username"], cfg["password"]
            if not publishedprices.preflight(username, password):
                checks.append((chain_key, "preflight failed"))
                continue
            files = publishedprices.list_files(username, password)
            cats = {f.category.lower() for f in files}
            checks.append((chain_key, cats))
        except Exception as e:
            checks.append((chain_key, f"ERROR: {e}"))

    for name, result in checks:
        if isinstance(result, set):
            has_promo = any("promo" in c for c in result)
            marker = "YES" if has_promo else "no"
            print(f"  {name:<20} promo category present: {marker:<4} (all categories: {sorted(result)})")
        else:
            print(f"  {name:<20} {result}")
    print()


def parse_promo_xml_inline(xml_bytes: bytes):
    """Throwaway parser matching the real schema found live -- not the
    final shufersal.parse_promo_xml(), just enough structure to analyze
    real data before committing to a dataclass design."""
    root = ET.fromstring(xml_bytes)

    def text(el, tag, default=""):
        child = el.find(tag)
        return child.text.strip() if child is not None and child.text else default

    promos = []
    promotions_el = root.find("Promotions")
    if promotions_el is None:
        return promos
    for promo in promotions_el.findall("Promotion"):
        items = []
        for group in promo.findall("./Groups/Group"):
            for pi in group.findall("./PromotionItems/PromotionItem"):
                items.append(
                    {
                        "item_code": text(pi, "ItemCode"),
                        "min_qty": float(text(pi, "MinQty", "0") or 0),
                        "discount_rate": float(text(pi, "DiscountRate", "0") or 0),
                        "discounted_price": float(text(pi, "DiscountedPrice", "0") or 0),
                    }
                )
        promos.append(
            {
                "promotion_id": text(promo, "PromotionID"),
                "description": text(promo, "PromotionDescription"),
                "start": text(promo, "PromotionStartDateTime"),
                "end": text(promo, "PromotionEndDateTime"),
                "club_id": text(promo, "ClubID"),
                "is_coupon": text(promo, "AdditionalIsCoupon") == "1",
                "is_gift_item_promo_level": text(promo, "IsGiftItem") not in ("", "0"),
                "items": items,
            }
        )
    return promos


def parse_dt(s: str):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def shape_survey() -> None:
    print("=" * 70)
    print("PART B -- real shape survey across several Shufersal Kfar Saba stores")
    print("=" * 70)

    all_files = list(list_files(max_pages=200))
    stores_file = list_stores_file(all_files)
    stores = parse_stores_xml(download(stores_file))
    ks_ids = kfar_saba_stores(stores)
    print(f"Kfar Saba store ids confirmed live: {sorted(ks_ids)}\n")

    today = dt.date.today()
    club_ids_seen = Counter()
    total_promos = 0
    tally = Counter()
    join_checked = 0
    join_confirmed_cheaper = 0
    example_simple = None

    for store_id in SAMPLE_STORE_IDS:
        if store_id not in ks_ids:
            print(f"  store {store_id}: not confirmed Kfar Saba live today, skipping")
            continue

        promo_files = [
            f for f in all_files if f.store_id == store_id and f.category.lower() == "promofull"
        ]
        if not promo_files:
            print(f"  store {store_id}: no promofull file found today")
            continue
        promo_file = promo_files[0]
        print(f"  store {store_id}: downloading {promo_file.filename} ({promo_file.size})...")
        promo_xml = download(promo_file)
        promos = parse_promo_xml_inline(promo_xml)
        print(f"    {len(promos)} <Promotion> elements")
        total_promos += len(promos)

        # Also grab this store's own PriceFull for the join-check.
        price_files = [f for f in all_files if f.store_id == store_id and f.category.lower() == "pricefull"]
        regular_price_by_code = {}
        if price_files:
            price_records = parse_price_xml(download(price_files[0]))
            regular_price_by_code = {r.item_code: r.item_price for r in price_records}

        for p in promos:
            club_ids_seen[p["club_id"]] += 1
            start, end = parse_dt(p["start"]), parse_dt(p["end"])
            date_active = start is not None and end is not None and start.date() <= today <= end.date()
            all_customers = p["club_id"].strip().startswith("0")
            is_coupon = p["is_coupon"]
            is_gift = p["is_gift_item_promo_level"]
            min_qty_simple = all(i["min_qty"] <= 1 for i in p["items"]) if p["items"] else False
            has_discount = any(i["discounted_price"] > 0 or i["discount_rate"] > 0 for i in p["items"])

            if not date_active:
                tally["expired_or_future"] += 1
                continue
            if is_coupon:
                tally["coupon_gated"] += 1
                continue
            if not all_customers:
                tally["club_gated"] += 1
                continue
            if is_gift or not min_qty_simple or not has_discount:
                tally["gift_or_bundle_only"] += 1
                continue

            tally["simple_active_universal"] += 1
            for i in p["items"]:
                if i["item_code"] in regular_price_by_code and i["discounted_price"] > 0:
                    join_checked += 1
                    if i["discounted_price"] < regular_price_by_code[i["item_code"]]:
                        join_confirmed_cheaper += 1
                        if example_simple is None:
                            example_simple = (p["description"], i["item_code"], i["discounted_price"], regular_price_by_code[i["item_code"]], p["end"])

    print(f"\nTotal <Promotion> elements sampled: {total_promos}")
    print("\nClassification tally:")
    for k, v in tally.most_common():
        pct = 100 * v / max(total_promos, 1)
        print(f"  {k:<28} {v:>6}  ({pct:.1f}%)")

    print(f"\nJoin-check (simple promos only): {join_checked} item_codes matched against PriceFull,")
    print(f"  {join_confirmed_cheaper} confirmed actually cheaper than the regular shelf price ({100*join_confirmed_cheaper/max(join_checked,1):.1f}%)")

    print("\nClubID sentinel values actually seen (raw, for the startswith('0') decision):")
    for club_id, count in club_ids_seen.most_common(10):
        print(f"  {club_id!r}: {count}")

    if example_simple:
        desc, code, disc_price, reg_price, end = example_simple
        print(f"\nWorked example of a real simple/confirmed promo:")
        print(f"  {desc!r} | item {code} | promo price {disc_price} < regular {reg_price} | valid until {end}")
    else:
        print("\nNo simple+confirmed-cheaper example found in this sample.")


if __name__ == "__main__":
    check_cross_chain_categories()
    shape_survey()
