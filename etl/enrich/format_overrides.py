"""Manual store-format overrides for real branches whose name carries no
reliable format signal, or a misleading one -- same pattern as
etl/enrich/address_overrides.py: not guesses, each entry sourced against an
independent source, keyed by the same namespaced store_id used everywhere
else downstream (catalogs_by_store, store_names, coords, formats).

Empty for now: etl/enrich/store_format.py's new default ("supermarket"
instead of the old, wrongly-small "neighborhood" default) already resolves
both cases reported live -- שוק העיר and a Shufersal "שלי"-format Rothschild
branch -- without needing an explicit entry here. Add one only for a
store_id confirmed, with an independent source, to need a DIFFERENT format
than what the name-keyword heuristic already produces on its own.
"""

FORMAT_OVERRIDES: dict[str, str] = {}
