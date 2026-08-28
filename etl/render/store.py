"""Renders site/store/{id}/index.html -- one page per branch: the products
where this store is notably the cheapest or priciest relative to the other
branches for the exact same barcode (brief section 3 drill-down target from
the map), plus a real client-side search over everything this store sells.
"""
from __future__ import annotations

import json
from html import escape

from etl.enrich.geocode import GeoPoint
from etl.scoring.cross_branch_spread import SpreadResult
from etl.scoring.store_ranking import StoreScore
from etl.scrapers.shufersal import PriceRecord

STORE_CSS = """
.navrow{ display:flex; gap:10px; flex-wrap:wrap; margin:-6px 0 22px; }
.navbtn{ font-family:'Assistant',sans-serif; font-weight:700; font-size:.85rem; padding:8px 16px;
  border-radius:999px; border:1.5px solid var(--navy); background:var(--navy-soft); color:var(--navy);
  text-decoration:none; display:inline-flex; align-items:center; gap:6px; }
.navbtn:hover{ background:var(--navy); color:#fff; }
.storecard{ display:flex; flex-wrap:wrap; gap:8px 22px; align-items:baseline; margin:18px 0 30px;
  padding:14px 18px; background:var(--paper-raised); border:1px solid var(--line); border-radius:10px; }
.storecard .score{ font-family:'IBM Plex Mono',monospace; font-size:.9rem; }
h2.section-title{ font-size:1.15rem; margin:40px 0 6px; }
p.section-sub{ color:var(--ink-muted); font-size:.9rem; margin:0 0 16px; }
section.list{ display:flex; flex-direction:column; gap:12px; }
.card.spread{ display:flex; align-items:center; gap:14px; flex-wrap:wrap; }
.card.spread .info{ display:flex; align-items:center; gap:12px; flex:1; min-width:0; }
.card.spread .name{ font-weight:600; font-size:.98rem; }
.card.spread .name small{ display:block; color:var(--ink-muted); font-weight:400; font-size:.78rem; margin-top:2px; }
.card.spread .prices{ font-family:'IBM Plex Mono',monospace; font-size:.95rem; white-space:nowrap; margin-inline-start:auto; }
#searchBox{ width:100%; font-family:'Assistant',sans-serif; font-size:1rem; padding:12px 16px;
  border:1.5px solid var(--line); border-radius:10px; background:var(--paper-raised); color:var(--ink); margin-bottom:14px; }
#searchResults{ display:flex; flex-direction:column; gap:8px; max-height:420px; overflow-y:auto; }
.searchrow{ display:flex; justify-content:space-between; padding:9px 14px; background:var(--paper-raised);
  border:1px solid var(--line); border-radius:8px; font-size:.92rem; }
.searchrow .p{ font-family:'IBM Plex Mono',monospace; font-variant-numeric:tabular-nums; }
#searchHint{ font-size:.85rem; color:var(--ink-muted); }
"""


def top_deals(
    spreads: list[SpreadResult], store_id: str, top_n: int = 8
) -> tuple[list[SpreadResult], list[SpreadResult]]:
    """The same (best, worst) slice used for display -- shared with the
    build script so it knows exactly which product pages are actually
    linked from a store page, instead of guessing separately."""
    best_deals = sorted(
        [s for s in spreads if s.cheap_store_id == store_id], key=lambda s: -s.spread_pct
    )[:top_n]
    worst_deals = sorted(
        [s for s in spreads if s.expensive_store_id == store_id], key=lambda s: -s.spread_pct
    )[:top_n]
    return best_deals, worst_deals


def _deal_card(
    s: SpreadResult, this_store_id: str, this_store_is_cheap: bool, image_urls: dict[str, str | None]
) -> str:
    from etl.render.layout import thumb_html

    this_price = s.cheap_price if this_store_is_cheap else s.expensive_price
    other_name = s.expensive_store_name if this_store_is_cheap else s.cheap_store_name
    other_price = s.expensive_price if this_store_is_cheap else s.cheap_price
    chip_class = "good" if this_store_is_cheap else "warm"
    sign = "-" if this_store_is_cheap else "+"
    return f"""
    <div class="card spread">
      <div class="info">
        {thumb_html(image_urls.get(s.item_code), s.item_name)}
        <div class="name"><a href="/frodo-project/product/{s.item_code}/">{escape(s.item_name)}</a><small>לעומת {escape(other_name)}: ₪{other_price:.2f}</small></div>
      </div>
      <div class="prices">₪{this_price:.2f} <span class="chip {chip_class}">{sign}{s.spread_pct*100:.0f}%</span></div>
    </div>"""


def render_store_html(
    store_id: str,
    store_name: str,
    score: StoreScore | None,
    spreads: list[SpreadResult],
    catalog: list[PriceRecord],
    coords: GeoPoint | None = None,
    image_urls: dict[str, str | None] | None = None,
    top_n: int = 8,
) -> str:
    from etl.render.layout import page_shell

    image_urls = image_urls or {}
    best_deals, worst_deals = top_deals(spreads, store_id, top_n)

    nav_html = ""
    if coords is not None:
        waze_url = f"https://waze.com/ul?ll={coords.lat},{coords.lon}&navigate=yes"
        gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={coords.lat},{coords.lon}"
        nav_html = f"""
  <div class="navrow">
    <a class="navbtn" href="{waze_url}" target="_blank" rel="noopener">🧭 נווט בוויז</a>
    <a class="navbtn" href="{gmaps_url}" target="_blank" rel="noopener">נווט בגוגל מפות</a>
  </div>"""

    search_items = [
        {"name": r.item_name, "price": r.item_price, "code": r.item_code}
        for r in catalog
        if r.item_price > 0
    ]
    search_json = json.dumps(search_items, ensure_ascii=False)

    score_html = (
        f'<span class="score">ציון: {score.avg_percentile:.2f} מתוך 1 (0=זול ביותר) · {score.items_compared:,} מוצרים משותפים</span>'
        if score
        else ""
    )

    best_html = "\n".join(_deal_card(s, store_id, True, image_urls) for s in best_deals) or "<p>אין עדיין מספיק נתונים.</p>"
    worst_html = "\n".join(_deal_card(s, store_id, False, image_urls) for s in worst_deals) or "<p>אין עדיין מספיק נתונים.</p>"

    body = f"""
  <div class="kicker">Frodo Project · דף סניף</div>
  <h1>{escape(store_name)}</h1>{nav_html}
  <div class="storecard">{score_html}</div>

  <h2 class="section-title">הכי משתלם כאן</h2>
  <p class="section-sub">מוצרים שהמחיר בסניף הזה נמוך משמעותית לעומת סניפים אחרים, על אותו ברקוד בדיוק.</p>
  <section class="list">{best_html}</section>

  <h2 class="section-title">הכי יקר כאן</h2>
  <p class="section-sub">מוצרים שהמחיר בסניף הזה גבוה משמעותית לעומת סניפים אחרים, על אותו ברקוד בדיוק.</p>
  <section class="list">{worst_html}</section>

  <h2 class="section-title">חיפוש מוצר בסניף הזה</h2>
  <input id="searchBox" type="text" placeholder="הקלד שם מוצר, למשל חלב או שוקולד..." autocomplete="off">
  <div id="searchHint">{len(search_items):,} מוצרים בקטלוג הסניף</div>
  <div id="searchResults"></div>
"""

    extra_head = f"<style>{STORE_CSS}</style>"
    extra_script = f"""<script>
(function(){{
  const items = {search_json};
  const box = document.getElementById("searchBox");
  const results = document.getElementById("searchResults");
  const hint = document.getElementById("searchHint");

  function render(query){{
    if (!query || query.length < 2){{
      results.innerHTML = "";
      hint.textContent = `{len(search_items):,} מוצרים בקטלוג הסניף`;
      return;
    }}
    const q = query.trim();
    const matches = items.filter(it => it.name.includes(q)).slice(0, 40);
    hint.textContent = `${{matches.length}} תוצאות (מוצג עד 40)`;
    results.innerHTML = matches.map(it =>
      `<div class="searchrow"><span>${{it.name}}</span><span class="p">₪${{it.price.toFixed(2)}}</span></div>`
    ).join("");
  }}

  box.addEventListener("input", (e)=> render(e.target.value));
}})();
</script>"""

    return page_shell(f"{store_name} — Frodo Project", "map", body, extra_head, extra_script)
