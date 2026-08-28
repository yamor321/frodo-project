"""Maintenance utility: re-fetch real Stores.xml live (both chains) and
re-geocode every known Kfar Saba branch, overwriting data/processed/
store_coords.json (used by scripts/build_site.py for fast local iteration
without hitting the network each run). Not part of the daily pipeline --
run manually whenever etl/enrich/geocode.py's matching rules change, or a
new chain is added, so the local dev snapshot reflects it instead of going
stale.

Usage: python scripts/regeocode_stores.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.enrich.address_overrides import ADDRESS_OVERRIDES
from etl.enrich.geocode import geocode_many
from etl.scrapers import carrefour
from etl.scrapers.shufersal import (
    KFAR_SABA_STORE_IDS,
    StoreRecord,
    download,
    kfar_saba_stores,
    list_files,
    list_stores_file,
    parse_stores_xml,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
CARREFOUR_PREFIX = "carrefour-"


def _geocode_chain(relevant: list[StoreRecord], key_prefix: str = "") -> dict:
    streets_by_key = {
        key_prefix + s.store_id: ADDRESS_OVERRIDES.get(key_prefix + s.store_id, s.address)
        for s in relevant
        if ADDRESS_OVERRIDES.get(key_prefix + s.store_id, s.address)
    }
    geo_results = geocode_many(list(set(streets_by_key.values())))

    out = {}
    for s in relevant:
        key = key_prefix + s.store_id
        street = streets_by_key.get(key)
        point = geo_results.get(street) if street else None
        entry = {"name": s.store_name, "query": street}
        if point:
            entry["lat"] = point.lat
            entry["lon"] = point.lon
        out[key] = entry
        status = f"{point.lat}, {point.lon}" if point else "NO MATCH"
        override_note = " (override)" if key in ADDRESS_OVERRIDES else ""
        print(f"  {key} ({s.store_name}) -- address={street!r}{override_note} -> {status}")
    return out


def main() -> None:
    print("Listing Shufersal portal...")
    all_files = list(list_files(max_pages=200))
    stores_file = list_stores_file(all_files)
    if stores_file is None:
        raise SystemExit("No Shufersal Stores file found this run.")

    stores = parse_stores_xml(download(stores_file))
    store_ids = kfar_saba_stores(stores) or KFAR_SABA_STORE_IDS
    relevant = [s for s in stores if s.store_id in store_ids]
    print(f"{len(relevant)} Kfar Saba Shufersal stores found.")
    out = _geocode_chain(relevant)

    print("\nListing Carrefour portal...")
    carrefour_files = carrefour.list_files()
    carrefour_stores_file = list_stores_file(carrefour_files)
    if carrefour_stores_file is not None:
        c_stores = parse_stores_xml(carrefour.download(carrefour_stores_file))
        c_store_ids = kfar_saba_stores(c_stores) or carrefour.KFAR_SABA_STORE_IDS
        c_relevant = [s for s in c_stores if s.store_id in c_store_ids]
        print(f"{len(c_relevant)} Kfar Saba Carrefour stores found.")
        out.update(_geocode_chain(c_relevant, key_prefix=CARREFOUR_PREFIX))
    else:
        print("No Carrefour Stores file found this run -- skipping.")

    out_path = ROOT / "data" / "processed" / "store_coords.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
