"""Renders site/branches/index.html -- the full cross-branch price-spread
table (every comparable item, not just the homepage's top 10), with a real
client-side search/sort so it's actually usable at thousands of rows.
"""
from __future__ import annotations

import json
from html import escape

from etl.scoring.cross_branch_spread import SpreadResult

BRANCHES_CSS = """
#branchSearch{ width:100%; font-family:'Assistant',sans-serif; font-size:1rem; padding:12px 16px;
  border:1.5px solid var(--line); border-radius:10px; background:var(--paper-raised); color:var(--ink); margin-bottom:14px; }
#branchHint{ font-size:.85rem; color:var(--ink-muted); margin-bottom:14px; }
.branch-table{ width:100%; border-collapse:collapse; font-size:.92rem; }
.branch-table th{ text-align:right; font-family:'IBM Plex Mono',monospace; font-size:.72rem; text-transform:uppercase;
  letter-spacing:.05em; color:var(--ink-muted); padding:8px 10px; border-bottom:1px solid var(--line); cursor:pointer;
  user-select:none; white-space:nowrap; }
.branch-table th:hover{ color:var(--navy); }
.branch-table td{ padding:10px; border-bottom:1px solid var(--line); vertical-align:top; }
.branch-table td.num{ font-family:'IBM Plex Mono',monospace; font-variant-numeric:tabular-nums; white-space:nowrap; }
.branch-table .store-name{ color:var(--ink-muted); font-size:.85rem; }
.table-wrap{ overflow-x:auto; }
"""


def render_branches_html(spreads: list[SpreadResult]) -> str:
    from etl.render.layout import page_shell

    rows_json = json.dumps(
        [
            {
                "code": s.item_code,
                "name": s.item_name,
                "n": s.num_stores,
                "cheap_price": s.cheap_price,
                "cheap_store": s.cheap_store_name,
                "expensive_price": s.expensive_price,
                "expensive_store": s.expensive_store_name,
                "pct": round(s.spread_pct * 100, 1),
            }
            for s in spreads
        ],
        ensure_ascii=False,
    )

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
    tbody.innerHTML = shown.map(r => `
      <tr>
        <td><a href="/frodo-project/product/?code=${{r.code}}">${{r.name}}</a></td>
        <td class="num">₪${{r.cheap_price.toFixed(2)}}<div class="store-name">${{r.cheap_store}}</div></td>
        <td class="num">₪${{r.expensive_price.toFixed(2)}}<div class="store-name">${{r.expensive_store}}</div></td>
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
