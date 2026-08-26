"""Client for Shufersal's price-transparency portal.

Lists, downloads, and parses the Store/Price/PriceFull files Shufersal is
legally required to publish (see ../../docs/sources.md for the regulation
and verified portal details).

Portal: https://prices.shufersal.co.il/ -- confirmed to require no login.
"""
from __future__ import annotations

import gzip
import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterable, Iterator

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://prices.shufersal.co.il/"
REQUEST_TIMEOUT = 20


@dataclass
class PriceFile:
    """One row from the portal's file-listing table."""

    url: str
    filename: str
    updated_at: str
    size: str
    file_type: str  # e.g. "GZ"
    category: str  # e.g. "price", "pricefull", "promo", "promofull", "stores"
    store_id: str
    store_name: str


@dataclass
class PriceRecord:
    """One <Item> normalized into the project's canonical schema."""

    chain_id: str
    subchain_id: str
    store_id: str
    item_code: str
    item_name: str
    manufacturer_name: str
    manufacturer_country: str
    unit_qty: str
    quantity: str
    unit_of_measure: str
    is_weighted: bool
    qty_in_package: str
    item_price: float
    unit_of_measure_price: float
    price_update_time: str


def list_files(max_pages: int = 200) -> Iterator[PriceFile]:
    """Walk the portal's file-listing table and yield every row found.

    No query-string filter for store/category was found on the live portal
    (checked: ?code=, ?store=, ?storeId=, ?category=, ?fileType=, ?type= all
    no-op). The table *does* support deterministic sorting via
    ?sort=Branch&sortdir=ASC, so this walks every page in that order and lets
    callers filter client-side. A page with zero rows ends the walk.
    """
    session = requests.Session()
    page = 1
    while page <= max_pages:
        resp = session.get(
            BASE_URL,
            params={"page": page, "sort": "Branch", "sortdir": "ASC"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        rows = list(_parse_listing_page(resp.text))
        if not rows:
            return
        yield from rows
        page += 1


def _parse_listing_page(html: str) -> Iterator[PriceFile]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="webgrid")
    if table is None:
        return
    body = table.find("tbody")
    if body is None:
        return
    for tr in body.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 7:
            continue
        link = cells[0].find("a")
        if link is None or not link.get("href"):
            continue
        store_id, _, store_name = cells[5].get_text(strip=True).partition(" - ")
        yield PriceFile(
            url=link["href"],
            filename=cells[6].get_text(strip=True),
            updated_at=cells[1].get_text(strip=True),
            size=cells[2].get_text(strip=True),
            file_type=cells[3].get_text(strip=True),
            category=cells[4].get_text(strip=True),
            store_id=store_id.strip(),
            store_name=store_name.strip(),
        )


@dataclass
class StoreRecord:
    """One <Store> from the chain-wide Stores file."""

    chain_id: str
    subchain_id: str
    store_id: str
    store_name: str
    address: str
    city_code: str
    zip_code: str


def list_stores_file(files: Iterable[PriceFile]) -> PriceFile | None:
    """Pick the single chain-wide Stores row out of a file listing.

    Unlike Price/PriceFull, Stores is published once for the whole chain
    (category == "stores", store_id == "All"), not per branch.
    """
    for f in files:
        if f.category.lower() == "stores":
            return f
    return None


def parse_stores_xml(xml_bytes: bytes) -> list[StoreRecord]:
    """Parse the chain-wide Stores XML into normalized records.

    Real schema (verified live 2026-08-27): <Chain><ChainID/><ChainName/>
    <SubChains><SubChain><SubChainID/><SubChainName/><Stores><Store><StoreID/>
    <BikoretNo/><StoreType/><StoreName/><Address/><City/><ZIPCode/></Store>...
    `<City>` is a numeric settlement code (סמל יישוב), not a city name string --
    e.g. every confirmed Kfar Saba branch carries City=6900.
    """
    root = ET.fromstring(xml_bytes)
    chain_id = _text(root, "ChainID")

    records = []
    for subchain in root.findall("./SubChains/SubChain"):
        subchain_id = _text(subchain, "SubChainID")
        for store in subchain.findall("./Stores/Store"):
            records.append(
                StoreRecord(
                    chain_id=chain_id,
                    subchain_id=subchain_id,
                    store_id=_text(store, "StoreID"),
                    store_name=_text(store, "StoreName"),
                    address=_text(store, "Address"),
                    city_code=_text(store, "City"),
                    zip_code=_text(store, "ZIPCode"),
                )
            )
    return records


def kfar_saba_stores(stores: Iterable[StoreRecord]) -> set[str]:
    """Store IDs whose official settlement code (City) is Kfar Saba (6900).

    Objective, data-driven replacement for KFAR_SABA_STORE_IDS below (which
    was identified by manually reading Hebrew branch names) -- verified live
    2026-08-27: all 6 manually-identified branches carry City=="6900".
    """
    return {s.store_id for s in stores if s.city_code == KFAR_SABA_CITY_CODE}


def download(price_file: PriceFile) -> bytes:
    """Download and gunzip one listed file; return raw XML bytes."""
    resp = requests.get(price_file.url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as gz:
        return gz.read()


def parse_price_xml(xml_bytes: bytes) -> list[PriceRecord]:
    """Parse a Price/PriceFull XML payload into normalized records."""
    root = ET.fromstring(xml_bytes)
    chain_id = _text(root, "ChainID")
    subchain_id = _text(root, "SubChainID")
    store_id = _text(root, "StoreID")

    items_el = root.find("Items")
    if items_el is None:
        return []

    records = []
    for item in items_el.findall("Item"):
        records.append(
            PriceRecord(
                chain_id=chain_id,
                subchain_id=subchain_id,
                store_id=store_id,
                item_code=_text(item, "ItemCode"),
                item_name=_text(item, "ItemName"),
                manufacturer_name=_text(item, "ManufactureName"),
                manufacturer_country=_text(item, "ManufactureCountry"),
                unit_qty=_text(item, "UnitQty"),
                quantity=_text(item, "Quantity"),
                unit_of_measure=_text(item, "UnitOfMeasure"),
                is_weighted=_text(item, "bIsWeighted") == "1",
                qty_in_package=_text(item, "QtyInPackage"),
                item_price=float(_text(item, "ItemPrice") or 0),
                unit_of_measure_price=float(_text(item, "UnitOfMeasurePrice") or 0),
                price_update_time=_text(item, "PriceUpdateTime"),
            )
        )
    return records


def _text(el: ET.Element, tag: str) -> str:
    child = el.find(tag)
    return child.text.strip() if child is not None and child.text else ""


# Official settlement code (סמל יישוב) for Kfar Saba, per the live Stores file.
KFAR_SABA_CITY_CODE = "6900"

# Fallback only, for when a Stores file isn't available: branches identified
# manually by reading Hebrew branch names on 2026-08-26, later confirmed
# (2026-08-27) to all carry City==6900 in the official Stores file. Prefer
# kfar_saba_stores(parse_stores_xml(...)) over this constant.
KFAR_SABA_STORE_IDS = {"144", "394", "615", "682", "752", "845"}


def kfar_saba_full_catalog_files(
    files: Iterable[PriceFile], store_ids: Iterable[str] = KFAR_SABA_STORE_IDS
) -> Iterator[PriceFile]:
    """Filter a file listing down to full-catalog files for the given stores.

    Pass the dynamic result of kfar_saba_stores(parse_stores_xml(...)) as
    store_ids; defaults to the manually-identified fallback set.
    """
    store_ids = set(store_ids)
    for f in files:
        if f.store_id in store_ids and f.category.lower() == "pricefull":
            yield f
