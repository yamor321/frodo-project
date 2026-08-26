"""Client for Israel's official price-controlled consumer products dataset.

Source: data.gov.il (CKAN open-data portal), dataset
"price_controlled_consumer_products". This is the machine-readable dataset
version of the Ministry of Economy/Agriculture's regulated-price list --
NOT the https://www.gov.il/.../food-price-control-search HTML page, which
sits behind Cloudflare and returned 403 to every plain HTTP request tried
(including its own internal `/he/api/DynamicCollector` endpoint). The
data.gov.il API has no such block and needs no browser.

Verified live 2026-08-27: plain `requests.get` -> HTTP 200, clean JSON,
391 records (full history, not just current price -- one row per price
change per product, back to 2007+ per the dataset description).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterator

import requests

API_URL = "https://data.gov.il/api/3/action/datastore_search"
RESOURCE_ID = "0a760550-0426-4eb7-acf6-2ee919bf12e7"
REQUEST_TIMEOUT = 20
PAGE_SIZE = 200


@dataclass
class ControlledPriceRecord:
    """One historical row from the dataset -- one price change for one product.

    retail_price/eilat_consumer_price can be None: older rows (pre-2016ish)
    published only the consumer price, per the source data (verified live).
    """

    product: str
    update_date: str  # as published, DD/MM/YYYY
    retail_price: float | None
    consumer_price: float
    eilat_consumer_price: float | None


def fetch_all_records() -> Iterator[ControlledPriceRecord]:
    """Page through the full dataset (verified: 391 records total)."""
    offset = 0
    while True:
        resp = requests.get(
            API_URL,
            params={"resource_id": RESOURCE_ID, "limit": PAGE_SIZE, "offset": offset},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        records = payload["result"]["records"]
        if not records:
            return
        for r in records:
            yield ControlledPriceRecord(
                product=r["product"],
                update_date=r["update date"],
                retail_price=_optional_float(r["retailer pricre without VAT"]),
                consumer_price=float(r["consumers price includes VAT"]),
                eilat_consumer_price=_optional_float(r["consumer price in Eilat"]),
            )
        offset += PAGE_SIZE


def _optional_float(value) -> float | None:
    return None if value is None else float(value)


def current_controlled_prices() -> list[ControlledPriceRecord]:
    """Collapse the full history down to the latest known price per product."""
    latest: dict[str, tuple[dt.date, ControlledPriceRecord]] = {}
    for rec in fetch_all_records():
        parsed_date = dt.datetime.strptime(rec.update_date, "%d/%m/%Y").date()
        prior = latest.get(rec.product)
        if prior is None or parsed_date > prior[0]:
            latest[rec.product] = (parsed_date, rec)
    return [rec for _date, rec in latest.values()]


# The dairy-relevant subset of the 22 controlled products, by exact "product"
# name as published (verified live 2026-08-27 -- pagination surfaces 22
# distinct products, one more than the "21 תוצאות" the HTML page's filter UI
# advertises: it also includes "חמאה רגילה"/butter, excluded here since the
# brief's own dairy list (section 4) names milk/white cheese/hard cheese/
# cream/eshel/gil but not butter). Eggs/bread/salt are excluded too -- out
# of scope for the dairy pilot.
DAIRY_PRODUCT_NAMES = {
    "חלב טרי בקרטון 1% שומן (רגיל)",
    "חלב טרי בקרטון 3% שומן (רגיל)",
    "חלב טרי בשקית 1% שומן (רגיל)",
    "חלב טרי בשקית 3% שומן (רגיל)",
    "גבינה לבנה 5%",
    "גבינה חצי קשה עמק (רגילה) 28% שומן",
    "גבינה חצי קשה גלבוע 22% שומן",
    "אשל 4.5% שומן",
    "גיל 3% שומן",
    "שמנת חמוצה 15% שומן רגילה",
    "שמנת מתוקה 38% שומן",
}


def current_dairy_controlled_prices() -> list[ControlledPriceRecord]:
    """Current controlled prices, filtered to the dairy pilot's product set."""
    return [r for r in current_controlled_prices() if r.product in DAIRY_PRODUCT_NAMES]
