#!/usr/bin/env python3
"""
أسئلة إضافية لأقسام "الرقم الأقرب" (غير كرة القدم): لحد 1000 سؤال بكل قسم، سهلة لمتوسطة ومسلية.

المصادر:
- Wikidata (بالأسماء العربية بس، ومع فلتر شهرة عشان ما تطلع أشياء مغمورة):
  دول (مساحة، سكان، حدود، مفتاح اتصال)، جبال، أنهار، جزر، مدن كبيرة، معارك، حروب، معاهدات، مشاهير (سنة الميلاد)،
  علماء ومخترعين، اختراعات، عناصر كيميائية، حيوانات (وزن، طول، عمر، حمل، سرعة)، رياضيين (ميلاد، طول)،
  أفلام، ألعاب فيديو، شركات وماركات سيارات.
- جداول ثابتة مأكد منها: سور القرآن الـ114 (آيات، ترتيب، جزء)، الأنبياء، الأشهر الهجرية، الكواكب، الأولمبياد.

الاستخدام: python engine/numbers_gen.py  (بيكتب docs/games/numbers_q.json)
"""
from __future__ import annotations

import json
import math
import random
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from players import sparql, qid, v, year, log  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "games" / "numbers_q.json"
CAP = 1000
NOW = time.gmtime().tm_year

# ---------------------------------------------------------------- القرآن
SURAHS = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف",
          "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان",
          "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص",
          "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات",
          "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون",
          "التغابن", "الطلاق", "التحريم", "الملك", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القيامة",
          "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التكوير", "الانفطار", "المطففين", "الانشقاق", "البروج", "الطارق",
          "الأعلى", "الغاشية", "الفجر", "البلد", "الشمس", "الليل", "الضحى", "الشرح", "التين", "العلق", "القدر", "البينة", "الزلزلة",
          "العاديات", "القارعة", "التكاثر", "العصر", "الهمزة", "الفيل", "قريش", "الماعون", "الكوثر", "الكافرون", "النصر", "المسد",
          "الإخلاص", "الفلق", "الناس"]
AYAT = [7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128, 111, 110, 98, 135, 112, 78, 118, 64, 77, 227, 93,
        88, 69, 60, 34, 30, 73, 54, 45, 83, 182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38, 29, 18, 45, 60, 49, 62, 55, 78, 96, 29, 22,
        24, 13, 14, 11, 11, 18, 12, 12, 30, 52, 52, 44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42, 29, 19, 36, 25, 22, 17, 19, 26, 30,
        20, 15, 21, 11, 8, 8, 19, 5, 8, 8, 11, 11, 8, 3, 9, 5, 4, 7, 3, 6, 3, 5, 4, 5, 6]
JUZ = [1, 1, 3, 4, 6, 7, 8, 9, 10, 11, 11, 12, 13, 13, 14, 14, 15, 15, 16, 16, 17, 17, 18, 18, 18, 19, 19, 20, 20, 21, 21, 21, 21,
       22, 22, 22, 23, 23, 23, 24, 24, 25, 25, 25, 25, 26, 26, 26, 26, 26, 26, 27, 27, 27, 27, 27, 27] + [28] * 9 + [29] * 11 + [30] * 37
PROPHETS = [("موسى", 136), ("إبراهيم", 69), ("نوح", 43), ("يوسف", 27), ("لوط", 27), ("آدم", 25), ("عيسى", 25), ("هارون", 20),
            ("إسحاق", 17), ("سليمان", 17), ("داود", 16), ("يعقوب", 16), ("إسماعيل", 12), ("شعيب", 11), ("صالح", 9), ("هود", 7),
            ("زكريا", 7), ("يحيى", 5), ("محمد ﷺ", 4), ("يونس", 4), ("أيوب", 4)]
HIJRI = ["محرم", "صفر", "ربيع الأول", "ربيع الآخر", "جمادى الأولى", "جمادى الآخرة", "رجب", "شعبان", "رمضان", "شوال", "ذو القعدة", "ذو الحجة"]
PRAYERS = [("الفجر", 2), ("الظهر", 4), ("العصر", 4), ("المغرب", 3), ("العشاء", 4)]

# ---------------------------------------------------------------- الكواكب والأولمبياد (أرقام ثابتة)
PLANETS = [  # الاسم، القطر بالكم، بعد عن الشمس (مليون كم)، طول السنة بأيام الأرض
    ("عطارد", 4879, 58, 88), ("الزهرة", 12104, 108, 225), ("الأرض", 12742, 150, 365), ("المريخ", 6779, 228, 687),
    ("المشتري", 139820, 778, 4333), ("زحل", 116460, 1434, 10759), ("أورانوس", 50724, 2871, 30687), ("نبتون", 49244, 4495, 60190),
]
OLYMPICS = [(1896, "أثينا"), (1900, "باريس"), (1904, "سانت لويس"), (1908, "لندن"), (1912, "ستوكهولم"), (1920, "أنتويرب"),
            (1924, "باريس"), (1928, "أمستردام"), (1932, "لوس أنجلوس"), (1936, "برلين"), (1948, "لندن"), (1952, "هلسنكي"),
            (1956, "ملبورن"), (1960, "روما"), (1964, "طوكيو"), (1968, "مكسيكو سيتي"), (1972, "ميونخ"), (1976, "مونتريال"),
            (1980, "موسكو"), (1984, "لوس أنجلوس"), (1988, "سيول"), (1992, "برشلونة"), (1996, "أتلانتا"), (2000, "سيدني"),
            (2004, "أثينا"), (2008, "بكين"), (2012, "لندن"), (2016, "ريو دي جانيرو"), (2020, "طوكيو"), (2024, "باريس")]


def bi(x):
    return "ب" + x


def li(x):
    return "لل" + x[2:] if x.startswith("ال") else "ل" + x


def clean(x):
    return re.sub(r"\s*\([^)]*\)\s*$", "", x or "").strip()


def is_ar(x):
    return bool(x) and bool(re.search(r"[؀-ۿ]", x)) and not re.search(r"[A-Za-z]{3,}", x)


def nice(x: float) -> float | int:
    """تقريب لطيف: 3 أرقام مهمة"""
    if x == 0:
        return 0
    d = 3 - int(math.floor(math.log10(abs(x)))) - 1
    r = round(x, d)
    return int(r) if r == int(r) else r


def q_safe(query: str, tries: int = 2):
    try:
        return sparql(query, tries=tries)
    except SystemExit:
        log("  ما زبط استعلام، بنكمل")
        return []
    finally:
        time.sleep(1.5)


def labelled(rows, key="x"):
    """صفوف بأسماء عربية وبدون تكرار، مرتبة حسب الشهرة"""
    out, seen = [], set()
    for b in sorted(rows, key=lambda b: -int(float(v(b, "l") or 0))):
        name = clean(v(b, "ar"))
        k = qid(v(b, key))
        if not is_ar(name) or k in seen:
            continue
        seen.add(k)
        out.append((name, b))
    return out


class Bank:
    def __init__(self):
        self.cats: dict[str, list] = {}
        self.seen = set()

    def add(self, cat, q, a, unit="", note=""):
        if a is None or q in self.seen:
            return
        if isinstance(a, float) and a.is_integer():
            a = int(a)
        self.seen.add(q)
        self.cats.setdefault(cat, []).append([q, a, unit, note])


def islamic(B: Bank):
    C = "إسلامية"
    for k, (s, a, j) in enumerate(zip(SURAHS, AYAT, JUZ), start=1):
        B.add(C, f"كم آية بسورة {s}؟", a, "آية", "")
        B.add(C, f"شو ترتيب سورة {s} بالمصحف؟", k, "", "")
        B.add(C, f"بأي جزء بتبدأ سورة {s}؟", j, "", "")
    for n, c in PROPHETS:
        B.add(C, f"كم مرة انذكر اسم {n} بالقرآن؟", c, "مرة", "حسب العدّ المشهور")
    for k, m in enumerate(HIJRI, start=1):
        B.add(C, f"شو ترتيب شهر {m} بالسنة الهجرية؟", k, "", "")
    for n, r in PRAYERS:
        B.add(C, f"كم ركعة فرض صلاة {n}؟", r, "ركعات" if r > 2 else "ركعتين", "")
    # سور جزء عمّ القصيرة: مجموع آيات سورتين ورا بعض (سهل ومسلّي للحفّاظ)
    for k in range(113):
        B.add(C, f"كم آية بسورتي {SURAHS[k]} و{SURAHS[k + 1]} مع بعض؟", AYAT[k] + AYAT[k + 1], "آية", f"{AYAT[k]} + {AYAT[k + 1]}")
    from collections import Counter
    for j, n in sorted(Counter(JUZ).items()):
        if n >= 2:
            B.add(C, f"كم سورة بتبدأ بالجزء {j}؟", n, "سور", "")
    for k in range(113):
        if AYAT[k] != AYAT[k + 1]:
            B.add(C, f"قديش الفرق بعدد الآيات بين سورة {SURAHS[k]} وسورة {SURAHS[k + 1]}؟", abs(AYAT[k] - AYAT[k + 1]), "آية", f"{AYAT[k]} و{AYAT[k + 1]}")
    B.add(C, "كم سورة بجزء عمّ (الجزء الثلاثين)؟", 37, "سورة", "من النبأ للناس")
    B.add(C, "كم سورة بجزء تبارك (الجزء 29)؟", 11, "سورة", "من الملك للمرسلات")


def space(B: Bank):
    C = "علوم وجسم الإنسان"
    for n, d, au, yr in PLANETS:
        B.add(C, f"كم كيلومتر تقريباً قطر كوكب {n}؟", d, "كم", "")
        if n != "الأرض":
            B.add(C, f"كم مليون كيلومتر تقريباً بعد كوكب {n} عن الشمس؟", au, "مليون كم", "")
            B.add(C, f"كم يوم أرضي بتطوّل السنة على كوكب {n}؟", yr, "يوم", "يعني دورة وحدة حول الشمس")


def olympics(B: Bank):
    C = "رياضة"
    order = {}
    words = {1: "أول مرة", 2: "تاني مرة", 3: "تالت مرة"}
    total = {}
    for _, c in OLYMPICS:
        total[c] = total.get(c, 0) + 1
    for y, c in OLYMPICS:
        order[c] = order.get(c, 0) + 1
        tail = f" {words[order[c]]}" if total[c] > 1 else ""
        B.add(C, f"بأي سنة انقامت الألعاب الأولمبية الصيفية {bi(c)}{tail}؟", y, "", "أولمبياد طوكيو 2020 انلعب فعلياً سنة 2021" if y == 2020 else "")


# ---------------------------------------------------------------- Wikidata
def countries(B: Bank):
    rows = q_safe("""SELECT ?x ?ar ?l ?area ?pop ?code (COUNT(DISTINCT ?nb) AS ?nbs) WHERE {
        ?x wdt:P31 wd:Q6256; wikibase:sitelinks ?l; rdfs:label ?ar FILTER(LANG(?ar)="ar")
        OPTIONAL { ?x p:P2046/psn:P2046/wikibase:quantityAmount ?area }
        OPTIONAL { ?x wdt:P1082 ?pop }
        OPTIONAL { ?x wdt:P474 ?code }
        OPTIONAL { ?x wdt:P47 ?nb. ?nb wdt:P31 wd:Q6256 } } GROUP BY ?x ?ar ?l ?area ?pop ?code""", 3)
    best = {}
    for name, b in labelled(rows):
        d = best.setdefault(name, {"l": int(float(v(b, "l") or 0))})
        for k in ("area", "pop", "code", "nbs"):
            if v(b, k) and k not in d:
                d[k] = v(b, k)
    for name, d in sorted(best.items(), key=lambda kv: -kv[1]["l"]):
        if d.get("area"):
            km2 = float(d["area"]) / 1e6
            if km2 >= 1:
                B.add("جغرافيا", f"كم كيلومتر مربع تقريباً مساحة {name}؟", nice(km2), "كم²", "")
        if d.get("pop"):
            p = float(d["pop"])
            if p >= 1e6:
                B.add("جغرافيا", f"كم مليون تقريباً عدد سكان {name}؟", nice(p / 1e6), "مليون", "حسب آخر رقم مسجل")
            elif p >= 1e4:
                B.add("جغرافيا", f"كم ألف تقريباً عدد سكان {name}؟", nice(p / 1e3), "ألف", "حسب آخر رقم مسجل")
        if d.get("nbs") and 1 <= int(d["nbs"]) <= 16:
            B.add("جغرافيا", f"كم دولة بتحدّ {name} برياً؟", int(d["nbs"]), "دول", "")
        if d.get("code"):
            c = re.sub(r"[^\d]", "", str(d["code"]))[:4]
            if c and len(c) <= 3:
                B.add("أرقام من حياتنا", f"شو مفتاح الاتصال الدولي {li(name)}؟", int(c), "", f"+{c}")
    log(f"  دول: {len(best)}")


def geo_features(B: Bank):
    specs = [
        ("Q8502", "P2044", 30, 260, lambda n, val: (f"كم متر ارتفاع {n if n.startswith(('جبل', 'قمة')) else 'جبل ' + n}؟", round(val), "متر")),
        ("Q4022", "P2043", 35, 180, lambda n, val: (f"كم كيلومتر تقريباً طول {n if n.startswith('نهر') else 'نهر ' + n}؟", nice(val / 1000), "كم")),
        ("Q23442", "P2046", 45, 90, lambda n, val: (f"كم كيلومتر مربع تقريباً مساحة {n if n.startswith('جزيرة') else 'جزيرة ' + n}؟", nice(val / 1e6), "كم²")),
        ("Q23397", "P2046", 40, 80, lambda n, val: (f"كم كيلومتر مربع تقريباً مساحة {n if n.startswith('بحيرة') else 'بحيرة ' + n}؟", nice(val / 1e6), "كم²")),
    ]
    for cls, prop, minl, lim, fmt in specs:
        rows = q_safe(f"""SELECT ?x ?ar ?l ?val WHERE {{ ?x wdt:P31 wd:{cls}; wikibase:sitelinks ?l; p:{prop}/psn:{prop}/wikibase:quantityAmount ?val.
            FILTER(?l >= {minl}) ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }}""")
        n = 0
        for name, b in labelled(rows)[:lim]:
            val = float(v(b, "val"))
            if val <= 0:
                continue
            q, a, unit = fmt(name, val)
            if a and a > 0:
                B.add("جغرافيا", q, a, unit, "")
                n += 1
        log(f"  {cls}: {n}")
    rows = q_safe("""SELECT ?x ?ar ?l ?pop WHERE { ?x wdt:P31 wd:Q1637706; wikibase:sitelinks ?l; wdt:P1082 ?pop.
        FILTER(?l >= 80 && ?pop >= 1000000) ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }""")
    for name, b in labelled(rows)[:220]:
        B.add("جغرافيا", f"كم مليون تقريباً عدد سكان مدينة {name}؟", nice(float(v(b, "pop")) / 1e6), "مليون", "حسب آخر رقم مسجل")


def events(B: Bank):
    specs = [("Q178561", 30, 320, "بأي سنة صارت {n}؟"), ("Q198", 35, 180, "بأي سنة بلّشت {n}؟"), ("Q131569", 25, 120, "بأي سنة انوقّعت {n}؟"),
             ("Q10931", 30, 80, "بأي سنة صارت {n}؟"), ("Q2133344", 35, 60, "بأي سنة انطلقت {n}؟"), ("Q7944", 35, 60, "بأي سنة صار {n}؟"),
             ("Q168983", 30, 60, "بأي سنة صار {n}؟")]
    for cls, minl, lim, tmpl in specs:
        rows = q_safe(f"""SELECT ?x ?ar ?l ?t WHERE {{ ?x wdt:P31 wd:{cls}; wikibase:sitelinks ?l. FILTER(?l >= {minl})
            {{ ?x wdt:P585 ?t }} UNION {{ ?x wdt:P580 ?t }} ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }}""")
        n = 0
        for name, b in labelled(rows)[:lim]:
            y = year(v(b, "t"))
            if y and 600 <= y <= NOW:
                B.add("تاريخ", tmpl.format(n=name), y, "", "")
                n += 1
        log(f"  {cls}: {n}")


def history_extra(B: Bank):
    rows = q_safe("""SELECT ?x ?ar ?l ?a ?b WHERE { ?x wdt:P31 wd:Q48349; wikibase:sitelinks ?l. FILTER(?l >= 40)
        OPTIONAL { ?x wdt:P571 ?a } OPTIONAL { ?x wdt:P576 ?b } ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }""")
    for name, b in labelled(rows)[:120]:
        a, z = year(v(b, "a")), year(v(b, "b"))
        if a and 500 <= a <= 1950:
            B.add("تاريخ", f"بأي سنة تأسست {name}؟", a, "", "")
        if z and 500 <= z <= 2000:
            B.add("تاريخ", f"بأي سنة انتهت {name}؟", z, "", "")
    rows = q_safe("""SELECT ?x ?ar ?l ?t WHERE { ?x p:P166 ?st. ?st ps:P166 ?pr; pq:P585 ?t. ?pr wdt:P31 wd:Q7191.
        ?x wikibase:sitelinks ?l. FILTER(?l >= 60) ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }""")
    for name, b in labelled(rows)[:180]:
        y = year(v(b, "t"))
        if y:
            B.add("تاريخ", f"بأي سنة أخذ {name} جائزة نوبل؟", y, "", "")
    for cls, word in (("Q12518", "انبنى"), ("Q570116", "افتتح"), ("Q839954", "انبنى")):
        rows = q_safe(f"""SELECT ?x ?ar ?l ?t WHERE {{ ?x wdt:P31 wd:{cls}; wikibase:sitelinks ?l; wdt:P571 ?t. FILTER(?l >= 45)
            ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }}""")
        for name, b in labelled(rows)[:120]:
            y = year(v(b, "t"))
            if y and 1000 <= y <= NOW:
                B.add("تاريخ", f"بأي سنة {word} «{name}»؟", y, "", "")


def people(B: Bank):
    groups = [  # (مهنة، أقل شهرة، كم، القسم)
        ("Q116", 60, 120, "تاريخ"), ("Q33999", 90, 220, "أرقام من حياتنا"), ("Q177220", 70, 160, "أرقام من حياتنا"),
        ("Q36180", 110, 150, "تاريخ"), ("Q1028181", 80, 90, "تاريخ"), ("Q4964182", 90, 80, "تاريخ"), ("Q36834", 70, 70, "أرقام من حياتنا"),
        ("Q169470", 70, 150, "علوم وجسم الإنسان"), ("Q593644", 60, 90, "علوم وجسم الإنسان"), ("Q170790", 60, 100, "علوم وجسم الإنسان"),
        ("Q205375", 45, 100, "علوم وجسم الإنسان"), ("Q864503", 50, 60, "علوم وجسم الإنسان"), ("Q11063", 50, 60, "علوم وجسم الإنسان"),
        ("Q39631", 50, 60, "علوم وجسم الإنسان"),
        ("Q3665646", 35, 160, "رياضة"), ("Q10833314", 35, 150, "رياضة"), ("Q10841764", 35, 110, "رياضة"), ("Q11338576", 30, 100, "رياضة"),
        ("Q10843402", 30, 80, "رياضة"), ("Q11513337", 30, 100, "رياضة"), ("Q10873124", 35, 70, "رياضة"), ("Q2309784", 40, 50, "رياضة"),
        ("Q11303721", 35, 40, "رياضة"), ("Q11607585", 30, 50, "رياضة"), ("Q13474373", 40, 50, "رياضة"),
    ]
    used = set()
    for occ, minl, lim, cat in groups:
        rows = q_safe(f"""SELECT ?x ?ar ?l ?b ?h WHERE {{ ?x wdt:P106 wd:{occ}; wikibase:sitelinks ?l; wdt:P569 ?b. FILTER(?l >= {minl})
            OPTIONAL {{ ?x p:P2048/psn:P2048/wikibase:quantityAmount ?h }}
            ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }}""")
        n = 0
        for name, b in labelled(rows):
            k = qid(v(b, "x"))
            if k in used:
                continue
            used.add(k)
            y = year(v(b, "b"))
            if not y or y < 1000:
                continue
            B.add(cat, f"بأي سنة انولد {name}؟", y, "", "")
            if cat == "رياضة" and v(b, "h"):
                h = float(v(b, "h")) * 100
                if 150 <= h <= 230:
                    B.add(cat, f"كم طول {name} بالسنتيمتر؟", round(h), "سم", "")
            n += 1
            if n >= lim:
                break
        log(f"  {occ}: {n}")


def science(B: Bank):
    C = "علوم وجسم الإنسان"
    rows = q_safe("""SELECT ?x ?ar ?l ?z ?d WHERE { ?x wdt:P31 wd:Q11344; wdt:P1086 ?z; wikibase:sitelinks ?l.
        OPTIONAL { ?x wdt:P575 ?d } ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }""")
    for name, b in labelled(rows):
        z = int(float(v(b, "z")))
        if z <= 118:
            B.add(C, f"شو الرقم الذري لعنصر {name}؟", z, "", "")
        y = year(v(b, "d"))
        if y and 1600 <= y <= NOW:
            B.add(C, f"بأي سنة انكشف عنصر {name}؟", y, "", "")
    rows = q_safe("""SELECT ?x ?ar ?l ?t WHERE { ?x wdt:P575 ?t; wikibase:sitelinks ?l. FILTER(?l >= 60)
        FILTER NOT EXISTS { ?x wdt:P31 wd:Q11344 } ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }""")
    n = 0
    for name, b in labelled(rows)[:220]:
        y = year(v(b, "t"))
        if y and 1400 <= y <= NOW:
            B.add(C, f"بأي سنة انخترع أو انكشف «{name}»؟", y, "", "")
            n += 1
    log(f"  اختراعات: {n}")


def animals(B: Bank):
    C = "حيوانات"
    props = [("P2067", "كم كيلو تقريباً وزن {n} الكبير؟", 1, "كيلو", lambda x: x), ("P2048", "كم سنتيمتر تقريباً طول {n}؟", 1, "سم", lambda x: x * 100),
             ("P2043", "كم سنتيمتر تقريباً طول جسم {n}؟", 1, "سم", lambda x: x * 100), ("P2250", "كم سنة تقريباً بيعيش {n}؟", 1, "سنة", lambda x: x / 31557600),
             ("P3063", "كم يوم تقريباً مدة حمل {n}؟", 1, "يوم", lambda x: x / 86400), ("P2052", "كم كيلو بالساعة تقريباً أعلى سرعة عند {n}؟", 1, "كم/س", lambda x: x * 3.6)]
    for prop, tmpl, _, unit, conv in props:
        rows = q_safe(f"""SELECT ?x ?ar ?l ?val WHERE {{ ?x p:{prop}/psn:{prop}/wikibase:quantityAmount ?val; wdt:P171 ?par; wikibase:sitelinks ?l.
            FILTER(?l >= 35) ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }}""", 3)
        n = 0
        for name, b in labelled(rows)[:160]:
            val = conv(float(v(b, "val")))
            if val > 0:
                B.add(C, tmpl.format(n=name), nice(val), unit, "حسب الأرقام المسجلة، وبتختلف من حيوان لحيوان")
                n += 1
        log(f"  حيوانات {prop}: {n}")
    # كم رجل: طيور (2) وعناكب (8) وحشرات (6)، من رتب معروفة (مستوى أو مستويين تحت الصنف)
    groups = [("Q5113", 2, "رجلين", "لأنه طير"), ("Q1390", 6, "أرجل", "لأنه حشرة"), ("Q1358", 8, "أرجل", "لأنه من العنكبوتيات")]
    for cls, legs, unit, why in groups:
        rows = q_safe(f"""SELECT ?x ?ar ?l WHERE {{ ?x wdt:P171/wdt:P171/wdt:P171 wd:{cls}; wikibase:sitelinks ?l. FILTER(?l >= 40)
            ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }}""", 1)
        rows += q_safe(f"""SELECT ?x ?ar ?l WHERE {{ ?x wdt:P171/wdt:P171/wdt:P171/wdt:P171 wd:{cls}; wikibase:sitelinks ?l. FILTER(?l >= 40)
            ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }}""", 1)
        n = 0
        for name, b in labelled(rows)[:140]:
            B.add(C, f"كم رجل عند {name}؟", legs, unit, why)
            n += 1
        log(f"  أرجل {cls}: {n}")
    # حجرات القلب حسب الصنف
    for cls, ch, why in (("Q5113", 4, "قلب الطيور 4 حجرات"), ("Q10811", 3, "قلب الزواحف غالباً 3 حجرات"), ("Q10908", 3, "قلب البرمائيات 3 حجرات")):
        rows = q_safe(f"""SELECT ?x ?ar ?l WHERE {{ ?x wdt:P171/wdt:P171/wdt:P171 wd:{cls}; wikibase:sitelinks ?l. FILTER(?l >= 50)
            ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }}""", 1)
        for name, b in labelled(rows)[:40]:
            if "تمساح" in name:
                continue
            B.add(C, f"كم حجرة بقلب {name}؟", ch, "حجرات", why)


def culture(B: Bank):
    C = "أرقام من حياتنا"
    specs = [("Q11424", 60, 260, "بأي سنة نزل فيلم «{n}»؟", "P577"), ("Q7889", 45, 150, "بأي سنة نزلت لعبة «{n}»؟", "P577"),
             ("Q5398426", 45, 120, "بأي سنة نزل مسلسل «{n}»؟", "P580"), ("Q581714", 30, 80, "بأي سنة نزل الكرتون «{n}»؟", "P580"),
             ("Q35127", 50, 80, "بأي سنة انطلق موقع «{n}»؟", "P571"), ("Q166142", 50, 60, "بأي سنة نزل تطبيق «{n}»؟", "P577")]
    for cls, minl, lim, tmpl, prop in specs:
        rows = q_safe(f"""SELECT ?x ?ar ?l ?t WHERE {{ ?x wdt:P31 wd:{cls}; wdt:{prop} ?t; wikibase:sitelinks ?l. FILTER(?l >= {minl})
            ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }}""", 3)
        n = 0
        for name, b in labelled(rows)[:lim]:
            y = year(v(b, "t"))
            if y and 1900 <= y <= NOW:
                B.add(C, tmpl.format(n=name), y, "", "")
                n += 1
        log(f"  {cls}: {n}")
    for cls, minl, lim, tmpl in [("Q4830453", 60, 160, "بأي سنة تأسست شركة {n}؟"), ("Q891723", 60, 160, "بأي سنة تأسست شركة {n}؟"),
                                 ("Q6881511", 60, 120, "بأي سنة تأسست شركة {n}؟"), ("Q786820", 35, 90, "بأي سنة تأسست {n}؟"),
                                 ("Q431289", 40, 100, "بأي سنة انطلقت ماركة {n}؟"), ("Q167270", 40, 80, "بأي سنة انطلقت ماركة {n}؟")]:
        rows = q_safe(f"""SELECT ?x ?ar ?l ?t WHERE {{ ?x wdt:P31 wd:{cls}; wikibase:sitelinks ?l; wdt:P571 ?t. FILTER(?l >= {minl})
            ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }}""")
        n = 0
        for name, b in labelled(rows)[:lim]:
            y = year(v(b, "t"))
            if y and 1800 <= y <= NOW:
                B.add(C, tmpl.format(n=name), y, "", "")
                n += 1
        log(f"  {cls}: {n}")


def main() -> int:
    B = Bank()
    islamic(B)
    space(B)
    olympics(B)
    for step in (countries, geo_features, events, history_extra, people, science, animals, culture):
        log(f"بجيب: {step.__name__}")
        try:
            step(B)
        except Exception as e:
            log(f"  {step.__name__} ما زبط: {e}")
    rnd = random.Random(7)
    out = {}
    for cat, qs in B.cats.items():
        if len(qs) > CAP:   # بنخلي أول الأسئلة (الأشهر) ونختار من الباقي
            head = qs[: CAP // 2]
            rest = qs[CAP // 2:]
            rnd.shuffle(rest)
            qs = head + rest[: CAP - len(head)]
        out[cat] = qs
        log(f"  {cat}: {len(qs)}")
    OUT.write_text(json.dumps({"generated": time.strftime("%Y-%m-%d"), "cats": out}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"numbers_q.json: {sum(len(q) for q in out.values())} سؤال ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
