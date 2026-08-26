# מקורות מאומתים

כל הפרטים בקובץ זה נבדקו בפועל (ביקור בדפים חיים, לא רק חיפוש) ב-26.08.2026.
לגרסה המעוצבת המלאה של תכנית הארכיטקטורה (כולל אופציות מחסנית ומבנה תיקיות) ראו
את הארטיפקט שפורסם לפרויקט: "שקיפות מחירים כפר סבא".

## דף הקישורים המרכזי

https://www.gov.il/he/pages/cpfta_prices_regulations — רשות ההגנת הצרכן ולסחר
הוגן, כ-29 רשתות עם קישור "לצפייה במחירים" לכל אחת.

## הבסיס החוקי

- חוק קידום התחרות בענפי המזון והפארם, התשע"ד-2014 (חוק אב)
- תקנות קידום התחרות בענף המזון (שקיפות מחירים), התשע"ה-2014 (התקנות המפעילות)
  - סעיף 3(2): עדכון תוך שעה ממועד השינוי בקופה
  - סעיף 5: שמירת קבצים 3 חודשים ממועד הפרסום
- סף מחזור 250 מיליון ₪ מדווח בבריף הפרויקט, לא אומת ישירות בטקסט התקנה.

## כלי קוד פתוח קיים

github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers (גם `il-supermarket-scraper` ב-PyPI) —
מכסה 30+ רשתות, תמיכה ב-binaprojects.com ו-publishedprices.co.il, בדיקות יומיות אוטומטיות.
שימש כנקודת התייחסות; הפרסר בפועל בפרויקט זה (`etl/scrapers/shufersal.py`) נכתב עצמאית מול
פורטל שופרסל (שאינו רץ על אחת משתי הפלטפורמות המשותפות, ולכן ממילא לא מכוסה ישירות שם).

## רשתות עם סניף מאומת בכפר סבא

| רשת | סניפים בכפר סבא (portal store id) | פלטפורמה | login | אמינות ידועה |
|---|---|---|---|---|
| שופרסל | 144, 394, 615, 682, 752, 845 | prices.shufersal.co.il | לא | לא דווחו תקלות; **נבחרה כרשת הפיילוט** |
| רמי לוי | גלגלי הפלדה 5 + 2 סניפי "בשכונה" | publishedprices.co.il | כן | חשד לא-מאומת לדיווח חלקי |
| יוחננוף | אתיר ידע 1 | publishedprices.co.il | כן | ממצא ריקנות קבצים, לא מתוארך |
| ויקטורי | אנגל 78, מרכז דמרי | laibcatalog.co.il/victory | לא | מקור השתנה בעבר, נדרש fallback |
| מחסני השוק | לוי אשכול 37 | laibcatalog.co.il/mshuk | לא | מקור השתנה בעבר, נדרש fallback |
| אושר עד | דרך הים 9 (+ סניף מתוכנן) | publishedprices.co.il | כן | לא נבדק |
| חצי חינם | לא אותר סניף בעיר עצמה | shop.hazi-hinam.co.il | — | לא רלוונטי לפיילוט |

## שופרסל — מנגנון בפועל (מאומת מול הפורטל החי, 26.08.2026)

- קבצים מתארחים ב-Azure Blob (`pricesprodpublic.blob.core.windows.net`) עם SAS
  token חתום בקישור ההורדה עצמו בטבלת ה-HTML של הפורטל. ה-token פג תוקף באותו יום —
  יש להוריד מיד אחרי הליסטינג, לא לשמור קישורים לשימוש מאוחר.
- דפדוף: `?page=N`. מיון דטרמיניסטי לפי סניף: `?sort=Branch&sortdir=ASC`.
  **לא נמצא פרמטר סינון לפי סניף/קטגוריה** (נבדקו ולא עבדו: `?code=`, `?store=`,
  `?storeId=`, `?category=`, `?fileType=`, `?type=`) — הפתרון שיושם הוא מעבר על כל
  העמודים וסינון בצד הלקוח.
- קטגוריות זמינות (עמודת "קטגוריה" בטבלה): `price` (דלתא), `pricefull` (קטלוג
  מלא), `promo`, `promofull`, `stores`.
- סכימת XML מאומתת מקובץ אמיתי (`Root > ChainID/SubChainID/StoreID/BikoretNo/Items > Item > ...`):
  `ItemCode, ItemName, ManufactureName, ManufactureCountry, UnitQty, Quantity,
  UnitOfMeasure, bIsWeighted, QtyInPackage, ItemPrice, UnitOfMeasurePrice,
  AllowDiscount, PriceUpdateTime`.
- **אומת חי ב-26.08.2026**: כל 6 סניפי כפר סבא פרסמו PriceFull באותו יום
  (03:00–03:40), בין 147KB ל-430KB דחוס, 8,717 פריטים בקטלוג המלא של סניף 144
  לבדו.
- **סיכון מאומת בפועל, לא רק תיאורטי**: התאמת מוצרי חלב לפי מילת מפתח בשם המוצר
  מייצרת false positives אמיתיים — "שוקולד חלב" (milk chocolate) ו"גלידת שמנת"
  (cream-flavored ice cream) שניהם עולים בחיפוש מילות מפתח (חלב/שמנת) בלי להיות
  מוצרי החלב המפוקחים בפועל. ראה `tests/test_shufersal_parser.py::test_naive_dairy_keyword_match_has_false_positives`
  ו-`scripts/demo_shufersal.py`. זה בדיוק התרחיש שסעיף 4 בבריף מתכנן עבורו — סיווג
  מבוסס LLM מול רשימת קטגוריות סגורה, לא חיפוש מילת מפתח נאיבי.

## בנצ'מרקים (שכבה 3)

| מקור | כתובת | פורמט | תדירות / היסטוריה |
|---|---|---|---|
| מחירים מפוקחים — משרד החקלאות/הכלכלה | gov.il/he/departments/dynamiccollectors/food-price-control-search | HTML חי ומסונן, 21 מוצרים | לא סדירה (~רבעונית) |
| מדד מחירים לצרכן — למ"ס | api.cbs.gov.il/index/data/price | API — XML/JSON/CSV/XLS | חודשי (15 לחודש), מ-1997 |
| מדד מחירי מזון עולמי — FAO | fao.org/worldfoodsituation/foodpricesindex | Excel + CSV | חודשי, מ-1990, 5 תתי-מדדים |
