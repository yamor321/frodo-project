"""Renders site/product/{barcode}/index.html -- one product compared across
every branch that carries it (brief section 3: the actual cross-branch
comparison, at full resolution, not just the min/max used for the spread
list). `from_store_id` highlights the branch the visitor drilled down from.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape

from etl.enrich.geocode import GeoPoint
from etl.scrapers.shufersal import PriceRecord

PRODUCT_CSS = """
.product-head{ display:flex; align-items:center; gap:16px; }
.product-head .thumb{ width:96px; height:96px; border-radius:12px; }
.pricelist{ display:flex; flex-direction:column; gap:10px; margin:20px 0; }
.prow{ display:flex; justify-content:space-between; align-items:center; padding:14px 18px;
  background:var(--paper-raised); border:1px solid var(--line); border-radius:10px; }
.prow.highlight{ border-color:var(--navy); box-shadow:0 0 0 2px var(--navy-soft); }
.prow .store{ font-weight:600; }
.prow .store small{ display:block; font-weight:400; color:var(--ink-muted); font-size:.78rem; margin-top:2px; }
.prow .price{ font-family:'IBM Plex Mono',monospace; font-size:1.1rem; font-variant-numeric:tabular-nums; }
#productMap{ width:100%; height:340px; border-radius:14px; border:1px solid var(--line); box-shadow:var(--shadow); }
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
    image_url: str | None = None,
    coords: dict[str, GeoPoint] | None = None,
    base_path: str = "/frodo-project",
) -> str:
    from etl.render.layout import (
        LEAFLET_CSS,
        LEAFLET_JS,
        LEAFLET_MAP_CSS,
        LEAFLET_SCORE_COLOR_JS,
        page_shell,
        thumb_html,
    )

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

    # Per-product normalization, not the store's sitewide percentile score --
    # a store that's expensive overall can still be the cheapest place for
    # THIS item, and that's exactly what a visitor standing in the aisle
    # wants to see. t=0 is the cheapest store for this barcode, t=1 the
    # priciest, among only the stores that carry it.
    coords = coords or {}
    map_points = []
    if store_prices:
        prices = [sp.price for sp in store_prices]
        min_p, max_p = min(prices), max(prices)
        span = max_p - min_p
        for sp in store_prices:
            pt = coords.get(sp.store_id)
            if pt is None:
                continue
            t = (sp.price - min_p) / span if span > 0 else 0.0
            map_points.append(
                {"id": sp.store_id, "name": sp.store_name, "price": sp.price, "t": t, "lat": pt.lat, "lon": pt.lon}
            )

    if map_points:
        map_html = """
  <h2 class="section-title">איפה המוצר הזה הכי זול לידך</h2>
  <p class="section-sub">צבע = מיקום המחיר בין הזול ליקר ביותר עבור המוצר הזה בלבד (ירוק=זול, אדום=יקר) -- לא ציון הסניף הכללי.</p>
  <div class="controls">
    <button class="locbtn" id="locBtn">📍 מצא את המיקום שלי</button>
  </div>
  <div id="productMap"></div>
  <div class="legend-scale"><span>זול יחסית</span><div class="bar"></div><span>יקר יחסית</span></div>
  <div id="nearest"></div>
"""
    else:
        map_html = """
  <h2 class="section-title">איפה המוצר הזה הכי זול לידך</h2>
  <p class="section-sub">אין עדיין מספיק נתוני מיקום לסניפים שמוכרים את המוצר הזה.</p>
"""

    body = f"""
  <div class="kicker">Frodo Project · דף מוצר</div>
  <div class="product-head">
    {thumb_html(image_url, item_name)}
    <h1>{escape(item_name)}</h1>
  </div>
  {spread_line}
  <div class="pricelist">{''.join(rows)}</div>
  {map_html}
"""

    extra_head = f"<style>{PRODUCT_CSS}</style>"
    extra_script = ""
    if map_points:
        map_json = json.dumps(map_points, ensure_ascii=False)
        extra_head += f"\n{LEAFLET_CSS}\n<style>{LEAFLET_MAP_CSS}</style>"
        extra_script = f"""{LEAFLET_JS}
<script>
(function(){{
  const points = {map_json};
  const BASE = "{base_path}";

  {LEAFLET_SCORE_COLOR_JS}

  const map = L.map('productMap');
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 16,
  }}).addTo(map);

  const bounds = [];
  points.forEach(p=>{{
    const color = scoreColor(p.t);
    const icon = L.divIcon({{html: `<div class="store-pin" style="width:18px;height:18px;border-radius:50%;background:${{color}}"></div>`, className: "", iconSize: [18,18], iconAnchor: [9,9]}});
    const marker = L.marker([p.lat, p.lon], {{icon}});
    marker.bindTooltip(p.name);
    marker.bindPopup(`
      <div class="store-popup">
        <b>${{p.name}}</b>
        <div class="meta">₪${{p.price.toFixed(2)}}</div>
        <a class="openbtn" href="${{BASE}}/store/${{p.id}}/">פתח דף סניף ←</a>
      </div>
    `);
    marker.addTo(map);
    bounds.push([p.lat, p.lon]);
  }});
  map.fitBounds(bounds, {{padding: [24,24], maxZoom: 16}});

  let meMarker = null;
  function haversine(lat1,lon1,lat2,lon2){{
    const R = 6371000, toRad = d=>d*Math.PI/180;
    const dLat = toRad(lat2-lat1), dLon = toRad(lon2-lon1);
    const a = Math.sin(dLat/2)**2 + Math.cos(toRad(lat1))*Math.cos(toRad(lat2))*Math.sin(dLon/2)**2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  }}
  function placeMe(lat, lon){{
    if (meMarker) map.removeLayer(meMarker);
    meMarker = L.circleMarker([lat, lon], {{radius:9, color:"#fff", weight:3, fillColor:"var(--ink)", fillOpacity:1}}).addTo(map);
    map.panTo([lat, lon]);
    let nearest = null, bestD = Infinity;
    points.forEach(p=>{{
      const d = haversine(lat, lon, p.lat, p.lon);
      if (d < bestD){{ bestD = d; nearest = p; }}
    }});
    const box = document.getElementById("nearest");
    if (nearest){{
      const km = (bestD/1000).toFixed(1);
      box.style.display = "block";
      box.innerHTML = `הסניף הקרוב ביותר: <b><a href="${{BASE}}/store/${{nearest.id}}/">${{nearest.name}}</a></b> — כ-${{km}} ק"מ, ₪${{nearest.price.toFixed(2)}}.`;
    }}
  }}
  map.on('click', (e)=>{{ placeMe(e.latlng.lat, e.latlng.lng); }});
  document.getElementById("locBtn").addEventListener("click", ()=>{{
    if (!navigator.geolocation){{ alert("הדפדפן לא תומך באיתור מיקום"); return; }}
    navigator.geolocation.getCurrentPosition(
      (pos)=>{{ placeMe(pos.coords.latitude, pos.coords.longitude); }},
      ()=>{{ alert("לא הצלחתי לקבל מיקום — אפשר גם ללחוץ ישירות על המפה"); }}
    );
  }});
}})();
</script>"""

    return page_shell(f"{item_name} — Frodo Project", "map", body, extra_head, extra_script)
