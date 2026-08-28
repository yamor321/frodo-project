"""Client for the shared "Bina" price-transparency platform at
<prefix>.binaprojects.com, used by Shuk HaIr (and ~10 other chains not
relevant to this pilot) to publish regulated Price/PriceFull/Stores files.

No login of any kind -- every request is a plain unauthenticated GET,
verified live 2026-08-28 against two real chains (King Store, Shuk HaIr):

- Listing: GET {base}/MainIO_Hok.aspx?_={chain_id}&wReshet=הכל&WFileType=&
  WDate=&WStore= -> a JSON array (not HTML), one object per file:
  {"FileNm": "PriceFull7290058148776-000-311-...GZ", "Store": "...", ...}.
- Download is a two-hop redirect, NOT a direct URL -- easy to get wrong
  without checking live: GET {base}/Download.aspx?FileNm={filename} returns
  JSON `[{"SPath": "<real file URL>"}]`; only THAT url serves the actual
  (gzipped) bytes.
- Same regulated XML schema as every other chain in this project --
  shufersal.py's parse_price_xml()/parse_stores_xml() work unmodified,
  verified against a real downloaded Shuk HaIr PriceFull (1,938,656 bytes
  uncompressed) and a real Stores file (26 stores).
- Filenames use an uppercase ".GZ" extension (Shufersal/Carrefour use
  lowercase) -- handled case-insensitively below, not assumed.

**Kfar Saba, confirmed via each chain's real Stores file, not a news
article:**
- Shuk HaIr: exactly one branch, store "011", "כפר סבא מזרח", אלי הורוביץ 26
  (official City filter, code 6900 -- see shufersal.kfar_saba_stores()).
- King Store: checked and found NONE. A local news article
  (kfarsaba.mynet.co.il) reported King Store "opening" a branch in the
  city, but the live Stores file (29 stores total, checked 2026-08-28) has
  no branch carrying the official Kfar Saba city code. Left out rather than
  guessed in -- add it back once the Stores file actually shows one.

url_perfix/chain_id values are read from OpenIsraeliSupermarkets'
scrappers/{king_store,shuk_ahir}.py and engines/bina.py (see docs/sources.md).
"""
from __future__ import annotations

import gzip
import io
import re

import requests

from etl.scrapers.shufersal import PriceFile

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

# url_perfix + chain_id, read verbatim from OpenIsraeliSupermarkets'
# scrappers/shuk_ahir.py. Only chains with a confirmed live Kfar Saba branch
# (see module docstring) -- this is not the platform's full chain roster.
CHAINS = {
    "shuk-hair": {"url_perfix": "shuk-hayir", "chain_id": "7290058148776"},
}

# Fallback constant (same role as carrefour.KFAR_SABA_STORE_IDS and
# victory.KFAR_SABA_STORE_IDS): lets daily_snapshot.py's raw-snapshot
# fallback find this store even if live discovery fails outright, without
# needing a live Stores file to derive it from that day.
SHUK_HAIR_KFAR_SABA_STORE_IDS = {"011"}

# Same dash-separated convention confirmed for every other chain in this
# project -- category prefix, digits (chain_id) with no separator, then a
# dash-joined tail (4 fields per-store, 3 for the chain-wide Stores file).
# Extension is case-insensitive: Bina uses uppercase ".GZ" live, unlike
# Shufersal/Carrefour's lowercase.
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


def list_files(url_perfix: str, chain_id: str) -> list[PriceFile]:
    """List every Price/PriceFull/Stores file this chain has published."""
    base = f"http://{url_perfix}.binaprojects.com/"
    resp = _session.get(
        base + "MainIO_Hok.aspx",
        params={"_": chain_id, "wReshet": "הכל", "WFileType": "", "WDate": "", "WStore": ""},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()

    files = []
    for entry in resp.json():
        parsed = _parse_filename(entry["FileNm"])
        if parsed is None:
            continue
        files.append(
            PriceFile(
                url=f"{base}Download.aspx?FileNm={entry['FileNm']}",  # resolved to the real file URL by download()
                filename=entry["FileNm"],
                updated_at=entry.get("DateFile", ""),
                size="",
                file_type=parsed["ext"].upper(),
                category=parsed["category"],
                store_id=parsed["store_id"],
                store_name=entry.get("Store", "").strip(),
            )
        )
    return files


def download(price_file: PriceFile) -> bytes:
    """Resolve the real file URL (two-hop, see module docstring) and
    download + gunzip it."""
    resolve_resp = _session.get(price_file.url, timeout=REQUEST_TIMEOUT)
    resolve_resp.raise_for_status()
    real_url = resolve_resp.json()[0]["SPath"]

    file_resp = _session.get(real_url, timeout=REQUEST_TIMEOUT)
    file_resp.raise_for_status()
    with gzip.GzipFile(fileobj=io.BytesIO(file_resp.content)) as gz:
        return gz.read()
