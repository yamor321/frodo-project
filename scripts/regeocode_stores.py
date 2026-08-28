"""Maintenance utility: re-fetch real Stores.xml live and re-geocode every
known Kfar Saba Shufersal branch, overwriting data/processed/store_coords.json
(used by scripts/build_site.py for fast local iteration without hitting the
network each run). Not part of the daily pipeline -- run manually whenever
etl/enrich/geocode.py's matching rules change, so the local dev snapshot
reflects them instead of going stale.

Usage: python scripts/regeocode_stores.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.enrich.geocode import geocode_many
from etl.scrapers.shufersal import (
    KFAR_SABA_STORE_IDS,
    download,
    kfar_saba_stores,
    list_files,
    list_stores_file,
    parse_stores_xml,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> None:
    print("Listing Shufersal portal...")
    all_files = list(list_files(max_pages=200))
    stores_file = list_stores_file(all_files)
    if stores_file is None:
        raise SystemExit("No Stores file found this run.")

    stores = parse_stores_xml(download(stores_file))
    store_ids = kfar_saba_stores(stores) or KFAR_SABA_STORE_IDS
    relevant = [s for s in stores if s.store_id in store_ids]
    print(f"{len(relevant)} Kfar Saba stores found.")

    streets_by_store = {s.store_id: s.address for s in relevant if s.address}
    geo_results = geocode_many(list(set(streets_by_store.values())))

    out = {}
    for s in relevant:
        point = geo_results.get(s.address) if s.address else None
        entry = {"name": s.store_name, "query": s.address}
        if point:
            entry["lat"] = point.lat
            entry["lon"] = point.lon
        out[s.store_id] = entry
        status = f"{point.lat}, {point.lon}" if point else "NO MATCH"
        print(f"  {s.store_id} ({s.store_name}) -- address={s.address!r} -> {status}")

    out_path = ROOT / "data" / "processed" / "store_coords.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
