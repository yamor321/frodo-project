"""Manual address overrides for real branches whose Stores.xml `Address`
field (Shufersal's own regulatory feed) is missing, or too generic for
Nominatim's structured search to place -- these are NOT guesses: each
value is a real street+number, verified against an independent public
source (see the comment on each entry), the same way any other display-only
enrichment on this site is sourced. The underlying price data these
branches sell is untouched by this file -- it only fixes where their pin
lands on the map.
"""

ADDRESS_OVERRIDES: dict[str, str] = {
    # Stores.xml Address == "" for this branch (no street at all).
    # Verified: https://easy.co.il/en/page/26978433 and
    # https://www.hasnif.co.il/%D7%A9%D7%95%D7%A4%D7%A8%D7%A1%D7%9C-%D7%90%D7%A7%D7%A1%D7%A4%D7%A8%D7%A1-%D7%AA%D7%9C-%D7%97%D7%99-%D7%9B%D7%A4%D7%A8-%D7%A1%D7%91%D7%90/
    "140": "תל חי 40",
    # Stores.xml Address == "כפר סבא" (city name only, no street).
    # Verified against Be's own branch locator: https://www.bestore.co.il/online/he/branchs
    "615": "כצנלסון 14",
    # Stores.xml Address == "ויצמן 300 מתחם G" -- this branch is inside the
    # "Kanyon G" mall. "ויצמן 300" (from Stores.xml, or easy.co.il) turned
    # out to geocode to the same point as an unrelated branch (Weizmann 29)
    # -- imprecise, not just differently formatted. The mall's real address
    # is Weizmann 207, confirmed independently by the mall's own site, Israel
    # Post, and the developer's project page, not just one directory listing:
    # https://g-city.co.il/shopping-center/g-%D7%9B%D7%A4%D7%A8-%D7%A1%D7%91%D7%90/
    # https://doar.org.il/%D7%9B%D7%A4%D7%A8-%D7%A1%D7%91%D7%90/%D7%A1%D7%A0%D7%99%D7%A3-%D7%A7%D7%A0%D7%99%D7%95%D7%9F-%D7%92%D7%99-%D7%9B%D7%A4%D7%A8-%D7%A1%D7%91%D7%90-613/
    # https://www.electra.co.il/%D7%A4%D7%A8%D7%95%D7%99%D7%A7%D7%98%D7%99%D7%9D/%D7%9E%D7%A8%D7%9B%D7%96%D7%99%D7%9D_%D7%9E%D7%A1%D7%97%D7%A8%D7%99%D7%99%D7%9D/%D7%A7%D7%A0%D7%99%D7%95%D7%9F_g_%D7%9B%D7%A4%D7%A8_%D7%A1%D7%91%D7%90
    "259": "ויצמן 207",
}
