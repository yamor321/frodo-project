"""Daily collection run: Shufersal Kfar Saba branches -> permanent raw
snapshot + dairy price-gap output + cross-branch spread + rendered
multi-page site (home, map, one page per store, one page per compared
product).

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
from etl.concurrency import fetch_concurrently
from etl.enrich.address_overrides import ADDRESS_OVERRIDES
from etl.enrich.geocode import geocode_many
from etl.enrich.product_images import get_image_urls
from etl.render.branches import render_branches_html
from etl.render.map import render_map_html
from etl.render.methodology import render_methodology_html
from etl.render.product import collect_store_prices, render_product_html
from etl.render.render_site import render_index_html
from etl.render.store import render_store_html, top_deals
from etl.scoring.benchmark_gap import compute_gaps
from etl.scoring.cross_branch_spread import compute_spreads
from etl.scoring.store_ranking import compute_store_scores
from etl.scrapers import carrefour
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

# Carrefour store IDs are namespaced in every shared dict (catalogs_by_store,
# store_names, coords, formats) so they can never collide with Shufersal's
# own bare numeric IDs -- both chains happen to use small numeric codes.
# Shufersal itself stays unprefixed since it's the pilot chain and its URLs
# (/store/144/, etc.) are already live.
CARREFOUR_PREFIX = "carrefour-"


def store_format(name: str) -> str:
    """See docs/sources.md: the chain's own format branding in the name is
    the only real size signal -- the official StoreType field only
    distinguishes physical/online, not store size. "היפר" catches
    Carrefour's own hyper-format branches the same way "דיל"/"יוניברס"
    catches Shufersal's."""
    return "hyper" if any(kw in name for kw in ("דיל", "יוניברס", "היפר")) else "neighborhood"


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
    store_addresses: dict[str, str] = {}
    if stores_file is not None:
        stores = parse_stores_xml(download(stores_file))
        store_ids = kfar_saba_stores(stores) or KFAR_SABA_STORE_IDS
        store_names = {s.store_id: s.store_name for s in stores if s.store_id in store_ids}
        store_addresses = {s.store_id: s.address for s in stores if s.store_id in store_ids}
        print(f"Kfar Saba stores (from official City==6900 filter): {sorted(store_ids)}")
    else:
        store_ids = KFAR_SABA_STORE_IDS
        print(f"No Stores file found this run -- falling back to known IDs: {sorted(store_ids)}")

    controlled = current_dairy_controlled_prices()
    print(f"{len(controlled)} controlled dairy products fetched.")

    files_to_fetch = list(kfar_saba_full_catalog_files(all_files, store_ids))
    print(f"Downloading {len(files_to_fetch)} store catalogs concurrently...")
    xml_blobs = fetch_concurrently([lambda f=f: download(f) for f in files_to_fetch])

    all_gaps = []
    catalogs_by_store: dict[str, list] = {}
    for f, xml_bytes in zip(files_to_fetch, xml_blobs):
        if xml_bytes is None:
            print(f"  store {f.store_id}: download failed, skipped")
            continue
        (raw_dir / f.filename).with_suffix(".xml").write_bytes(xml_bytes)
        catalog = parse_price_xml(xml_bytes)
        catalogs_by_store[f.store_id] = catalog
        gaps = compute_gaps(catalog, controlled)
        print(f"  store {f.store_id}: {len(catalog)} items, {len(gaps)} matched")
        all_gaps.extend(gaps)

    print("\nListing Carrefour portal...")
    carrefour_files = carrefour.list_files()
    carrefour_stores_file = list_stores_file(carrefour_files)
    if carrefour_stores_file is not None:
        c_stores = parse_stores_xml(carrefour.download(carrefour_stores_file))
        c_store_ids = kfar_saba_stores(c_stores) or carrefour.KFAR_SABA_STORE_IDS
        for s in c_stores:
            if s.store_id in c_store_ids:
                key = CARREFOUR_PREFIX + s.store_id
                store_names[key] = s.store_name
                store_addresses[key] = s.address
        print(f"Carrefour Kfar Saba stores (from official City==6900 filter): {sorted(c_store_ids)}")

        carrefour_catalog_files = list(kfar_saba_full_catalog_files(carrefour_files, c_store_ids))
        print(f"Downloading {len(carrefour_catalog_files)} Carrefour store catalogs concurrently...")
        carrefour_blobs = fetch_concurrently([lambda f=f: carrefour.download(f) for f in carrefour_catalog_files])
        for f, xml_bytes in zip(carrefour_catalog_files, carrefour_blobs):
            if xml_bytes is None:
                print(f"  carrefour store {f.store_id}: download failed, skipped")
                continue
            (raw_dir / f.filename).with_suffix(".xml").write_bytes(xml_bytes)
            catalog = parse_price_xml(xml_bytes)
            key = CARREFOUR_PREFIX + f.store_id
            catalogs_by_store[key] = catalog
            gaps = compute_gaps(catalog, controlled)
            print(f"  carrefour store {f.store_id}: {len(catalog)} items, {len(gaps)} matched")
            all_gaps.extend(gaps)
    else:
        print("No Carrefour Stores file found this run -- skipping Carrefour for today.")

    spreads = compute_spreads(catalogs_by_store, store_names, min_stores=4)
    scores = compute_store_scores(catalogs_by_store, store_names, min_stores=4)
    print(f"\n{len(spreads)} comparable items, {len(scores)} scored stores.")

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

    print("\nGeocoding store addresses (cached -- only new addresses hit the network)...")
    streets_by_store = {
        sid: ADDRESS_OVERRIDES.get(sid, addr)
        for sid, addr in store_addresses.items()
        if ADDRESS_OVERRIDES.get(sid, addr)
    }
    geo_results = geocode_many(list(set(streets_by_store.values())))
    coords = {sid: geo_results.get(street) for sid, street in streets_by_store.items()}
    coords = {sid: pt for sid, pt in coords.items() if pt is not None}

    formats = {sid: store_format(name) for sid, name in store_names.items()}

    print("\nRendering pages...")
    (site_dir / "index.html").write_text(
        render_index_html(spreads, all_gaps, generated_at=now.strftime("%d.%m.%Y, %H:%M")),
        encoding="utf-8",
    )

    methodology_dir = site_dir / "methodology"
    methodology_dir.mkdir(exist_ok=True)
    (methodology_dir / "index.html").write_text(render_methodology_html(), encoding="utf-8")

    branches_dir = site_dir / "branches"
    branches_dir.mkdir(exist_ok=True)
    (branches_dir / "index.html").write_text(render_branches_html(spreads), encoding="utf-8")

    map_dir = site_dir / "map"
    map_dir.mkdir(exist_ok=True)
    (map_dir / "index.html").write_text(render_map_html(scores, coords, formats), encoding="utf-8")

    scores_by_id = {s.store_id: s for s in scores}
    referenced_item_codes = set()
    for store_id in store_names:
        best, worst = top_deals(spreads, store_id)
        for s in best + worst:
            referenced_item_codes.add(s.item_code)

    print(f"\nFetching product images for {len(referenced_item_codes)} products (cached)...")
    image_urls = get_image_urls(list(referenced_item_codes))
    print(f"  {sum(1 for u in image_urls.values() if u)}/{len(referenced_item_codes)} found")

    for store_id, name in store_names.items():
        store_dir = site_dir / "store" / store_id
        store_dir.mkdir(parents=True, exist_ok=True)
        (store_dir / "index.html").write_text(
            render_store_html(
                store_id,
                name,
                scores_by_id.get(store_id),
                spreads,
                catalogs_by_store.get(store_id, []),
                coords=coords.get(store_id),
                image_urls=image_urls,
            ),
            encoding="utf-8",
        )

    for code in referenced_item_codes:
        item_name = next((s.item_name for s in spreads if s.item_code == code), code)
        store_prices = collect_store_prices(catalogs_by_store, code, store_names)
        prod_dir = site_dir / "product" / code
        prod_dir.mkdir(parents=True, exist_ok=True)
        (prod_dir / "index.html").write_text(
            render_product_html(code, item_name, store_prices, image_url=image_urls.get(code)),
            encoding="utf-8",
        )

    print(f"Rendered index, map, {len(store_names)} store pages, {len(referenced_item_codes)} product pages.")


if __name__ == "__main__":
    main()
