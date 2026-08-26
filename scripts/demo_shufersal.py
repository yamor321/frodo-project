"""Proof-of-concept run: list the live Shufersal portal, find today's
full-catalog file for each confirmed Kfar Saba branch, download, parse, and
report a dairy-category slice -- end to end, against real data.

Usage: python scripts/demo_shufersal.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scrapers.shufersal import (
    KFAR_SABA_STORE_IDS,
    download,
    kfar_saba_full_catalog_files,
    list_files,
    parse_price_xml,
)

DAIRY_KEYWORDS = ["גבינה צהובה", "גבינה לבנה", "קוטג", "אשל", "יוגורט", "חלב "]


def main() -> None:
    print(f"Listing live portal, filtering for Kfar Saba stores {sorted(KFAR_SABA_STORE_IDS)}...")
    targets = []
    found_stores = set()
    rows_walked = 0
    for f in list_files(max_pages=200):
        rows_walked += 1
        if f.store_id in KFAR_SABA_STORE_IDS and f.category.lower() == "pricefull":
            targets.append(f)
            found_stores.add(f.store_id)
        if found_stores == KFAR_SABA_STORE_IDS:
            break
    print(f"Walked {rows_walked} file rows before stopping (found {len(found_stores)}/{len(KFAR_SABA_STORE_IDS)} target stores).")
    print(f"Found {len(targets)} PriceFull files for Kfar Saba branches today:")
    for t in targets:
        print(f"  store {t.store_id} ({t.store_name}) -- updated {t.updated_at}, {t.size}")

    if not targets:
        print("No PriceFull files found for Kfar Saba branches on this run.")
        return

    target = targets[0]
    print(f"\nDownloading + parsing: store {target.store_id} ({target.store_name})...")
    xml_bytes = download(target)
    records = parse_price_xml(xml_bytes)
    print(f"Parsed {len(records)} items.")

    dairy = [r for r in records if any(k in r.item_name for k in DAIRY_KEYWORDS)]
    print(f"\nKeyword-matched dairy-ish items: {len(dairy)} (naive match -- see test suite for why this needs refining)")
    for r in dairy[:8]:
        print(f"  {r.item_code:>15}  {r.item_name:<35}  ₪{r.item_price:.2f}")


if __name__ == "__main__":
    main()
