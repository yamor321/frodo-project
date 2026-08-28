"""Renders site/methodology/index.html -- the full source list and a plain
explanation of how every number on the site is computed. Previously this
was crammed into every page's footer; as more sources and networks are
added (product images, geocoding, and eventually more chains) a dedicated
page is what actually lets every claim stay linked to a real source,
instead of the list just growing in a footer no one reads.
"""
from __future__ import annotations

METHODOLOGY_CSS = """
.method-section{ margin:34px 0; }
.method-section h2{ font-size:1.15rem; margin:0 0 8px; }
.method-section p{ color:var(--ink-muted); line-height:1.65; max-width:68ch; margin:0 0 10px; }
.source-list{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:10px; }
.source-list li{ background:var(--paper-raised); border:1px solid var(--line); border-radius:10px;
  padding:12px 16px; font-size:.92rem; line-height:1.55; }
.source-list b{ display:block; margin-bottom:2px; }
.principle{ border-inline-start:3px solid var(--navy); padding:4px 16px; margin:14px 0; color:var(--ink-muted);
  font-size:.92rem; line-height:1.6; }
"""


def render_methodology_html() -> str:
    from etl.render.layout import page_shell

    body = """
  <div class="kicker">Frodo Project · מתודולוגיה ומקורות</div>
  <h1>איך כל מספר באתר מחושב</h1>
  <p class="lede">כל מספר באתר הזה הוא אריתמטיקה טהורה על נתונים רשמיים — אין שדה אחד שמייצג שיפוט אנושי או קביעה של מודל שפה. הדף הזה מפרט בדיוק מאיפה כל מספר מגיע ואיך הוא מחושב.</p>

  <div class="method-section">
    <h2>1. איסוף המחירים</h2>
    <p>שרשראות השיווק מחויבות בחוק לפרסם קבצי מחירים מלאים לכל סניף, מתעדכנים תוך שעה משינוי בקופה. האתר קורא ישירות מהקבצים הרשמיים האלה — לא מדגם, לא הערכה.</p>
  </div>

  <div class="method-section">
    <h2>2. השוואה בין סניפים</h2>
    <p>לכל ברקוד שמופיע ב-4 סניפים לפחות באותו יום: המחיר הזול ביותר, היקר ביותר, והפער באחוזים ביניהם. אותו מוצר פיזי בדיוק, מושווה למחיר בפועל שהרשת עצמה מפרסמת.</p>
    <div class="principle">עיקרון: אין "מוצר דומה" או "מוצר שווה ערך" — רק אותו קוד מוצר (ברקוד) בדיוק, בשני סניפים או יותר.</div>
  </div>

  <div class="method-section">
    <h2>3. ציון סניף (המפה)</h2>
    <p>לכל מוצר משותף בין 4 סניפים לפחות, כל סניף מקבל אחוזון לפי מיקומו במחיר (0=זול ביותר, 100=יקר ביותר). ציון הסניף הוא הממוצע של האחוזונים האלה על כל המוצרים המשותפים שהוא מוכר. זה מספר יחסי בין הסניפים שנאספו באתר בלבד — לא "יקר" או "זול" באופן מוחלט.</p>
  </div>

  <div class="method-section">
    <h2>4. השוואה מול מחיר מפוקח</h2>
    <p>עבור מוצרי חלב שכפופים לפיקוח מחירים, המחיר בפועל מושווה למחיר המקסימלי הרשמי. ההתאמה בין מוצר בקטלוג לבין מוצר מפוקח נעשית בכלל דטרמיניסטי — מילת קטגוריה, אחוז שומן, כמות — <b>לא</b> בעזרת מודל שפה. כשההתאמה לא חד-משמעית (למשל כשלא ברור אם מדובר בקרטון או שקית), המערכת מציגה את שני המועמדים ומסמנת זאת כדו-משמעי, במקום לנחש.</p>
  </div>

  <div class="method-section">
    <h2>5. מיקום על המפה</h2>
    <p>כתובות הסניפים מגיעות מהקובץ הרשמי של הרשת, וממוקמות על המפה באמצעות שירות גיאוקוד חיצוני (OpenStreetMap Nominatim). זהו שירות חינמי ואמין, אך לא בהכרח מדויק ברמת הכניסה הפיזית לחנות — לכן מיקום הפין עשוי להיות משוער.</p>
  </div>

  <div class="method-section">
    <h2>6. תמונות מוצר</h2>
    <p>תמונות, כשקיימות, מגיעות ממאגר Open Food Facts הפתוח לפי ברקוד. הכיסוי חלקי — לא לכל מוצר יש תמונה במאגר, ובמקרה כזה מוצגת תיבה ריקה במקום תמונה שבורה.</p>
  </div>

  <div class="method-section">
    <h2>מקורות</h2>
    <ul class="source-list">
      <li><b><a href="https://prices.shufersal.co.il/" target="_blank" rel="noopener">פורטל שקיפות המחירים של שופרסל</a></b>קובצי המחירים המלאים של כל סניף, כפי שהרשת מחויבת לפרסם בחוק.</li>
      <li><b><a href="https://prices.carrefour.co.il/" target="_blank" rel="noopener">פורטל שקיפות המחירים של קרפור</a></b>אותו חוק, אותו פורמט קבצים — קובצי המחירים המלאים של כל סניף.</li>
      <li><b><a href="https://data.gov.il/dataset/price_controlled_consumer_products" target="_blank" rel="noopener">מאגר המחירים המפוקחים, data.gov.il</a></b>משרד הכלכלה והתעשייה ומשרד החקלאות — API ציבורי, ללא צורך במפתח.</li>
      <li><b><a href="https://www.nevo.co.il/law_html/law01/500_150.htm" target="_blank" rel="noopener">תקנות קידום התחרות בענף המזון (שקיפות מחירים), התשע"ה-2014</a></b>הבסיס החוקי לחובת פרסום קובצי המחירים.</li>
      <li><b><a href="https://nominatim.openstreetmap.org/" target="_blank" rel="noopener">OpenStreetMap Nominatim</a></b>גיאוקוד כתובות למיקום על המפה — חינמי, ללא מפתח.</li>
      <li><b><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a></b>רעפי המפה עצמה.</li>
      <li><b><a href="https://world.openfoodfacts.org/" target="_blank" rel="noopener">Open Food Facts</a></b>תמונות מוצר לפי ברקוד, כשקיימות — מאגר פתוח ושיתופי.</li>
      <li><b><a href="https://github.com/yamor321/frodo-project" target="_blank" rel="noopener">קוד המקור המלא של הפרויקט</a></b>כל שלב בחישוב פתוח לבדיקה — האתר נבנה ומתעדכן אוטומטית פעם ביום.</li>
    </ul>
  </div>
"""

    return page_shell(
        "מתודולוגיה ומקורות — Frodo Project", "methodology", body, f"<style>{METHODOLOGY_CSS}</style>"
    )
