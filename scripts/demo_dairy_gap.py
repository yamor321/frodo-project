"""Proof-of-concept run: Shufersal store 144 (Kfar Saba) full catalog ->
match against MoAg's live controlled-price API -> real price-gap table.

This is the first end-to-end output of the project's core idea (brief
section 1-2): a number that comes purely from arithmetic on two official
sources, no judgment field, no LLM.

Usage: python scripts/demo_dairy_gap.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.benchmarks.moag_controlled_prices import current_dairy_controlled_prices
from etl.scoring.benchmark_gap import compute_gaps
from etl.scrapers.shufersal import (
    KFAR_SABA_STORE_IDS,
    download,
    kfar_saba_full_catalog_files,
    list_files,
    parse_price_xml,
)


def main() -> None:
    print("Fetching MoAg controlled dairy prices (data.gov.il)...")
    controlled = current_dairy_controlled_prices()
    print(f"  {len(controlled)} controlled dairy products.")

    print(f"\nListing Shufersal portal, filtering for Kfar Saba stores {sorted(KFAR_SABA_STORE_IDS)}...")
    target_file = None
    for f in list_files(max_pages=200):
        if f.store_id in KFAR_SABA_STORE_IDS and f.category.lower() == "pricefull":
            target_file = f
            break
    if target_file is None:
        print("No PriceFull file found for any Kfar Saba branch on this run.")
        return
    print(f"  Using store {target_file.store_id} ({target_file.store_name}), updated {target_file.updated_at}.")

    print("Downloading + parsing catalog...")
    catalog = parse_price_xml(download(target_file))
    print(f"  {len(catalog)} items.")

    print("\nMatching against controlled prices and computing gaps...\n")
    gaps = compute_gaps(catalog, controlled)

    if not gaps:
        print("No catalog items matched a controlled product on this run.")
        return

    print(f"{'מוצר בפועל':<38} {'מחיר בפועל':>10} {'מחיר מפוקח':>10} {'פער %':>8}")
    print("-" * 70)
    for g in sorted(gaps, key=lambda g: (g.ambiguous, g.gap_pct is None)):
        if g.ambiguous:
            print(f"{g.item_name:<38} {g.actual_price:>10.2f} {'(דו-משמעי)':>10} {'—':>8}   [{', '.join(g.controlled_product_names)}]")
        else:
            print(f"{g.item_name:<38} {g.actual_price:>10.2f} {g.controlled_consumer_price:>10.2f} {g.gap_pct*100:>7.1f}%")

    matched_unambiguous = [g for g in gaps if not g.ambiguous]
    if matched_unambiguous:
        avg_gap = sum(g.gap_pct for g in matched_unambiguous) / len(matched_unambiguous)
        print(f"\n{len(gaps)} matched item(s) ({len(matched_unambiguous)} unambiguous). Average gap: {avg_gap*100:.1f}%")


if __name__ == "__main__":
    main()
