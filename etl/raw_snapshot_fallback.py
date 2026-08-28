"""Fallback to the most recent previously-collected raw snapshot when a
chain's live collection fails outright for the day (e.g. Victory's TCP-level
block from GitHub Actions -- see etl/scrapers/victory.py).

**Checked live 2026-08-28, not assumed:** laibcatalog.co.il's own `getfiles`
API only ever returns TODAY's files. Tried several plausible date query
params (date/day/fileDate/d/from=20260827 against a real Victory chain_id)
-- every one returned the identical today-only listing, proving the
parameter is ignored rather than unsupported-but-silently-accepted. There is
no "ask for yesterday" option upstream, so the only place "yesterday's data"
can come from is this project's own already-committed history.

Every successful run already writes each store's raw PriceFull XML to
data/raw/<date>/ (see scripts/daily_snapshot.py) and that directory is
committed daily -- real history that already exists, not something new to
build. This module just reads it back when today's live collection for a
chain comes up empty, so a store the site already knows about doesn't
silently vanish for a day; it shows the most recent real prices still
available, clearly labeled with the date they're actually from (never
presented as if they were today's -- see render_store_html's as_of_date).

**Bug found and fixed from the first real production case, not caught
locally:** the daily workflow now triggers on every push, not just once a
day (see .github/workflows/daily-shufersal.yml), so "today" can have
several runs -- Victory succeeded in an earlier run on 2026-08-28
(data/raw/2026-08-28/PriceFull7290696200003-...-079-...xml exists, real,
committed) and then failed in a later same-day run, but the live site
still lost the store's page entirely. The original version of this function
started its search at `before - 1 day`, deliberately excluding `before`
(today) itself, on the assumption that a same-day failure means today's own
directory has nothing usable yet -- true for a single-run day, false once
multiple runs happen per day. Fixed by starting the search at `before`
itself (days_back=0): a same-day earlier success is found first, before
falling back further to yesterday and beyond.
"""
from __future__ import annotations

import datetime as dt
import pathlib

from etl.scrapers.shufersal import PriceRecord, parse_price_xml


def find_fallback_catalogs(
    raw_root: pathlib.Path,
    prefix: str,
    store_ids: set[str],
    before: dt.date,
    max_lookback_days: int = 7,
) -> tuple[dict[str, list[PriceRecord]], dict[str, str]]:
    """Walk backward from `before` (exclusive) looking for each store's most
    recent raw PriceFull XML. Returns (catalogs_by_store, as_of_date_by_store),
    both keyed by the same namespaced store id (prefix + store_id) used
    everywhere else in the pipeline.

    Each store is searched independently and stops as soon as it's found --
    a chain-wide outage means every one of its stores will typically resolve
    to the same day in practice, but nothing here assumes that, since a
    single missing day for one store shouldn't block finding an otherwise
    available one.

    Searches `before` itself first (days_back=0), then walks backward --
    NOT exclusive of today. A same-day earlier run's success is exactly what
    this needs to find when a later same-day run fails (see module
    docstring for the real case that caught this).
    """
    catalogs: dict[str, list[PriceRecord]] = {}
    as_of: dict[str, str] = {}
    remaining = set(store_ids)

    for days_back in range(0, max_lookback_days + 1):
        if not remaining:
            break
        day = (before - dt.timedelta(days=days_back)).isoformat()
        day_dir = raw_root / day
        if not day_dir.exists():
            continue
        for store_id in list(remaining):
            match = next(day_dir.glob(f"PriceFull*-{store_id}-*.xml"), None)
            if match is None:
                continue
            catalogs[prefix + store_id] = parse_price_xml(match.read_bytes())
            as_of[prefix + store_id] = day
            remaining.discard(store_id)

    return catalogs, as_of
