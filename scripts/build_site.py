"""Builds the full multi-page site from already-downloaded raw catalogs and
already-computed geocode/score caches -- no network calls, fast to iterate
on. This is the local dev-loop counterpart to daily_snapshot.py (which does
the network fetch + commit); once this is verified working, daily_snapshot
will be updated to call the same render_* functions.

Usage: python scripts/build_site.py
"""
import glob
import json
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.concurrency import fetch_concurrently
from etl.enrich.product_images import get_image_urls
from etl.render.branches import render_branches_html
from etl.render.map import render_map_html
from etl.render.methodology import render_methodology_html
from etl.render.product import build_products_payload, collect_all_store_prices, render_product_shell_html
from etl.render.render_site import render_index_html
from etl.render.store import render_store_html, top_deals
from etl.scoring.benchmark_gap import compute_gaps
from etl.scoring.cross_branch_spread import compute_spreads
from etl.scoring.store_ranking import compute_store_scores
from etl.scrapers import carrefour, victory
from etl.scrapers.shufersal import kfar_saba_full_catalog_files, kfar_saba_stores, list_stores_file, parse_price_xml, parse_stores_xml

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "2026-08-28"
SITE_DIR = ROOT / "site"

# Chain store IDs are namespaced so they can never collide with each
# other's own bare numeric IDs -- see the same constants in
# scripts/daily_snapshot.py. Shufersal stays unprefixed (pilot chain,
# already-live URLs).
CARREFOUR_PREFIX = "carrefour-"
VICTORY_PREFIX = "victory-"

STORE_NAMES = {
    "230": 'שלי כ"ס- ויצמן', "36": 'שלי כ"ס- רוטשילד', "144": "דיל שבירו כפר סבא",
    "682": "BE כפר סבא צפון", "648": "BE מאיר-כפרסבא", "615": "BE כפר סבא",
    "845": "אקספרס נחשון כפר סבא", "752": "אקספרס כפר סבא דוכיפת",
    "394": "אקספרס הכרמל כפר סבא", "375": 'אקספרס כ"ס- הגליל',
    "171": "אקספרס אוסטשינסקי", "140": "אקספרס תל חי",
    "335": 'אקספרס כ"ס- בן גוריון', "259": 'יוניברס גזית כ"ס- ויצמן',
}


def _prune_stale_dirs(parent_dir: pathlib.Path, keep_names: set[str]) -> None:
    """Remove any subdirectory of `parent_dir` not in `keep_names`.

    The generation loops below only ever WRITE the pages a run currently
    references -- they never delete one that's no longer needed. A page
    that was correctly generated on one run (e.g. a product comparison
    later found to rest on a bad barcode match, see etl/scoring/
    item_code_filters.py) would otherwise sit on disk forever, unlinked
    from the live site but still committed and reachable by direct URL.
    """
    if not parent_dir.exists():
        return
    for child in parent_dir.iterdir():
        if child.is_dir() and child.name not in keep_names:
            shutil.rmtree(child)


def store_format(name: str) -> str:
    """Read off the chain's own format branding in the name -- see
    docs/sources.md for why this drives the map icon instead of the
    official StoreType field (which only distinguishes physical/online).
    "היפר" catches Carrefour's own hyper-format branches."""
    return "hyper" if any(kw in name for kw in ("דיל", "יוניברס", "היפר")) else "neighborhood"


def main() -> None:
    print("Loading cached raw catalogs (no network)...")
    # A store can have more than one cached file (re-runs on different days
    # land in the same date-named folder) -- always take the one with the
    # latest embedded publish timestamp, never glob order.
    latest_by_store: dict[str, tuple[str, str]] = {}
    for path in glob.glob(str(RAW_DIR / "PriceFull*.xml")):
        m = re.search(r"-(\d{1,3})-(\d{8}-\d{6})\.xml$", path)
        store_id = str(int(m.group(1)))  # normalize away zero-padding (e.g. "036" -> "36")
        published_at = m.group(2)
        if store_id not in latest_by_store or published_at > latest_by_store[store_id][0]:
            latest_by_store[store_id] = (published_at, path)

    catalogs_by_store = {}
    store_names = dict(STORE_NAMES)
    for store_id, (published_at, path) in latest_by_store.items():
        catalogs_by_store[store_id] = parse_price_xml(pathlib.Path(path).read_bytes())
        print(f"  {store_id} ({store_names.get(store_id, '?')}): {len(catalogs_by_store[store_id])} items [{published_at}]")

    print("\nListing Carrefour and Victory (live -- fast, no pagination needed)...")
    carrefour_files = carrefour.list_files()
    carrefour_stores_file = list_stores_file(carrefour_files)
    carrefour_catalog_files = []
    if carrefour_stores_file is not None:
        c_stores = parse_stores_xml(carrefour.download(carrefour_stores_file))
        c_store_ids = kfar_saba_stores(c_stores) or carrefour.KFAR_SABA_STORE_IDS
        for s in c_stores:
            if s.store_id in c_store_ids:
                store_names[CARREFOUR_PREFIX + s.store_id] = s.store_name
        carrefour_catalog_files = list(kfar_saba_full_catalog_files(carrefour_files, c_store_ids))

    victory_files = victory.list_files(victory.VICTORY_CHAIN_IDS)
    victory_stores_file = list_stores_file(victory_files)
    victory_catalog_files = []
    if victory_stores_file is not None:
        v_stores = parse_stores_xml(victory.download(victory_stores_file))
        v_store_ids = kfar_saba_stores(v_stores)
        for s in v_stores:
            if s.store_id in v_store_ids:
                store_names[VICTORY_PREFIX + s.store_id] = s.store_name
        victory_catalog_files = list(kfar_saba_full_catalog_files(victory_files, v_store_ids))

    # Downloaded in one combined concurrent batch, not one chain after the
    # other -- neither chain has to wait for the other's downloads to
    # finish before its own start.
    tasks = [lambda f=f: carrefour.download(f) for f in carrefour_catalog_files] + [
        lambda f=f: victory.download(f) for f in victory_catalog_files
    ]
    owners = [(CARREFOUR_PREFIX, f) for f in carrefour_catalog_files] + [
        (VICTORY_PREFIX, f) for f in victory_catalog_files
    ]
    print(f"Downloading {len(tasks)} Carrefour+Victory store catalogs concurrently...")
    blobs = fetch_concurrently(tasks)
    for (prefix, f), xml_bytes in zip(owners, blobs):
        if xml_bytes is None:
            print(f"  {prefix}{f.store_id}: download failed, skipped")
            continue
        key = prefix + f.store_id
        catalogs_by_store[key] = parse_price_xml(xml_bytes)
        print(f"  {key} ({store_names.get(key, '?')}): {len(catalogs_by_store[key])} items")

    coords_raw = json.loads((ROOT / "data" / "processed" / "store_coords.json").read_text(encoding="utf-8"))
    from etl.enrich.geocode import GeoPoint

    coords = {sid: GeoPoint(v["lat"], v["lon"]) for sid, v in coords_raw.items() if v.get("lat")}
    formats = {sid: store_format(name) for sid, name in store_names.items()}

    print("\nComputing spreads and scores...")
    spreads = compute_spreads(catalogs_by_store, store_names, min_stores=4)
    scores = compute_store_scores(catalogs_by_store, store_names, min_stores=4)
    print(f"  {len(spreads)} comparable items, {len(scores)} scored stores")

    dairy_gaps_raw = json.loads((ROOT / "data" / "processed" / "2026-08-28" / "dairy_gap.json").read_text(encoding="utf-8"))
    from etl.scoring.benchmark_gap import GapResult

    gaps = [GapResult(**g) for g in dairy_gaps_raw if g["store_id"] == "144"]

    print("\nRendering pages...")
    (SITE_DIR / "index.html").write_text(
        render_index_html(spreads, gaps, generated_at="28.08.2026 (build מקומי)"), encoding="utf-8"
    )
    print("  site/index.html")

    methodology_dir = SITE_DIR / "methodology"
    methodology_dir.mkdir(exist_ok=True)
    (methodology_dir / "index.html").write_text(render_methodology_html(), encoding="utf-8")
    print("  site/methodology/index.html")

    branches_dir = SITE_DIR / "branches"
    branches_dir.mkdir(exist_ok=True)
    (branches_dir / "index.html").write_text(render_branches_html(spreads), encoding="utf-8")
    print("  site/branches/index.html")

    map_dir = SITE_DIR / "map"
    map_dir.mkdir(exist_ok=True)
    (map_dir / "index.html").write_text(render_map_html(scores, coords, formats), encoding="utf-8")
    print("  site/map/index.html")

    scores_by_id = {s.store_id: s for s in scores}
    referenced_item_codes = set()
    for store_id in store_names:
        best, worst = top_deals(spreads, store_id)
        for s in best + worst:
            referenced_item_codes.add(s.item_code)

    print(f"\nFetching product images for {len(referenced_item_codes)} products (cached)...")
    image_urls = get_image_urls(list(referenced_item_codes))
    print(f"  {sum(1 for u in image_urls.values() if u)}/{len(referenced_item_codes)} found")

    _prune_stale_dirs(SITE_DIR / "store", set(store_names))
    for store_id, name in store_names.items():
        store_dir = SITE_DIR / "store" / store_id
        store_dir.mkdir(parents=True, exist_ok=True)
        html = render_store_html(
            store_id,
            name,
            scores_by_id.get(store_id),
            spreads,
            catalogs_by_store.get(store_id, []),
            coords=coords.get(store_id),
            image_urls=image_urls,
        )
        (store_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"  site/store/*/index.html ({len(store_names)} stores)")

    _prune_stale_dirs(SITE_DIR / "product", set())
    product_dir = SITE_DIR / "product"
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / "index.html").write_text(render_product_shell_html(), encoding="utf-8")

    all_store_prices = collect_all_store_prices(catalogs_by_store, store_names, min_stores=4)
    products_payload = build_products_payload(spreads, all_store_prices, image_urls, coords)
    (SITE_DIR / "products.json").write_text(json.dumps(products_payload, ensure_ascii=False), encoding="utf-8")

    search_index = [
        {"code": s.item_code, "name": s.item_name, "cheap_price": s.cheap_price} for s in spreads
    ]
    (SITE_DIR / "search-index.json").write_text(json.dumps(search_index, ensure_ascii=False), encoding="utf-8")
    print(f"  site/product/index.html + site/products.json ({len(products_payload):,} products, every /branches/ link resolves)")


if __name__ == "__main__":
    main()
