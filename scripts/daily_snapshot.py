"""Daily collection run: every chain's Kfar Saba branches -> permanent raw
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
import shutil
import sys
import traceback
from typing import Callable

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
from etl.scrapers import carrefour, victory
from etl.scrapers.shufersal import (
    KFAR_SABA_STORE_IDS,
    PriceFile,
    download,
    kfar_saba_full_catalog_files,
    kfar_saba_stores,
    list_files,
    list_stores_file,
    parse_price_xml,
    parse_stores_xml,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]


@dataclasses.dataclass
class ChainCollection:
    """One chain's discovery results, ready for the combined download step.

    Store IDs are namespaced per chain (prefix + the chain's own store_id)
    everywhere downstream (catalogs_by_store, store_names, coords, formats,
    /store/{id}/ URLs) so they can never collide -- every chain here
    happens to use small numeric branch codes, and more than one has
    already been seen reusing the same one. Shufersal (the pilot chain)
    keeps its bare numeric IDs since its URLs are already live.
    """

    prefix: str
    download_fn: Callable[[PriceFile], bytes]
    catalog_files: list[PriceFile]
    store_names: dict[str, str]
    store_addresses: dict[str, str]


def store_format(name: str) -> str:
    """See docs/sources.md: the chain's own format branding in the name is
    the only real size signal -- the official StoreType field only
    distinguishes physical/online, not store size. "היפר" catches
    Carrefour's own hyper-format branches the same way "דיל"/"יוניברס"
    catches Shufersal's."""
    return "hyper" if any(kw in name for kw in ("דיל", "יוניברס", "היפר")) else "neighborhood"


def _safe_collect(chain_name: str, collect_fn: Callable[[], "ChainCollection"], prefix: str) -> "ChainCollection":
    """Run one chain's discovery, but never let it take the whole run down.

    Each chain talks to a different real-world portal this project doesn't
    control -- one being temporarily unreachable, rate-limiting, or
    returning something unexpected is a "that chain is missing today", not
    a reason the other chains (and the rest of the site) shouldn't update.
    The full traceback still prints, so a real failure is visible in the
    workflow log, not swallowed silently.
    """
    try:
        return collect_fn()
    except Exception:
        print(f"\n{chain_name} collection failed, skipping it for today:")
        traceback.print_exc()
        return ChainCollection(prefix, lambda f: b"", [], {}, {})


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


def _collect_shufersal() -> ChainCollection:
    print("Listing Shufersal portal...")
    all_files = list(list_files(max_pages=200))
    stores_file = list_stores_file(all_files)
    if stores_file is None:
        print(f"No Stores file found this run -- falling back to known IDs: {sorted(KFAR_SABA_STORE_IDS)}")
        return ChainCollection("", download, [], {}, {})

    stores = parse_stores_xml(download(stores_file))
    store_ids = kfar_saba_stores(stores) or KFAR_SABA_STORE_IDS
    print(f"Shufersal Kfar Saba stores (from official City filter): {sorted(store_ids)}")
    return ChainCollection(
        prefix="",
        download_fn=download,
        catalog_files=list(kfar_saba_full_catalog_files(all_files, store_ids)),
        store_names={s.store_id: s.store_name for s in stores if s.store_id in store_ids},
        store_addresses={s.store_id: s.address for s in stores if s.store_id in store_ids},
    )


def _collect_carrefour() -> ChainCollection:
    print("Listing Carrefour portal...")
    files = carrefour.list_files()
    stores_file = list_stores_file(files)
    if stores_file is None:
        print("No Carrefour Stores file found this run -- skipping Carrefour for today.")
        return ChainCollection("carrefour-", carrefour.download, [], {}, {})

    stores = parse_stores_xml(carrefour.download(stores_file))
    store_ids = kfar_saba_stores(stores) or carrefour.KFAR_SABA_STORE_IDS
    print(f"Carrefour Kfar Saba stores (from official City filter): {sorted(store_ids)}")
    prefix = "carrefour-"
    return ChainCollection(
        prefix=prefix,
        download_fn=carrefour.download,
        catalog_files=list(kfar_saba_full_catalog_files(files, store_ids)),
        store_names={prefix + s.store_id: s.store_name for s in stores if s.store_id in store_ids},
        store_addresses={prefix + s.store_id: s.address for s in stores if s.store_id in store_ids},
    )


def _collect_victory() -> ChainCollection:
    print("Listing Victory portal...")
    files = victory.list_files(victory.VICTORY_CHAIN_IDS)
    stores_file = list_stores_file(files)
    if stores_file is None:
        print("No Victory Stores file found this run -- skipping Victory for today.")
        return ChainCollection("victory-", victory.download, [], {}, {})

    stores = parse_stores_xml(victory.download(stores_file))
    store_ids = kfar_saba_stores(stores)
    print(f"Victory Kfar Saba stores (from official City filter): {sorted(store_ids)}")
    prefix = "victory-"
    return ChainCollection(
        prefix=prefix,
        download_fn=victory.download,
        catalog_files=list(kfar_saba_full_catalog_files(files, store_ids)),
        store_names={prefix + s.store_id: s.store_name for s in stores if s.store_id in store_ids},
        store_addresses={prefix + s.store_id: s.address for s in stores if s.store_id in store_ids},
    )


def main() -> None:
    now = dt.datetime.now()
    today = now.date().isoformat()
    raw_dir = ROOT / "data" / "raw" / today
    processed_dir = ROOT / "data" / "processed" / today
    site_dir = ROOT / "site"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    site_dir.mkdir(parents=True, exist_ok=True)

    # Discovery (listing + Stores file) happens per chain -- each chain's
    # API/portal shape is different enough that unifying this part isn't
    # worth it. The part that actually dominates run time -- downloading
    # every store's full catalog -- is NOT done per chain: every chain's
    # target files are combined into one flat list below and fetched in a
    # single concurrent batch, so chain 2 doesn't wait for chain 1's
    # downloads to finish before its own start.
    chains = [
        _safe_collect("Shufersal", _collect_shufersal, ""),
        _safe_collect("Carrefour", _collect_carrefour, "carrefour-"),
        _safe_collect("Victory", _collect_victory, "victory-"),
    ]

    controlled = current_dairy_controlled_prices()
    print(f"\n{len(controlled)} controlled dairy products fetched.")

    tasks = []
    task_owners: list[tuple[ChainCollection, PriceFile]] = []
    for chain in chains:
        for f in chain.catalog_files:
            tasks.append(lambda f=f, dl=chain.download_fn: dl(f))
            task_owners.append((chain, f))

    print(f"\nDownloading {len(tasks)} store catalogs across {len(chains)} chains concurrently...")
    blobs = fetch_concurrently(tasks)

    all_gaps = []
    catalogs_by_store: dict[str, list] = {}
    for (chain, f), xml_bytes in zip(task_owners, blobs):
        key = chain.prefix + f.store_id
        if xml_bytes is None:
            print(f"  {key}: download failed, skipped")
            continue
        (raw_dir / f.filename).with_suffix(".xml").write_bytes(xml_bytes)
        catalog = parse_price_xml(xml_bytes)
        catalogs_by_store[key] = catalog
        gaps = compute_gaps(catalog, controlled)
        print(f"  {key}: {len(catalog)} items, {len(gaps)} matched")
        all_gaps.extend(gaps)

    store_names: dict[str, str] = {}
    store_addresses: dict[str, str] = {}
    for chain in chains:
        store_names.update(chain.store_names)
        store_addresses.update(chain.store_addresses)

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

    _prune_stale_dirs(site_dir / "store", set(store_names))
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

    _prune_stale_dirs(site_dir / "product", referenced_item_codes)
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
