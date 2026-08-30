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
    # Stores.xml Address == "אלי הורוביץ 26" -- spelled with an extra ו that
    # doesn't match OSM's own street name. Nominatim returns zero results for
    # the Stores.xml spelling but one clean, sensible result (Kfar Saba's
    # industrial zone) for "אלי הורביץ" -- same street, not a different
    # location; confirmed live 2026-08-28 (both "אלי הורביץ 26" and the
    # English "Eli Hurvitz 26" resolve to the identical point).
    "shukhair-011": "אלי הורביץ 26",
    # Stores.xml Address == "גלגלי פלדה 2" -- missing the definite article
    # (should be "גלגלי הפלדה", not "גלגלי פלדה"). Independently confirmed
    # against three unrelated directories (easy.co.il, d.co.il, hasnif.co.il),
    # all spelling it "גלגלי הפלדה 2"; that spelling is also OSM's own street
    # name, confirmed live 2026-08-29:
    # https://easy.co.il/en/page/25162482
    # https://www.d.co.il/80209714/35760/
    # https://www.hasnif.co.il/%D7%A8%D7%9E%D7%99-%D7%9C%D7%95%D7%99-%D7%9B%D7%A4%D7%A8-%D7%A1%D7%91%D7%90/
    "rami-levy-033": "גלגלי הפלדה 2",
    # Stores.xml Address == "דרך הים 9" -- OSM's own street name is just
    # "הים", not "דרך הים"; the "דרך" prefix makes Nominatim's structured
    # search return zero results. Same street/number, confirmed live
    # 2026-08-29 against openinghours.co.il and easy.co.il (both list
    # "דרך הים 9" as this branch's address, i.e. this is a naming-convention
    # mismatch with OSM, not a wrong address):
    # https://easy.co.il/en/page/10111012
    # https://openinghours.co.il/%D7%90%D7%95%D7%A9%D7%A8-%D7%A2%D7%93-%D7%9B%D7%A4%D7%A8-%D7%A1%D7%91%D7%90-%D7%93%D7%A8%D7%9A-%D7%94%D7%99%D7%9D-9
    "osher-ad-031": "הים 9",
    # Stores.xml Address == 'מרכז מסחרי "שרונה", דרך השרון 12' -- the mall
    # name prefix breaks Nominatim's structured street-field search entirely,
    # and (same pattern as osher-ad-031 above) OSM's own street name is just
    # "השרון", not "דרך השרון". Confirmed live 2026-08-29 against
    # pricepilot.co.il, which independently lists this branch's address as
    # "דרך השרון 12, כפר סבא":
    # https://pricepilot.co.il/store/Derech%20HaSharon%2012,%20Kfar%20Saba/10fd7b78-b652-4037-9b1d-e24693f4c872
    "keshet-019": "השרון 12",
    # Stores.xml Address == "unknown" (a placeholder, not a real value -- see
    # UNUSABLE_ADDRESSES in scripts/daily_snapshot.py). The real address
    # isn't in Shufersal's own feed at all here, so unlike the other entries
    # above this isn't a spelling fix -- it's sourced independently from
    # three unrelated directories (d.co.il, easy.co.il, t.co.il), all listing
    # this branch at "עתיר ידע 1", confirmed live 2026-08-29:
    # https://www.d.co.il/80282954/35760/
    # https://easy.co.il/en/page/26388450
    # https://www.t.co.il/Business/Card-780835.html
    "yohananof-024": "עתיר ידע 1",
    # Stores.xml Address == "הסדנא 17, כפר סבא" -- a real street, but OSM only
    # holds it under its Latin transliteration ("HaSadna"), not the Hebrew
    # spelling; Nominatim returns zero results for "הסדנא 17" (confirmed live
    # 2026-08-30) and one clean result for "HaSadna 17", inside
    # KFAR_SABA_BOUNDS, in the same industrial zone as osher-ad-031's override
    # above. Independently confirmed as a real Kfar Saba industrial-zone
    # street (not guessed from the geocode result alone) via b144.co.il's own
    # listings for numbers 1 and 7 on this street, and menivim-reit.co.il's
    # description of a building "at the corner of HaSadna and Binyamin
    # Yehalom, in the Kfar Saba industrial zone":
    # https://www.b144.co.il/maps/%D7%9B%D7%A4%D7%A8-%D7%A1%D7%91%D7%90/%D7%94%D7%A1%D7%93%D7%A0%D7%90/
    # https://www.menivim-reit.co.il/%D7%A0%D7%9B%D7%A1%D7%99-%D7%94%D7%A7%D7%A8%D7%9F/%D7%9B%D7%A4%D7%A8-%D7%A1%D7%91%D7%90/
    "wolt-005": "HaSadna 17",
}
