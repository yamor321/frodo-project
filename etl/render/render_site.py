"""Renders site/index.html (brief section 3, layer 4) from already-computed
data. This module does no fetching and no computation of its own -- it only
turns SpreadResult/GapResult records into the final HTML file that gets
committed and served by GitHub Pages. Keeping rendering separate from
computation is what lets layer 4 stay "read from ready tables only" (brief
section 3): no live queries, nothing here can fail against a live source.

Uses the shared etl/render/layout.py shell (fonts/tokens/nav/footer) so the
homepage matches every other page instead of carrying its own separate
design system.
"""
from __future__ import annotations

from html import escape

from etl.scoring.benchmark_gap import GapResult
from etl.scoring.cross_branch_spread import SpreadResult

INDEX_CSS = """
.headline-stat{ margin:26px 0 30px; padding:22px 24px; background:var(--navy); color:#fff;
  border-radius:16px; box-shadow:var(--shadow); }
.headline-stat .num{ font-family:'Frank Ruhl Libre',serif; font-weight:900; font-size:clamp(1.6rem,5vw,2.4rem);
  font-variant-numeric:tabular-nums; line-height:1.2; }
.headline-stat p{ margin:10px 0 0; opacity:.92; font-size:.98rem; max-width:52ch; line-height:1.55; }
.headline-stat a.cta-map{ display:inline-flex; align-items:center; gap:8px; margin-top:16px; padding:11px 22px;
  background:#fff; color:var(--navy); border-radius:999px; font-weight:700; text-decoration:none; font-size:.92rem; }
.headline-stat a.cta-map:hover{ opacity:.9; }

.storecard{ display:flex; flex-wrap:wrap; gap:8px 22px; align-items:baseline; margin-top:20px;
  padding:14px 18px; background:var(--paper-raised); border:1px solid var(--line); border-radius:10px; }
.storecard .meta{ font-size:.85rem; color:var(--ink-muted); }

section.list{ display:flex; flex-direction:column; gap:12px; margin:20px 0 30px; }
.card{ display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; }
.card .name{ font-size:1.02rem; font-weight:600; }
.card .name small{ display:block; font-weight:400; color:var(--ink-muted); font-size:.82rem; margin-top:3px; }
.card .prices{ display:flex; align-items:baseline; gap:14px; flex-wrap:wrap; }
.price-actual{ font-family:'IBM Plex Mono',monospace; font-weight:600; font-size:1.15rem; font-variant-numeric:tabular-nums; }
.price-ref{ font-size:.85rem; color:var(--ink-muted); font-variant-numeric:tabular-nums; }
.chip.neutral{ background:var(--paper); color:var(--ink-muted); }
.card.spread{ flex-direction:column; align-items:flex-start; gap:12px; }
.range{ display:flex; align-items:center; gap:14px; flex-wrap:wrap; }
.range-point{ display:flex; flex-direction:column; gap:2px; }
.range-point b{ font-family:'IBM Plex Mono',monospace; font-weight:600; font-size:1.2rem; font-variant-numeric:tabular-nums; }
.range-point.cheap b{ color:var(--good); }
.range-point small{ color:var(--ink-muted); font-size:.78rem; }
.range-arrow{ color:var(--ink-muted); font-size:1.2rem; }

h2.section-title{ font-size:1.15rem; margin:40px 0 6px; }
p.section-sub{ color:var(--ink-muted); font-size:.92rem; margin:0 0 16px; max-width:60ch; line-height:1.55; }
@media (max-width:520px){ .card{ flex-direction:column; align-items:flex-start; } }
"""


def _spread_card(s: SpreadResult) -> str:
    coverage = f' <small class="ltr" style="font-weight:400;color:var(--ink-muted)">· נמצא ב-{s.num_stores} סניפים</small>' if s.num_stores >= 5 else ""
    return f"""
    <div class="card spread">
      <div class="name"><a href="/frodo-project/product/{s.item_code}/">{escape(s.item_name)}</a>{coverage}</div>
      <div class="range">
        <span class="range-point cheap"><b class="ltr">₪{s.cheap_price:.2f}</b><small><a href="/frodo-project/store/{s.cheap_store_id}/">{escape(s.cheap_store_name)}</a></small></span>
        <span class="range-arrow">←</span>
        <span class="range-point"><b class="ltr">₪{s.expensive_price:.2f}</b><small><a href="/frodo-project/store/{s.expensive_store_id}/">{escape(s.expensive_store_name)}</a></small></span>
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
    from etl.render.layout import page_shell

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

    body = f"""
  <div class="kicker">Frodo Project · פיילוט כפר סבא</div>
  <h1>אותו מוצר, אותה עיר, פערי מחיר אמיתיים</h1>
  <p class="lede">כמה רשתות שיווק מפעילות סניפים בכפר סבא, בפורמטים שונים. השוואה בין המחירים שכל רשת מפרסמת בעצמה — אותו ברקוד, אותו יום — מראה פערים אמיתיים בין הסניפים על אותו מוצר בדיוק.</p>
  <div class="storecard">
    <b>כפר סבא · השוואת מחירים בין סניפים</b>
    <span class="meta ltr">עודכן {escape(generated_at)}</span>
  </div>
{hero_html}
  <h2 class="section-title">המוצרים עם הפער הגדול ביותר בין סניפים</h2>
  <p class="section-sub">כל שורה: אותו ברקוד (אותו מוצר פיזי), שנמצא ב-4 סניפים לפחות, באותו יום. <a href="/frodo-project/branches/">כל {len(spreads):,} הפערים ←</a></p>

  <section class="list">{spread_cards}
  </section>

  <h2 class="section-title">מול המחיר המפוקח בחוק</h2>
  <p class="section-sub">מוצרי חלב שאפשר להתאים בביטחון למחיר המקסימלי הרשמי, לפי הנתונים הרשמיים של משרד הכלכלה/החקלאות.</p>

  <section class="list">{gap_cards}
  </section>
"""

    return page_shell("מחירי סופרמרקטים כפר סבא — Frodo Project", "home", body, f"<style>{INDEX_CSS}</style>")
