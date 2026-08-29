"""Renders site/regulated-prices/index.html -- dairy products checked
against the official regulated ceiling price (MOAG/MOAG-Agriculture data,
see docs/sources.md). Split out of the homepage (etl/render/render_site.py)
on purpose: this project compares prices between stores, not which chains
comply with a regulated ceiling (that's the regulator's own job) -- keeping
it as background information on its own page instead of the homepage's
biggest section avoids implying otherwise.
"""
from __future__ import annotations

from collections import defaultdict
from html import escape

from etl.scoring.benchmark_gap import GapResult

REGULATED_CSS = """
section.list{ display:flex; flex-direction:column; gap:12px; margin:20px 0 30px; }
.card.spread{ display:flex; flex-direction:column; align-items:flex-start; gap:12px; }
.card .name{ font-size:1.02rem; font-weight:600; }
.card .name small{ display:block; font-weight:400; color:var(--ink-muted); font-size:.82rem; margin-top:3px; }
.range{ display:flex; align-items:center; gap:14px; flex-wrap:wrap; }
.range-point{ display:flex; flex-direction:column; gap:2px; }
.range-point b{ font-family:'IBM Plex Mono',monospace; font-weight:600; font-size:1.2rem; font-variant-numeric:tabular-nums; }
.range-point.cheap b{ color:var(--good); }
.range-point small{ color:var(--ink-muted); font-size:.78rem; }
.range-arrow{ color:var(--ink-muted); font-size:1.2rem; }
.price-ref{ font-size:.85rem; color:var(--ink-muted); font-variant-numeric:tabular-nums; }
"""


def _gap_group_card(item_name: str, controlled_names: list[str], controlled_price: float, group: list[GapResult], store_names: dict[str, str]) -> str:
    """One card per product, showing the range of actual prices found
    across every store that carries it against the single controlled
    reference price -- not a separate near-duplicate card per store (the
    old _gap_card had no store field at all, so the same handful of
    controlled products repeated once per carrying store: with 30 stores
    and ~7 controlled dairy items, that's ~100+ near-identical cards in a
    row for a visitor to scroll past)."""
    entries = sorted(
        ((g.store_id, store_names.get(g.store_id, g.store_id), g.actual_price) for g in group),
        key=lambda e: e[2],
    )
    cheap_id, cheap_name, cheap_price = entries[0]
    expensive_id, expensive_name, expensive_price = entries[-1]
    controlled_name = escape(", ".join(controlled_names))
    coverage = (
        f' <small class="ltr" style="font-weight:400;color:var(--ink-muted)">· נמצא ב-{len(entries)} סניפים</small>'
        if len(entries) >= 2
        else ""
    )

    if cheap_price == expensive_price:
        range_html = f'<span class="range-point"><b class="ltr">₪{cheap_price:.2f}</b><small><a href="/frodo-project/store/{cheap_id}/">{escape(cheap_name)}</a></small></span>'
    else:
        range_html = f"""<span class="range-point cheap"><b class="ltr">₪{cheap_price:.2f}</b><small><a href="/frodo-project/store/{cheap_id}/">{escape(cheap_name)}</a></small></span>
        <span class="range-arrow">←</span>
        <span class="range-point"><b class="ltr">₪{expensive_price:.2f}</b><small><a href="/frodo-project/store/{expensive_id}/">{escape(expensive_name)}</a></small></span>"""

    return f"""
    <div class="card spread">
      <div class="name">{escape(item_name)}<small>מפוקח כ: {controlled_name}</small>{coverage}</div>
      <div class="range">{range_html}</div>
      <span class="price-ref ltr">מחיר מפוקח (מקסימום): ₪{controlled_price:.2f}</span>
    </div>"""


def render_regulated_prices_html(gaps: list[GapResult], store_names: dict[str, str]) -> str:
    from etl.render.layout import page_shell

    unambiguous_gaps = [g for g in gaps if not g.ambiguous]
    grouped_gaps: dict[str, list[GapResult]] = defaultdict(list)
    for g in unambiguous_gaps:
        grouped_gaps[g.item_code].append(g)
    gap_cards = "\n".join(
        _gap_group_card(group[0].item_name, group[0].controlled_product_names, group[0].controlled_consumer_price, group, store_names)
        for group in grouped_gaps.values()
    )

    body = f"""
  <div class="kicker">Frodo Project · מחירים מפוקחים</div>
  <h1>מחירים מול התקרה המפוקחת בחוק</h1>
  <p class="lede">מוצרי חלב שאפשר להתאים בביטחון למחיר המקסימלי הרשמי, לפי הנתונים הרשמיים של משרד הכלכלה/החקלאות. זה מידע רקע בלבד -- לא בדיקת ציות של רשתות (זה תפקיד הפיקוח), אלא הקשר נוסף להשוואת המחירים שבאתר.</p>

  <section class="list">{gap_cards}
  </section>
"""

    return page_shell("מחירים מפוקחים — Frodo Project", "regulated", body, f"<style>{REGULATED_CSS}</style>")
