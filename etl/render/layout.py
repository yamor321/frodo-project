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
nav.topnav a.brand{ font-family:'Frank Ruhl Libre',serif; font-weight:700; font-size:1.05rem; color:var(--ink); }
nav.topnav .spacer{ flex:1; }
nav.topnav a.current{ color:var(--navy); }

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

.thumb{ width:44px; height:44px; flex:none; border-radius:8px; overflow:hidden; background:var(--paper);
  border:1px solid var(--line); display:flex; align-items:center; justify-content:center; }
.thumb img{ width:100%; height:100%; object-fit:contain; }
.thumb.empty{ color:var(--ink-muted); font-size:1.2rem; }

footer.sitefoot{ margin-top:50px; padding-top:20px; border-top:1px solid var(--line); font-size:.84rem;
  color:var(--ink-muted); line-height:1.7; }
footer.sitefoot a{ color:var(--navy); }
"""

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
    link ('home' | 'map')."""

    def nav_class(key: str) -> str:
        return "current" if key == current else ""

    return f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{FONT_LINK}
<style>{PAGE_CSS}</style>
{extra_head}
</head>
<body>
<div class="page">
  <nav class="topnav">
    <a class="brand" href="/frodo-project/">Frodo Project</a>
    <a class="{nav_class('home')}" href="/frodo-project/">בית</a>
    <a class="{nav_class('map')}" href="/frodo-project/map/">מפה</a>
    <span class="spacer"></span>
    <a href="https://github.com/yamor321/frodo-project" target="_blank" rel="noopener">קוד המקור</a>
  </nav>
{body}
  <footer class="sitefoot">
    <a href="https://prices.shufersal.co.il/" target="_blank" rel="noopener">פורטל שקיפות המחירים של שופרסל</a> ·
    נבנה אוטומטית מנתונים רשמיים, מתעדכן יומית.
  </footer>
</div>
{extra_script}
</body>
</html>
"""
