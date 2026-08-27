"""Exploratory analysis: within Shufersal's own Kfar Saba branches, how much
does the SAME product (same barcode) vary in price across the 6 confirmed
branches? This is layer-2-at-city-scale -- doesn't need a second chain to be
interesting, since Shufersal runs different store formats (Deal/Sheli
budget, BE convenience, Express mini) in the same city.

Usage: python scripts/explore_kfar_saba_spread.py
"""
import pathlib
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.scrapers.shufersal import (
    KFAR_SABA_STORE_IDS,
    download,
    kfar_saba_full_catalog_files,
    list_files,
)


def main() -> None:
    print("Listing portal and finding PriceFull for all 6 Kfar Saba branches...")
    all_files = list(list_files(max_pages=200))
    targets = list(kfar_saba_full_catalog_files(all_files, KFAR_SABA_STORE_IDS))
    print(f"Found {len(targets)} branch catalogs.\n")

    # item_code -> store_id -> (item_name, price)
    by_item: dict[str, dict[str, tuple[str, float]]] = defaultdict(dict)
    store_names: dict[str, str] = {}

    for f in targets:
        store_names[f.store_id] = f.store_name
        print(f"Downloading store {f.store_id} ({f.store_name})...")
        from etl.scrapers.shufersal import parse_price_xml

        records = parse_price_xml(download(f))
        print(f"  {len(records)} items")
        for r in records:
            by_item[r.item_code][r.store_id] = (r.item_name, r.item_price)

    print(f"\n{len(by_item)} distinct barcodes seen across all 6 branches.\n")

    # Items present in >=4 of the 6 branches, with real price spread.
    spreads = []
    for code, store_prices in by_item.items():
        if len(store_prices) < 4:
            continue
        prices = [p for _name, p in store_prices.values()]
        lo, hi = min(prices), max(prices)
        if lo <= 0:
            continue
        spread_pct = (hi - lo) / lo
        name = next(iter(store_prices.values()))[0]
        spreads.append((spread_pct, hi - lo, code, name, store_prices))

    spreads.sort(key=lambda x: -x[0])

    print(f"Items in >=4/6 branches with the largest price spread (top 20 of {len(spreads)}):\n")
    print(f"{'מוצר':<38} {'סניפים':>7} {'זול':>8} {'יקר':>8} {'פער %':>8}")
    print("-" * 78)
    for spread_pct, spread_abs, code, name, store_prices in spreads[:20]:
        prices = sorted(store_prices.items(), key=lambda kv: kv[1][1])
        lo_store, (_ln, lo_price) = prices[0]
        hi_store, (_hn, hi_price) = prices[-1]
        print(
            f"{name:<38} {len(store_prices):>7} {lo_price:>8.2f} {hi_price:>8.2f} {spread_pct*100:>7.1f}%"
        )
        print(f"   זול ביותר: {lo_store} ({store_names.get(lo_store,'')})  |  יקר ביותר: {hi_store} ({store_names.get(hi_store,'')})")


if __name__ == "__main__":
    main()
