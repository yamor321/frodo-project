"""Client for Wolt Market's price-transparency portal.

Wolt Market is a genuinely independent, legally-mandated chain -- its own
`<ChainID>7290058249350</ChainID>`, distinct from Rami Levy's
(`7290058140886`), confirmed via a real downloaded Stores file, not a resale
of another chain's inventory under a shared identity. Listed on its own row
on the official gov.il regulated-chains page (`cpfta_prices_regulations`),
with its own "לצפייה במחירים" link to this portal, same as every other
chain -- not flagged as anything unusual by the regulator itself.

Previously excluded from this project (see docs/sources.md's "Wolt Market"
entries) as a "dark store, no physical address" -- that research happened on
a day this project's sandbox couldn't reach wolt.com at all, and was never
actually verified against the live portal. Re-checked live 2026-08-30: the
portal is reachable, the chain has a real Kfar Saba branch, and its address
turned out to be a real street (see etl/enrich/address_overrides.py's
"wolt-005" entry), not a URL like every other online-only store found
elsewhere in this project (see shufersal.online_stores()).

No login of any kind -- every request is a plain unauthenticated GET,
verified live 2026-08-30:

- Listing is a two-level plain HTML directory, not a table or JSON API:
  `GET {BASE_URL}index.html` -> `<li><a href="{date}.html">{date}</a></li>`
  per available date (confirmed reverse-chronological, today first -- read
  what the page actually says instead of assuming `date.today()` matches,
  same principle as Carrefour's own `path` extraction). `GET
  {BASE_URL}{date}.html` -> `<li><a href="download/{date}/{filename}">
  {filename}</a></li>` per file for that date.
- Download is a single direct GET (confirmed live: `Content-Type:
  application/gzip`, byte-exact gzip stream) -- unlike Bina's two-hop
  redirect, no resolution step needed.
- Filenames use the exact same dash-separated convention as every other
  chain in this project (e.g. `PriceFull7290058249350-000-005-20260830-
  000033.gz`, `Stores7290058249350-000-20260830-000009.gz`) -- reuses the
  same parsing shape as Bina's `_parse_filename` (kept as a local copy,
  matching the project's existing pattern of each chain module owning its
  own filename parsing independently, since the ".GZ" case and field count
  have already been shown to vary chain to chain).
- Same regulated XML schema as every other chain -- `shufersal.
  parse_stores_xml()` parses a real downloaded Stores file (43 stores)
  completely unmodified. `parse_price_xml()` needed one shared fix (not a
  Wolt-specific fork): Wolt's real PriceFull files spell the weighted-item
  flag `<blsWeighted>` (lowercase L) where every other chain spells it
  `<bIsWeighted>` (capital I) -- see shufersal._text()'s multi-tag support.

**Kfar Saba, confirmed via the real Stores file:** exactly one branch,
store "005", "וולט מרקט | כפר סבא", Address "הסדנא 17, כפר סבא", City
"כפר סבא" (city-name convention, like Victory -- already handled by
shufersal.kfar_saba_stores()'s KFAR_SABA_CITY_NAMES). Every Wolt store
nationally (43 total, confirmed live) is StoreType=="2" -- this is a fully
online/dark-store chain, no physical retail anywhere, so plain
kfar_saba_stores() (not kfar_saba_stores_with_online()) is what's used to
collect it in daily_snapshot.py -- the online-union helper's job is finding
a national online store for an otherwise-physical chain, which doesn't apply
here at all, and would incorrectly pull in stores from other cities if it
were used (Wolt publishes 43 StoreType=="2" rows nationally, not one).

Two known non-production rows exist in the live file, confirmed by store
ID: "038" ("Wolt Market Israel Test Venue", City="רחובות") and "041"
("Wolt Market | Marlog Atlas (CLOSED)", City="כפר קאסם"). Neither carries
Kfar Saba's city, so kfar_saba_stores() already excludes both without any
extra filtering needed here -- noted for anyone debugging a full national
Stores dump, not because this module does anything special about them.
"""
from __future__ import annotations

import gzip
import io
import re

import requests
from bs4 import BeautifulSoup

from etl.scrapers.shufersal import PriceFile

BASE_URL = "https://wm-gateway.wolt.com/isr-prices/public/v1/"
REQUEST_TIMEOUT = 20

_session = requests.Session()
_session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
)

# Fallback constant (same role as carrefour.KFAR_SABA_STORE_IDS and
# victory.KFAR_SABA_STORE_IDS): lets daily_snapshot.py's raw-snapshot
# fallback find this store even if live discovery fails outright.
KFAR_SABA_STORE_IDS = {"005"}

# Same dash-separated convention confirmed for every other chain -- category
# prefix, digits (chain_id), then a dash-joined tail (4 fields per-store, 3
# for the chain-wide Stores file). Kept as a local copy rather than a shared
# import -- see etl/scrapers/bina.py's own _parse_filename for why (each
# chain module has already been shown to need its own extension-case/field-
# count handling, not one they can all safely share).
_FILENAME_RE = re.compile(r"^([A-Za-z]+)(\d+)-(.+)\.(gz|xml)$", re.IGNORECASE)


def _parse_filename(name: str) -> dict | None:
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
    """List every Price/PriceFull/Stores file Wolt Market has published for
    its most recent available date.

    Two-hop discovery: the date index, then that date's own file list --
    both plain unauthenticated HTML directories (confirmed live, see module
    docstring), not a table or JSON API like every other chain here.
    """
    index_resp = _session.get(BASE_URL + "index.html", timeout=REQUEST_TIMEOUT)
    index_resp.raise_for_status()
    dates = [a["href"] for a in BeautifulSoup(index_resp.text, "html.parser").find_all("a")]
    if not dates:
        raise ValueError("Wolt Market portal page structure changed -- no dates found in index.html")
    latest_date_html = dates[0]  # confirmed live: reverse-chronological, today first

    files_resp = _session.get(BASE_URL + latest_date_html, timeout=REQUEST_TIMEOUT)
    files_resp.raise_for_status()

    files = []
    for a in BeautifulSoup(files_resp.text, "html.parser").find_all("a"):
        href = a["href"]  # "download/{date}/{filename}"
        filename = href.rsplit("/", 1)[-1]
        parsed = _parse_filename(filename)
        if parsed is None:
            continue
        files.append(
            PriceFile(
                url=BASE_URL + href,
                filename=filename,
                updated_at="",
                size="",
                file_type=parsed["ext"].upper(),
                category=parsed["category"],
                store_id=parsed["store_id"],
                store_name="",  # not exposed by this listing -- only the real Stores file has names
            )
        )
    return files


def download(price_file: PriceFile) -> bytes:
    """Download and gunzip one listed file -- confirmed live: every file
    here (including Stores) is gzipped, unlike Carrefour's uncompressed
    Stores.xml, so this always gunzips rather than branching on extension."""
    resp = _session.get(price_file.url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as gz:
        return gz.read()
