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

LEAFLET_CSS = '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="">'
LEAFLET_JS = '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>'

MAP_CSS = """
.controls{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:14px; align-items:center; }
button.locbtn{ font-family:'Assistant',sans-serif; font-weight:700; font-size:.88rem; padding:9px 18px;
  border-radius:999px; border:1.5px solid var(--navy); background:var(--navy-soft); color:var(--navy); cursor:pointer; }
button.locbtn:hover{ background:var(--navy); color:#fff; }
.type-filters{ display:flex; gap:16px; flex-wrap:wrap; margin-bottom:14px; font-size:.85rem; }
.type-filters label{ display:inline-flex; align-items:center; gap:6px; cursor:pointer; }
.type-filters label.disabled{ opacity:.5; cursor:not-allowed; }
#leafletMap{ width:100%; height:480px; border-radius:14px; border:1px solid var(--line); box-shadow:var(--shadow); }
.legend-scale{ display:flex; align-items:center; gap:10px; margin-top:12px; font-size:.8rem; color:var(--ink-muted); }
.legend-scale .bar{ width:140px; height:10px; border-radius:6px; background:linear-gradient(to left, var(--good), #C9C4A8, var(--brick)); }
#nearest{ margin-top:14px; padding:14px 18px; border-radius:12px; background:var(--navy-soft); color:var(--navy); font-size:.92rem; display:none; }
#nearest b{ color:var(--ink); }
.leaflet-marker-icon.store-pin{ border:1.5px solid #fff; box-shadow:0 1px 3px rgba(0,0,0,.25); }
.leaflet-tile-pane{ filter:grayscale(45%) saturate(65%) brightness(1.08) contrast(.92); }
"""


def render_map_html(
    scores: list[StoreScore],
    coords: dict[str, GeoPoint],
    formats: dict[str, str],
    base_path: str = "/frodo-project",
) -> str:
    from etl.render.layout import page_shell

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
  <h1>מפת מחירים — שופרסל בכפר סבא</h1>
  <p class="lede">כל נקודה = סניף. הצבע = כמה יקר הוא בממוצע ביחס לשאר הסניפים, על אלפי מוצרים משותפים. לחיצה על סניף פותחת את דף המוצרים הבולטים שלו.</p>

  <div class="controls">
    <button class="locbtn" id="locBtn">📍 מצא את המיקום שלי</button>
    <span style="font-size:.85rem;color:var(--ink-muted);">או לחץ על המפה כדי לסמן מיקום</span>
  </div>

  <div class="type-filters">
    <label><input type="checkbox" id="fmtHyper" checked> ריבוע · פורמט גדול (דיל/יוניברס)</label>
    <label><input type="checkbox" id="fmtNeighborhood" checked> עיגול · שכונתי/נוחות</label>
    <label class="disabled" title="עוד לא נאסף מידע"><input type="checkbox" disabled> פארמות · בקרוב</label>
  </div>

  <div id="leafletMap"></div>
  <div class="legend-scale"><span>זול יחסית</span><div class="bar"></div><span>יקר יחסית</span></div>
  <div id="nearest"></div>
"""

    extra_head = f"{LEAFLET_CSS}\n<style>{MAP_CSS}</style>"

    extra_script = f"""{LEAFLET_JS}
<script>
(function(){{
  const stores = {data_json};
  const BASE = "{base_path}";

  function scoreColor(score){{
    const stops = [[0.12,0.48,0.27],[0.79,0.77,0.66],[0.65,0.23,0.18]];
    const t = score <= 0.5 ? score*2 : (score-0.5)*2;
    const [a,b] = score <= 0.5 ? [stops[0],stops[1]] : [stops[1],stops[2]];
    const mix = a.map((v,i)=>Math.round((v + (b[i]-v)*t)*255));
    return `rgb(${{mix[0]}},${{mix[1]}},${{mix[2]}})`;
  }}

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
    maxZoom: 19,
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
    marker.bindTooltip(`<b>${{s.name}}</b><br>ציון ${{s.score.toFixed(2)}} מתוך 1 (0=זול ביותר)<br>${{s.items.toLocaleString()}} מוצרים משותפים`);
    marker.on('click', ()=>{{ window.location.href = `${{BASE}}/store/${{s.id}}/`; }});
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
      box.innerHTML = `הסניף הקרוב ביותר: <b><a href="${{BASE}}/store/${{nearest.id}}/">${{nearest.name}}</a></b> — כ-${{km}} ק"מ, ציון ${{nearest.score.toFixed(2)}} מתוך 1.`;
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
