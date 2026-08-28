"""Renders the static site (brief section 3, layer 4) from already-computed
data. This module does no fetching and no computation of its own -- it only
turns SpreadResult/GapResult records into the final HTML file that gets
committed and served by GitHub Pages. Keeping rendering separate from
computation is what lets layer 4 stay "read from ready tables only" (brief
section 3): no live queries, nothing here can fail against a live source.
"""
from __future__ import annotations

from html import escape

from etl.scoring.benchmark_gap import GapResult
from etl.scoring.cross_branch_spread import SpreadResult

PAGE_CSS = """
:root{
  --paper:#F1F3EC; --paper-raised:#FBFBF6; --ink:#1B2118; --ink-muted:#5C6754;
  --line:#DCE0D2; --brand:#2F5233; --brand-ink:#1D3320; --brand-soft:#E1E8D9;
  --good:#1F6E5C; --good-soft:#DDEFE9; --neutral-chip:#EEF0E7; --neutral-ink:#4B5545;
  --warm:#B8632E; --warm-soft:#F5E4D4;
  --shadow:0 1px 2px rgba(27,33,24,.06), 0 10px 28px rgba(27,33,24,.07);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --paper:#12160F; --paper-raised:#191F14; --ink:#E9EDE3; --ink-muted:#9BAA8E;
    --line:#2B3323; --brand:#7FBF8E; --brand-ink:#CFEAD3; --brand-soft:#1E2C1D;
    --good:#5FC7A9; --good-soft:#183A30; --neutral-chip:#232B1E; --neutral-ink:#AAB79C;
    --warm:#E2A159; --warm-soft:#382712;
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 10px 28px rgba(0,0,0,.35);
  }
}
:root[data-theme="dark"]{
  --paper:#12160F; --paper-raised:#191F14; --ink:#E9EDE3; --ink-muted:#9BAA8E;
  --line:#2B3323; --brand:#7FBF8E; --brand-ink:#CFEAD3; --brand-soft:#1E2C1D;
  --good:#5FC7A9; --good-soft:#183A30; --neutral-chip:#232B1E; --neutral-ink:#AAB79C;
  --warm:#E2A159; --warm-soft:#382712;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 10px 28px rgba(0,0,0,.35);
}
*{box-sizing:border-box;}
body{ margin:0; background:var(--paper); color:var(--ink);
  font-family:'Assistant',-apple-system,'Segoe UI',sans-serif; direction:rtl;
  -webkit-font-smoothing:antialiased; }
.page{ max-width:840px; margin:0 auto; padding:36px 20px 90px; }
h1,h2{ font-family:'Rubik',-apple-system,sans-serif; font-weight:800; text-wrap:balance; margin:0; }
.ltr{ direction:ltr; unicode-bidi:isolate; font-family:'IBM Plex Mono',monospace; }
a{ color:var(--brand-ink); text-decoration-color:var(--brand); text-underline-offset:3px; }
a:hover{ text-decoration-thickness:2px; }
nav.topnav{ display:flex; align-items:center; gap:18px; padding:24px 0 0; font-size:.88rem; }
nav.topnav a{ color:var(--ink); text-decoration:none; font-weight:600; }
nav.topnav a.brand{ font-family:'Rubik',sans-serif; font-weight:800; font-size:1.05rem; }
.cta-map{ display:inline-flex; align-items:center; gap:8px; margin-top:16px; padding:11px 22px;
  background:#fff; color:var(--brand-ink); border-radius:999px; font-weight:700; text-decoration:none;
  font-size:.92rem; }
.cta-map:hover{ opacity:.9; }
header.hero{ padding-bottom:26px; border-bottom:2px solid var(--ink); margin-bottom:8px; }
.eyebrow{ display:inline-flex; align-items:center; gap:8px; font-size:.78rem; font-weight:700;
  letter-spacing:.04em; color:var(--brand-ink); background:var(--brand-soft);
  padding:5px 12px; border-radius:999px; margin-bottom:16px; }
h1{ font-size:clamp(1.9rem,5vw,2.6rem); line-height:1.15; margin-bottom:14px; }
.lede{ color:var(--ink-muted); font-size:1.08rem; line-height:1.6; max-width:56ch; }
.storecard{ display:flex; flex-wrap:wrap; gap:8px 22px; align-items:baseline; margin-top:22px;
  padding:14px 18px; background:var(--paper-raised); border:1px solid var(--line); border-radius:10px; }
.storecard .meta{ font-size:.85rem; color:var(--ink-muted); }
.headline-stat{ margin:34px 0 30px; padding:22px 24px; background:var(--brand); color:#fff;
  border-radius:16px; box-shadow:var(--shadow); }
.headline-stat .num{ font-family:'Rubik',sans-serif; font-weight:800; font-size:clamp(1.6rem,5vw,2.4rem);
  font-variant-numeric:tabular-nums; line-height:1.2; }
.headline-stat p{ margin:10px 0 0; opacity:.92; font-size:.98rem; max-width:52ch; line-height:1.55; }
section.list{ display:flex; flex-direction:column; gap:14px; margin:30px 0; }
.card{ background:var(--paper-raised); border:1px solid var(--line); border-radius:14px;
  padding:18px 20px; box-shadow:var(--shadow); display:flex; align-items:center;
  justify-content:space-between; gap:16px; flex-wrap:wrap; }
.card .name{ font-size:1.02rem; font-weight:600; }
.card .name small{ display:block; font-weight:400; color:var(--ink-muted); font-size:.82rem; margin-top:3px; }
.card .prices{ display:flex; align-items:baseline; gap:14px; flex-wrap:wrap; }
.price-actual{ font-family:'Rubik',sans-serif; font-weight:800; font-size:1.5rem; font-variant-numeric:tabular-nums; }
.price-ref{ font-size:.85rem; color:var(--ink-muted); font-variant-numeric:tabular-nums; }
.chip{ font-family:'IBM Plex Mono',monospace; font-size:.8rem; font-weight:500; padding:4px 10px;
  border-radius:999px; white-space:nowrap; }
.chip.neutral{ background:var(--neutral-chip); color:var(--neutral-ink); }
.chip.warm{ background:var(--warm-soft); color:var(--warm); }
.card.spread{ flex-direction:column; align-items:flex-start; gap:12px; }
.range{ display:flex; align-items:center; gap:14px; flex-wrap:wrap; }
.range-point{ display:flex; flex-direction:column; gap:2px; }
.range-point b{ font-family:'Rubik',sans-serif; font-weight:800; font-size:1.35rem; font-variant-numeric:tabular-nums; }
.range-point.cheap b{ color:var(--good); }
.range-point small{ color:var(--ink-muted); font-size:.78rem; }
.range-arrow{ color:var(--ink-muted); font-size:1.2rem; }
.transparency-note{ font-size:.85rem; color:var(--ink-muted); line-height:1.6;
  border-inline-start:3px solid var(--line); padding:10px 16px; margin:26px 0; }
h2.section-title{ font-size:1.15rem; margin:44px 0 6px; }
p.section-sub{ color:var(--ink-muted); font-size:.92rem; margin:0 0 18px; max-width:60ch; line-height:1.55; }
footer{ margin-top:50px; padding-top:20px; border-top:1px solid var(--line); }
footer h2{ font-size:1rem; margin-bottom:10px; }
footer ul{ margin:0; padding-inline-start:20px; font-size:.86rem; color:var(--ink-muted); line-height:1.9; }
.feedback-tag{ margin-top:30px; font-size:.8rem; color:var(--ink-muted); text-align:center; }
@media (max-width:520px){ .page{ padding:24px 14px 70px; } .card{ flex-direction:column; align-items:flex-start; } }
"""


def _spread_card(s: SpreadResult) -> str:
    coverage = f' <small class="ltr" style="font-weight:400;color:var(--ink-muted)">· נמצא ב-{s.num_stores} סניפים</small>' if s.num_stores >= 5 else ""
    return f"""
    <div class="card spread">
      <div class="name">{escape(s.item_name)}{coverage}</div>
      <div class="range">
        <span class="range-point cheap"><b class="ltr">₪{s.cheap_price:.2f}</b><small>{escape(s.cheap_store_name)}</small></span>
        <span class="range-arrow">←</span>
        <span class="range-point"><b class="ltr">₪{s.expensive_price:.2f}</b><small>{escape(s.expensive_store_name)}</small></span>
      </div>
      <span class="chip warm">+{s.spread_pct*100:.1f}%</span>
    </div>"""


def _gap_card(g: GapResult) -> str:
    chip_class = "warm" if (g.gap_pct or 0) > 0.01 else "neutral"
    sign = "+" if (g.gap_pct or 0) > 0 else ""
    controlled_name = escape(", ".join(g.controlled_product_names))
    return f"""
    <div class="card">
      <div class="name">{escape(g.item_name)}<small>מפוקח כ: {controlled_name}</small></div>
      <div class="prices">
        <span class="price-actual ltr">₪{g.actual_price:.2f}</span>
        <span class="price-ref ltr">מקסימום: ₪{g.controlled_consumer_price:.2f}</span>
        <span class="chip {chip_class}">{sign}{g.gap_pct*100:.1f}%</span>
      </div>
    </div>"""


def render_index_html(
    spreads: list[SpreadResult],
    gaps: list[GapResult],
    generated_at: str,
    top_n_spreads: int = 10,
) -> str:
    unambiguous_gaps = [g for g in gaps if not g.ambiguous]
    top_spreads = spreads[:top_n_spreads]
    hero = top_spreads[0] if top_spreads else None

    spread_cards = "\n".join(_spread_card(s) for s in top_spreads)
    gap_cards = "\n".join(_gap_card(g) for g in unambiguous_gaps)

    hero_html = (
        f"""
  <div class="headline-stat">
    <div class="num ltr">₪{hero.cheap_price:.2f} ← ₪{hero.expensive_price:.2f}</div>
    <p><b>{escape(hero.item_name)}</b> — אותו ברקוד, אותה רשת, אותה עיר. ₪{hero.cheap_price:.2f}
    ב{escape(hero.cheap_store_name)}, ₪{hero.expensive_price:.2f} ב{escape(hero.expensive_store_name)}.
    פער של {hero.spread_pct*100:.1f}% על אותו מוצר בדיוק.</p>
    <a class="cta-map" href="/frodo-project/map/">כנסו למפה — ראו את הסניפים לידכם ←</a>
  </div>"""
        if hero
        else ""
    )

    return f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<title>מחירי חלב כפר סבא</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Rubik:wght@500;700;800&family=Assistant:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{PAGE_CSS}</style>
</head>
<body>
<div class="page">

  <nav class="topnav"><a class="brand" href="/frodo-project/">Frodo Project</a><a href="/frodo-project/map/">מפה</a></nav>

  <header class="hero">
    <span class="eyebrow">Frodo Project · פיילוט כפר סבא</span>
    <h1>אותו מוצר, אותה עיר, פערי מחיר אמיתיים</h1>
    <p class="lede">שופרסל מפעילה כמה סניפים בכפר סבא, בפורמטים שונים. השוואה בין המחירים שהרשת עצמה מפרסמת — אותו ברקוד, אותו יום — מראה פערים בין הסניפים על אותו מוצר בדיוק.</p>
    <div class="storecard">
      <b>שופרסל · סניפי כפר סבא</b>
      <span class="meta ltr">עודכן {escape(generated_at)}</span>
    </div>
  </header>
{hero_html}
  <h2 class="section-title">המוצרים עם הפער הגדול ביותר בין סניפים</h2>
  <p class="section-sub">כל שורה: אותו ברקוד (אותו מוצר פיזי), שנמצא ב-4 סניפים לפחות, באותו יום.</p>

  <section class="list">{spread_cards}
  </section>

  <h2 class="section-title">מול המחיר המפוקח בחוק</h2>
  <p class="section-sub">מוצרי חלב שאפשר להתאים בביטחון למחיר המקסימלי הרשמי, לפי הנתונים הרשמיים של משרד הכלכלה/החקלאות.</p>

  <section class="list">{gap_cards}
  </section>

  <footer>
    <h2>מקורות ושיטה</h2>
    <ul>
      <li><a href="https://prices.shufersal.co.il/" target="_blank" rel="noopener">פורטל שקיפות המחירים של שופרסל</a> — קובצי המחירים המלאים של כל סניף, כפי שהרשת מחויבת לפרסם בחוק.</li>
      <li><a href="https://data.gov.il/dataset/price_controlled_consumer_products" target="_blank" rel="noopener">מאגר המחירים המפוקחים, data.gov.il</a> — משרד הכלכלה והתעשייה ומשרד החקלאות.</li>
      <li><a href="https://www.nevo.co.il/law_html/law01/500_150.htm" target="_blank" rel="noopener">תקנות קידום התחרות בענף המזון (שקיפות מחירים), התשע"ה-2014</a> — הבסיס החוקי לפרסום קובצי המחירים.</li>
    </ul>
    <p class="feedback-tag">נוצר אוטומטית מנתוני האמת האחרונים · עוד רשתות בכפר סבא, ואז ערים נוספות, בדרך.</p>
  </footer>

</div>
</body>
</html>
"""
