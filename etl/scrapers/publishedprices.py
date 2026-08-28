"""Client for the shared "Cerberus Web Client" price-transparency platform
at url.publishedprices.co.il, used by Rami Levy, Yohananof, Osher Ad,
Tiv Taam, Dor Alon (AM:PM), Yellow, Stop Market, Fresh Market/Super Dosh,
Keshet Teamim, and Salach Dabach (branded "Angus") -- all ten confirmed to
have a real Kfar Saba branch (see docs/sources.md, 28.08.2026 research
passes) -- plus ~20 other chains on the same platform with no known Kfar
Saba presence.

**This module used to talk FTP to a different host (url.retail.
publishedprices.co.il). That's now dead code, not just unused -- confirmed
from TWO independent cloud environments (this dev sandbox AND a real
GitHub Actions run, commit 66f1517) that the FTP data channel is blocked
outright: login succeeds, every LIST/RETR times out, for all ten chains.
See docs/sources.md's "Cerberus" sections for the full diagnostic trail
(including a real, fixed TLS bug for Dor Alon that turned out not to matter
-- the block sits beneath login regardless of FTP vs FTPS).**

**The fix: this platform ALSO exposes a normal HTTPS web client (the same
UI a human uses in a browser) at a DIFFERENT host -- url.publishedprices.co.il,
no "retail." -- and it is NOT subject to the FTP block, confirmed live
2026-08-28.** The exact same username/password used for FTP logs into this
web client too -- nothing to register, no new credentials needed. Verified
end-to-end against three different chains, including ones with a real
non-empty password (Paz_bo/paz468, SalachD/12345): login succeeds, the file
listing returns real current files, and a real file downloads and gunzips
to the same `<Root><ChainID>...` schema already confirmed everywhere else
in this project.

The flow, confirmed live by reading the actual page + its AJAX calls (not
guessed from a summary):
1. GET /login -> a `<meta name="csrftoken" content="...">` tag carries a
   token that must be echoed back on the next POST.
2. POST /login/user with username, password, csrftoken, r="" -> sets a
   session cookie and redirects to /file on success.
3. GET /file -> a FRESH csrftoken (it rotates per page load, the /login
   one won't work here).
4. POST /file/json/dir with csrftoken + jQuery-DataTables-style paging
   params (sEcho, iDisplayStart, iDisplayLength) -> JSON `{"aaData": [...]}`
   listing every file. iDisplayLength=100000 returned all 2,787 of Rami
   Levy's files in one call -- no pagination needed at this project's scale.
5. GET /file/d/<filename> -> the raw file bytes (gzip for Price*/PriceFull*,
   uncompressed .xml for Stores).

Username/chain_id values are not this project's own discovery -- read
verbatim from OpenIsraeliSupermarkets/israeli-supermarket-scarpers
(github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers), an
actively maintained open-source scraper covering 30+ Israeli chains, whose
`cerberus.py` engine uses these same credentials over FTP against a
sibling host. That project's FTP approach is exactly what this module used
to do and no longer does, for the reasons above.

**No independent fallback exists for Victory/Machsanei HaShuk:** checked
whether either chain is also reachable through this platform as a backup
path when laibcatalog.co.il is blocked (see etl/scrapers/victory.py). Both
have a "Matrix"-engine legacy scraper in the same reference project, but it
also targets laibcatalog.co.il (a different page on the SAME host, not a
different host) -- so it would fail identically to the TCP-level block
already diagnosed there. No real fallback, just two paths to one blocked
door.
"""
from __future__ import annotations

import gzip
import io
import re

import requests

from etl.scrapers.shufersal import PriceFile

BASE_URL = "https://url.publishedprices.co.il"
REQUEST_TIMEOUT = 30

_CSRF_RE = re.compile(r'name="csrftoken"[^>]*(?:value|content)="([^"]+)"')

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# username/password + chain_id, read verbatim from OpenIsraeliSupermarkets'
# scrappers/{ramilevy,yohananof,osherad,tivtaam,doralon,yellow,stop_market,
# superdosh,keshet,salachdabach}.py (see module docstring). Most of this
# platform's chains use an empty password; two below don't -- these are the
# credentials that project publishes for reading this legally-mandated
# public data, not a secret this project discovered or is bypassing
# anything to get. Same credentials work over both FTP (dead, see module
# docstring) and this HTTPS client -- nothing chain-specific about the
# transport.
CHAINS = {
    "rami-levy": {"username": "RamiLevi", "password": "", "chain_id": "7290058140886"},
    "yohananof": {"username": "yohananof", "password": "", "chain_id": "7290803800003"},
    "osher-ad": {"username": "osherad", "password": "", "chain_id": "7290103152017"},
    "tiv-taam": {"username": "TivTaam", "password": "", "chain_id": "7290873255550"},
    "dor-alon": {"username": "doralon", "password": "", "chain_id": "7290492000005"},
    "yellow": {"username": "Paz_bo", "password": "paz468", "chain_id": "7290644700005"},
    "stop-market": {"username": "Stop_Market", "password": "", "chain_id": "72906390"},
    "fresh-market": {"username": "freshmarket", "password": "", "chain_id": "7290876100000"},
    "keshet": {"username": "Keshet", "password": "", "chain_id": "7290785400000"},
    "salach-dabach": {"username": "SalachD", "password": "12345", "chain_id": "7290526500006"},
}

# Same dash-separated convention confirmed for Shufersal/Carrefour/Victory:
# a category prefix, digits (chain_id) with no separator, then a dash-joined
# tail. Per-store files have 4 tail fields (subchain-store-date-time); the
# chain-wide Stores file has 3 (subchain-date-time, store_id normalizes to
# "All"). Mirrors carrefour.py's _parse_filename exactly -- kept as a local
# copy rather than a shared import since it's three lines and each chain's
# module already owns its own filename quirks independently.
_FILENAME_RE = re.compile(r"^([A-Za-z]+)(\d+)-(.+)\.(gz|xml)$")


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


def _get_csrf(session: requests.Session, path: str) -> str:
    resp = session.get(f"{BASE_URL}{path}", timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    m = _CSRF_RE.search(resp.text)
    if not m:
        raise ValueError(f"csrftoken not found on {path} -- page structure may have changed")
    return m.group(1)


def _login(username: str, password: str = "") -> requests.Session:
    """One session per call rather than a shared/pooled one -- matches this
    project's existing per-call-connection precedent (see e.g. Shuk HaIr's
    _connect()) and sidesteps any thread-safety question, since
    fetch_concurrently() runs chains on a thread pool.

    Raises PermissionError if login didn't actually succeed (POST
    /login/user returns 200 either way -- success is a redirect to /file,
    not the status code).
    """
    session = requests.Session()
    session.headers.update({"User-Agent": _USER_AGENT})
    token = _get_csrf(session, "/login")
    resp = session.post(
        f"{BASE_URL}/login/user",
        data={"username": username, "password": password, "csrftoken": token, "r": ""},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    if not resp.url.rstrip("/").endswith("/file"):
        raise PermissionError(f"login failed for {username!r} (landed on {resp.url}, not /file)")
    return session


def preflight(username: str, password: str = "") -> bool:
    """Cheap reachability check -- call this BEFORE list_files()/download()
    so a chain that can't log in this run is skipped instead of discovered
    partway through a real collection attempt."""
    return preflight_diagnostic(username, password)["ok"]


def preflight_diagnostic(username: str, password: str = "") -> dict:
    """Same check as preflight(), but returns which step failed and the
    real exception -- see docs/sources.md for why this project writes these
    to a committed file rather than trusting a boolean: it's what caught
    Dor Alon's real (since-superseded) FTP/TLS bug, not a guess."""
    result = {"host": BASE_URL, "username": username, "ok": False, "failed_at": None, "error": None}
    try:
        result["failed_at"] = "login"
        session = _login(username, password)
        result["failed_at"] = "list"
        token = _get_csrf(session, "/file")
        resp = session.post(
            f"{BASE_URL}/file/json/dir",
            data={"csrftoken": token, "sEcho": 1, "iDisplayStart": 0, "iDisplayLength": 1},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        if resp.json().get("error"):
            raise ValueError(str(resp.json()["error"]))
        result["ok"] = True
        result["failed_at"] = None
    except Exception as exc:  # noqa: BLE001 -- deliberately broad, see docstring
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def list_files(username: str, password: str = "") -> list[PriceFile]:
    """List every Price/PriceFull/Stores file this chain's account can see.

    Does NOT run preflight() itself -- callers doing a real collection run
    should call preflight() first and skip entirely on failure, per this
    module's own health-check principle; a function that quietly no-ops on
    an unreachable source is harder to distinguish from "genuinely zero
    files" than a caller that checked and skipped on purpose.

    iDisplayLength=100000 in one call, confirmed live to return everything
    (2,787 files for Rami Levy) rather than needing real pagination -- this
    project's per-chain volumes never approach that ceiling.
    """
    session = _login(username, password)
    token = _get_csrf(session, "/file")
    resp = session.post(
        f"{BASE_URL}/file/json/dir",
        data={"csrftoken": token, "sEcho": 1, "iDisplayStart": 0, "iDisplayLength": 100000},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    entries = resp.json().get("aaData", [])

    files = []
    for entry in entries:
        parsed = _parse_filename(entry["name"])
        if parsed is None:
            continue
        files.append(
            PriceFile(
                url=f"{BASE_URL}/file/d/{entry['name']}",
                filename=entry["name"],
                updated_at=entry.get("ftime", ""),
                size=str(entry.get("size", "")),
                file_type=parsed["ext"].upper(),
                category=parsed["category"],
                store_id=parsed["store_id"],
                store_name="",
            )
        )
    return files


def download(username: str, price_file: PriceFile, password: str = "") -> bytes:
    """Download and (if needed) gunzip one listed file."""
    session = _login(username, password)
    resp = session.get(price_file.url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if price_file.filename.lower().endswith(".gz"):
        with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as gz:
            return gz.read()
    return resp.content
