"""Renders site/branches/index.html -- the full cross-branch price-spread
table (every comparable item, not just the homepage's top 10), with a real
client-side search/sort so it's actually usable at thousands of rows.
"""
from __future__ import annotations

import json
from html import escape

from etl.scoring.active_promos import ActivePromo
from etl.scoring.cross_branch_spread import SpreadResult

BRANCHES_CSS = """
#branchSearch{ width:100%; font-family:'Assistant',sans-serif; font-size:1rem; padding:12px 16px;
  border:1.5px solid var(--line); border-radius:10px; background:var(--paper-raised); color:var(--ink); margin-bottom:14px; }
#branchHint{ font-size:.85rem; color:var(--ink-muted); margin-bottom:14px; }
.branch-table{ width:100%; border-collapse:collapse; font-size:.92rem; }
.branch-table th{ text-align:right; font-family:'Assistant',sans-serif; font-weight:700; font-size:.72rem; text-transform:uppercase;
  letter-spacing:.05em; color:var(--ink-muted); padding:8px 10px; border-bottom:1px solid var(--line); cursor:pointer;
  user-select:none; white-space:nowrap; }
.branch-table th:hover{ color:var(--navy); }
.branch-table td{ padding:10px; border-bottom:1px solid var(--line); vertical-align:top; }
.branch-table td.num{ font-weight:600; font-variant-numeric:tabular-nums; white-space:nowrap; }
.branch-table .store-name{ color:var(--ink-muted); font-size:.85rem; }
.table-wrap{ overflow-x:auto; }
.flag-badge{ display:inline-block; margin-inline-start:6px; font-size:.78rem; color:var(--brick);
  cursor:help; }
"""


def _row_dict(s: SpreadResult, active_promos: dict[str, dict[str, ActivePromo]]) -> dict:
    row = {
        "code": s.item_code,
        "name": s.item_name,
        "n": s.num_stores,
        "cheap_price": s.cheap_price,
        "cheap_store": s.cheap_store_name,
        "expensive_price": s.expensive_price,
        "expensive_store": s.expensive_store_name,
        "pct": round(s.spread_pct * 100, 1),
        "flagged": s.flagged,
    }
    cheap_promo = active_promos.get(s.cheap_store_id, {}).get(s.item_code)
    if cheap_promo is not None:
        row["cheap_promo"] = cheap_promo.discounted_price
    expensive_promo = active_promos.get(s.expensive_store_id, {}).get(s.item_code)
    if expensive_promo is not None:
        row["expensive_promo"] = expensive_promo.discounted_price
    return row


def render_branches_html(spreads: list[SpreadResult], active_promos: dict[str, dict[str, ActivePromo]] | None = None) -> str:
    from etl.render.layout import page_shell

    active_promos = active_promos or {}
    # Only cheap_promo/expensive_promo carry a real value (see _row_dict) --
    # most of 15,000+ rows have neither, so this stays close to the same
    # payload size as before instead of adding two null fields per row.
    rows_json = json.dumps([_row_dict(s, active_promos) for s in spreads], ensure_ascii=False)

    body = f"""
  <div class="kicker">Frodo Project · פערי מחיר בין סניפים</div>
  <h1>כל הפערים — לא רק ה-Top 10</h1>
  <p class="lede">{len(spreads):,} מוצרים שנמצאו ב-4 סניפים בכפר סבא לפחות (מכל הרשתות שנאספו), באותו יום. כל שורה: אותו ברקוד בדיוק, הזול והיקר ביותר בין הסניפים.</p>

  <input id="branchSearch" type="text" placeholder="הקלד שם מוצר לסינון..." autocomplete="off" aria-label="סינון לפי שם מוצר">
  <div id="branchHint" aria-live="polite">{len(spreads):,} מוצרים · לחיצה על כותרת עמודה ממיינת</div>

  <div class="table-wrap">
    <table class="branch-table">
      <thead>
        <tr>
          <th data-key="name">מוצר</th>
          <th data-key="cheap_price">הזול ביותר</th>
          <th data-key="expensive_price">היקר ביותר</th>
          <th data-key="pct">פער</th>
          <th data-key="n">סניפים</th>
        </tr>
      </thead>
      <tbody id="branchBody"></tbody>
    </table>
  </div>
"""

    extra_head = f"<style>{BRANCHES_CSS}</style>"
    extra_script = f"""<script>
(function(){{
  const rows = {rows_json};
  const tbody = document.getElementById("branchBody");
  const search = document.getElementById("branchSearch");
  const hint = document.getElementById("branchHint");
  let sortKey = "pct", sortDir = -1;

  function render(){{
    const q = search.value.trim();
    let filtered = q ? rows.filter(r => r.name.includes(q)) : rows;
    filtered = filtered.slice().sort((a,b) => {{
      const av = a[sortKey], bv = b[sortKey];
      if (typeof av === "string") return sortDir * av.localeCompare(bv, "he");
      return sortDir * (av - bv);
    }});
    hint.textContent = `${{filtered.length.toLocaleString()}} מוצרים` + (q ? ` (מסונן מתוך {len(spreads):,})` : " · לחיצה על כותרת עמודה ממיינת");
    const shown = filtered.slice(0, 500);
    // Real confirmed sale price (see etl/scoring/active_promos.py) --
    // Shufersal only, v1. Struck-through regular price next to the
    // highlighted promo price, same badge as the product/store pages.
    function priceCell(price, promo){{
      if (promo == null) return `₪${{price.toFixed(2)}}`;
      return `<span style="text-decoration:line-through;color:var(--ink-muted);font-weight:400;">₪${{price.toFixed(2)}}</span> ₪${{promo.toFixed(2)}} <span class="chip good">מבצע</span>`;
    }}
    tbody.innerHTML = shown.map(r => `
      <tr>
        <td><a href="/frodo-project/product/?code=${{r.code}}">${{r.name}}</a>${{r.flagged ? '<span class="flag-badge" title="פער חריג מאוד -- ייתכן מבצע או טעות נתונים אצל הרשת, לא באג בצד שלנו">⚠ פער חריג</span>' : ''}}</td>
        <td class="num">${{priceCell(r.cheap_price, r.cheap_promo)}}<div class="store-name">${{r.cheap_store}}</div></td>
        <td class="num">${{priceCell(r.expensive_price, r.expensive_promo)}}<div class="store-name">${{r.expensive_store}}</div></td>
        <td class="num">${{r.pct.toFixed(1)}}%</td>
        <td class="num">${{r.n}}</td>
      </tr>`).join("");
    if (filtered.length > 500) {{
      hint.textContent += ` · מוצגות 500 הראשונות, חדדו את החיפוש כדי לראות עוד`;
    }}
  }}

  document.querySelectorAll(".branch-table th").forEach(th => {{
    th.addEventListener("click", () => {{
      const key = th.dataset.key;
      if (sortKey === key) sortDir *= -1; else {{ sortKey = key; sortDir = key === "name" ? 1 : -1; }}
      render();
    }});
  }});
  search.addEventListener("input", render);
  render();
}})();
</script>"""

    return page_shell("כל פערי המחיר — Frodo Project", "branches", body, extra_head, extra_script)
