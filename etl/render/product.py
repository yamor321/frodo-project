"""Renders site/product/index.html -- ONE generic page for every comparable
product, not a pre-baked file per barcode. Previously this module wrote
site/product/{barcode}/index.html for every code, but only codes referenced
from some store's top-8 best/worst list ever got a file -- meanwhile
site/branches/index.html links to every product compute_spreads() finds
(13,000+), so the vast majority of those links 404'd. This page instead
reads ?code= (and optional &from=) from the URL and renders client-side
from site/products.json, so every comparable product resolves, and the
page never needs to be regenerated file-by-file as the catalog grows.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from etl.enrich.geocode import GeoPoint
from etl.scoring.cross_branch_spread import SpreadResult
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
.chart-box{ background:var(--paper-raised); border:1px solid var(--line); border-radius:14px; padding:16px 18px 10px; margin:14px 0 26px; }
.sparkline{ display:block; }
.sparkline-labels{ display:flex; justify-content:space-between; font-size:.76rem; color:var(--ink-muted);
  font-family:'IBM Plex Mono',monospace; margin-top:4px; }
.chart-empty{ color:var(--ink-muted); font-size:.9rem; }
"""


@dataclass
class StorePrice:
    store_id: str
    store_name: str
    price: float


def collect_all_store_prices(
    catalogs_by_store: dict[str, list[PriceRecord]],
    store_names: dict[str, str],
    min_stores: int = 4,
) -> dict[str, list[StorePrice]]:
    """Single-pass grouping of every catalog record by item_code, mirroring
    compute_spreads()'s own grouping (etl/scoring/cross_branch_spread.py --
    same reliability filter, same min_stores threshold) on purpose: this
    must cover exactly the product universe /branches/ links to, not a
    separately-drifting scope. Calling collect_store_prices() once per code
    in a loop (the old per-code-page approach) is O(codes x total records)
    -- with 13,000+ codes and tens of thousands of catalog rows that's far
    too slow; this does one O(total records) pass instead.
    """
    from etl.scoring.item_code_filters import is_reliable_item_code

    by_item: dict[str, dict[str, tuple[str, float]]] = defaultdict(dict)
    for store_id, records in catalogs_by_store.items():
        for r in records:
            if r.item_price > 0 and is_reliable_item_code(r.item_code):
                by_item[r.item_code][store_id] = (r.item_name, r.item_price)

    result: dict[str, list[StorePrice]] = {}
    for code, prices_by_store in by_item.items():
        if len(prices_by_store) < min_stores:
            continue
        result[code] = [
            StorePrice(sid, store_names.get(sid, sid), price) for sid, (_name, price) in prices_by_store.items()
        ]
    return result


def build_products_payload(
    spreads: list[SpreadResult],
    all_store_prices: dict[str, list[StorePrice]],
    image_urls: dict[str, str | None],
    coords: dict[str, GeoPoint],
) -> dict:
    """JSON-serializable payload for site/products.json. One entry per
    product in `spreads` (the same universe /branches/ already lists), each
    carrying every store's price for it -- this is what the generic product
    page fetches once and renders client-side.
    """
    payload = {}
    for s in spreads:
        prices = []
        for sp in all_store_prices.get(s.item_code, []):
            entry = {"store_id": sp.store_id, "store_name": sp.store_name, "price": sp.price}
            pt = coords.get(sp.store_id)
            if pt is not None:
                entry["lat"] = pt.lat
                entry["lon"] = pt.lon
            prices.append(entry)
        payload[s.item_code] = {
            "name": s.item_name,
            "image_url": image_urls.get(s.item_code),
            "prices": prices,
        }
    return payload


# Number of trailing characters of an item_code used as the shard key. Two
# hex/decimal-ish digits gives up to 100 buckets -- verified against a real
# snapshot (14,323 products): a single products.json serializes to ~12.8MB,
# which every visitor to any product link would download in full before
# anything renders. Sharding by code suffix (not a numeric hash) means the
# client can compute the identical key with a plain string slice, so there's
# no hash function to keep in sync between Python and JS.
SHARD_KEY_LENGTH = 2


def shard_key(item_code: str) -> str:
    return item_code[-SHARD_KEY_LENGTH:]


def shard_products_payload(payload: dict) -> dict[str, dict]:
    """Splits the full products payload into shards keyed by shard_key(),
    so a visitor to any one product page fetches a small slice (order of
    ~140 products on the current snapshot) instead of the entire catalog.
    """
    shards: dict[str, dict] = defaultdict(dict)
    for code, entry in payload.items():
        shards[shard_key(code)][code] = entry
    return dict(shards)


def render_product_shell_html(base_path: str = "/frodo-project") -> str:
    """The single generic product page. Reads ?code= and optional &from=
    from the URL, fetches `{base_path}/products.json` once, and renders the
    same pricelist + mini-map view the old per-barcode static pages had --
    same markup/classes, same mini-map behavior (etl/render/layout.py's
    LEAFLET_* helpers), just built client-side instead of at snapshot time.
    """
    from etl.render.layout import ESC_HTML_JS, LEAFLET_CSS, LEAFLET_JS, LEAFLET_MAP_CSS, LEAFLET_SCORE_COLOR_JS, page_shell

    body = """
  <div class="kicker">Frodo Project · דף מוצר</div>
  <div id="productRoot"><p class="lede">טוען...</p></div>
"""

    extra_head = f"<style>{PRODUCT_CSS}</style>\n{LEAFLET_CSS}\n<style>{LEAFLET_MAP_CSS}</style>"

    # Plain (non f-string) JS body -- avoids doubling every literal `{`/`}`
    # in a giant f-string. The one dynamic value (BASE) is spliced in via a
    # single .replace() below instead.
    script_body = (
        LEAFLET_SCORE_COLOR_JS
        + "\n"
        + ESC_HTML_JS
        + """
(function(){
  const params = new URLSearchParams(location.search);
  const code = params.get("code");
  const fromStore = params.get("from");
  const root = document.getElementById("productRoot");

  // Both url and name are escaped here (attribute context: src=""/alt="")
  // -- image_url comes from the public, user-editable Open Food Facts API
  // and product names come from chains' own catalog files, neither fully
  // trusted, and this result is assigned via innerHTML below.
  // Small inline-SVG line chart, no external chart library (the site
  // loads nothing but Leaflet, from CDN, and this shouldn't add a second
  // dependency for one chart type). `points` is chronological [{y, label}].
  function sparklineSvg(points, color){
    if (points.length < 2) return '<p class="chart-empty">אין עדיין מספיק נקודות לגרף (נדרשות לפחות 2).</p>';
    var w = 600, h = 140, pad = 10;
    var ys = points.map(function(p){ return p.y; });
    var minY = Math.min.apply(null, ys), maxY = Math.max.apply(null, ys);
    if (minY === maxY) { minY -= 1; maxY += 1; }
    var stepX = points.length > 1 ? (w - pad*2) / (points.length - 1) : 0;
    function xAt(i){ return pad + i*stepX; }
    function yAt(v){ return h - pad - (v - minY) / (maxY - minY) * (h - pad*2); }
    var path = points.map(function(p,i){ return (i===0?"M":"L") + xAt(i).toFixed(1) + "," + yAt(p.y).toFixed(1); }).join(" ");
    var dots = points.map(function(p,i){
      return '<circle cx="' + xAt(i).toFixed(1) + '" cy="' + yAt(p.y).toFixed(1) + '" r="3" fill="' + color + '"><title>' + escHtml(p.label) + '</title></circle>';
    }).join("");
    return '<svg viewBox="0 0 ' + w + ' ' + h + '" class="sparkline" preserveAspectRatio="none" style="width:100%;height:140px">' +
      '<path d="' + path + '" fill="none" stroke="' + color + '" stroke-width="2"/>' + dots + '</svg>' +
      '<div class="sparkline-labels"><span>' + escHtml(points[0].label) + '</span><span>' + escHtml(points[points.length-1].label) + '</span></div>';
  }

  function loadHistoryCharts(code, shard){
    var priceEl = document.getElementById("priceHistoryChart");
    var cpiEl = document.getElementById("cpiChart");
    if (!priceEl || !cpiEl) return;
    Promise.all([
      fetch(BASE_PATH + "/price-history/" + shard + ".json").then(function(r){ return r.ok ? r.json() : {}; }).catch(function(){ return {}; }),
      fetch(BASE_PATH + "/food-cpi.json").then(function(r){ return r.ok ? r.json() : []; }).catch(function(){ return []; }),
    ]).then(function(results){
      var history = (results[0] && results[0][code]) || [];
      var points = history.map(function(h){ return {y: h.avg, label: h.date + ": ₪" + h.avg.toFixed(2)}; });
      priceEl.innerHTML = sparklineSvg(points, "var(--navy)");

      var cpi = results[1] || [];
      var cpiPoints = cpi.map(function(p){
        var mm = String(p.m).padStart(2, "0");
        return {y: p.v, label: p.y + "-" + mm};
      });
      cpiEl.innerHTML = sparklineSvg(cpiPoints, "var(--ink-muted)");
    }).catch(function(){
      priceEl.innerHTML = '<p class="chart-empty">שגיאה בטעינת נתוני מגמה.</p>';
      cpiEl.innerHTML = '<p class="chart-empty">שגיאה בטעינת נתוני מגמה.</p>';
    });
  }

  function thumbHtml(url, name){
    if (url) return '<div class="thumb"><img src="' + escHtml(url) + '" alt="' + escHtml(name) + '" loading="lazy"></div>';
    return '<div class="thumb empty">—</div>';
  }

  function initMap(points){
    const map = L.map('productMap');
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 16,
    }).addTo(map);
    const bounds = [];
    points.forEach(function(p){
      const color = scoreColor(p.t);
      const icon = L.divIcon({html: '<div class="store-pin" style="width:18px;height:18px;border-radius:50%;background:' + color + '"></div>', className: "", iconSize: [18,18], iconAnchor: [9,9]});
      const marker = L.marker([p.lat, p.lon], {icon: icon});
      // direction:"top" avoids Leaflet's default direction:"auto", which
      // picks left/right assuming LTR -- this page is dir="rtl", so auto
      // placement lands the tooltip far from the cursor.
      marker.bindTooltip(p.name, {direction: "top", offset: [0, -9]});
      marker.bindPopup(
        '<div class="store-popup"><b>' + escHtml(p.name) + '</b>' +
        '<div class="meta">₪' + p.price.toFixed(2) + '</div>' +
        '<a class="openbtn" href="' + BASE_PATH + '/store/' + p.id + '/">פתח דף סניף ←</a></div>'
      );
      marker.addTo(map);
      bounds.push([p.lat, p.lon]);
    });
    map.fitBounds(bounds, {padding: [24,24], maxZoom: 16});

    let meMarker = null;
    function haversine(lat1,lon1,lat2,lon2){
      const R = 6371000, toRad = function(d){ return d*Math.PI/180; };
      const dLat = toRad(lat2-lat1), dLon = toRad(lon2-lon1);
      const a = Math.sin(dLat/2)**2 + Math.cos(toRad(lat1))*Math.cos(toRad(lat2))*Math.sin(dLon/2)**2;
      return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    }
    function placeMe(lat, lon){
      if (meMarker) map.removeLayer(meMarker);
      meMarker = L.circleMarker([lat, lon], {radius:9, color:"#fff", weight:3, fillColor:"var(--ink)", fillOpacity:1}).addTo(map);
      map.panTo([lat, lon]);
      let nearest = null, bestD = Infinity;
      points.forEach(function(p){
        const d = haversine(lat, lon, p.lat, p.lon);
        if (d < bestD){ bestD = d; nearest = p; }
      });
      const box = document.getElementById("nearest");
      if (nearest){
        const km = (bestD/1000).toFixed(1);
        box.style.display = "block";
        box.innerHTML = 'הסניף הקרוב ביותר: <b><a href="' + BASE_PATH + '/store/' + nearest.id + '/">' + escHtml(nearest.name) + '</a></b> — כ-' + km + ' ק"מ, ₪' + nearest.price.toFixed(2) + '.';
      }
    }
    map.on('click', function(e){ placeMe(e.latlng.lat, e.latlng.lng); });
    const locBtn = document.getElementById("locBtn");
    if (locBtn) locBtn.addEventListener("click", function(){
      if (!navigator.geolocation){ alert("הדפדפן לא תומך באיתור מיקום"); return; }
      navigator.geolocation.getCurrentPosition(
        function(pos){ placeMe(pos.coords.latitude, pos.coords.longitude); },
        function(){ alert("לא הצלחתי לקבל מיקום — אפשר גם ללחוץ ישירות על המפה"); }
      );
    });
  }

  function render(product){
    const ordered = product.prices.slice().sort(function(a,b){ return a.price-b.price; });
    const cheapest = ordered[0], priciest = ordered[ordered.length-1];
    const samePriceEverywhere = cheapest && priciest && cheapest.price === priciest.price;

    const rows = ordered.map(function(sp){
      let tag = "";
      if (!samePriceEverywhere && sp.price === cheapest.price) tag = ' <span class="chip good">הכי זול</span>';
      else if (!samePriceEverywhere && sp.price === priciest.price) tag = ' <span class="chip warm">הכי יקר</span>';
      const cls = sp.store_id === fromStore ? "prow highlight" : "prow";
      return (
        '<div class="' + cls + '">' +
        '<span class="store">' + escHtml(sp.store_name) + tag + '<small><a href="' + BASE_PATH + '/store/' + sp.store_id + '/">לדף הסניף</a></small></span>' +
        '<span class="price ltr">₪' + sp.price.toFixed(2) + '</span></div>'
      );
    }).join("");

    let spreadLine = "";
    if (cheapest && priciest && cheapest.price > 0 && cheapest.store_id !== priciest.store_id) {
      const pct = (priciest.price - cheapest.price) / cheapest.price * 100;
      spreadLine = '<p class="lede">פער של <b>' + pct.toFixed(0) + '%</b> בין הזול ליקר ביותר, על אותו ברקוד בדיוק, ב-' + ordered.length + ' סניפים.</p>';
    }

    document.title = product.name + " — Frodo Project";

    const mapPoints = [];
    const prices = ordered.map(function(sp){ return sp.price; });
    const minP = Math.min.apply(null, prices), maxP = Math.max.apply(null, prices);
    const span = maxP - minP;
    ordered.forEach(function(sp){
      if (sp.lat == null || sp.lon == null) return;
      const t = span > 0 ? (sp.price - minP) / span : 0.0;
      mapPoints.push({id: sp.store_id, name: sp.store_name, price: sp.price, t: t, lat: sp.lat, lon: sp.lon});
    });

    const mapSection = mapPoints.length ? (
      '<h2 class="section-title">איפה המוצר הזה הכי זול לידך</h2>' +
      '<p class="section-sub">צבע = מיקום המחיר בין הזול ליקר ביותר עבור המוצר הזה בלבד (ירוק=זול, אדום=יקר) -- לא ציון הסניף הכללי.</p>' +
      '<div class="controls"><button class="locbtn" id="locBtn">📍 מצא את המיקום שלי</button></div>' +
      '<div id="productMap"></div>' +
      '<div class="legend-scale"><span>זול יחסית</span><div class="bar"></div><span>יקר יחסית</span></div>' +
      '<div id="nearest"></div>'
    ) : (
      '<h2 class="section-title">איפה המוצר הזה הכי זול לידך</h2>' +
      '<p class="section-sub">אין עדיין מספיק נתוני מיקום לסניפים שמוכרים את המוצר הזה.</p>'
    );

    var historySection =
      '<h2 class="section-title">מגמת מחיר לאורך זמן</h2>' +
      '<p class="section-sub">המעקב שלנו על המוצר הזה התחיל ב-26.08.2026 וגדל יום אחרי יום -- אין דרך להשיג היסטוריה אמיתית מלפני כן (מקורות הרשתות עצמן לא חושפים ארכיון).</p>' +
      '<div class="chart-box" id="priceHistoryChart"><p class="chart-empty">טוען...</p></div>' +
      '<p class="section-sub">להקשר: מדד המזון הכללי בישראל (הלמ"ס), לאורך שנים -- לא המחיר של המוצר הזה, אלא מגמת מחירי המזון הכלל-ארצית כערך ייחוס.</p>' +
      '<div class="chart-box" id="cpiChart"><p class="chart-empty">טוען...</p></div>';

    root.innerHTML =
      '<div class="product-head">' + thumbHtml(product.image_url, product.name) + '<h1>' + escHtml(product.name) + '</h1></div>' +
      spreadLine +
      '<div class="pricelist">' + rows + '</div>' +
      historySection +
      mapSection;

    loadHistoryCharts(code, code.slice(-2));

    if (mapPoints.length) {
      // A map-init failure (e.g. the Leaflet CDN blocked or unreachable)
      // must not wipe out the pricelist that's already correctly rendered
      // above -- without this, an unrelated map error bubbles up through
      // the fetch().then() chain into the top-level .catch(), which
      // overwrites root.innerHTML with a generic "failed to load" message
      // even though the real product data loaded and rendered just fine.
      try { initMap(mapPoints); } catch (e) { console.error("Product mini-map failed to init:", e); }
    }
  }

  if (!code) {
    root.innerHTML = '<p class="lede">לא צוין קוד מוצר. <a href="' + BASE_PATH + '/branches/">חפשו מוצר ברשימת הפערים ←</a></p>';
  } else {
    // Products are sharded by the last two characters of their code (see
    // shard_key() in this module) so a product page only downloads a small
    // slice of the catalog instead of the entire multi-MB file. A shard
    // that genuinely doesn't exist (no product ends in that suffix) is a
    // real 404, handled the same as "code not in this shard" below --
    // both mean "not a comparable product," not a network error.
    const shard = code.slice(-2);
    fetch(BASE_PATH + "/products/" + shard + ".json").then(function(r){
      return r.ok ? r.json() : null;
    }).then(function(shardData){
      const product = shardData ? shardData[code] : null;
      if (!product) {
        root.innerHTML = '<p class="lede">המוצר הזה לא נמצא (אולי אין מספיק סניפים שמוכרים אותו היום כדי להשוות). <a href="' + BASE_PATH + '/branches/">חפשו מוצר אחר ←</a></p>';
        return;
      }
      render(product);
    }).catch(function(){
      root.innerHTML = '<p class="lede">שגיאה בטעינת נתוני המוצר. נסו לרענן.</p>';
    });
  }
})();
"""
    )

    extra_script = (
        f'{LEAFLET_JS}\n<script>\nconst BASE_PATH = "{base_path}";\n' + script_body + "\n</script>"
    )

    return page_shell("מוצר — Frodo Project", "product", body, extra_head, extra_script)
