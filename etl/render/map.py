"""Renders site/map/index.html -- a real interactive Leaflet + OpenStreetMap
map (not the schematic SVG used in the sandboxed artifact prototype; this
page is served by GitHub Pages, a normal website with no CSP restriction on
external tiles). Markers link through to each store's own page (brief
section 3 drill-down: map -> store -> product).
"""
from __future__ import annotations

import json
from html import escape

from etl.enrich.geocode import GeoPoint
from etl.scoring.store_ranking import StoreScore

# LEAFLET_CSS/JS, the base map CSS, and the score-color gradient all live in
# layout.py now -- shared verbatim with the per-product mini-map in
# product.py so the two can never drift into different-looking color scales.
MAP_CSS = """
.type-filters{ display:flex; gap:16px; flex-wrap:wrap; margin-bottom:14px; font-size:.85rem; }
.type-filters label{ display:inline-flex; align-items:center; gap:6px; cursor:pointer; }
.type-filters label.disabled{ opacity:.5; cursor:not-allowed; }
"""


def render_map_html(
    scores: list[StoreScore],
    coords: dict[str, GeoPoint],
    formats: dict[str, str],
    base_path: str = "/frodo-project",
) -> str:
    from etl.render.layout import LEAFLET_CSS, LEAFLET_JS, LEAFLET_MAP_CSS, LEAFLET_SCORE_COLOR_JS, page_shell

    points = []
    for s in scores:
        pt = coords.get(s.store_id)
        if pt is None:
            continue
        points.append(
            {
                "id": s.store_id,
                "name": s.store_name,
                "score": round(s.avg_percentile, 4),
                "items": s.items_compared,
                "lat": pt.lat,
                "lon": pt.lon,
                "format": formats.get(s.store_id, "neighborhood"),
            }
        )
    data_json = json.dumps(points, ensure_ascii=False)

    body = f"""
  <div class="kicker">Frodo Project · שכבה 2 · דירוג סניפים</div>
  <h1>מפת מחירים — כפר סבא</h1>
  <p class="lede">כל נקודה = סניף. הצבע = כמה יקר הוא בממוצע ביחס לשאר הסניפים, על אלפי מוצרים משותפים. לחיצה על סניף פותחת את דף המוצרים הבולטים שלו. מיקום הסניף על המפה מבוסס על geocoding אוטומטי מהכתובת הרשמית ועשוי להיות משוער — לא תמיד מדויק לכניסה עצמה.</p>

  <div class="controls">
    <button class="locbtn" id="locBtn">📍 מצא את המיקום שלי</button>
    <span style="font-size:.85rem;color:var(--ink-muted);">או לחץ על המפה כדי לסמן מיקום</span>
  </div>

  <div class="type-filters">
    <label><input type="checkbox" id="fmtHyper" checked> ריבוע · פורמט גדול (דיל/יוניברס)</label>
    <label><input type="checkbox" id="fmtNeighborhood" checked> עיגול · שכונתי/נוחות</label>
    <label class="disabled" title="עוד לא נאסף מידע"><input type="checkbox" disabled aria-label="פארמות, בקרוב, עדיין לא נאסף מידע"> פארמות · בקרוב</label>
  </div>

  <div id="leafletMap"></div>
  <div class="legend-scale"><span>זול יחסית</span><div class="bar"></div><span>יקר יחסית</span></div>
  <div id="nearest"></div>
"""

    extra_head = f"{LEAFLET_CSS}\n<style>{LEAFLET_MAP_CSS}</style>\n<style>{MAP_CSS}</style>"

    extra_script = f"""{LEAFLET_JS}
<script>
(function(){{
  const stores = {data_json};
  const BASE = "{base_path}";

  {LEAFLET_SCORE_COLOR_JS}

  const lats = stores.map(s=>s.lat), lons = stores.map(s=>s.lon);
  const centerLat = (Math.min(...lats)+Math.max(...lats))/2;
  const centerLon = (Math.min(...lons)+Math.max(...lons))/2;

  const map = L.map('leafletMap').setView([centerLat, centerLon], 14);
  // Plain OpenStreetMap tiles: no signup, no API key, no watermark -- the
  // CARTO basemaps tried earlier turned out to require a key in production
  // (showed as an "API KEY REQUIRED" watermark once deployed, even though a
  // handful of local test loads had gone through). A CSS filter on the
  // tile pane above does the "leaner" styling instead, on tiles that are
  // guaranteed to actually render.
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    // Capped below the zoom where individual building outlines start
    // rendering -- keeps the map graphic/lean instead of relying on
    // users not to zoom in past it.
    maxZoom: 16,
  }}).addTo(map);

  const hyperLayer = L.layerGroup().addTo(map);
  const neighborhoodLayer = L.layerGroup().addTo(map);

  stores.forEach(s=>{{
    const color = scoreColor(s.score);
    const size = s.format === "hyper" ? 22 : 16;
    const shape = s.format === "hyper"
      ? `<div class="store-pin" style="width:${{size}}px;height:${{size}}px;border-radius:7px;background:${{color}}"></div>`
      : `<div class="store-pin" style="width:${{size}}px;height:${{size}}px;border-radius:50%;background:${{color}}"></div>`;
    const icon = L.divIcon({{html: shape, className: "", iconSize: [size,size], iconAnchor: [size/2, size/2]}});
    const marker = L.marker([s.lat, s.lon], {{icon}});
    // Tooltip is hover-only, so it's a no-op on touch devices -- that's fine,
    // it's just a desktop quick-glance label. The actual identification +
    // navigation happens through the popup below, which opens on tap/click
    // on every device: without this, a mobile tap had no hover step at all,
    // so the very first touch fired the click handler and jumped straight
    // into the store page with no chance to see which store it even was.
    // direction:"top" is deliberate, not cosmetic -- Leaflet's default
    // direction:"auto" picks left/right based on LTR assumptions and the
    // whole page is dir="rtl" (layout.py), so without this the tooltip
    // landed far from the cursor instead of right above the pin.
    marker.bindTooltip(s.name, {{direction: "top", offset: [0, -(size/2)]}});
    marker.bindPopup(`
      <div class="store-popup">
        <b>${{s.name}}</b>
        <div class="meta">מדד חיסכון ${{100 - Math.round(s.score*100)}} מתוך 100 (ככל שגבוה יותר -- זול יותר)<br>${{s.items.toLocaleString()}} מוצרים משותפים</div>
        <a class="openbtn" href="${{BASE}}/store/${{s.id}}/">פתח דף סניף ←</a>
      </div>
    `);
    (s.format === "hyper" ? hyperLayer : neighborhoodLayer).addLayer(marker);
  }});

  document.getElementById("fmtHyper").addEventListener("change", (e)=>{{
    if (e.target.checked) map.addLayer(hyperLayer); else map.removeLayer(hyperLayer);
  }});
  document.getElementById("fmtNeighborhood").addEventListener("change", (e)=>{{
    if (e.target.checked) map.addLayer(neighborhoodLayer); else map.removeLayer(neighborhoodLayer);
  }});

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
    stores.forEach(s=>{{
      const d = haversine(lat, lon, s.lat, s.lon);
      if (d < bestD){{ bestD = d; nearest = s; }}
    }});
    const box = document.getElementById("nearest");
    if (nearest){{
      const km = (bestD/1000).toFixed(1);
      box.style.display = "block";
      box.innerHTML = `הסניף הקרוב ביותר: <b><a href="${{BASE}}/store/${{nearest.id}}/">${{nearest.name}}</a></b> — כ-${{km}} ק"מ, מדד חיסכון ${{100 - Math.round(nearest.score*100)}} מתוך 100 (ככל שגבוה יותר -- זול יותר).`;
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

    return page_shell("מפת מחירים כפר סבא", "map", body, extra_head, extra_script)
