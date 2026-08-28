"""Client for the shared "Cerberus" price-transparency FTP platform at
url.retail.publishedprices.co.il, used by Rami Levy, Yohananof, Osher Ad,
Tiv Taam, Dor Alon (AM:PM), Yellow, Stop Market, Fresh Market/Super Dosh,
Keshet Teamim, and Salach Dabach (branded "Angus") -- all ten confirmed to
have a real Kfar Saba branch (see docs/sources.md, 28.08.2026 research
passes) -- plus ~20 other chains on the same platform with no known Kfar
Saba presence.

**Confirmed live 2026-08-28, from this project's own session:** the FTP
server accepts a login with each chain's own username and an EMPTY password
-- no personal account, no admin approval, nothing to register. Verified
independently with both Python's ftplib and curl, against three real chain
usernames:

    ftp.login(user="RamiLevi", passwd="")   -> 230 Password Ok, User logged in
    ftp.login(user="yohananof", passwd="")  -> 230 Password Ok, User logged in
    ftp.login(user="osherad", passwd="")    -> 230 Password Ok, User logged in

This is a DIFFERENT host from the HTTP portal at
https://url.publishedprices.co.il (no "retail." in the hostname), which is a
separate, admin-gated web UI with its own human-reviewed account-request
form. That portal is not needed for this project -- registering there can be
dropped.

Username/chain_id values below are not this project's own discovery -- read
verbatim from OpenIsraeliSupermarkets/israeli-supermarket-scarpers
(github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers), an
actively maintained open-source scraper covering 30+ Israeli chains, whose
`cerberus.py` engine implements this exact FTP handshake against this exact
host (default ftp_host="url.retail.publishedprices.co.il", ftp_password="").

**Not yet confirmed (blocked, not skipped):** this dev sandbox's shell cannot
open any outbound FTP data connection at all -- confirmed generally, not just
against this host: the same PASV/active timeout happens against
ftp.debian.org too, and a bare connection to an unrelated FTP host on port 21
also just hangs. The control channel (login) works fine over the same
connection; only the data channel (LIST/RETR, passive or active) never
completes. That means, until this runs somewhere with a working data channel:
- The exact listing/filename shape on THIS server is assumed, not confirmed,
  to match the convention already verified for Shufersal/Carrefour/Victory
  (same regulation, same schema every time so far).
- Kfar Saba branch numbers for these three chains are UNKNOWN -- they can
  only come from a real downloaded Stores file.
- Whether shufersal.parse_price_xml()/parse_stores_xml() work unmodified here
  is UNCONFIRMED for the same reason.

GitHub Actions runners have ordinary unrestricted outbound internet access
(unlike this sandbox), so this is expected to work once it runs there -- the
mirror image of the Victory situation (there GitHub was blocked and a home
network worked; here this dev sandbox is blocked and GitHub is expected to
work). That expectation needs a live CI run to actually confirm.

**Health check, not a blind attempt:** `preflight()` below runs the same
FTP login it would need anyway plus one lightweight, scoped LIST, with a
short timeout -- so a chain whose data channel is unreachable this run gets
skipped in seconds, not discovered by a hung listing/download attempt.
Callers (any future daily_snapshot.py integration) are expected to call this
BEFORE attempting real collection, exactly the lesson this module itself was
built around (see etl/health_check.py's docstring).

**Dor Alon needs FTPS, confirmed live 2026-08-28 from a committed diagnostics
file, not guessed:** `daily_snapshot.py` writes `data/processed/<date>/
cerberus_diagnostics.json` every run (see its module docstring for why --
this dev sandbox can't read GitHub Actions' own logs). That file showed
Dor Alon failing at the login step with a real FTP error (`530 Secure
connection required`), distinct from every other chain's generic data-
channel timeout. Confirmed directly: plain `ftplib.FTP` login gets the same
530; `ftplib.FTP_TLS` (+ `prot_p()` to secure the data channel too) logs in
fine. `CHAINS["dor-alon"]["use_tls"]` is `True`; every other chain tested so
far accepts plain FTP, so don't assume TLS is needed platform-wide.

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

import ftplib
import gzip
import io
import re

from etl.health_check import ftp_preflight, ftp_preflight_diagnostic
from etl.scrapers.shufersal import PriceFile

FTP_HOST = "url.retail.publishedprices.co.il"
FTP_TIMEOUT = 30

# ftp_username/ftp_password + chain_id, read verbatim from
# OpenIsraeliSupermarkets' scrappers/{ramilevy,yohananof,osherad,tivtaam,
# doralon,yellow,stop_market,superdosh,keshet,salachdabach}.py (see module
# docstring). Most of this platform's chains use an empty password; two
# below don't -- these are the credentials that project publishes for
# reading this legally-mandated public data, not a secret this project
# discovered or is bypassing anything to get.
CHAINS = {
    "rami-levy": {"ftp_username": "RamiLevi", "ftp_password": "", "chain_id": "7290058140886", "use_tls": False},
    "yohananof": {"ftp_username": "yohananof", "ftp_password": "", "chain_id": "7290803800003", "use_tls": False},
    "osher-ad": {"ftp_username": "osherad", "ftp_password": "", "chain_id": "7290103152017", "use_tls": False},
    "tiv-taam": {"ftp_username": "TivTaam", "ftp_password": "", "chain_id": "7290873255550", "use_tls": False},
    # Confirmed live 2026-08-28: this account rejects plain FTP with a real
    # error (530 Secure connection required), not the generic data-channel
    # timeout every other chain here hits -- found from cerberus_diagnostics.json,
    # not guessed. Plain ftplib.FTP login fails; ftplib.FTP_TLS login succeeds.
    "dor-alon": {"ftp_username": "doralon", "ftp_password": "", "chain_id": "7290492000005", "use_tls": True},
    "yellow": {"ftp_username": "Paz_bo", "ftp_password": "paz468", "chain_id": "7290644700005", "use_tls": False},
    "stop-market": {"ftp_username": "Stop_Market", "ftp_password": "", "chain_id": "72906390", "use_tls": False},
    "fresh-market": {"ftp_username": "freshmarket", "ftp_password": "", "chain_id": "7290876100000", "use_tls": False},
    "keshet": {"ftp_username": "Keshet", "ftp_password": "", "chain_id": "7290785400000", "use_tls": False},
    "salach-dabach": {"ftp_username": "SalachD", "ftp_password": "12345", "chain_id": "7290526500006", "use_tls": False},
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


def _connect(ftp_username: str, ftp_password: str = "", use_tls: bool = False) -> ftplib.FTP:
    """One connection per call rather than a shared/pooled session:
    ftplib.FTP isn't safe to share across concurrent threads, and
    fetch_concurrently() runs downloads on a thread pool -- an independent
    connection per call is the correct match, not an oversight."""
    ftp = ftplib.FTP_TLS(timeout=FTP_TIMEOUT) if use_tls else ftplib.FTP(timeout=FTP_TIMEOUT)
    ftp.connect(FTP_HOST, 21)
    ftp.login(user=ftp_username, passwd=ftp_password)
    if use_tls:
        ftp.prot_p()  # secure the data channel too, not just the control channel
    return ftp


def preflight(ftp_username: str, ftp_password: str = "", use_tls: bool = False) -> bool:
    """Cheap reachability check -- call this BEFORE list_files()/download()
    so an unreachable chain is skipped in seconds instead of discovered by a
    hung listing attempt. See etl/health_check.py and the module docstring."""
    return ftp_preflight(FTP_HOST, ftp_username, ftp_password, use_tls=use_tls)


def preflight_diagnostic(ftp_username: str, ftp_password: str = "", use_tls: bool = False) -> dict:
    """Same check as preflight(), but returns which step failed and the real
    exception -- see etl/health_check.ftp_preflight_diagnostic. Exists so a
    CI-only failure can be understood from a committed diagnostics file
    (this dev sandbox can't reach GitHub Actions' own logs directly) instead
    of guessed at."""
    return ftp_preflight_diagnostic(FTP_HOST, ftp_username, ftp_password, use_tls=use_tls)


def list_files(ftp_username: str, ftp_password: str = "", use_tls: bool = False) -> list[PriceFile]:
    """List this chain's Stores and PriceFull files.

    Does NOT run preflight() itself -- callers doing a real collection run
    should call preflight() first and skip entirely on failure, per this
    module's own health-check principle; a function that quietly no-ops on
    an unreachable source is harder to distinguish from "genuinely zero
    files" than a caller that checked and skipped on purpose.

    Scoped server-side to two glob patterns (not a full directory dump) --
    this project never needs Price/Promo delta files, only PriceFull +
    Stores, same as Shufersal/Carrefour/Victory. UNCONFIRMED: whether this
    server's NLST honors the same wildcard glob syntax the reference scraper
    uses (see module docstring) -- needs a live run to verify.
    """
    ftp = _connect(ftp_username, ftp_password, use_tls)
    try:
        names: list[str] = []
        for pattern in ("*store*", "*pricefull*"):
            try:
                names.extend(ftp.nlst(pattern))
            except ftplib.error_perm:
                continue  # no matches for this pattern -- not an error
    finally:
        ftp.quit()

    files = []
    for name in names:
        parsed = _parse_filename(name)
        if parsed is None:
            continue
        files.append(
            PriceFile(
                url=name,  # FTP path, not an HTTP URL -- download() RETRs this by name
                filename=name,
                updated_at="",
                size="",
                file_type=parsed["ext"].upper(),
                category=parsed["category"],
                store_id=parsed["store_id"],
                store_name="",
            )
        )
    return files


def download(ftp_username: str, price_file: PriceFile, ftp_password: str = "", use_tls: bool = False) -> bytes:
    """Download and (if needed) gunzip one listed file."""
    ftp = _connect(ftp_username, ftp_password, use_tls)
    buf = io.BytesIO()
    try:
        ftp.retrbinary(f"RETR {price_file.filename}", buf.write)
    finally:
        ftp.quit()
    buf.seek(0)
    if price_file.filename.lower().endswith(".gz"):
        with gzip.GzipFile(fileobj=buf) as gz:
            return gz.read()
    return buf.read()
