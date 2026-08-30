"""Renders site/index.html (brief section 3, layer 4) from already-computed
data. This module does no fetching and no computation of its own -- it only
turns SpreadResult records into the final HTML file that gets
committed and served by GitHub Pages. Keeping rendering separate from
computation is what lets layer 4 stay "read from ready tables only" (brief
section 3): no live queries, nothing here can fail against a live source.

Uses the shared etl/render/layout.py shell (fonts/tokens/nav/footer) so the
homepage matches every other page instead of carrying its own separate
design system.
"""
from __future__ import annotations

from html import escape

from etl.scoring.active_promos import ActivePromo, PromoHighlight, format_promo_end_date
from etl.scoring.cross_branch_spread import SpreadResult
from etl.scoring.store_ranking import StoreScore

# Number of leaderboard/spread rows visible before a "show 5 more" click --
# the rest are rendered up-front (not fetched) but start hidden, per
# REVEAL_MORE_SCRIPT in layout.py.
REVEAL_BATCH = 5

INDEX_CSS = """
.headline-stat{ margin:26px 0 30px; padding:22px 24px; background:var(--navy); color:#fff;
  border-radius:16px; box-shadow:var(--shadow); }
.headline-stat .num{ font-weight:800; font-size:clamp(1.6rem,5vw,2.4rem);
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
.price-actual{ font-weight:700; font-size:1.15rem; font-variant-numeric:tabular-nums; }
.price-ref{ font-size:.85rem; color:var(--ink-muted); font-variant-numeric:tabular-nums; }
.card.spread{ flex-direction:column; align-items:stretch; gap:8px; padding:14px 18px; }
.card.spread .top-row{ display:flex; align-items:center; gap:10px; }
.card.spread .top-row .name{ flex:1; min-width:0; }
.range{ display:flex; align-items:baseline; gap:10px; flex-wrap:wrap; }
.range-point{ display:inline-flex; align-items:baseline; gap:5px; }
.range-point b{ font-weight:700; font-size:1rem; font-variant-numeric:tabular-nums; }
.range-point.cheap b{ color:var(--good); }
.range-point small{ color:var(--ink-muted); font-size:.8rem; }
.range-arrow{ color:var(--ink-muted); font-size:1rem; }

h2.section-title{ font-size:1.15rem; margin:40px 0 6px; }
p.section-sub{ color:var(--ink-muted); font-size:.92rem; margin:0 0 16px; max-width:60ch; line-height:1.55; }
@media (max-width:520px){ .card{ flex-direction:column; align-items:flex-start; } }

.lb-list{ display:flex; flex-direction:column; gap:8px; margin:20px 0 10px; }
.lb-row{ display:flex; align-items:center; gap:14px; padding:10px 16px; background:var(--paper-raised);
  border:1px solid var(--line); border-radius:10px; }
.lb-row .lb-rank{ font-weight:600; color:var(--ink-muted); width:1.6em; text-align:center; flex-shrink:0; }
.lb-row a{ flex:1; min-width:0; font-weight:600; font-size:.94rem; line-height:1.3; }
.lb-row .lb-score-wrap{ display:flex; align-items:center; gap:8px; flex-shrink:0; }
.lb-row .lb-bar{ width:80px; height:7px; border-radius:4px; background:var(--line); overflow:hidden; }
.lb-row .lb-bar-fill{ display:block; height:100%; border-radius:4px; }
.lb-row .lb-score-num{ font-weight:600; font-size:.88rem; width:2.4em; text-align:left; }
"""


def _range_price_html(price: float, promo: ActivePromo | None) -> str:
    """The regular price, or -- when this exact (item, store) has a real
    confirmed active promo (see etl/scoring/active_promos.py) -- the
    regular price struck through next to the promo price and a "מבצע"
    badge, same visual language as the store/product pages. Added here
    (homepage spread cards) after a user report: the badge existed on
    product/store pages but never on the homepage, the first page anyone
    actually lands on -- so the feature was real but effectively
    invisible to a casual visitor who never clicks through."""
    if promo is None:
        return f'<b class="ltr">₪{price:.2f}</b>'
    end_label = format_promo_end_date(promo.end_datetime)
    end_html = f" עד {end_label}" if end_label else ""
    return (
        f'<b class="ltr" style="text-decoration:line-through;color:var(--ink-muted);font-weight:400;font-size:.85rem;">₪{price:.2f}</b> '
        f'<b class="ltr">₪{promo.discounted_price:.2f}</b>'
        f'<span class="chip good" style="margin-inline-start:4px;">מבצע{end_html}</span>'
    )


def _spread_card(s: SpreadResult, active_promos: dict[str, dict[str, ActivePromo]] | None = None) -> str:
    active_promos = active_promos or {}
    coverage = f' <small class="ltr" style="font-weight:400;color:var(--ink-muted)">· נמצא ב-{s.num_stores} סניפים</small>' if s.num_stores >= 5 else ""
    cheap_promo = active_promos.get(s.cheap_store_id, {}).get(s.item_code)
    expensive_promo = active_promos.get(s.expensive_store_id, {}).get(s.item_code)
    return f"""
    <div class="card spread">
      <div class="top-row">
        <div class="name"><a href="/frodo-project/product/?code={s.item_code}">{escape(s.item_name)}</a>{coverage}</div>
        <span class="chip warm">+{s.spread_pct*100:.1f}%</span>
      </div>
      <div class="range">
        <span class="range-point cheap">{_range_price_html(s.cheap_price, cheap_promo)}<small><a href="/frodo-project/store/{s.cheap_store_id}/">{escape(s.cheap_store_name)}</a></small></span>
        <span class="range-arrow">←</span>
        <span class="range-point">{_range_price_html(s.expensive_price, expensive_promo)}<small><a href="/frodo-project/store/{s.expensive_store_id}/">{escape(s.expensive_store_name)}</a></small></span>
      </div>
    </div>"""


def _promo_highlight_card(h: PromoHighlight) -> str:
    end_label = format_promo_end_date(h.end_datetime)
    end_html = f" עד {end_label}" if end_label else ""
    discount_pct = round((h.regular_price - h.discounted_price) / h.regular_price * 100)
    return f"""
    <div class="card spread">
      <div class="top-row">
        <div class="name"><a href="/frodo-project/product/?code={h.item_code}">{escape(h.item_name)}</a></div>
        <span class="chip good">-{discount_pct}%</span>
      </div>
      <div class="range">
        <span class="range-point cheap">
          <b class="ltr" style="text-decoration:line-through;color:var(--ink-muted);font-weight:400;font-size:.85rem;">₪{h.regular_price:.2f}</b>
          <b class="ltr">₪{h.discounted_price:.2f}</b>
          <small><a href="/frodo-project/store/{h.store_id}/">{escape(h.store_name)}</a> · מבצע{end_html}</small>
        </span>
      </div>
    </div>"""


def _lb_row(rank: int, s: StoreScore) -> str:
    from etl.render.leaderboard import score_color

    savings = 100 - round(s.avg_percentile * 100)
    color = score_color(s.avg_percentile)
    return f"""
    <div class="lb-row"><span class="lb-rank ltr">{rank}</span>
      <a href="/frodo-project/store/{s.store_id}/">{escape(s.store_name)}</a>
      <span class="lb-score-wrap"><span class="lb-bar"><span class="lb-bar-fill" style="width:{savings}%;background:{color}"></span></span><span class="lb-score-num ltr">{savings}</span></span>
    </div>"""


def _reveal_wrap(html: str, group: str, visible: bool) -> str:
    """Wraps one already-rendered row/card so items past REVEAL_BATCH start
    hidden -- see REVEAL_MORE_CSS/SCRIPT in layout.py. Rows are rendered
    server-side up front (not fetched on click); this just toggles a class."""
    if visible:
        return html
    return f'<div data-reveal-group="{group}" class="reveal-hidden">{html}</div>'


def render_index_html(
    spreads: list[SpreadResult],
    scores: list[StoreScore],
    generated_at: str,
    top_n_spreads: int = 20,
    active_promos: dict[str, dict[str, ActivePromo]] | None = None,
    promo_highlights: list[PromoHighlight] | None = None,
) -> str:
    from etl.render.layout import PIN_ICON_SVG, REVEAL_MORE_CSS, REVEAL_MORE_SCRIPT, page_shell

    # A real, dedicated "active promos" section -- distinct from the
    # "biggest gap between stores" section below, which selects for an
    # extreme cross-store difference (200%+ spreads are common there) and
    # essentially never coincides with a real Shufersal promo (typically
    # 5-10% off). Without this section the promo feature was technically
    # working but invisible on the page anyone actually lands on first.
    top_promos = (promo_highlights or [])[:top_n_spreads]
    promo_cards = "\n".join(
        _reveal_wrap(_promo_highlight_card(h), "promos", i < REVEAL_BATCH) for i, h in enumerate(top_promos)
    )
    promos_more_btn = (
        f'<button class="reveal-more-btn" data-reveal-group="promos" data-reveal-step="{REVEAL_BATCH}">עוד {REVEAL_BATCH} ←</button>'
        if len(top_promos) > REVEAL_BATCH
        else ""
    )
    promos_section = (
        f"""
  <hr class="sketchy-divider">
  <h2 class="section-title">מבצעים פעילים עכשיו</h2>
  <p class="section-sub">מחירי מבצע אמיתיים, מאומתים מול המחיר הרגיל בפועל -- כרגע משופרסל בלבד (רשתות נוספות בהמשך). ראו איך זה מחושב במתודולוגיה.</p>

  <section class="list">{promo_cards}
  </section>
  {promos_more_btn}
"""
        if top_promos
        else ""
    )

    # Headline/top-spread selection skips flagged (implausibly extreme,
    # likely promo-or-data-quality) entries -- see FLAG_SPREAD_PCT in
    # cross_branch_spread.py. They stay visible (with a warning badge) on
    # /branches/, just not as the homepage's own headline.
    unflagged = [s for s in spreads if not s.flagged]
    top_spreads = unflagged[:top_n_spreads]
    hero = top_spreads[0] if top_spreads else None

    spread_cards = "\n".join(
        _reveal_wrap(_spread_card(s, active_promos), "spreads", i < REVEAL_BATCH) for i, s in enumerate(top_spreads)
    )
    spreads_more_btn = (
        f'<button class="reveal-more-btn" data-reveal-group="spreads" data-reveal-step="{REVEAL_BATCH}">עוד {REVEAL_BATCH} ←</button>'
        if len(top_spreads) > REVEAL_BATCH
        else ""
    )

    ordered_scores = sorted(scores, key=lambda s: s.avg_percentile)
    lb_rows = "\n".join(
        _reveal_wrap(_lb_row(i + 1, s), "lb", i < REVEAL_BATCH) for i, s in enumerate(ordered_scores)
    )
    lb_more_btn = (
        f'<button class="reveal-more-btn" data-reveal-group="lb" data-reveal-step="{REVEAL_BATCH}">עוד {REVEAL_BATCH} ←</button>'
        if len(ordered_scores) > REVEAL_BATCH
        else ""
    )

    hero_html = (
        f"""
  <div class="headline-stat">
    <div class="num ltr">₪{hero.cheap_price:.2f} ← ₪{hero.expensive_price:.2f}</div>
    <p><b>{escape(hero.item_name)}</b> — אותו ברקוד, אותה רשת, אותה עיר. ₪{hero.cheap_price:.2f}
    ב{escape(hero.cheap_store_name)}, ₪{hero.expensive_price:.2f} ב{escape(hero.expensive_store_name)}.
    פער של {hero.spread_pct*100:.1f}% על אותו מוצר בדיוק.</p>
    <a class="cta-map" href="/frodo-project/map/">{PIN_ICON_SVG}כנסו למפה — ראו את הסניפים לידכם ←</a>
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
{promos_section}
  <hr class="sketchy-divider">
  <h2 class="section-title">איזה סניף הכי משתלם?</h2>
  <p class="section-sub">מדד חיסכון ממוצע על פני מוצרים משותפים -- ככל שגבוה יותר, זול יותר. הדירוג הוא לפי איזור (כפר סבא) -- אנשים לא נוסעים רחוק בשביל סופר; איזורים נוספים בהמשך. <a href="/frodo-project/leaderboard/">כל הדירוג המלא ←</a></p>

  <div class="lb-list">{lb_rows}
  </div>
  {lb_more_btn}

  <hr class="sketchy-divider">
  <h2 class="section-title">המוצרים עם הפער הגדול ביותר בין סניפים</h2>
  <p class="section-sub">כל שורה: אותו ברקוד (אותו מוצר פיזי), שנמצא ב-4 סניפים לפחות, באותו יום. <a href="/frodo-project/branches/">כל {len(spreads):,} הפערים ←</a></p>

  <section class="list">{spread_cards}
  </section>
  {spreads_more_btn}
"""

    return page_shell(
        "מחירי סופרמרקטים כפר סבא — Frodo Project",
        "home",
        body,
        f"<style>{INDEX_CSS}{REVEAL_MORE_CSS}</style>",
        REVEAL_MORE_SCRIPT,
    )
