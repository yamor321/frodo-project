"""Client for Carrefour's price-transparency portal.

Same regulated XML schema as Shufersal -- verified live 2026-08-28:
Shufersal's own `parse_price_xml()` and `parse_stores_xml()` parse real
Carrefour files unmodified (12,461 items from a real PriceFull, 147 stores
from the real Stores file, both well-formed). Both chains publish under the
same law, so only file discovery/download differs -- this module reuses
`PriceFile` / `StoreRecord` / `parse_price_xml` / `parse_stores_xml` /
`list_stores_file` / `kfar_saba_full_catalog_files` / `kfar_saba_stores`
from shufersal.py rather than redefining them.

Portal: https://prices.carrefour.co.il/ -- confirmed to require no login.
Unlike Shufersal's paginated webgrid, the homepage embeds TODAY's complete
file listing directly as inline JS (`const path = '...'`, `const files =
[...]`, `const branches = {...}`) -- no pagination to walk, and the download
URL is simply `{origin}/{path}/{filename}` (confirmed by downloading a real
file this way and getting an exact byte-size match to the listed size).
"""
from __future__ import annotations

import gzip
import io
import json
import re

import requests

from etl.scrapers.shufersal import PriceFile

BASE_URL = "https://prices.carrefour.co.il/"
REQUEST_TIMEOUT = 20

# Verified live 2026-08-28 against the portal's own Stores file (city_code
# == "6900" for all five -- same official settlement-code filter as
# Shufersal, via shufersal.kfar_saba_stores()). Two of the five have no
# physical storefront -- their Stores-file Address field is literally a URL,
# not a street ("471" is Carrefour's own online store, "473" is the Quik
# rapid-delivery concept) -- geocoding them is expected to find nothing,
# which is correct (no pin), not a bug.
KFAR_SABA_STORE_IDS = {"010", "400", "404", "471", "473"}

_FILENAME_RE = re.compile(r"^([A-Za-z]+)(\d+)-(.+)\.(gz|xml)$")


def _parse_filename(name: str) -> dict | None:
    """Carrefour filenames come in two shapes: per-store files have four
    dash-separated fields after the chain ID (subchain-store-date-time,
    e.g. PriceFull...-001-010-20260828-051001.gz); the chain-wide Stores
    file has three (a fixed "000" placeholder instead of subchain+store,
    e.g. Stores...-000-20260828-000100.xml). `None` for anything else.
    """
    m = _FILENAME_RE.match(name)
    if not m:
        return None
    category, chain_id, rest, ext = m.groups()
    parts = rest.split("-")
    if len(parts) == 4:
        subchain_id, store_id, _date, _time = parts
    elif len(parts) == 3:
        subchain_id, _date, _time = parts
        store_id = "All"
    else:
        return None
    return {"category": category, "chain_id": chain_id, "subchain_id": subchain_id, "store_id": store_id, "ext": ext}


def list_files() -> list[PriceFile]:
    """Fetch the portal homepage and parse its inline file listing.

    No pagination needed: the homepage embeds today's complete listing
    directly, unlike Shufersal's paginated webgrid table.
    """
    resp = requests.get(BASE_URL, timeout=REQUEST_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    html = resp.text

    path_m = re.search(r"const path = '(\d+)'", html)
    files_m = re.search(r"const files = (\[.*?\]);", html)
    branches_m = re.search(r"const branches = (\{.*?\});", html)
    if not (path_m and files_m and branches_m):
        raise ValueError("Carrefour portal page structure changed -- couldn't find path/files/branches")

    path = path_m.group(1)
    raw_files = json.loads(files_m.group(1))
    branches: dict[str, str] = json.loads(branches_m.group(1))

    files = []
    for f in raw_files:
        parsed = _parse_filename(f["name"])
        if parsed is None:
            continue
        files.append(
            PriceFile(
                url=f"{BASE_URL}{path}/{f['name']}",
                filename=f["name"],
                updated_at=f.get("modified", ""),
                size=str(f.get("size", "")),
                file_type=parsed["ext"].upper(),
                category=parsed["category"],
                store_id=parsed["store_id"],
                store_name=branches.get(parsed["store_id"], ""),
            )
        )
    return files


def download(price_file: PriceFile) -> bytes:
    """Download one listed file. `.gz` files (Price/PriceFull/Promo/
    PromoFull) are gunzipped like Shufersal's; the Stores file is published
    uncompressed (`.xml`) and returned as-is."""
    resp = requests.get(price_file.url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if price_file.filename.lower().endswith(".gz"):
        with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as gz:
            return gz.read()
    return resp.content
