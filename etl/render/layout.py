"""Shared page shell (fonts, CSS tokens, header nav, footer) for every page
in site/, so the design system lives in one place instead of being copied
into each render_*.py module.
"""
from __future__ import annotations

PAGE_CSS = """
:root{
  --paper:#F3F1E9; --paper-raised:#FFFFFF; --ink:#191914; --ink-muted:#625F53;
  --line:#D8D4C5; --navy:#1F3A5F; --navy-soft:#DCE4EC; --brick:#A63A2E; --brick-soft:#F2E2DC;
  --good:#1E7A46; --good-soft:#DCEDE2; --accent:#B8823A; --accent-soft:#F2E4CA;
  --shadow:0 2px 4px rgba(25,25,20,.06), 0 16px 36px rgba(25,25,20,.10);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --paper:#15140F; --paper-raised:#1D1C15; --ink:#EFEDE3; --ink-muted:#A6A28E;
    --line:#332F22; --navy:#7FA6D6; --navy-soft:#1E2B3B; --brick:#E08069; --brick-soft:#3A2620;
    --good:#5FBF87; --good-soft:#1C3527; --accent:#D9A857; --accent-soft:#3B2F17;
    --shadow:0 2px 4px rgba(0,0,0,.4), 0 16px 36px rgba(0,0,0,.4);
  }
}
:root[data-theme="dark"]{
  --paper:#15140F; --paper-raised:#1D1C15; --ink:#EFEDE3; --ink-muted:#A6A28E;
  --line:#332F22; --navy:#7FA6D6; --navy-soft:#1E2B3B; --brick:#E08069; --brick-soft:#3A2620;
  --good:#5FBF87; --good-soft:#1C3527; --accent:#D9A857; --accent-soft:#3B2F17;
  --shadow:0 2px 4px rgba(0,0,0,.4), 0 16px 36px rgba(0,0,0,.4);
}
*{box-sizing:border-box;}
body{ margin:0; background:var(--paper); color:var(--ink); font-family:'Assistant',sans-serif;
  direction:rtl; -webkit-font-smoothing:antialiased; overflow-x:hidden;
  /* A barely-there paper-fleck texture instead of a flat fill -- part of
     the "editorial/warm" design direction (2026-08-30): cheap (pure CSS
     gradients, no image asset) and subtle enough to stay invisible in
     dark mode (same rgba values read as near-nothing on a dark base). */
  background-image:
    radial-gradient(circle at 18% 24%, rgba(25,25,20,.025) 0, transparent 38%),
    radial-gradient(circle at 82% 12%, rgba(25,25,20,.02) 0, transparent 42%),
    radial-gradient(circle at 64% 82%, rgba(25,25,20,.025) 0, transparent 40%),
    radial-gradient(circle at 8% 88%, rgba(25,25,20,.018) 0, transparent 35%);
  background-attachment:fixed;
}
/* Hand-drawn-feeling divider: a gently wavy rule instead of a straight
   border-bottom, used where a section break wants some warmth. */
.sketchy-divider{ height:10px; margin:0; border:none; background-repeat:repeat-x; background-size:40px 10px;
  background-position:center; opacity:.6;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='40' height='10'%3E%3Cpath d='M0,5 Q5,1 10,5 T20,5 T30,5 T40,5' fill='none' stroke='%23B8823A' stroke-width='1.5' stroke-linecap='round'/%3E%3C/svg%3E"); }
:root[data-theme="dark"] .sketchy-divider{
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='40' height='10'%3E%3Cpath d='M0,5 Q5,1 10,5 T20,5 T30,5 T40,5' fill='none' stroke='%23D9A857' stroke-width='1.5' stroke-linecap='round'/%3E%3C/svg%3E"); }
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]) .sketchy-divider{
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='40' height='10'%3E%3Cpath d='M0,5 Q5,1 10,5 T20,5 T30,5 T40,5' fill='none' stroke='%23D9A857' stroke-width='1.5' stroke-linecap='round'/%3E%3C/svg%3E");
  }
}
.page{ max-width:820px; margin:0 auto; padding:0 20px 80px; }
.ltr{ direction:ltr; unicode-bidi:isolate; font-variant-numeric:tabular-nums; }
a{ color:var(--navy); text-decoration-color:var(--navy); text-underline-offset:3px; }
a:hover{ text-decoration-thickness:2px; }
a:focus-visible, button:focus-visible, input:focus-visible{ outline:2px solid var(--navy); outline-offset:2px; }

nav.topnav{ display:flex; align-items:center; gap:18px; padding:18px 0; border-bottom:1px solid var(--line);
  margin-bottom:28px; font-size:.88rem; }
nav.topnav a{ color:var(--ink); text-decoration:none; font-weight:600; }
nav.topnav a.brand{ font-weight:800; font-size:1.05rem; color:var(--ink);
  display:inline-flex; align-items:center; gap:6px; }
nav.topnav .spacer{ flex:1; }
nav.topnav a.current{ color:var(--navy); }
nav.topnav .brand-mark{ display:inline-flex; align-items:flex-end; gap:2px; margin-inline-end:2px; }
button.theme-toggle{ font-size:1rem; line-height:1; background:none; border:1px solid var(--line);
  border-radius:999px; width:30px; height:30px; cursor:pointer; color:var(--ink); }
button.theme-toggle:hover{ border-color:var(--navy); }

h1{ font-weight:800; font-size:clamp(1.8rem,5vw,2.6rem); line-height:1.15; letter-spacing:-.01em;
  margin:0 0 14px; text-wrap:balance; }
h2{ font-weight:800; font-size:1.3rem; letter-spacing:-.005em; margin:0 0 10px; }
.kicker{ font-family:'Assistant',sans-serif; font-weight:700; font-size:.76rem; letter-spacing:.08em; text-transform:uppercase;
  color:var(--accent); margin-bottom:10px; }
.lede{ color:var(--ink-muted); font-size:1.05rem; line-height:1.6; max-width:60ch; margin:0 0 8px; }

.card{ background:var(--paper-raised); border:1px solid var(--line); border-radius:14px; padding:18px 20px;
  box-shadow:var(--shadow); }
.chip{ font-family:'Assistant',sans-serif; font-size:.78rem; font-weight:600; padding:4px 10px;
  border-radius:999px; white-space:nowrap; display:inline-block; }
.chip.warm{ background:var(--brick-soft); color:var(--brick); }
.chip.good{ background:var(--good-soft); color:var(--good); }
.chip.neutral{ background:var(--paper); color:var(--ink-muted); }

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

/* 6 links + brand + theme toggle + external link no longer fit one row on a
   narrow phone -- scrolls as a single row (like tabs) instead of wrapping to
   2-3 rows (which would push all page content down) or overflowing the whole
   page horizontally (the bug this fixes: overflow-x:hidden on body alone
   would've just clipped the nav with no way to reach the hidden links). */
@media (max-width:640px){
  nav.topnav{ overflow-x:auto; flex-wrap:nowrap; -webkit-overflow-scrolling:touch;
    scrollbar-width:none; }
  nav.topnav::-webkit-scrollbar{ display:none; }
  nav.topnav a, nav.topnav button, nav.topnav .spacer{ flex-shrink:0; }
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
/* Leaflet isn't RTL-aware -- without this, tooltip/popup auto-placement
   (which assumes LTR) miscalculates on this dir="rtl" page. */
.leaflet-container{ direction:ltr; }
.legend-scale{ display:flex; align-items:center; gap:10px; margin-top:12px; font-size:.8rem; color:var(--ink-muted); }
.legend-scale .bar{ width:140px; height:10px; border-radius:6px; background:linear-gradient(to left, var(--good), #C9C4A8, var(--brick)); }
#nearest{ margin-top:14px; padding:14px 18px; border-radius:12px; background:var(--navy-soft); color:var(--navy); font-size:.92rem; display:none; }
#nearest b{ color:var(--ink); }
/* Targets the inner element passed as divIcon html -- Leaflet puts
   leaflet-marker-icon on the outer wrapper it creates, not this element.
   .store-pin (a flat div, still used by the "online" triangle -- see
   map.py's pinIcon()) gets a plain border+shadow; every other format is an
   inline SVG pin with its own gradient fill and white stroke already baked
   in, so it only needs the drop-shadow here, not a border. */
.leaflet-marker-icon .store-pin{ border:1.5px solid #fff; box-shadow:0 1px 3px rgba(0,0,0,.25); }
.leaflet-marker-icon svg{ filter:drop-shadow(0 2px 3px rgba(0,0,0,.3)); overflow:visible; }
.leaflet-tile-pane{ filter:grayscale(45%) saturate(65%) brightness(1.08) contrast(.92); }
.store-popup{ font-family:'Assistant',sans-serif; min-width:170px; }
.store-popup b{ font-size:.98rem; }
.store-popup .meta{ font-size:.82rem; color:var(--ink-muted); margin-top:2px; }
.store-popup a.openbtn{ display:inline-block; margin-top:8px; font-weight:700; color:var(--navy); text-decoration:none; }
.store-popup a.openbtn:hover{ text-decoration:underline; }
"""

# Shared "show N more" progressive-reveal widget, used wherever a list is
# rendered fully server-side (small enough -- leaderboard rows, homepage
# spread cards) but only the first few should show by default. Rows past
# the first batch carry data-reveal-group="X" and start with the
# reveal-hidden class; a button with class="reveal-more-btn"
# data-reveal-group="X" un-hides the next batch on each click. Plain
# server-rendered rows revealed by class toggle, not a fetch -- there's
# nothing to fetch, everything's already in the page.
REVEAL_MORE_CSS = """
.reveal-more-btn{ display:block; margin:16px auto 0; padding:9px 26px; border-radius:999px;
  border:1.5px solid var(--navy); background:var(--navy-soft); color:var(--navy); font-weight:700;
  font-size:.88rem; cursor:pointer; font-family:'Assistant',sans-serif; }
.reveal-more-btn:hover{ background:var(--navy); color:#fff; }
.reveal-hidden{ display:none; }
"""

REVEAL_MORE_SCRIPT = """<script>
(function(){
  document.querySelectorAll(".reveal-more-btn").forEach(function(btn){
    btn.addEventListener("click", function(){
      var group = btn.dataset.revealGroup;
      var step = parseInt(btn.dataset.revealStep || "5", 10);
      var hidden = document.querySelectorAll('[data-reveal-group="' + group + '"].reveal-hidden');
      for (var i = 0; i < hidden.length && i < step; i++) hidden[i].classList.remove("reveal-hidden");
      if (hidden.length <= step) btn.style.display = "none";
    });
  });
})();
</script>"""

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
#gsWrap{ position:relative; margin:0 0 6px; }
#gsBox{ width:100%; font-family:'Assistant',sans-serif; font-size:1rem; padding:12px 16px;
  border:1.5px solid var(--line); border-radius:10px; background:var(--paper-raised); color:var(--ink); }
#gsResults{ display:none; position:absolute; top:calc(100% + 4px); right:0; left:0; z-index:20;
  background:var(--paper-raised); border:1px solid var(--line); border-radius:10px; box-shadow:var(--shadow);
  max-height:360px; overflow-y:auto; }
.gsrow{ display:flex; justify-content:space-between; align-items:center; gap:12px; padding:10px 16px; font-size:.92rem;
  color:var(--ink); text-decoration:none; border-bottom:1px solid var(--line); }
.gsrow:last-child{ border-bottom:none; }
.gsrow:hover{ background:var(--paper); }
.gsrow .gsname{ display:flex; flex-direction:column; gap:2px; min-width:0; }
.gsrow .gscoverage{ font-size:.76rem; color:var(--ink-muted); }
.gsrow .gsbadge{ display:inline-block; margin-inline-end:6px; padding:1px 7px; border-radius:999px;
  background:var(--brick-soft); color:var(--brick); font-size:.74rem; font-weight:700; }
.gsrow .p{ font-weight:600; color:var(--ink-muted); white-space:nowrap; }
.gsrow.gsempty{ color:var(--ink-muted); justify-content:center; }
#gsTip{ font-size:.78rem; color:var(--ink-muted); margin:0 2px 22px; }
"""

GLOBAL_SEARCH_HTML = """
  <div id="gsWrap">
    <input id="gsBox" type="text" placeholder="חיפוש מוצר באתר..." autocomplete="off" aria-label="חיפוש מוצר באתר">
    <div id="gsResults" aria-live="polite"></div>
  </div>
  <p id="gsTip">שמות המוצרים כפי שהרשתות עצמן מפרסמות אותם -- לפעמים מקוצרים או עם * (מסמן לרוב מבצע או כמות באריזה); ריחוף/מגע על שם מציג אותו במלואו.</p>
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

  // Some chains wrap a promo marker literally around the item name in
  // their own published data (e.g. "*מבצע* משחת שיניים ה") -- there's no
  // separate promo/discount field in the source (see docs/sources.md), so
  // this is the only signal we have. Strip the wrapper and show it as a
  // small badge instead of raw asterisks; a bare "*" elsewhere in a name
  // (chains also use it as a pack-count multiplication sign) is left as-is
  // and explained by the fixed #gsTip note instead, since it's not
  // reliably a promo marker.
  function formatProductName(name){{
    const m = /^\\*\\s*מבצע\\s*\\*\\s*/.exec(name);
    return m ? {{badge: "מבצע", clean: name.slice(m[0].length)}} : {{badge: null, clean: name}};
  }}

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
    results.innerHTML = matches.map(it => {{
      const f = formatProductName(it.name);
      const badge = f.badge ? `<span class="gsbadge">${{escHtml(f.badge)}}</span>` : "";
      const coverage = it.n ? `<small class="gscoverage">נמצא ב-${{it.n}} סניפים</small>` : "";
      return `<a class="gsrow" href="/frodo-project/product/?code=${{escHtml(it.code)}}">` +
        `<span class="gsname">` +
        `<span class="name" title="${{escHtml(it.name)}}">${{badge}}${{escHtml(f.clean)}}</span>` +
        `${{coverage}}</span>` +
        `<span class="p">מ-₪${{it.cheap_price.toFixed(2)}}</span></a>`;
    }}).join("");
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

# A small hand-drawn-feeling accent icon (a map pin sketched with a
# slightly uneven stroke, not a crisp geometric one) -- part of the
# "editorial/warm" design pass (2026-08-30), used sparingly next to a CTA
# or section heading, never as a functional map marker (etl/render/map.py
# keeps its own precise divIcon pins for that).
PIN_ICON_SVG = (
    '<svg class="pin-icon" width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" fill="none">'
    '<path d="M12 3 C7 3 4.5 6.3 4.6 10 C4.7 14.2 9.3 18.5 11.7 20.8 '
    'C11.9 21 12.1 21 12.3 20.8 C14.8 18.4 19.3 14 19.4 9.8 C19.5 6.1 17 3 12 3 Z" '
    'stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>'
    '<circle cx="12" cy="10.5" r="2.6" stroke="currentColor" stroke-width="1.5"/>'
    "</svg>"
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


# Font choices, revised a second time (2026-08-30) after "it still doesn't
# look uniform -- heading one font, numbers another, rest of the site a
# third." That complaint was correct and diagnosed properly, not just
# patched again by swapping in yet another font: the previous system mixed
# THREE unrelated type families (Suez One, a Hebrew display serif; Fraunces,
# a Latin-only high-contrast editorial serif; Assistant, a neutral sans) --
# three different letterform styles, stroke contrasts and proportions, none
# of them drawn to sit together, which is exactly why it read as
# uncoordinated no matter how each looked alone (confirmed against real
# typography guidance: multi-script pairing needs deliberate weight/size
# harmonization, and mixing typefaces "for personality" without that is a
# classic amateur tell). The actual fix real high-end products use is the
# opposite of adding a third font: ONE properly engineered multi-script
# family, used everywhere, with hierarchy carried by weight and size alone.
# Assistant already qualifies -- its Hebrew was designed specifically to
# complement its own Latin (built on Adobe's Source Sans), so its own
# numerals were drawn as part of the same family, not borrowed from
# elsewhere. So: Suez One and Fraunces are both gone. Assistant, at a real
# weight range (300-800), is now the only typeface on the site.
FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;500;600;700;800&display=swap" '
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
