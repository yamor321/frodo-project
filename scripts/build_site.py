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
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.render.map import render_map_html
from etl.render.product import collect_store_prices, render_product_html
from etl.render.render_site import render_index_html
from etl.render.store import render_store_html, top_deals
from etl.scoring.benchmark_gap import compute_gaps
from etl.scoring.cross_branch_spread import compute_spreads
from etl.scoring.store_ranking import compute_store_scores
from etl.scrapers.shufersal import parse_price_xml

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "2026-08-28"
SITE_DIR = ROOT / "site"

STORE_NAMES = {
    "230": 'שלי כ"ס- ויצמן', "36": 'שלי כ"ס- רוטשילד', "144": "דיל שבירו כפר סבא",
    "682": "BE כפר סבא צפון", "648": "BE מאיר-כפרסבא", "615": "BE כפר סבא",
    "845": "אקספרס נחשון כפר סבא", "752": "אקספרס כפר סבא דוכיפת",
    "394": "אקספרס הכרמל כפר סבא", "375": 'אקספרס כ"ס- הגליל',
    "171": "אקספרס אוסטשינסקי", "140": "אקספרס תל חי",
    "335": 'אקספרס כ"ס- בן גוריון', "259": 'יוניברס גזית כ"ס- ויצמן',
}


def store_format(name: str) -> str:
    """Read off the chain's own format branding in the name -- see
    docs/sources.md for why this drives the map icon instead of the
    official StoreType field (which only distinguishes physical/online)."""
    return "hyper" if ("דיל" in name or "יוניברס" in name) else "neighborhood"


def main() -> None:
    print("Loading cached raw catalogs (no network)...")
    catalogs_by_store = {}
    for path in glob.glob(str(RAW_DIR / "PriceFull*.xml")):
        m = re.search(r"-(\d{1,3})-\d{8}-\d{6}\.xml$", path)
        store_id = str(int(m.group(1)))  # normalize away zero-padding (e.g. "036" -> "36")
        catalogs_by_store[store_id] = parse_price_xml(pathlib.Path(path).read_bytes())
        print(f"  {store_id} ({STORE_NAMES.get(store_id, '?')}): {len(catalogs_by_store[store_id])} items")

    coords_raw = json.loads((ROOT / "data" / "processed" / "store_coords.json").read_text(encoding="utf-8"))
    from etl.enrich.geocode import GeoPoint

    coords = {sid: GeoPoint(v["lat"], v["lon"]) for sid, v in coords_raw.items() if v.get("lat")}
    formats = {sid: store_format(name) for sid, name in STORE_NAMES.items()}

    print("\nComputing spreads and scores...")
    spreads = compute_spreads(catalogs_by_store, STORE_NAMES, min_stores=4)
    scores = compute_store_scores(catalogs_by_store, STORE_NAMES, min_stores=4)
    print(f"  {len(spreads)} comparable items, {len(scores)} scored stores")

    dairy_gaps_raw = json.loads((ROOT / "data" / "processed" / "2026-08-28" / "dairy_gap.json").read_text(encoding="utf-8"))
    from etl.scoring.benchmark_gap import GapResult

    gaps = [GapResult(**g) for g in dairy_gaps_raw if g["store_id"] == "144"]

    print("\nRendering pages...")
    (SITE_DIR / "index.html").write_text(
        render_index_html(spreads, gaps, generated_at="28.08.2026 (build מקומי)"), encoding="utf-8"
    )
    print("  site/index.html")

    map_dir = SITE_DIR / "map"
    map_dir.mkdir(exist_ok=True)
    (map_dir / "index.html").write_text(render_map_html(scores, coords, formats), encoding="utf-8")
    print("  site/map/index.html")

    scores_by_id = {s.store_id: s for s in scores}
    referenced_item_codes = set()

    for store_id, name in STORE_NAMES.items():
        store_dir = SITE_DIR / "store" / store_id
        store_dir.mkdir(parents=True, exist_ok=True)
        html = render_store_html(
            store_id, name, scores_by_id.get(store_id), spreads, catalogs_by_store.get(store_id, [])
        )
        (store_dir / "index.html").write_text(html, encoding="utf-8")

        best, worst = top_deals(spreads, store_id)
        for s in best + worst:
            referenced_item_codes.add(s.item_code)
    print(f"  site/store/*/index.html ({len(STORE_NAMES)} stores)")

    for code in referenced_item_codes:
        item_name = next((s.item_name for s in spreads if s.item_code == code), code)
        store_prices = collect_store_prices(catalogs_by_store, code, STORE_NAMES)
        prod_dir = SITE_DIR / "product" / code
        prod_dir.mkdir(parents=True, exist_ok=True)
        (prod_dir / "index.html").write_text(
            render_product_html(code, item_name, store_prices), encoding="utf-8"
        )
    print(f"  site/product/*/index.html ({len(referenced_item_codes)} products, every link from a store page resolves)")


if __name__ == "__main__":
    main()
