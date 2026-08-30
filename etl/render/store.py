"""Renders site/store/{id}/index.html -- one page per branch: the products
where this store is notably the cheapest or priciest relative to the other
branches for the exact same barcode (brief section 3 drill-down target from
the map), plus a real client-side search over everything this store sells.
"""
from __future__ import annotations

from html import escape

from etl.enrich.geocode import GeoPoint
from etl.scoring.active_promos import ActivePromo, format_promo_end_date
from etl.scoring.cross_branch_spread import SpreadResult
from etl.scoring.store_ranking import StoreScore
from etl.scrapers.shufersal import PriceRecord

STORE_CSS = """
.store-address{ color:var(--ink-muted); font-size:.95rem; margin:-8px 0 14px; }
.navrow{ display:flex; gap:10px; flex-wrap:wrap; margin:-6px 0 22px; }
.navbtn{ font-family:'Assistant',sans-serif; font-weight:700; font-size:.85rem; padding:8px 16px;
  border-radius:999px; border:1.5px solid var(--navy); background:var(--navy-soft); color:var(--navy);
  text-decoration:none; display:inline-flex; align-items:center; gap:6px; }
.navbtn:hover{ background:var(--navy); color:#fff; }
.storecard{ display:flex; flex-wrap:wrap; gap:8px 22px; align-items:baseline; margin:18px 0 30px;
  padding:14px 18px; background:var(--paper-raised); border:1px solid var(--line); border-radius:10px; }
.storecard .score{ font-family:'Assistant',sans-serif; font-size:.9rem; }
h2.section-title{ font-size:1.15rem; margin:40px 0 6px; }
p.section-sub{ color:var(--ink-muted); font-size:.9rem; margin:0 0 16px; }
section.list{ display:flex; flex-direction:column; gap:12px; }
.card.spread{ display:flex; align-items:center; gap:14px; flex-wrap:wrap; }
.card.spread .info{ display:flex; align-items:center; gap:12px; flex:1; min-width:0; }
.card.spread .name{ font-weight:600; font-size:.98rem; }
.card.spread .name small{ display:block; color:var(--ink-muted); font-weight:400; font-size:.78rem; margin-top:2px; }
.card.spread .prices{ font-weight:700; font-size:1rem; white-space:nowrap; margin-inline-start:auto; }
#searchBox{ width:100%; font-family:'Assistant',sans-serif; font-size:1rem; padding:12px 16px;
  border:1.5px solid var(--line); border-radius:10px; background:var(--paper-raised); color:var(--ink); margin-bottom:14px; }
#searchResults{ display:flex; flex-direction:column; gap:8px; max-height:420px; overflow-y:auto; }
.searchrow{ display:flex; justify-content:space-between; gap:12px; padding:9px 14px; background:var(--paper-raised);
  border:1px solid var(--line); border-radius:8px; font-size:.92rem; }
.searchrow .name{ min-width:0; }
.searchrow .p{ font-weight:600; font-variant-numeric:tabular-nums; white-space:nowrap; }
#searchHint{ font-size:.85rem; color:var(--ink-muted); }
"""


def store_search_items(catalog: list[PriceRecord]) -> list[dict]:
    """The lean {name, price, code} shape used by this store's catalog
    search -- shared with the build scripts so the exact same filter
    (item_price > 0) produces both the count shown in render_store_html()
    and the site/store/{id}/catalog.json file the search box fetches."""
    return [
        {"name": r.item_name, "price": r.item_price, "code": r.item_code}
        for r in catalog
        if r.item_price > 0
    ]


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
    s: SpreadResult,
    this_store_id: str,
    this_store_is_cheap: bool,
    image_urls: dict[str, str | None],
    base_path: str = "/frodo-project",
    active_promo: ActivePromo | None = None,
) -> str:
    from etl.render.layout import thumb_html

    this_price = s.cheap_price if this_store_is_cheap else s.expensive_price
    other_name = s.expensive_store_name if this_store_is_cheap else s.cheap_store_name
    other_price = s.expensive_price if this_store_is_cheap else s.cheap_price
    chip_class = "good" if this_store_is_cheap else "warm"
    sign = "-" if this_store_is_cheap else "+"
    # &from= lets the product page highlight the row for the store the
    # visitor drilled down from (see .prow.highlight in etl/render/product.py).
    product_url = f"{base_path}/product/?code={s.item_code}&from={this_store_id}"

    # Real confirmed sale price (see etl/scoring/active_promos.py) --
    # regular price struck through, promo price highlighted, end date
    # shown per explicit user request ("אם יש תוקף של המבצעים זה יהיה
    # מעולה"). Shufersal only, v1 -- see docs/sources.md.
    if active_promo is not None:
        end_label = format_promo_end_date(active_promo.end_datetime)
        end_html = f" עד {end_label}" if end_label else ""
        price_html = (
            f'<span class="ltr" style="text-decoration:line-through;color:var(--ink-muted);font-weight:400;">₪{this_price:.2f}</span> '
            f'<span class="ltr">₪{active_promo.discounted_price:.2f}</span> '
            f'<span class="chip good">מבצע{end_html}</span>'
        )
    else:
        price_html = f"₪{this_price:.2f}"

    return f"""
    <div class="card spread">
      <div class="info">
        {thumb_html(image_urls.get(s.item_code), s.item_name)}
        <div class="name"><a href="{product_url}">{escape(s.item_name)}</a><small>לעומת {escape(other_name)}: ₪{other_price:.2f}</small></div>
      </div>
      <div class="prices">{price_html} <span class="chip {chip_class}">{sign}{s.spread_pct*100:.0f}%</span></div>
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
    as_of_date: str | None = None,
    address: str | None = None,
    base_path: str = "/frodo-project",
    is_online: bool = False,
    active_promos: dict[str, ActivePromo] | None = None,
) -> str:
    from etl.render.layout import ESC_HTML_JS, page_shell

    image_urls = image_urls or {}
    best_deals, worst_deals = top_deals(spreads, store_id, top_n)

    stale_html = ""
    if as_of_date:
        # Set only when this run's own live collection for this chain
        # failed and these are the most recent prices this project actually
        # has instead (see etl/raw_snapshot_fallback.py) -- never silently
        # presented as freshly collected, per this project's honesty-in-
        # labeling principle. Phrased to stay accurate whether as_of_date is
        # an earlier day OR earlier today (the daily workflow can run
        # several times a day) -- "source unavailable today" would
        # self-contradict when as_of_date IS today's date.
        stale_html = f'<div style="margin:-10px 0 18px;"><span class="chip warm">המחירים כאן מהאיסוף האחרון שהצליח, {escape(as_of_date)} — הריצה הנוכחית לא הצליחה לרענן אותם</span></div>'

    nav_html = ""
    if coords is not None:
        waze_url = f"https://waze.com/ul?ll={coords.lat},{coords.lon}&navigate=yes"
        gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={coords.lat},{coords.lon}"
        nav_html = f"""
  <div class="navrow">
    <a class="navbtn" href="{waze_url}" target="_blank" rel="noopener">🧭 נווט בוויז</a>
    <a class="navbtn" href="{gmaps_url}" target="_blank" rel="noopener">נווט בגוגל מפות</a>
  </div>"""

    search_items_count = len(store_search_items(catalog))

    score_html = (
        f'<span class="score">מדד חיסכון: {100 - round(score.avg_percentile*100)} מתוך 100 (ככל שגבוה יותר -- זול יותר) · {score.items_compared:,} מוצרים משותפים</span>'
        if score
        else ""
    )

    active_promos = active_promos or {}
    best_html = "\n".join(
        _deal_card(s, store_id, True, image_urls, base_path, active_promos.get(s.item_code)) for s in best_deals
    ) or "<p>אין עדיין מספיק נתונים.</p>"
    worst_html = "\n".join(
        _deal_card(s, store_id, False, image_urls, base_path, active_promos.get(s.item_code)) for s in worst_deals
    ) or "<p>אין עדיין מספיק נתונים.</p>"

    address_html = f'<p class="store-address">{escape(address)}</p>' if address else ""

    # Informational, not a warning (unlike stale_html above) -- shown
    # whenever the chain's own Stores.xml marks this store StoreType=="2"
    # (see shufersal.online_stores()), regardless of whether it happens to
    # have geocodable coordinates. A real address (Wolt Market's Kfar Saba
    # branch) still gets nav buttons above -- this chip is what makes clear
    # that's a delivery/pickup point, not a walk-in storefront.
    online_html = (
        '<div style="margin:-10px 0 18px;"><span class="chip neutral">סניף אונליין בלבד — משלוחים/איסוף, אין כניסה פיזית לקונים</span></div>'
        if is_online
        else ""
    )

    body = f"""
  <div class="kicker">Frodo Project · דף סניף</div>
  <h1>{escape(store_name)}</h1>
  {address_html}{nav_html}
  {online_html}
  {stale_html}
  <div class="storecard">{score_html}</div>

  <h2 class="section-title">הכי משתלם כאן</h2>
  <p class="section-sub">מוצרים שהמחיר בסניף הזה נמוך משמעותית לעומת סניפים אחרים, על אותו ברקוד בדיוק.</p>
  <section class="list">{best_html}</section>

  <h2 class="section-title">הכי יקר כאן</h2>
  <p class="section-sub">מוצרים שהמחיר בסניף הזה גבוה משמעותית לעומת סניפים אחרים, על אותו ברקוד בדיוק.</p>
  <section class="list">{worst_html}</section>

  <h2 class="section-title">חיפוש מוצר בסניף הזה</h2>
  <input id="searchBox" type="text" placeholder="הקלד שם מוצר, למשל חלב או שוקולד..." autocomplete="off" aria-label="חיפוש מוצר בקטלוג הסניף">
  <div id="searchHint" aria-live="polite">{search_items_count:,} מוצרים בקטלוג הסניף</div>
  <div id="searchResults" aria-live="polite"></div>
"""

    extra_head = f"<style>{STORE_CSS}</style>"
    # The full catalog (up to ~9,000 items, ~800KB for the biggest stores)
    # is fetched from site/store/{id}/catalog.json lazily on first keystroke
    # instead of being embedded in the page -- every visitor was downloading
    # the entire catalog up front before, whether or not they ever used the
    # search box. Same fetch-on-interaction pattern as the global search
    # (layout.py's GLOBAL_SEARCH_SCRIPT) and /branches/'s search.
    extra_script = f"""<script>
(function(){{
  const BASE = "{base_path}";
  let items = [];
  let itemsLoaded = false;
  const box = document.getElementById("searchBox");
  const results = document.getElementById("searchResults");
  const hint = document.getElementById("searchHint");
  const defaultHint = "{search_items_count:,} מוצרים בקטלוג הסניף";

  {ESC_HTML_JS}

  function ensureLoaded(cb){{
    if (itemsLoaded) {{ cb(); return; }}
    // itemsLoaded (not items itself) marks success -- on a failed fetch
    // items stays [] but itemsLoaded stays false, so the next keystroke
    // retries instead of permanently showing zero results for the rest
    // of the page's life after one transient network hiccup.
    fetch(BASE + "/store/{store_id}/catalog.json").then(r=>r.json()).then(data=>{{ items = data; itemsLoaded = true; cb(); }}).catch(()=>{{ cb(); }});
  }}

  function render(query){{
    if (!query || query.length < 2){{
      results.innerHTML = "";
      hint.textContent = defaultHint;
      return;
    }}
    const q = query.trim();
    const matches = items.filter(it => it.name.includes(q)).slice(0, 40);
    hint.textContent = `${{matches.length}} תוצאות (מוצג עד 40)`;
    results.innerHTML = matches.map(it =>
      `<div class="searchrow"><span class="name" title="${{escHtml(it.name)}}">${{escHtml(it.name)}}</span><span class="p">₪${{it.price.toFixed(2)}}</span></div>`
    ).join("");
  }}

  box.addEventListener("input", (e)=> ensureLoaded(()=> render(e.target.value)));
}})();
</script>"""

    return page_shell(f"{store_name} — Frodo Project", "map", body, extra_head, extra_script)
