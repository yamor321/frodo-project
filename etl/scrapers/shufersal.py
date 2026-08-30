"""Client for Shufersal's price-transparency portal.

Lists, downloads, and parses the Store/Price/PriceFull files Shufersal is
legally required to publish (see ../../docs/sources.md for the regulation
and verified portal details).

Portal: https://prices.shufersal.co.il/ -- confirmed to require no login.
"""
from __future__ import annotations

import datetime as dt
import gzip
import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Iterable, Iterator

import requests
from bs4 import BeautifulSoup

from etl.concurrency import fetch_concurrently

BASE_URL = "https://prices.shufersal.co.il/"
REQUEST_TIMEOUT = 20
LISTING_BATCH_SIZE = 8


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


def _fetch_listing_page(session: requests.Session, page: int) -> list["PriceFile"]:
    resp = session.get(
        BASE_URL,
        params={"page": page, "sort": "Branch", "sortdir": "ASC"},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return list(_parse_listing_page(resp.text))


def list_files(max_pages: int = 200) -> Iterator[PriceFile]:
    """Walk the portal's file-listing table and yield every row found.

    No query-string filter for store/category was found on the live portal
    (checked: ?code=, ?store=, ?storeId=, ?category=, ?fileType=, ?type= all
    no-op). The table *does* support deterministic sorting via
    ?sort=Branch&sortdir=ASC, so this walks every page in that order and lets
    callers filter client-side. A page with zero rows ends the walk.

    Pages are independent GETs (page N doesn't depend on page N-1's
    content), so they're fetched LISTING_BATCH_SIZE at a time instead of one
    at a time -- measured live at ~3s/page, a full walk (the portal lists
    every store nationwide, not just Kfar Saba, so this can run to hundreds
    of pages) was taking 10+ minutes fetched sequentially. Results still
    come out in page order; the walk stops at the first page in that order
    with zero rows, same as before.
    """
    session = requests.Session()
    page = 1
    while page <= max_pages:
        batch = list(range(page, min(page + LISTING_BATCH_SIZE, max_pages + 1)))
        results = fetch_concurrently(
            [lambda p=p: _fetch_listing_page(session, p) for p in batch],
            max_workers=LISTING_BATCH_SIZE,
        )
        for rows in results:
            if not rows:  # empty page, or a failed fetch (None) -- either ends the walk
                return
            yield from rows
        page += LISTING_BATCH_SIZE


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
    # "1" = physical branch, "2" = non-physical (online/pickup/fulfillment) --
    # verified live 2026-08-30 across 826 stores, 7 chains, 4 independent
    # platforms, zero exceptions. Documented in this schema comment since
    # 2026-08-27 but never actually parsed until now -- see
    # kfar_saba_stores_with_online() below for how it's used.
    store_type: str = ""


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
                    store_type=_text(store, "StoreType"),
                )
            )
    return records


KFAR_SABA_CITY_NAMES = {"כפר סבא", "כפר-סבא"}


def kfar_saba_stores(stores: Iterable[StoreRecord]) -> set[str]:
    """Store IDs identifying Kfar Saba, from the City field or (as a last
    resort) the store's own name.

    Objective, data-driven replacement for KFAR_SABA_STORE_IDS below (which
    was identified by manually reading Hebrew branch names) -- verified live
    2026-08-27: all 6 manually-identified Shufersal branches carry
    City=="6900" (the official settlement code). Carrefour's Stores file
    uses the same numeric convention.

    Not every chain does, though -- verified live 2026-08-28: Victory's own
    Stores file puts the literal city NAME ("כפר סבא") in this field
    instead of the settlement code, which silently returned zero matches
    until this was caught. Matching both forms here (rather than picking
    one and hoping) is what makes this function actually chain-agnostic,
    instead of coincidentally working for the two chains it happened to be
    written against.

    A third gap, confirmed live 2026-08-29 by reading the real Stores.xml
    (not a web search): Yohananof (store 024) and Keshet (store 019) both
    publish City=="0" -- checked directly, not assumed: that's a clear
    placeholder, not a real settlement code (which would never be "0"), so
    it carries no usable signal at all. Their StoreName is the literal,
    exact string "כפר סבא" though, same as branches this function already
    recognizes by City. Only when City is one of the known placeholder
    values does this fall back to an EXACT match on the store's own name
    (not a substring check -- "כפר סבא" appearing inside a longer
    promotional name wouldn't mean the store is actually there, and a
    store with a real, different, non-placeholder City code should never
    be pulled in just because of its name).
    """
    UNUSABLE_CITY_CODES = {"", "0", "unknown"}
    matches = set()
    for s in stores:
        if s.city_code == KFAR_SABA_CITY_CODE or s.city_code in KFAR_SABA_CITY_NAMES:
            matches.add(s.store_id)
        elif s.city_code in UNUSABLE_CITY_CODES and s.store_name.strip() in KFAR_SABA_CITY_NAMES:
            matches.add(s.store_id)
    return matches


def online_stores(stores: Iterable[StoreRecord]) -> set[str]:
    """Store IDs marked non-physical (StoreType=="2") -- see StoreRecord's
    docstring for the live verification behind this. Chain-agnostic, no city
    logic; a chain publishing this store nationally, unrelated to Kfar Saba,
    is exactly as findable here as one that happens to be local."""
    return {s.store_id for s in stores if s.store_type == "2"}


def kfar_saba_stores_with_online(stores: Iterable[StoreRecord]) -> set[str]:
    """kfar_saba_stores(), extended with a chain's online branch when it has
    exactly one nationally.

    Carrefour's online stores (471/473) already show up on the site today --
    but only by accident: their <City> happens to equal Kfar Saba's own code,
    the same filter used for physical branches, not because anything
    recognizes "online" as a category. Verified live 2026-08-30: most chains
    that publish a StoreType=="2" row publish exactly ONE nationally
    (Shufersal, Rami Levy, Yohananof) -- for those, this union is what makes
    that store findable at all, since a national online store has no reason
    to carry Kfar Saba's own city code (Shufersal's online store 413 carries
    City=="7900", nowhere close). Gated on already having a real physical
    presence (`physical`) so this never pulls in a chain with no Kfar Saba
    branch at all.

    Deliberately NOT unioned when a chain publishes more than one
    StoreType=="2" row (`len(online) == 1` check): Tiv Taam publishes SEVEN
    ("ליקוט <city>", one per regional hub, none tagged Kfar Saba) -- with no
    single objective winner among seven, including all of them would flood
    Kfar Saba's own leaderboard/branches list with rows labeled by other
    cities. Left out of v1 on purpose, not forgotten (see docs/sources.md) --
    if a chain ever consolidates to one national online store, it starts
    showing up here with no code change.

    Carrefour itself is unaffected by this function: it has THREE
    StoreType=="2" rows nationally (471, 473, and 472 elsewhere), so the
    len==1 gate never fires for it -- it keeps showing 471/473 exactly as
    before, through the existing city-code match alone."""
    physical = kfar_saba_stores(stores)
    if not physical:
        return physical
    online = online_stores(stores)
    return physical | online if len(online) == 1 else physical


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
                is_weighted=_text(item, "bIsWeighted", "blsWeighted") == "1",
                qty_in_package=_text(item, "QtyInPackage"),
                item_price=float(_text(item, "ItemPrice") or 0),
                unit_of_measure_price=float(_text(item, "UnitOfMeasurePrice") or 0),
                price_update_time=_text(item, "PriceUpdateTime"),
            )
        )
    return records


def _text(el: ET.Element, *tags: str) -> str:
    """Read the first present tag's text, trying each in order.

    Multi-tag support exists for one confirmed real-world quirk: Wolt
    Market's own PriceFull files (verified live 2026-08-30) spell the
    weighted-item flag <blsWeighted> (lowercase L) where every other chain's
    schema spells it <bIsWeighted> (capital I). Every other field name
    matches Shufersal's schema exactly, so this stays the one shared parser
    instead of forking a Wolt-specific copy."""
    for tag in tags:
        child = el.find(tag)
        if child is not None and child.text:
            return child.text.strip()
    return ""


# Official settlement code (סמל יישוב) for Kfar Saba, per the live Stores file.
KFAR_SABA_CITY_CODE = "6900"

# Fallback only, for when a Stores file isn't available: branches identified
# manually by reading Hebrew branch names on 2026-08-26, later confirmed
# (2026-08-27) to all carry City==6900 in the official Stores file. Prefer
# kfar_saba_stores(parse_stores_xml(...)) over this constant.
#
# "413" ("שופרסל ONLINE", the chain's national online store) added
# 2026-08-30 for the same reason Carrefour's own online stores are already
# in its equivalent constant -- a real bug caught with Victory's own online
# store (etl/scrapers/victory.py) showed that a fallback constant missing a
# newly-added online id silently drops that store's page the next time
# fallback is the only thing that finds it, even though Shufersal itself
# (unlike Victory) is reliably reachable and rarely needs this path at all.
KFAR_SABA_STORE_IDS = {"144", "394", "413", "615", "682", "752", "845"}


def kfar_saba_full_catalog_files(
    files: Iterable[PriceFile], store_ids: Iterable[str] = KFAR_SABA_STORE_IDS, category: str = "pricefull"
) -> Iterator[PriceFile]:
    """Filter a file listing down to the latest full-catalog file per store.

    Pass the dynamic result of kfar_saba_stores(parse_stores_xml(...)) as
    store_ids; defaults to the manually-identified fallback set.

    `category` defaults to "pricefull" (every existing caller relies on
    this default, unchanged) -- pass "promofull" to select promo files
    instead, reusing the exact same "latest file per store, by filename
    timestamp" logic rather than duplicating it.

    Some chains (verified live for Carrefour, 2026-08-28: stores 471/473
    each published two full PriceFull snapshots on the same day) publish
    more than one PriceFull per store per day -- always keep the latest by
    the timestamp embedded in the filename, not just the first/last one
    encountered in listing order.
    """
    store_ids = set(store_ids)
    latest: dict[str, PriceFile] = {}
    for f in files:
        if f.store_id not in store_ids or f.category.lower() != category:
            continue
        if f.store_id not in latest or f.filename > latest[f.store_id].filename:
            latest[f.store_id] = f
    yield from latest.values()


@dataclass
class PromoItem:
    """One <PromotionItem> inside a <Promotion>'s <Groups>."""

    item_code: str
    min_qty: float
    discount_rate: float
    discounted_price: float


@dataclass
class PromoRecord:
    """One <Promotion>, normalized. A single promotion can cover several
    item_codes (via items) -- unlike PriceRecord, which is already
    one-row-per-item_code, a promotion is one-row-per-deal.

    Real schema (verified live 2026-08-30, store 144): Root > Promotions >
    Promotion > Groups > Group > PromotionItems > PromotionItem -- nested,
    unlike PriceFull's flat Items > Item. A promotion's items are
    flattened across all its Groups into this record's `items` list;
    Groups exist in the source (each with its own DiscountType) but
    nothing here has per-group semantics to preserve yet.
    """

    chain_id: str
    subchain_id: str
    store_id: str
    promotion_id: str
    description: str
    start_datetime: str
    end_datetime: str
    club_id: str
    is_coupon: bool
    is_gift_item: bool
    items: list[PromoItem] = field(default_factory=list)


def parse_promo_xml(xml_bytes: bytes) -> list[PromoRecord]:
    """Parse a Promo/PromoFull XML payload into normalized records."""
    root = ET.fromstring(xml_bytes)
    chain_id = _text(root, "ChainID")
    subchain_id = _text(root, "SubChainID")
    store_id = _text(root, "StoreID")

    promotions_el = root.find("Promotions")
    if promotions_el is None:
        return []

    records = []
    for promo in promotions_el.findall("Promotion"):
        items = []
        for group in promo.findall("./Groups/Group"):
            for pi in group.findall("./PromotionItems/PromotionItem"):
                items.append(
                    PromoItem(
                        item_code=_text(pi, "ItemCode"),
                        min_qty=float(_text(pi, "MinQty") or 0),
                        discount_rate=float(_text(pi, "DiscountRate") or 0),
                        discounted_price=float(_text(pi, "DiscountedPrice") or 0),
                    )
                )
        records.append(
            PromoRecord(
                chain_id=chain_id,
                subchain_id=subchain_id,
                store_id=store_id,
                promotion_id=_text(promo, "PromotionID"),
                description=_text(promo, "PromotionDescription"),
                start_datetime=_text(promo, "PromotionStartDateTime"),
                end_datetime=_text(promo, "PromotionEndDateTime"),
                club_id=_text(promo, "ClubID"),
                is_coupon=_text(promo, "AdditionalIsCoupon") == "1",
                is_gift_item=_text(promo, "IsGiftItem") not in ("", "0"),
                items=items,
            )
        )
    return records


_PROMO_DT_FORMATS = ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S")


def _parse_promo_dt(value: str) -> dt.datetime | None:
    for fmt in _PROMO_DT_FORMATS:
        try:
            return dt.datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def is_simple_active_promo(promo: PromoRecord, today: dt.date) -> bool:
    """True only for a promotion any shopper can get today -- no coupon,
    no club-card restriction, no minimum-quantity/bundle requirement.

    Verified live 2026-08-30 across 5,284 real promotions (5 Kfar Saba
    Shufersal stores): 52.8% pass this exact check ("simple_active_
    universal"), 39.6% are gift/bundle deals, 7.0% require a coupon, 0.6%
    are club-restricted -- not a negligible slice, worth building on. The
    club_id.startswith("0") check specifically was verified against the
    real sentinel values seen: "0 - כלל הלקוחות" (all customers) covered
    5,250 of 5,284 promotions; every other value seen was a specific named
    club, never another all-customers spelling. is_gift_item lives at the
    Promotion level in the real schema (not per-item) -- confirmed live,
    not assumed.

    Deliberately excludes coupon-gated, club-gated, and bundle/gift-only
    promos from v1 -- not because they're not real promotions, but because
    showing "cheaper!" to a shopper who then can't actually get that price
    at checkout (no coupon, no club card, wrong quantity) would be worse
    than not showing anything. Not built, deliberately, not forgotten --
    see docs/sources.md.

    This function alone is NOT sufficient to decide a promo is really
    worth showing -- see compute_active_promos() in etl/scoring/
    active_promos.py, which additionally requires the discounted price to
    actually be lower than that item's real PriceFull price. The same
    live survey found ~30% of "simple" promos (by this function's
    criteria alone) do NOT show a real discount once cross-checked against
    the regular shelf price -- likely stale promo metadata vs. an
    already-updated shelf price. The cross-check is a required filter,
    not an optional validation step.
    """
    start = _parse_promo_dt(promo.start_datetime)
    end = _parse_promo_dt(promo.end_datetime)
    if start is None or end is None or not (start.date() <= today <= end.date()):
        return False
    if not promo.club_id.strip().startswith("0"):
        return False
    if promo.is_coupon or promo.is_gift_item:
        return False
    return True


def simple_promo_item_prices(promo: PromoRecord) -> dict[str, float]:
    """item_code -> discounted_price, restricted to line items that are
    themselves simple (min_qty<=1, a real positive discounted price) --
    a promo can pass is_simple_active_promo() at the header level but
    still bundle one weird line item alongside simple ones."""
    return {i.item_code: i.discounted_price for i in promo.items if i.min_qty <= 1 and i.discounted_price > 0}
