"""Renders site/product/{barcode}/index.html -- one product compared across
every branch that carries it (brief section 3: the actual cross-branch
comparison, at full resolution, not just the min/max used for the spread
list). `from_store_id` highlights the branch the visitor drilled down from.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape

from etl.scrapers.shufersal import PriceRecord

PRODUCT_CSS = """
.pricelist{ display:flex; flex-direction:column; gap:10px; margin:20px 0; }
.prow{ display:flex; justify-content:space-between; align-items:center; padding:14px 18px;
  background:var(--paper-raised); border:1px solid var(--line); border-radius:10px; }
.prow.highlight{ border-color:var(--navy); box-shadow:0 0 0 2px var(--navy-soft); }
.prow .store{ font-weight:600; }
.prow .store small{ display:block; font-weight:400; color:var(--ink-muted); font-size:.78rem; margin-top:2px; }
.prow .price{ font-family:'IBM Plex Mono',monospace; font-size:1.1rem; font-variant-numeric:tabular-nums; }
"""


@dataclass
class StorePrice:
    store_id: str
    store_name: str
    price: float


def collect_store_prices(
    catalogs_by_store: dict[str, list[PriceRecord]], item_code: str, store_names: dict[str, str]
) -> list[StorePrice]:
    prices = []
    for store_id, records in catalogs_by_store.items():
        for r in records:
            if r.item_code == item_code and r.item_price > 0:
                prices.append(StorePrice(store_id, store_names.get(store_id, store_id), r.item_price))
                break
    return prices


def render_product_html(
    item_code: str,
    item_name: str,
    store_prices: list[StorePrice],
    from_store_id: str | None = None,
) -> str:
    from etl.render.layout import page_shell

    ordered = sorted(store_prices, key=lambda sp: sp.price)
    cheapest = ordered[0] if ordered else None
    priciest = ordered[-1] if ordered else None
    # A tie at the min (or max) is still the min (or max) -- tag every store
    # that matches the price, not just whichever sorted first. If every
    # store has the same price there's no meaningful "cheapest"/"priciest"
    # distinction, so skip both tags rather than mark everything both ways.
    same_price_everywhere = bool(cheapest and priciest and cheapest.price == priciest.price)

    rows = []
    for sp in ordered:
        cls = "prow highlight" if sp.store_id == from_store_id else "prow"
        tag = ""
        if not same_price_everywhere and cheapest and sp.price == cheapest.price:
            tag = ' <span class="chip good">הכי זול</span>'
        elif not same_price_everywhere and priciest and sp.price == priciest.price:
            tag = ' <span class="chip warm">הכי יקר</span>'
        rows.append(
            f"""
    <div class="{cls}">
      <span class="store">{escape(sp.store_name)}{tag}<small><a href="/frodo-project/store/{sp.store_id}/">לדף הסניף</a></small></span>
      <span class="price ltr">₪{sp.price:.2f}</span>
    </div>"""
        )

    spread_line = ""
    if cheapest and priciest and cheapest.price > 0 and cheapest.store_id != priciest.store_id:
        pct = (priciest.price - cheapest.price) / cheapest.price * 100
        spread_line = f'<p class="lede">פער של <b>{pct:.0f}%</b> בין הזול ליקר ביותר, על אותו ברקוד בדיוק, ב-{len(ordered)} סניפים.</p>'

    body = f"""
  <div class="kicker">Frodo Project · דף מוצר</div>
  <h1>{escape(item_name)}</h1>
  {spread_line}
  <div class="pricelist">{''.join(rows)}</div>
"""

    return page_shell(f"{item_name} — Frodo Project", "map", body, f"<style>{PRODUCT_CSS}</style>")
