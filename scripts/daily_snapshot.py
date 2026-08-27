"""Daily collection run: Shufersal Kfar Saba branches -> permanent raw
snapshot + dairy price-gap output + cross-branch spread + rendered site.

Per the brief (section 3): every day this doesn't run is permanently lost
history, since chains are only required to retain files for 3 months.
Invoked by .github/workflows/daily-shufersal.yml.

Usage: python scripts/daily_snapshot.py
"""
import dataclasses
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.benchmarks.moag_controlled_prices import current_dairy_controlled_prices
from etl.render.render_site import render_index_html
from etl.scoring.benchmark_gap import compute_gaps
from etl.scoring.cross_branch_spread import compute_spreads
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
    now = dt.datetime.now()
    today = now.date().isoformat()
    raw_dir = ROOT / "data" / "raw" / today
    processed_dir = ROOT / "data" / "processed" / today
    site_dir = ROOT / "site"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    site_dir.mkdir(parents=True, exist_ok=True)

    print("Listing Shufersal portal...")
    all_files = list(list_files(max_pages=200))

    stores_file = list_stores_file(all_files)
    store_names: dict[str, str] = {}
    if stores_file is not None:
        stores = parse_stores_xml(download(stores_file))
        store_ids = kfar_saba_stores(stores) or KFAR_SABA_STORE_IDS
        store_names = {s.store_id: s.store_name for s in stores}
        print(f"Kfar Saba stores (from official City==6900 filter): {sorted(store_ids)}")
    else:
        store_ids = KFAR_SABA_STORE_IDS
        print(f"No Stores file found this run -- falling back to known IDs: {sorted(store_ids)}")

    controlled = current_dairy_controlled_prices()
    print(f"{len(controlled)} controlled dairy products fetched.")

    all_gaps = []
    catalogs_by_store: dict[str, list] = {}
    for f in kfar_saba_full_catalog_files(all_files, store_ids):
        xml_bytes = download(f)
        (raw_dir / f.filename).with_suffix(".xml").write_bytes(xml_bytes)
        catalog = parse_price_xml(xml_bytes)
        catalogs_by_store[f.store_id] = catalog
        gaps = compute_gaps(catalog, controlled)
        print(f"  store {f.store_id}: {len(catalog)} items, {len(gaps)} matched")
        all_gaps.extend(gaps)

    spreads = compute_spreads(catalogs_by_store, store_names, min_stores=4)
    print(f"\n{len(spreads)} items found in >=4 branches with a computable spread.")

    gap_path = processed_dir / "dairy_gap.json"
    gap_path.write_text(
        json.dumps([dataclasses.asdict(g) for g in all_gaps], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    spread_path = processed_dir / "cross_branch_spread.json"
    spread_path.write_text(
        json.dumps([dataclasses.asdict(s) for s in spreads], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {gap_path} and {spread_path}")

    html = render_index_html(spreads, all_gaps, generated_at=now.strftime("%d.%m.%Y, %H:%M"))
    (site_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"Rendered {site_dir / 'index.html'}")


if __name__ == "__main__":
    main()
