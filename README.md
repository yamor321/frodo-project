# Frodo Project — שקיפות מחירים כפר סבא

פלטפורמה אזרחית להשוואת מחירי מוצרי צריכה בין רשתות, מול בנצ'מרק רשמי.
פיילוט: מוצרי חלב + השוואה בין סניפי שופרסל בכפר סבא. פרטי המקורות
והארכיטקטורה: [docs/sources.md](docs/sources.md).

## מצב נוכחי

הפייפליין היומי חי ורץ אוטומטית (`.github/workflows/daily-shufersal.yml`,
03:00 UTC): מוריד קטלוגים מ-14 סניפי שופרסל בכפר סבא (מזוהים לפי קוד יישוב
רשמי, לא רשימה ידנית), מחשב פער מול המחיר המפוקח וגם פער מחיר בין הסניפים
עצמם לאותו ברקוד, ומרנדר אתר סטטי ב-`site/index.html`. עדיין רק שופרסל
(רשת פיילוט אחת) ורק קטגוריית חלב.

## הרצה מקומית

```bash
pip install -r requirements.txt
python -m unittest discover tests    # בדיקות יחידה, כולל מול ה-API החי
python scripts/daily_snapshot.py     # הריצה היומית המלאה: איסוף → חישוב → רינדור אתר
```

## הפעלת האתר (חד-פעמי)

`site/index.html` מתעדכן אוטומטית בכל commit, אבל כדי שיהיה מוגש בפועל
לציבור: הגדרות הריפו ב-GitHub → Settings → Pages → Source: "Deploy from a
branch" → branch `master`, folder `/site`. בלי חשבון נוסף.

## מבנה תיקיות

```
etl/
  scrapers/shufersal.py         # רשימת קבצים, הורדה, פענוח Price/PriceFull/Stores
  benchmarks/moag_controlled_prices.py  # מחירים מפוקחים, data.gov.il API
  category_mapping/moag_matcher.py      # התאמה דטרמיניסטית מוצר→בנצ'מרק
  scoring/
    benchmark_gap.py            # פער מול המחיר המפוקח
    cross_branch_spread.py      # פער מחיר בין סניפי אותה רשת, אותו ברקוד
  render/render_site.py         # רינדור site/index.html מנתונים מוכנים בלבד
site/                            # פלט סטטי, מוגש ע"י GitHub Pages
data/
  raw/                           # תמונות מצב גולמיות (לא ב-git; ראו .gitignore)
  processed/                     # JSON: פערים מחושבים, לפי תאריך
tests/                           # בדיקות יחידה, כולל מול נתונים אמיתיים שמורים
scripts/                         # daily_snapshot.py (הרצה יומית) + סקריפטי הדגמה
docs/                            # מקורות מאומתים ותיעוד
```
