"""Daily collection run: Shufersal Kfar Saba branches -> permanent raw
snapshot + dairy price-gap output. Designed to be invoked by
.github/workflows/daily-shufersal.yml (not yet connected -- see that file's
header comment and docs/sources.md).

Per the brief (section 3): every day this doesn't run is permanently lost
history, since chains are only required to retain files for 3 months.

Usage: python scripts/daily_snapshot.py
"""
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.benchmarks.moag_controlled_prices import current_dairy_controlled_prices
from etl.scoring.benchmark_gap import compute_gaps
from etl.scrapers.shufersal import (
    KFAR_SABA_STORE_IDS,
    download,
    kfar_saba_full_catalog_files,
    kfar_saba_stores,
    list_files,
    list_stores_file,
    parse_price_xml,
    parse_stores_xml,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> None:
    today = dt.date.today().isoformat()
    raw_dir = ROOT / "data" / "raw" / today
    processed_dir = ROOT / "data" / "processed" / today
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    print("Listing Shufersal portal...")
    all_files = list(list_files(max_pages=200))

    stores_file = list_stores_file(all_files)
    if stores_file is not None:
        stores = parse_stores_xml(download(stores_file))
        store_ids = kfar_saba_stores(stores) or KFAR_SABA_STORE_IDS
        print(f"Kfar Saba stores (from official City==6900 filter): {sorted(store_ids)}")
    else:
        store_ids = KFAR_SABA_STORE_IDS
        print(f"No Stores file found this run -- falling back to known IDs: {sorted(store_ids)}")

    controlled = current_dairy_controlled_prices()
    print(f"{len(controlled)} controlled dairy products fetched.")

    all_gaps = []
    for f in kfar_saba_full_catalog_files(all_files, store_ids):
        xml_bytes = download(f)
        (raw_dir / f.filename).with_suffix(".xml").write_bytes(xml_bytes)
        catalog = parse_price_xml(xml_bytes)
        gaps = compute_gaps(catalog, controlled)
        print(f"  store {f.store_id}: {len(catalog)} items, {len(gaps)} matched")
        all_gaps.extend(
            {
                "store_id": g.store_id,
                "item_code": g.item_code,
                "item_name": g.item_name,
                "actual_price": g.actual_price,
                "controlled_product_names": g.controlled_product_names,
                "controlled_consumer_price": g.controlled_consumer_price,
                "gap_pct": g.gap_pct,
                "ambiguous": g.ambiguous,
            }
            for g in gaps
        )

    out_path = processed_dir / "dairy_gap.json"
    out_path.write_text(json.dumps(all_gaps, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {len(all_gaps)} gap records to {out_path}")


if __name__ == "__main__":
    main()
