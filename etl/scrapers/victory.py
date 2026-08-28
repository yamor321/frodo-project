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

**Confirmed 2026-08-28, from the actual GitHub Actions log (the user
fetched it -- GitHub requires sign-in to view Actions logs even on a
public repo, which this project's Claude session has no path to on its
own): GitHub's runners cannot open a TCP connection to laibcatalog.co.il
at all.**

    urllib3.exceptions.ConnectTimeoutError: ... Connection to
    laibcatalog.co.il timed out. (connect timeout=60)

That's a connect-level timeout, not an HTTP error -- no 403, no response
of any kind, the handshake itself never completes. A User-Agent header
(tried first, on the theory that a bot-filter was rejecting Python's
default one) cannot fix this: that's an HTTP-layer signal, and this never
gets far enough to send one. The far more likely explanation is
laibcatalog.co.il (a smaller platform than Shufersal/Carrefour, already
flagged in docs/sources.md as having changed/broken before) firewalling
off GitHub's/Azure's known IP ranges outright -- not unusual for a small
site defending against scraping traffic, and outside what any client-side
code change here can work around. The same code runs clean every time
from a home network.

Practical consequence: `_collect_victory()` in scripts/daily_snapshot.py
is expected to keep failing in the GitHub Actions environment specifically
until/unless that block lifts on their end. daily_snapshot.py's
`_safe_collect()` already isolates this -- one chain being unreachable
does not take the rest of the site down, it just means Victory's one
branch is missing from that day's build. Timeouts below are kept short
(not the 60s used before this was diagnosed) so a real block is detected
in seconds, not by burning minutes of every CI run retrying a connection
that was never going to succeed.
"""
from __future__ import annotations

import gzip
import io

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from etl.scrapers.shufersal import PriceFile

BASE_URL = "https://laibcatalog.co.il"
# (connect timeout, read timeout) -- connect fails fast since an actual
# network block manifests immediately, not by taking longer to think about
# it; read stays generous for a slow-but-working response (observed live:
# successful listing calls take 10-20s once connected).
REQUEST_TIMEOUT = (10, 30)

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
# genuinely transient blip. Kept small: if the connect timeout above is
# hit, it's a real network block, not something more retries fix.
_retry_adapter = HTTPAdapter(max_retries=Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504]))
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
