"""Renders site/leaderboard/index.html -- a full ranked comparison of every
scored store's avg_percentile (etl/scoring/store_ranking.py). This is the
metric most directly aimed at the project's "create competition through
transparency" goal (a store's rank against every other store on real,
official prices) -- but until now it only ever appeared as unlabeled
map-marker color or a single bare number on each store's own page, never as
a side-by-side ranking, which is the whole point of a competitive metric.
"""
from __future__ import annotations

from html import escape

from etl.scoring.store_ranking import StoreScore

LEADERBOARD_CSS = """
.leaderboard-table{ width:100%; border-collapse:collapse; font-size:.95rem; }
.leaderboard-table th{ text-align:right; font-family:'Assistant',sans-serif; font-weight:700; font-size:.72rem; text-transform:uppercase;
  letter-spacing:.05em; color:var(--ink-muted); padding:8px 10px; border-bottom:1px solid var(--line); white-space:nowrap; }
.leaderboard-table td{ padding:12px 10px; border-bottom:1px solid var(--line); vertical-align:middle; }
.leaderboard-table td.rank{ font-weight:600; color:var(--ink-muted); }
.leaderboard-table td.num{ font-weight:600; font-variant-numeric:tabular-nums; white-space:nowrap; }
.score-bar-wrap{ display:flex; align-items:center; gap:10px; min-width:140px; }
.score-bar{ flex:1; height:8px; border-radius:4px; background:var(--line); overflow:hidden; }
.score-bar-fill{ height:100%; border-radius:4px; }
.table-wrap{ overflow-x:auto; }
"""


def score_color(score: float) -> str:
    """Same 3-stop green/beige/brick gradient the map and product mini-map
    use client-side (etl/render/layout.py's LEAFLET_SCORE_COLOR_JS) -- a
    Python port so server-rendered table rows get identical colors without
    needing JS. This is exactly the case the project's "no field represents
    a judgment call" principle allows: color-coding a real computed number,
    not attaching a verdict label to it.
    """
    stops = [(0.12, 0.48, 0.27), (0.79, 0.77, 0.66), (0.65, 0.23, 0.18)]
    t = score * 2 if score <= 0.5 else (score - 0.5) * 2
    a, b = (stops[0], stops[1]) if score <= 0.5 else (stops[1], stops[2])
    mix = tuple(round((a[i] + (b[i] - a[i]) * t) * 255) for i in range(3))
    return f"rgb({mix[0]},{mix[1]},{mix[2]})"


def _row(rank: int, s: StoreScore) -> str:
    # Displayed number is inverted from the internal avg_percentile
    # (0=cheapest..1=priciest, unchanged -- see store_ranking.py) so a
    # HIGHER visible number reads as better, matching every other "score
    # out of 100" on the web. The color mapping (score_color, fed the raw
    # avg_percentile) was already correct -- cheap=green, expensive=red --
    # this only fixes the number and bar length, not the color.
    savings = 100 - round(s.avg_percentile * 100)
    color = score_color(s.avg_percentile)
    return f"""
        <tr>
          <td class="rank ltr">{rank}</td>
          <td><a href="/frodo-project/store/{s.store_id}/">{escape(s.store_name)}</a></td>
          <td class="num">
            <div class="score-bar-wrap">
              <span class="ltr">{savings}</span>
              <div class="score-bar"><div class="score-bar-fill" style="width:{savings}%;background:{color}"></div></div>
            </div>
          </td>
          <td class="num ltr">{s.items_compared:,}</td>
        </tr>"""


def render_leaderboard_html(scores: list[StoreScore]) -> str:
    from etl.render.layout import page_shell

    ordered = sorted(scores, key=lambda s: s.avg_percentile)
    rows = "\n".join(_row(i + 1, s) for i, s in enumerate(ordered))

    body = f"""
  <div class="kicker">Frodo Project · דירוג סניפים</div>
  <h1>איזה סניף הכי משתלם?</h1>
  <p class="lede">כל {len(ordered)} הסניפים שנאספו, מדורגים לפי מדד חיסכון ממוצע — 100 = עקבית הכי זול ביחס לשאר, 0 = עקבית הכי יקר, ממוצע על כל המוצרים המשותפים לכל סניף. הדירוג הוא לפי איזור (כפר סבא) — אנשים לא נוסעים רחוק בשביל סופר; איזורים נוספים בהמשך. <a href="/frodo-project/methodology/">איך זה מחושב ←</a></p>

  <div class="table-wrap">
    <table class="leaderboard-table">
      <thead>
        <tr>
          <th>#</th>
          <th>סניף</th>
          <th>מדד חיסכון (100=זול, 0=יקר)</th>
          <th>מוצרים משותפים</th>
        </tr>
      </thead>
      <tbody>{rows}
      </tbody>
    </table>
  </div>
"""

    return page_shell("דירוג סניפים — Frodo Project", "leaderboard", body, f"<style>{LEADERBOARD_CSS}</style>")
