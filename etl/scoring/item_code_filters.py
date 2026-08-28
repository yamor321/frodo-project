"""Shared filter for item codes that aren't reliable identifiers across
chains -- used by both cross_branch_spread.py and store_ranking.py, since
both group prices by item_code across whatever stores they're given.

The general problem, confirmed live across three chains now, not just one:
weighed/loose items with no real manufacturer barcode (produce, mostly)
get an item code each chain synthesizes *internally* for itself, not one
GS1 assigns. Each chain is consistent with its own convention, but nothing
stops two chains' independently-invented codes from colliding on
completely different real products. Two distinct shapes of this have
actually been seen, not just theorized:
- Carrefour/Shufersal: real-length (13-digit) codes that are mostly zeros
  -- 7290000000145 is red cabbage at Shufersal but a Maccabi Health Fund
  gift basket at Carrefour, on the same day. A fake 914% spread.
- Victory: bare short integers with no padding at all -- "2001" (yellow
  grapefruit) collided with an unrelated Carrefour product at "2001" too,
  producing a fake 832% spread that became the very next homepage headline
  after the first one was fixed.
Both rules stay, rather than replacing one with the other, because they
catch different chains' different internal conventions.
"""
from __future__ import annotations

import re

# Real GS1-assigned barcodes are at minimum 8 digits (EAN-8); genuine
# examples already in this dataset are 8, 12, or 13 digits. A code shorter
# than that is essentially guaranteed to be an internally-assigned PLU
# code, not a real per-product identifier meant to be globally comparable.
MIN_RELIABLE_CODE_LENGTH = 8

# "729" + 7 zeros + a short sequence number: real-length but effectively
# still a small internal counter padded out to look like a barcode.
_ZERO_PADDED_INTERNAL_CODE_RE = re.compile(r"^729000000\d{4}$")


def is_reliable_item_code(item_code: str) -> bool:
    if len(item_code) < MIN_RELIABLE_CODE_LENGTH:
        return False
    return not _ZERO_PADDED_INTERNAL_CODE_RE.match(item_code)
