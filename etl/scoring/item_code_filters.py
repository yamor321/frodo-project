"""Shared filter for item codes that aren't reliable identifiers across
chains -- used by both cross_branch_spread.py and store_ranking.py, since
both group prices by item_code across whatever stores they're given.
"""
from __future__ import annotations

import re

# Confirmed live 2026-08-28, comparing real Shufersal and Carrefour catalogs:
# a small class of item codes -- "729" followed by 7 zeros and a short
# sequence number -- are internally synthesized by each chain for
# weighed/loose items with no real manufacturer barcode (produce, in this
# case). Each chain assigns these consistently *within itself*, but they
# collide *between* chains: 7290000000145 is red cabbage at Shufersal but a
# Maccabi Health Fund gift basket at Carrefour, on the same day. Comparing
# across those two "products" produced a fake 914% spread that would have
# been the site's own homepage headline. This pattern excludes that whole
# class rather than special-casing the one code found -- the point isn't
# that this exact number is bad, it's that this whole code *shape* was
# never a trustworthy cross-chain identifier to begin with.
_SUSPICIOUS_INTERNAL_CODE_RE = re.compile(r"^729000000\d{4}$")


def is_reliable_item_code(item_code: str) -> bool:
    return not _SUSPICIOUS_INTERNAL_CODE_RE.match(item_code)
