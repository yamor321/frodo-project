"""Client for the shared "Cerberus" price-transparency FTP platform at
url.retail.publishedprices.co.il, used by Rami Levy, Yohananof, and Osher Ad
(and ~30 other chains not relevant to this pilot) to publish their regulated
Price/PriceFull/Stores files.

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
"""
from __future__ import annotations

import ftplib
import gzip
import io
import re

from etl.scrapers.shufersal import PriceFile

FTP_HOST = "url.retail.publishedprices.co.il"
FTP_TIMEOUT = 30

# ftp_username + chain_id per OpenIsraeliSupermarkets' scrappers/{ramilevy,
# yohananof,osherad}.py (see module docstring). Empty password, always.
CHAINS = {
    "rami-levy": {"ftp_username": "RamiLevi", "chain_id": "7290058140886"},
    "yohananof": {"ftp_username": "yohananof", "chain_id": "7290803800003"},
    "osher-ad": {"ftp_username": "osherad", "chain_id": "7290103152017"},
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


def _connect(ftp_username: str) -> ftplib.FTP:
    """One connection per call rather than a shared/pooled session:
    ftplib.FTP isn't safe to share across concurrent threads, and
    fetch_concurrently() runs downloads on a thread pool -- an independent
    connection per call is the correct match, not an oversight."""
    ftp = ftplib.FTP(timeout=FTP_TIMEOUT)
    ftp.connect(FTP_HOST, 21)
    ftp.login(user=ftp_username, passwd="")
    return ftp


def list_files(ftp_username: str) -> list[PriceFile]:
    """List this chain's Stores and PriceFull files.

    Scoped server-side to two glob patterns (not a full directory dump) --
    this project never needs Price/Promo delta files, only PriceFull +
    Stores, same as Shufersal/Carrefour/Victory. UNCONFIRMED: whether this
    server's NLST honors the same wildcard glob syntax the reference scraper
    uses (see module docstring) -- needs a live run to verify.
    """
    ftp = _connect(ftp_username)
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


def download(ftp_username: str, price_file: PriceFile) -> bytes:
    """Download and (if needed) gunzip one listed file."""
    ftp = _connect(ftp_username)
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
