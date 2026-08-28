"""Client for Victory's (and, if it ever gets a Kfar Saba branch, Machsanei
HaShuk's) laibcatalog.co.il API. Both chains share this same API host and
JSON schema -- the only real difference is which chain_id(s) to query.

No login required. `getbranches`/`getfiles` are a real JSON API (verified
live 2026-08-28), not an HTML table or inline JS like Shufersal/Carrefour --
much simpler to talk to, but two things confirmed live are worth keeping in
mind:
- `getfiles` returns the chain's FULL file listing regardless of
  `branchNumber`, so only one listing call per chain_id is needed -- looping
  per-branch would just repeat the same response.
- A chain_id with zero branches (Machsanei HaShuk's second chain_id, live)
  makes `getfiles` 400 ("FilesRootPath is invalid") -- skip it instead of
  calling getfiles at all.

Same regulated XML schema as Shufersal/Carrefour -- verified live against a
real PriceFull (8,948 items, store 079) and the real Stores file (70
stores): shufersal.py's parse_price_xml()/parse_stores_xml() work
unmodified. One real quirk in Victory's own Stores file: the nested
SubChain id element is spelled "SubChainId" (lowercase d) instead of
Shufersal/Carrefour's "SubChainID", so subchain_id comes back blank for
this chain -- harmless, nothing downstream keys on it. A second, more
consequential quirk -- the City field holds the literal city NAME here
instead of a settlement code -- is handled in shufersal.kfar_saba_stores()
directly, since that function needs to work for every chain, not just this
one.

Two runs against this module from GitHub Actions both failed while the
exact same code ran clean locally against live data every time -- couldn't
get the actual traceback out of GitHub's log viewer (requires sign-in even
on a public repo), but this is consistent with laibcatalog.co.il (a
smaller platform than Shufersal/Carrefour, already flagged in docs/
sources.md as having changed/broken before) rejecting requests with
Python's default User-Agent from a well-known cloud IP range, which a
basic bot-filter would plausibly do. Requests here go through a shared
Session with a browser-like User-Agent -- this was the one concrete,
untested difference against carrefour.py's client, which sets one on its
initial request and has not failed in CI.
"""
from __future__ import annotations

import gzip
import io

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from etl.scrapers.shufersal import PriceFile

BASE_URL = "https://laibcatalog.co.il"
REQUEST_TIMEOUT = 60  # live listing calls observed to take 10-20s

_session = requests.Session()
_session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
)
# Retries at the transport level (connection errors, 5xx, 429) -- covers a
# transient blip without needing a manual retry loop at every call site.
_retry_adapter = HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504]))
_session.mount("https://", _retry_adapter)
_session.mount("http://", _retry_adapter)

# Verified live 2026-08-28: Victory has exactly one Kfar Saba branch (079,
# "כפר סבא הירוקה", אנגל 78). Machsanei HaShuk's full branch list (71
# branches across both its chain_ids) has NONE in Kfar Saba -- the old
# planning-stage note ("לוי אשכול 37") didn't hold up against the live
# branch list, so it's left out rather than guessed back in. If it ever
# opens one, this same client covers it -- just add its chain_id below.
VICTORY_CHAIN_IDS = ["7290696200003", "7290058103393"]
MAHSANEI_HASHUK_CHAIN_IDS = ["7290661400001", "7290633800006"]


def list_files(chain_ids: list[str]) -> list[PriceFile]:
    """List every file the API has for the given chain_id(s)."""
    files = []
    for chain_id in chain_ids:
        resp = _session.get(
            f"{BASE_URL}/webapi/api/getbranches",
            params={"edi": chain_id},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        if not resp.json():
            continue

        resp = _session.get(
            f"{BASE_URL}/webapi/api/getfiles",
            params={"edi": chain_id},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        for entry in resp.json():
            category = entry.get("fileType", "")
            branch_number = entry.get("branchNumber")
            store_id = "All" if category.lower() == "stores" else f"{int(branch_number):03d}"
            files.append(
                PriceFile(
                    url=f"{BASE_URL}/webapi/{chain_id}/{entry['fileName']}",
                    filename=entry["fileName"],
                    updated_at=entry.get("fileDate", ""),
                    size=str(entry.get("fileSize", "")),
                    file_type="GZ",
                    category=category,
                    store_id=store_id,
                    store_name="",
                )
            )
    return files


def download(price_file: PriceFile) -> bytes:
    """Download and gunzip one listed file (every file observed live was
    .gz, including the Stores file -- unlike Carrefour's uncompressed
    Stores.xml)."""
    resp = _session.get(price_file.url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as gz:
        return gz.read()
