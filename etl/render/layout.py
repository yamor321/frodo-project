"""Shared page shell (fonts, CSS tokens, header nav, footer) for every page
in site/, so the design system lives in one place instead of being copied
into each render_*.py module.
"""
from __future__ import annotations

PAGE_CSS = """
:root{
  --paper:#F3F1E9; --paper-raised:#FFFFFF; --ink:#191914; --ink-muted:#625F53;
  --line:#D8D4C5; --navy:#1F3A5F; --navy-soft:#DCE4EC; --brick:#A63A2E; --brick-soft:#F2E2DC;
  --good:#1E7A46; --good-soft:#DCEDE2;
  --shadow:0 2px 4px rgba(25,25,20,.06), 0 16px 36px rgba(25,25,20,.10);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --paper:#15140F; --paper-raised:#1D1C15; --ink:#EFEDE3; --ink-muted:#A6A28E;
    --line:#332F22; --navy:#7FA6D6; --navy-soft:#1E2B3B; --brick:#E08069; --brick-soft:#3A2620;
    --good:#5FBF87; --good-soft:#1C3527;
    --shadow:0 2px 4px rgba(0,0,0,.4), 0 16px 36px rgba(0,0,0,.4);
  }
}
:root[data-theme="dark"]{
  --paper:#15140F; --paper-raised:#1D1C15; --ink:#EFEDE3; --ink-muted:#A6A28E;
  --line:#332F22; --navy:#7FA6D6; --navy-soft:#1E2B3B; --brick:#E08069; --brick-soft:#3A2620;
  --good:#5FBF87; --good-soft:#1C3527;
  --shadow:0 2px 4px rgba(0,0,0,.4), 0 16px 36px rgba(0,0,0,.4);
}
*{box-sizing:border-box;}
body{ margin:0; background:var(--paper); color:var(--ink); font-family:'Assistant',sans-serif;
  direction:rtl; -webkit-font-smoothing:antialiased; }
.page{ max-width:820px; margin:0 auto; padding:0 20px 80px; }
.ltr{ direction:ltr; unicode-bidi:isolate; font-family:'IBM Plex Mono',monospace; }
a{ color:var(--navy); text-decoration-color:var(--navy); text-underline-offset:3px; }
a:hover{ text-decoration-thickness:2px; }
a:focus-visible, button:focus-visible, input:focus-visible{ outline:2px solid var(--navy); outline-offset:2px; }

nav.topnav{ display:flex; align-items:center; gap:18px; padding:18px 0; border-bottom:1px solid var(--line);
  margin-bottom:28px; font-size:.88rem; }
nav.topnav a{ color:var(--ink); text-decoration:none; font-weight:600; }
nav.topnav a.brand{ font-family:'Frank Ruhl Libre',serif; font-weight:700; font-size:1.05rem; color:var(--ink);
  display:inline-flex; align-items:center; gap:6px; }
nav.topnav .spacer{ flex:1; }
nav.topnav a.current{ color:var(--navy); }
nav.topnav .brand-mark{ display:inline-flex; align-items:flex-end; gap:2px; margin-inline-end:2px; }
button.theme-toggle{ font-size:1rem; line-height:1; background:none; border:1px solid var(--line);
  border-radius:999px; width:30px; height:30px; cursor:pointer; color:var(--ink); }
button.theme-toggle:hover{ border-color:var(--navy); }

h1{ font-family:'Frank Ruhl Libre',serif; font-weight:900; font-size:clamp(1.8rem,5vw,2.6rem); line-height:1.12;
  margin:0 0 14px; text-wrap:balance; }
h2{ font-family:'Frank Ruhl Libre',serif; font-weight:700; font-size:1.3rem; margin:0 0 10px; }
.kicker{ font-family:'IBM Plex Mono',monospace; font-size:.76rem; letter-spacing:.08em; text-transform:uppercase;
  color:var(--navy); margin-bottom:10px; }
.lede{ color:var(--ink-muted); font-size:1.05rem; line-height:1.6; max-width:60ch; margin:0 0 8px; }

.card{ background:var(--paper-raised); border:1px solid var(--line); border-radius:14px; padding:18px 20px;
  box-shadow:var(--shadow); }
.chip{ font-family:'IBM Plex Mono',monospace; font-size:.78rem; font-weight:500; padding:4px 10px;
  border-radius:999px; white-space:nowrap; display:inline-block; }
.chip.warm{ background:var(--brick-soft); color:var(--brick); }
.chip.good{ background:var(--good-soft); color:var(--good); }

.thumb{ width:56px; height:56px; flex:none; border-radius:8px; overflow:hidden; background:var(--paper);
  border:1px solid var(--line); display:flex; align-items:center; justify-content:center; }
.thumb img{ width:100%; height:100%; object-fit:contain; }
.thumb.empty{ color:var(--ink-muted); font-size:1.2rem; }

footer.sitefoot{ margin-top:50px; padding-top:20px; border-top:1px solid var(--line); font-size:.84rem;
  color:var(--ink-muted); line-height:1.7; }
footer.sitefoot a{ color:var(--navy); }

@media (max-width:520px){
  .page{ padding:0 14px 60px; }
  .card{ flex-direction:column; align-items:flex-start; }
}
"""

LEAFLET_CSS = '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="">'
LEAFLET_JS = '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>'

# Shared by both the main map (etl/render/map.py) and the per-product
# mini-map (etl/render/product.py) so the two can never drift into visually
# different color scales or marker styles by accident.
LEAFLET_MAP_CSS = """
.controls{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:14px; align-items:center; }
button.locbtn{ font-family:'Assistant',sans-serif; font-weight:700; font-size:.88rem; padding:9px 18px;
  border-radius:999px; border:1.5px solid var(--navy); background:var(--navy-soft); color:var(--navy); cursor:pointer; }
button.locbtn:hover{ background:var(--navy); color:#fff; }
#leafletMap{ width:100%; height:480px; border-radius:14px; border:1px solid var(--line); box-shadow:var(--shadow); }
.legend-scale{ display:flex; align-items:center; gap:10px; margin-top:12px; font-size:.8rem; color:var(--ink-muted); }
.legend-scale .bar{ width:140px; height:10px; border-radius:6px; background:linear-gradient(to left, var(--good), #C9C4A8, var(--brick)); }
#nearest{ margin-top:14px; padding:14px 18px; border-radius:12px; background:var(--navy-soft); color:var(--navy); font-size:.92rem; display:none; }
#nearest b{ color:var(--ink); }
.leaflet-marker-icon.store-pin{ border:1.5px solid #fff; box-shadow:0 1px 3px rgba(0,0,0,.25); }
.leaflet-tile-pane{ filter:grayscale(45%) saturate(65%) brightness(1.08) contrast(.92); }
.store-popup{ font-family:'Assistant',sans-serif; min-width:170px; }
.store-popup b{ font-size:.98rem; }
.store-popup .meta{ font-size:.82rem; color:var(--ink-muted); margin-top:2px; }
.store-popup a.openbtn{ display:inline-block; margin-top:8px; font-weight:700; color:var(--navy); text-decoration:none; }
.store-popup a.openbtn:hover{ text-decoration:underline; }
"""

# Same 3-stop green/beige/red gradient everywhere a store or price gets
# color-coded -- interpolated (not re-typed) into each page's script so the
# main map and the product mini-map are guaranteed identical, not just similar.
LEAFLET_SCORE_COLOR_JS = """function scoreColor(score){
    const stops = [[0.12,0.48,0.27],[0.79,0.77,0.66],[0.65,0.23,0.18]];
    const t = score <= 0.5 ? score*2 : (score-0.5)*2;
    const [a,b] = score <= 0.5 ? [stops[0],stops[1]] : [stops[1],stops[2]];
    const mix = a.map((v,i)=>Math.round((v + (b[i]-v)*t)*255));
    return `rgb(${mix[0]},${mix[1]},${mix[2]})`;
  }"""

# A global product search, present on every page (not just the per-store
# catalog search in store.py, which stays -- that one searches a single
# store's full catalog including items with no comparison page of their
# own). Distinct #gs* ids/classes so the two searches never collide on a
# store page, which has both at once.
GLOBAL_SEARCH_CSS = """
#gsWrap{ position:relative; margin:0 0 22px; }
#gsBox{ width:100%; font-family:'Assistant',sans-serif; font-size:1rem; padding:12px 16px;
  border:1.5px solid var(--line); border-radius:10px; background:var(--paper-raised); color:var(--ink); }
#gsResults{ display:none; position:absolute; top:calc(100% + 4px); right:0; left:0; z-index:20;
  background:var(--paper-raised); border:1px solid var(--line); border-radius:10px; box-shadow:var(--shadow);
  max-height:360px; overflow-y:auto; }
.gsrow{ display:flex; justify-content:space-between; gap:12px; padding:10px 16px; font-size:.92rem;
  color:var(--ink); text-decoration:none; border-bottom:1px solid var(--line); }
.gsrow:last-child{ border-bottom:none; }
.gsrow:hover{ background:var(--paper); }
.gsrow .p{ font-family:'IBM Plex Mono',monospace; color:var(--ink-muted); white-space:nowrap; }
.gsrow.gsempty{ color:var(--ink-muted); justify-content:center; }
"""

GLOBAL_SEARCH_HTML = """
  <div id="gsWrap">
    <input id="gsBox" type="text" placeholder="חיפוש מוצר באתר..." autocomplete="off" aria-label="חיפוש מוצר באתר">
    <div id="gsResults" aria-live="polite"></div>
  </div>
"""

# A single HTML-escaping helper, embedded (not imported -- there's no JS
# module system here, same reason LEAFLET_SCORE_COLOR_JS below is
# duplicated by string concatenation rather than shared at runtime) into
# every inline script that builds HTML from data-sourced text so there's
# one correct implementation instead of ad-hoc template-literal
# concatenation. Escapes quotes too (unlike a textContent/innerHTML trick),
# so it's safe in both text and attribute-value contexts.
ESC_HTML_JS = """function escHtml(s){
    return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
  }"""

# Fetches site/search-index.json once, lazily (on first focus/keystroke,
# not on every page load) -- verified via Network tab to fire exactly once
# per page regardless of how many characters get typed.
GLOBAL_SEARCH_SCRIPT = f"""<script>
(function(){{
  let items = null;
  let itemsLoaded = false;
  const box = document.getElementById("gsBox");
  const results = document.getElementById("gsResults");
  if (!box) return;

  {ESC_HTML_JS}

  function ensureLoaded(cb){{
    if (itemsLoaded) {{ cb(); return; }}
    // Only itemsLoaded (never items itself) marks success -- on a failed
    // fetch (flaky connection, ad-blocker) items stays [] but itemsLoaded
    // stays false, so the NEXT keystroke retries instead of silently and
    // permanently showing zero results for the rest of the page's life.
    fetch("/frodo-project/search-index.json").then(r=>r.json()).then(data=>{{ items = data; itemsLoaded = true; cb(); }}).catch(()=>{{ items = []; cb(); }});
  }}

  function render(query){{
    const q = query.trim();
    if (!q || q.length < 2){{ results.style.display = "none"; results.innerHTML = ""; return; }}
    const matches = items.filter(it => it.name.includes(q)).slice(0, 20);
    if (!matches.length){{
      results.style.display = "block";
      results.innerHTML = '<div class="gsrow gsempty">אין תוצאות</div>';
      return;
    }}
    results.style.display = "block";
    results.innerHTML = matches.map(it =>
      `<a class="gsrow" href="/frodo-project/product/?code=${{escHtml(it.code)}}"><span>${{escHtml(it.name)}}</span><span class="p">מ-₪${{it.cheap_price.toFixed(2)}}</span></a>`
    ).join("");
  }}

  box.addEventListener("input", (e)=>{{ ensureLoaded(()=> render(e.target.value)); }});
  box.addEventListener("focus", ()=>{{ ensureLoaded(()=>{{}}); }});
  document.addEventListener("click", (e)=>{{
    if (!e.target.closest("#gsWrap")) {{ results.style.display = "none"; }}
  }});
}})();
</script>"""


# The site's one visual motif, repeated everywhere a price range is shown
# (.range-point: a short/cheap bar and a tall/expensive bar) -- reused here
# as the brand mark instead of a decorative logo, so the icon in the nav
# and browser tab is literally a miniature of what the site actually shows,
# not generic branding. Navy-only on purpose: --good/--brick stay reserved
# for real computed cheap/expensive signals (see docs -- reusing them here
# would blur "this color means a real number" into "this color is just
# decoration").
BRAND_MARK_SVG = (
    '<svg class="brand-mark" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">'
    '<rect x="3" y="13" width="7" height="8" rx="1.5" fill="#1F3A5F"/>'
    '<rect x="14" y="3" width="7" height="18" rx="1.5" fill="#1F3A5F"/>'
    "</svg>"
)

FAVICON_HREF = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E"
    "%3Crect x='3' y='13' width='7' height='8' rx='1.5' fill='%231F3A5F'/%3E"
    "%3Crect x='14' y='3' width='7' height='18' rx='1.5' fill='%231F3A5F'/%3E"
    "%3C/svg%3E"
)

# Runs synchronously in <head>, before the stylesheet paints anything, so a
# visitor who already chose dark mode never sees a flash of the light theme
# first. The toggle button's own click handler (in THEME_TOGGLE_SCRIPT,
# loaded later) is what writes to this same key.
THEME_INIT_SCRIPT = """<script>(function(){
  try{ var t = localStorage.getItem("frodo-theme"); if (t) document.documentElement.dataset.theme = t; }catch(e){}
})();</script>"""

THEME_TOGGLE_SCRIPT = """<script>(function(){
  var btn = document.getElementById("themeToggle");
  if (!btn) return;
  function isEffectivelyDark(theme){
    return theme === "dark" || (!theme && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }
  function updateLabel(theme){
    btn.textContent = isEffectivelyDark(theme) ? "☀️" : "🌙";
    btn.setAttribute("aria-label", isEffectivelyDark(theme) ? "עבור למצב בהיר" : "עבור למצב כהה");
  }
  updateLabel(document.documentElement.dataset.theme || "");
  btn.addEventListener("click", function(){
    var current = document.documentElement.dataset.theme || "";
    var next = isEffectivelyDark(current) ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try{ localStorage.setItem("frodo-theme", next); }catch(e){}
    updateLabel(next);
  });
})();</script>"""


def thumb_html(image_url: str | None, alt: str = "") -> str:
    """A small product thumbnail, or a plain fallback box when there's no
    image -- never a broken `<img>`. `image_url` is `None` for most
    products (Open Food Facts coverage is partial), which is expected and
    not an error."""
    from html import escape

    if image_url:
        return f'<div class="thumb"><img src="{escape(image_url)}" alt="{escape(alt)}" loading="lazy"></div>'
    return '<div class="thumb empty">—</div>'


FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@500;700;900'
    "&family=Assistant:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap\" "
    'rel="stylesheet">'
)


def page_shell(title: str, current: str, body: str, extra_head: str = "", extra_script: str = "") -> str:
    """Wrap `body` HTML in the shared shell. `current` selects the bold nav
    link ('home' | 'map' | 'leaderboard' | 'methodology')."""
    from html import escape

    def nav_class(key: str) -> str:
        return "current" if key == current else ""

    # STORE_NAMES (scripts/build_site.py) has real store names containing a
    # literal `"` (e.g. 'שלי כ"ס- ויצמן') that flow into `title` unescaped --
    # <title> is a text context so that was harmless, but the og:title meta
    # tag added below reflects the same string into an HTML *attribute*,
    # where an unescaped `"` truncates the attribute and corrupts the tag.
    safe_title = escape(title)

    return f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<title>{safe_title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="השוואת מחירי מוצרי צריכה בין רשתות שיווק וסניפים בכפר סבא, מול בנצ'מרק רשמי -- נתונים רשמיים בלבד, מתעדכן יומית.">
<meta name="theme-color" content="#1F3A5F">
<meta property="og:site_name" content="Frodo Project">
<meta property="og:title" content="{safe_title}">
<meta property="og:description" content="השוואת מחירי מוצרי צריכה בין רשתות שיווק וסניפים בכפר סבא, מול בנצ'מרק רשמי.">
<meta property="og:locale" content="he_IL">
<link rel="icon" href="{FAVICON_HREF}">
{THEME_INIT_SCRIPT}
{FONT_LINK}
<style>{PAGE_CSS}</style>
<style>{GLOBAL_SEARCH_CSS}</style>
{extra_head}
</head>
<body>
<div class="page">
  <nav class="topnav">
    <a class="brand" href="/frodo-project/">{BRAND_MARK_SVG} Frodo Project</a>
    <a class="{nav_class('home')}" href="/frodo-project/">בית</a>
    <a class="{nav_class('map')}" href="/frodo-project/map/">מפה</a>
    <a class="{nav_class('leaderboard')}" href="/frodo-project/leaderboard/">דירוג סניפים</a>
    <a class="{nav_class('methodology')}" href="/frodo-project/methodology/">מתודולוגיה ומקורות</a>
    <span class="spacer"></span>
    <button class="theme-toggle" id="themeToggle" type="button" aria-label="החלף בין מצב בהיר וכהה"></button>
    <a href="https://github.com/yamor321/frodo-project" target="_blank" rel="noopener">קוד המקור</a>
  </nav>
{GLOBAL_SEARCH_HTML}
{body}
  <footer class="sitefoot">
    נבנה אוטומטית מנתונים רשמיים, מתעדכן יומית ·
    <a href="/frodo-project/methodology/">כל המקורות ואיך כל מספר מחושב</a>
  </footer>
</div>
{GLOBAL_SEARCH_SCRIPT}
{THEME_TOGGLE_SCRIPT}
{extra_script}
</body>
</html>
"""
