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
                "format": formats.get(s.store_id, "supermarket"),
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
    <label><input type="checkbox" id="fmtHyper" checked> סופרמרקט ענק</label>
    <label><input type="checkbox" id="fmtSupermarket" checked> סופרמרקט</label>
    <label><input type="checkbox" id="fmtExpress" checked> מכולת / חנות נוחות</label>
    <label><input type="checkbox" id="fmtPharm" checked> פארם</label>
    <label><input type="checkbox" id="fmtOnline" checked> אונליין / משלוחים בלבד</label>
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

  const layersByFormat = {{
    hyper: L.layerGroup().addTo(map),
    supermarket: L.layerGroup().addTo(map),
    express: L.layerGroup().addTo(map),
    pharm: L.layerGroup().addTo(map),
    online: L.layerGroup().addTo(map),
  }};

  // Lightens an "rgb(r,g,b)" string (scoreColor's own output format) toward
  // white by `amt` (0..1) -- used for the pin's gradient top-stop, so the
  // fill reads as a rounded, lit shape instead of a flat color block.
  function lighten(rgbStr, amt){{
    const m = /rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)/.exec(rgbStr);
    if (!m) return rgbStr;
    const mix = v => Math.round(Number(v) + (255 - Number(v)) * amt);
    return `rgb(${{mix(m[1])}},${{mix(m[2])}},${{mix(m[3])}})`;
  }}

  // One small inline SVG per format -- distinguished by SHAPE, not just
  // color, same reasoning as the square/circle/triangle split this
  // replaces (identifiable in grayscale/colorblind viewing, not just as an
  // extra hue). A gradient fill + white outline instead of a flat CSS block
  // reads as a designed pin rather than a colored primitive, with no
  // external icon asset (consistent with this page's own "no external
  // asset" approach -- see the CARTO-tiles rejection note above).
  // Returns {{html, w, h, anchor}}; anchor is the point (in pixels from the
  // icon's top-left) that lands on the store's actual lat/lon.
  function pinIcon(format, color, gradId){{
    const light = lighten(color, 0.4);
    const grad = `<defs><linearGradient id="${{gradId}}" x1="0" y1="0" x2="0" y2="1">` +
      `<stop offset="0" stop-color="${{light}}"/><stop offset="1" stop-color="${{color}}"/></linearGradient></defs>`;
    const PIN_PATH = "M12 0C6.5 0 2 4.5 2 10c0 7.5 10 19 10 19s10-11.5 10-19c0-5.5-4.5-10-10-10z";
    if (format === "hyper"){{
      // Same map-pin teardrop as "supermarket", scaled up with an added
      // outer ring -- reads as "bigger format" at a glance, a distinct
      // silhouette from the plain pin even with color removed.
      const w = 30, h = 40;
      const html = `<svg width="${{w}}" height="${{h}}" viewBox="0 0 24 32">${{grad}}` +
        `<path d="${{PIN_PATH}}" fill="none" stroke="${{color}}" stroke-width="1.4" opacity=".45" transform="translate(12 10) scale(1.18) translate(-12 -10)"/>` +
        `<path d="${{PIN_PATH}}" fill="url(#${{gradId}})" stroke="#fff" stroke-width="1.6"/></svg>`;
      return {{html, w, h, anchor: [w/2, h]}};
    }}
    if (format === "express"){{
      // A small rounded square -- a genuinely different silhouette from the
      // pin shapes, reads as "small/quick" without needing color.
      const w = 16;
      const html = `<svg width="${{w}}" height="${{w}}" viewBox="0 0 24 24">${{grad}}` +
        `<rect x="2" y="2" width="20" height="20" rx="6" fill="url(#${{gradId}})" stroke="#fff" stroke-width="1.5"/></svg>`;
      return {{html, w, h: w, anchor: [w/2, w/2]}};
    }}
    if (format === "pharm"){{
      // A circle with a white cross cut out -- the universally recognized
      // pharmacy symbol, distinct from every other tier's silhouette.
      const w = 22;
      const html = `<svg width="${{w}}" height="${{w}}" viewBox="0 0 24 24">${{grad}}` +
        `<circle cx="12" cy="12" r="11" fill="url(#${{gradId}})" stroke="#fff" stroke-width="1.5"/>` +
        `<rect x="10.3" y="5" width="3.4" height="14" rx="1" fill="#fff"/>` +
        `<rect x="5" y="10.3" width="14" height="3.4" rx="1" fill="#fff"/></svg>`;
      return {{html, w, h: w, anchor: [w/2, w/2]}};
    }}
    if (format === "online"){{
      // Kept as the existing flat triangle -- already colorblind-tested by
      // the reasoning above, no reason to change a shape that already works.
      const w = 16;
      const html = `<div class="store-pin" style="width:${{w}}px;height:${{w}}px;background:${{color}};clip-path:polygon(50% 0%, 0% 100%, 100% 100%)"></div>`;
      return {{html, w, h: w, anchor: [w/2, w/2]}};
    }}
    // "supermarket" -- the new default format, and the plain/classic pin.
    const w = 22, h = 29;
    const html = `<svg width="${{w}}" height="${{h}}" viewBox="0 0 24 32">${{grad}}` +
      `<path d="${{PIN_PATH}}" fill="url(#${{gradId}})" stroke="#fff" stroke-width="1.5"/></svg>`;
    return {{html, w, h, anchor: [w/2, h]}};
  }}

  stores.forEach((s, i)=>{{
    const color = scoreColor(s.score);
    const {{html, w, h, anchor}} = pinIcon(s.format, color, `pinGrad${{i}}`);
    const icon = L.divIcon({{html, className: "", iconSize: [w, h], iconAnchor: anchor}});
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
    // landed far from the cursor instead of right above the pin. Offset is
    // -anchor[1] (not a fixed half-size) so it clears the icon correctly
    // regardless of shape -- anchor[1] is exactly the icon's own height
    // above the point that sits on the map.
    marker.bindTooltip(s.name, {{direction: "top", offset: [0, -anchor[1]]}});
    const onlineNote = s.format === "online"
      ? '<div class="meta" style="margin-top:4px;">🚚 משלוחים/איסוף בלבד — אין כניסה פיזית לקונים</div>'
      : "";
    marker.bindPopup(`
      <div class="store-popup">
        <b>${{s.name}}</b>
        <div class="meta">מדד חיסכון ${{100 - Math.round(s.score*100)}} מתוך 100 (ככל שגבוה יותר -- זול יותר)<br>${{s.items.toLocaleString()}} מוצרים משותפים</div>
        ${{onlineNote}}
        <a class="openbtn" href="${{BASE}}/store/${{s.id}}/">פתח דף סניף ←</a>
      </div>
    `);
    (layersByFormat[s.format] || layersByFormat.supermarket).addLayer(marker);
  }});

  document.getElementById("fmtHyper").addEventListener("change", (e)=>{{
    if (e.target.checked) map.addLayer(layersByFormat.hyper); else map.removeLayer(layersByFormat.hyper);
  }});
  document.getElementById("fmtSupermarket").addEventListener("change", (e)=>{{
    if (e.target.checked) map.addLayer(layersByFormat.supermarket); else map.removeLayer(layersByFormat.supermarket);
  }});
  document.getElementById("fmtExpress").addEventListener("change", (e)=>{{
    if (e.target.checked) map.addLayer(layersByFormat.express); else map.removeLayer(layersByFormat.express);
  }});
  document.getElementById("fmtPharm").addEventListener("change", (e)=>{{
    if (e.target.checked) map.addLayer(layersByFormat.pharm); else map.removeLayer(layersByFormat.pharm);
  }});
  document.getElementById("fmtOnline").addEventListener("change", (e)=>{{
    if (e.target.checked) map.addLayer(layersByFormat.online); else map.removeLayer(layersByFormat.online);
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
