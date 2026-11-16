#!/usr/bin/env python3
"""
مولّد بنك «جمع نقاط» من البيانات (Wikidata بـengine/wd + ملفات مفتوحة بـengine/data).

القواعد (طلب سامر: الجودة قبل العدد، بدون تكرار، بدون أسئلة مستحيلة):
- بناخذ الكيانات الأشهر أول (sitelinks + مقالة عربية)، وبنوقف لما يوصل القسم هدفه. ما بننزل للمغمورين عشان نعبّي عدد.
- الصعوبة من ترتيب الشهرة جوّا القسم، ومن قرب الخيارات الغلط (سهل = خيارات بعيدة، صعب = من نفس البلد/الفصيلة/الحقبة).
- الخيارات الغلط من نفس الصنف، والأشخاص من نفس الجنس.
- أي سؤال جوابه مش واحد (مكان بدولتين، اسم مكرر) بينشال.
"""
from __future__ import annotations

import json
import random
import re
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
WD = HERE / "wd"
DATA = HERE / "data"
R = random.Random(1116)

LATIN = re.compile(r"[A-Za-z]")
DIAC = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")


def log(m):
    import sys
    print(m, file=sys.stderr, flush=True)


# ---------- أدوات ----------
def norm(s: str) -> str:
    s = DIAC.sub("", str(s or ""))
    s = re.sub("[إأآٱ]", "ا", s).replace("ة", "ه").replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    s = re.sub(r"[\s\-_.,،:()«»\"'/]+", "", s)
    return s.lower()


def clean(s):
    if not s:
        return None
    s = DIAC.sub("", re.sub(r"\s*\([^)]*\)\s*", " ", str(s))).strip()
    s = re.sub(r"\s+", " ", s).strip(" ،,-")
    if not s or LATIN.search(s) or len(s) > 38 or re.fullmatch(r"[\d\s]+", s) or re.search(r"[Q]\d{2,}", s):
        return None
    return s


def wd(key):
    p = WD / f"{key}.json"
    if not p.exists():
        return []
    try:
        items = json.loads(p.read_text(encoding="utf-8"))["items"]
    except Exception:
        return []
    out = []
    for it in items:
        it["ar"] = clean(it.get("ar"))
        if it["ar"]:
            out.append(it)
    return out


def labs(it, k):
    out = []
    for v in it.get(k) or []:
        q, _, l = str(v).partition(":")
        l = clean(l)
        if l and l not in out:
            out.append(l)
    return out


def lab1(it, k):
    """قيمة وحدة بس (إذا في أكثر من قيمة مختلفة = مش واضح، منرجّع None)."""
    ls = labs(it, k)
    return ls[0] if len(ls) == 1 else None


def qids(it, k):
    return [str(v).partition(":")[0] for v in it.get(k) or []]


def year(it, k):
    ys = []
    for v in it.get(k) or []:
        try:
            y = int(str(v)[:5].replace("-", "")) if str(v).startswith("-") is False else -int(str(v)[1:5])
            ys.append(y)
        except Exception:
            pass
    return min(ys) if ys else None


def num(it, k):
    for v in it.get(k) or []:
        try:
            return float(v)
        except Exception:
            pass
    return None


def img_url(fname, w=640):
    if not fname:
        return None
    return "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(fname.replace(" ", "_")) + f"?width={w}"


def score(it):
    return it.get("sl", 0) * (1.35 if it.get("arw") else 1.0)


def dedupe(items):
    """كيان واحد لكل اسم (بعد التطبيع)، والأشهر بيربح. والأسماء المكررة لكيانات مختلفة بتنشال كلها (غموض)."""
    by = defaultdict(list)
    for it in items:
        by[norm(it["ar"])].append(it)
    out = []
    for k, group in by.items():
        group.sort(key=score, reverse=True)
        if len(group) > 1 and score(group[1]) > score(group[0]) * 0.5:
            continue   # اسمين لشيئين مشهورين = سؤال مش واضح
        out.append(group[0])
    return sorted(out, key=score, reverse=True)


def with_levels(items):
    """الصعوبة من ترتيب الشهرة: الربع الأول سهل ... الربع الأخير صعب جداً."""
    items = sorted(items, key=score, reverse=True)
    n = len(items)
    for i, it in enumerate(items):
        it["lv"] = 1 + min(3, int(4 * i / max(1, n)))
    return items


def pick_wrong(ans, cands, near=(), lv=2, k=3):
    """خيارات غلط: بالمستويات الصعبة من القريبين (near) أول، وبالسهلة من البعيدين."""
    na = norm(ans)
    seen = {na}
    out = []
    pools = []
    near = [c for c in near if c]
    far = [c for c in cands if c and c not in near]
    if lv >= 3:
        pools = [near, cands]
    elif lv == 2:
        pools = [near[: max(1, len(near) // 2)] + far, cands] if near else [cands]
    else:
        pools = [far or cands, cands]
    for pool in pools:
        for c in R.sample(pool, len(pool)):
            nc = norm(c)
            if nc in seen or na in nc or nc in na:
                continue
            seen.add(nc)
            out.append(c)
            if len(out) == k:
                return out
    return out if len(out) == k else None


# ---------- خرائط مساعدة ----------
_COUNTRY = None


def countries():
    """الدول من Wikidata: الاسم العربي ← قارة، عاصمة، عملة..."""
    global _COUNTRY
    if _COUNTRY is None:
        _COUNTRY = {}
        for it in wd("countries"):
            _COUNTRY[it["ar"]] = it
    return _COUNTRY


def continent_of(country_label):
    it = countries().get(country_label)
    return lab1(it, "continent") if it else None


def near_countries(country_label, pool):
    c = continent_of(country_label)
    return [x for x in pool if x != country_label and continent_of(x) == c] if c else []


ARAB_DESC_AR = re.compile(r"(مصري|سوري|لبناني|أردني|سعودي|كويتي|عراقي|مغربي|جزائري|تونسي|إماراتي|فلسطيني|قطري|بحريني|عماني|يمني|سوداني|ليبي|موريتاني)")
ARAB_DESC_EN = re.compile(r"(Egyptian|Syrian|Lebanese|Jordanian|Saudi|Kuwaiti|Iraqi|Moroccan|Algerian|Tunisian|Emirati|Palestinian|Qatari|Bahraini|Omani|Yemeni|Sudanese|Libyan|Mauritanian)")


def desc(it, en=None, ar=None):
    """الوصف بيأكد شو هالشخص فعلاً (مش كل اللي إله مهنة «ممثل» بويكيداتا ممثل)."""
    e, a = it.get("end"), it.get("ard") or ""
    e = e if isinstance(e, str) else ""
    return bool((en and re.search(en, e, re.I)) or (ar and re.search(ar, a)))


def only(items, en=None, ar=None):
    return [it for it in items if desc(it, en, ar)]


def arab(items):
    return [it for it in items if ARAB_DESC_AR.search(it.get("ard") or "") or ARAB_DESC_EN.search(it.get("end") or "")]


ARAB_AR = {"الأردن", "السعودية", "مصر", "العراق", "سوريا", "لبنان", "فلسطين", "الكويت", "الإمارات العربية المتحدة", "قطر", "البحرين",
           "سلطنة عمان", "اليمن", "المغرب", "الجزائر", "تونس", "ليبيا", "السودان", "موريتانيا", "الصومال", "جيبوتي", "جزر القمر"}


# ---------- مولّد أقسام الصور ----------
class Builder:
    def __init__(self, cats, Cat):
        self.cats, self.Cat = cats, Cat

    def cat(self, cid, name, icon):
        if cid not in self.cats:
            self.cats[cid] = self.Cat(cid, name, icon)
        return self.cats[cid]

    def image_cat(self, cid, name, icon, items, target, prompt, types=(), gender=False, group=None, img_key="img", min_items=20, max_words=5,
                  top=None, need_arw=False, same=None, type_max_lv=4):
        """قسم صور: سؤال «شو اسمه؟» لكل كيان + أنواع إضافية (دولة، مدينة...). بنوقف عند الهدف."""
        c = self.cat(cid, name, icon)
        items = [it for it in dedupe(items) if it.get(img_key) and len(it["ar"].split()) <= max_words and (it.get("arw") or not need_arw)]
        if top:
            items = items[:top]
        if len(items) < min_items:
            log(f"  ⚠️ {cid}: {len(items)} كيان بس")
        # بنقدّر كم كيان بدنا: كل كيان بيعطي 1 + أنواع
        per = 1 + sum(0.6 for _ in types)
        need = int(target * 1.12 / per) + 10
        items = with_levels(items[:max(need, min_items)])
        names = [it["ar"] for it in items]
        top = names[: max(12, len(names) // 2)]
        have = {(q[1], q[2][0]) for q in c.qs}
        for it in items:
            lv = it["lv"]
            near = []
            if group:
                g = group(it)
                near = [x["ar"] for x in items if x is not it and g and group(x) == g]
            if gender:
                sg = (it.get("gender") or [None])[0]
                pool = [x["ar"] for x in items if (x.get("gender") or [None])[0] == sg]
                near = [n for n in near if n in pool]
            elif same:
                sk = same(it)
                pool = [x["ar"] for x in items if same(x) == sk]
                near = [n for n in near if n in pool]
            else:
                pool = names
            wrong = pick_wrong(it["ar"], pool if lv >= 2 else [n for n in top if n in pool] or pool, near, lv)
            url = img_url(it[img_key])
            fem = (it.get("gender") or [None])[0] == "Q6581072"
            pr = (prompt[1] if fem else prompt[0]) if isinstance(prompt, tuple) else prompt
            if wrong and (pr, it["ar"]) not in have:
                c.add(lv, pr, [it["ar"]] + wrong, url)
                have.add((pr, it["ar"]))
            for (tprompt, fn, shift, tpool, tnear) in types:
                v = fn(it)
                if not v or lv > type_max_lv:
                    continue
                if isinstance(tprompt, tuple):
                    tprompt = tprompt[1] if fem else tprompt[0]
                vpool = tpool(items) if callable(tpool) else tpool
                vnear = tnear(v, vpool) if tnear else []
                tl = max(1, min(4, lv + shift))
                w = pick_wrong(v, vpool, vnear, tl)
                if w:
                    c.add(tl, tprompt, [v] + w, url)
        return c


def cat_countries(items, key="country"):
    """الدول اللي بتظهر بالقسم نفسه (عشان الخيارات تكون معقولة، مش جزر صغيرة ما حدا بيعرفها)."""
    cnt = Counter(lab1(x, key) for x in items if lab1(x, key))
    return [k for k, n in cnt.items() if n >= 2 and k in countries()]


def near_in(v, pool):
    c = continent_of(v)
    return [x for x in pool if x != v and continent_of(x) == c]


def place_types(country_q, city_q=None):
    """أنواع إضافية للأماكن: بأي دولة؟ بأي مدينة؟ (الجواب لازم يكون دولة وحدة واضحة)."""
    def ctry(it):
        v = lab1(it, "country")
        return v if v in countries() else None

    def citypool(items):
        return sorted({lab1(x, "city") for x in items if lab1(x, "city")})

    def city_of(it):
        v = lab1(it, "city")
        return v if v and norm(v) not in norm(it["ar"]) and v not in countries() and not re.search(r"(قضاء|محافظة|مقاطعة|ولاية|إقليم|منطقة)", v) else None

    t = [(country_q, ctry, 0, cat_countries, near_in)]
    if city_q:
        t.append((city_q, city_of, 1, citypool, lambda v, pool: pool))
    return t


def person_types(noun="هاد", noun_f=None):
    def nat(it):
        return lab1(it, "citizen") or lab1(it, "nat_sport")

    def natpool(items):
        cnt = Counter(nat(x) for x in items if nat(x))
        return [k for k, n in cnt.items() if n >= 2 and k in countries()]

    def near(v, pool):
        c = continent_of(v)
        return [x for x in pool if x != v and continent_of(x) == c]
    q = (f"من وين {noun}؟", f"من وين {noun_f}؟") if noun_f else f"من وين {noun}؟"
    return [(q, nat, 1, natpool, near)]


def generate(cats, Cat, targets):
    b = Builder(cats, Cat)
    T = targets
    nat_key = lambda it: lab1(it, "citizen") or lab1(it, "nat_sport")

    # ---- أماكن ----
    lm = wd("landmarks") + wd("whs")
    b.image_cat("landmarks", "معالم حول العالم", "🏛️", lm, T("landmarks"), "شو اسم هالمكان؟", place_types("بأي دولة هالمَعلم؟", "بأي مدينة هالمَعلم؟"), group=lambda it: lab1(it, "country"))
    b.image_cat("castles", "قلاع وقصور", "🏰", wd("castles"), T("castles"), "شو اسم هالقلعة/القصر؟", place_types("بأي دولة هالمكان؟", "بأي مدينة هالمكان؟"), group=lambda it: lab1(it, "country"))
    b.image_cat("mosques", "مساجد مشهورة", "🕌", wd("mosques"), T("mosques"), "شو اسم هالمسجد؟", place_types("بأي دولة هالمسجد؟", "بأي مدينة هالمسجد؟"), group=lambda it: lab1(it, "country"))
    b.image_cat("bridges", "جسور مشهورة", "🌉", wd("bridges"), T("bridges"), "شو اسم هالجسر؟", place_types("بأي دولة هالجسر؟", "بأي مدينة هالجسر؟"), group=lambda it: lab1(it, "country"))
    b.image_cat("towers", "أبراج وناطحات سحاب", "🏙️", wd("towers"), T("towers"), "شو اسم هالبرج؟", place_types("بأي دولة هالبرج؟", "بأي مدينة هالبرج؟"), group=lambda it: lab1(it, "country"))
    b.image_cat("museums", "متاحف عالمية", "🖼️", wd("museums"), T("museums"), "شو اسم هالمتحف؟", place_types("بأي دولة هالمتحف؟", "بأي مدينة هالمتحف؟"), group=lambda it: lab1(it, "country"))
    b.image_cat("ancient", "آثار وحضارات قديمة", "🏺", wd("ancient"), T("ancient"), "شو اسم هالموقع الأثري؟", place_types("بأي دولة هالموقع الأثري؟"),
                group=lambda it: lab1(it, "country"))
    b.image_cat("waterfalls", "شلالات", "💦", wd("waterfalls"), T("waterfalls"), "شو اسم هالشلال؟", place_types("بأي دولة هالشلال؟"),
                group=lambda it: lab1(it, "country"))
    b.image_cat("mountains", "جبال وقمم", "🏔️", wd("mountains"), T("mountains"), "شو اسم هالجبل؟", place_types("بأي دولة هالجبل؟"),
                group=lambda it: lab1(it, "continent"))
    b.image_cat("islands", "جزر مشهورة", "🏝️", wd("islands"), T("islands"), "شو اسم هالجزيرة؟", place_types("بأي دولة هالجزيرة؟"),
                group=lambda it: lab1(it, "continent"))
    b.image_cat("cities", "مدن العالم", "🌆", wd("cities"), T("cities"), "شو اسم هالمدينة؟", place_types("بأي دولة هالمدينة؟"),
                group=lambda it: lab1(it, "country"))
    st_types = place_types("بأي دولة هالملعب؟", "بأي مدينة هالملعب؟") + [("لأي نادي هالملعب؟", lambda it: lab1(it, "tenant"), 1,
                                          lambda items: sorted({lab1(x, "tenant") for x in items if lab1(x, "tenant")}), None)]
    b.image_cat("stadiums", "ملاعب العالم", "🏟️", wd("stadiums"), T("stadiums"), "شو اسم هالملعب؟", st_types, group=lambda it: lab1(it, "country"), type_max_lv=3)

    # ---- ناس ----
    ACT = (r"\b(actor|actress)\b", r"(ممثل|ممثلة)")
    b.image_cat("actors", "ممثلين", "🎬", only(wd("actors"), *ACT) + arab(only(wd("actors_arab"), *ACT)), T("actors"), ("مين هالممثل؟", "مين هالممثلة؟"), person_types("هالممثل", "هالممثلة"),
                gender=True, group=nat_key)
    SING = (r"\b(singer|rapper|vocalist|musician)\b", r"(مغن|مطرب|مغني|مغنية|مطربة)")
    b.image_cat("singerspics", "مطربين بالصور", "🎤", only(wd("singers"), *SING) + arab(only(wd("singers_arab"), *SING)), T("singerspics"), ("مين هالمطرب؟", "مين هالمطربة؟"), person_types("هالمطرب", "هالمطربة"),
                gender=True, group=nat_key)
    SCI = (r"(physicist|chemist|mathematician|biologist|scientist|inventor|astronomer|engineer|botanist|zoologist|naturalist|physician|geologist|polymath)",
           r"(عالم|فيزيائي|كيميائي|رياضي|مخترع|فلكي|مهندس|طبيب|عالمة)")
    b.image_cat("scientists", "علماء ومخترعين", "🔬", only(wd("scientists"), *SCI), T("scientists"), ("مين هالعالم؟", "مين هالعالمة؟"), person_types("هالعالم", "هالعالمة"), gender=True, group=nat_key)
    b.image_cat("historic", "شخصيات تاريخية بالصور", "📜", wd("historic_pol") + wd("historic_art") + wd("historic_arab") + only(wd("celebs_tv"), r"(politician|statesman|president|king|emperor|leader|revolutionary)", None), T("historic"), "مين هالشخصية؟", person_types("هالشخصية"),
                gender=True, group=nat_key)
    b.image_cat("celebs", "مشاهير بالصور", "⭐", wd("celebs_tv") + wd("celebs_biz") + wd("astronauts"), T("celebs"), "مين هاد؟", person_types("هالشخص"), gender=True, group=nat_key)
    ath_types = person_types("هالبطل", "هالبطلة") + [(("شو رياضة هالبطل؟", "شو رياضة هالبطلة؟"), lambda it: lab1(it, "sport"), 0,
                                            lambda items: sorted({lab1(x, "sport") for x in items if lab1(x, "sport")}), None)]
    b.image_cat("athletes", "أبطال رياضة عالميين", "🏅", wd("athletes"), T("athletes"), ("مين هالبطل؟", "مين هالبطلة؟"), ath_types, gender=True,
                group=lambda it: lab1(it, "sport"))
    b.image_cat("wrestlers", "مصارعين", "🤼", only(wd("wrestlers"), r"wrestler", r"مصارع"), T("wrestlers"), ("مين هالمصارع؟", "مين هالمصارعة؟"), (), gender=True)
    b.image_cat("coaches", "مدربين كرة قدم", "📋", wd("coaches"), T("coaches"), "مين هالمدرب؟", person_types("هالمدرب"), gender=True, group=nat_key)
    b.image_cat("arabplayers", "لاعبين عرب بالصور", "🌙", only(wd("arabplayers"), r"football|soccer", r"(كرة|لاعب)"), T("arabplayers"), "مين هاللاعب؟", person_types("هاللاعب"),
                gender=True, group=nat_key)

    # ---- طبيعة ----
    taxa_group = lambda it: lab1(it, "parent_taxon")
    # أسماء عائلات (كلبيات، أرنبيات...) وأشباه البشر مش أسماء حيوانات بتنعرف من صورة
    def species(items):
        return [it for it in items if not re.search(r"(يات|يّات)$", it["ar"]) and not re.search(r"^(إنسان|أسترالوبيثكس|هومو)", it["ar"])
                and not re.search(r"^(family|order|genus|superfamily|subfamily|infraorder|suborder|clade|tribe|group)\b|extinct species of human|hominin|archaic human", it.get("end") or "", re.I)]
    b.image_cat("animals", "حيوانات", "🦁", species(wd("mammals")), T("animals"), "شو هالحيوان؟", (), group=taxa_group, top=220, need_arw=True, max_words=3)
    b.image_cat("birds", "طيور بالصور", "🦅", species(wd("birds")), T("birds"), "شو هالطير؟", (), group=taxa_group, top=170, need_arw=True, max_words=3)
    b.image_cat("reptiles", "زواحف وبرمائيات", "🦎", species(wd("reptiles") + wd("amphibians")), T("reptiles"), "شو هالحيوان؟", (), group=taxa_group, top=90, need_arw=True, max_words=3)
    b.image_cat("sealife", "حيوانات بحرية", "🐙", species(wd("sharks") + wd("cetaceans") + wd("sea_more") + wd("crustaceans")), T("sealife"),
                "شو هالحيوان البحري؟", (), group=taxa_group, top=110, need_arw=True, max_words=3)
    b.image_cat("insects", "حشرات", "🐞", species(wd("insects2") + wd("arachnids")), T("insects"), "شو هاد؟", (), group=taxa_group, top=75, need_arw=True, max_words=3)
    b.image_cat("dinos", "ديناصورات", "🦖", wd("dinos"), T("dinos"), "شو اسم هالديناصور؟", (), group=taxa_group, top=45, need_arw=True, max_words=2)
    breed_types = [("من وين أصل هالسلالة؟", lambda it: lab1(it, "origin") if lab1(it, "origin") in countries() else None, 1,
                    lambda items: cat_countries(items, "origin"), near_in)]
    b.image_cat("pets", "سلالات كلاب وقطط", "🐕", [dict(x, _k="dog") for x in wd("dog_breeds")] + [dict(x, _k="cat") for x in wd("cat_breeds")], T("pets"), "شو هالسلالة؟", breed_types,
                same=lambda it: it.get("_k"))
    b.image_cat("plants", "ورود ونباتات", "🌷", wd("flowers"), T("plants"), "شو هالنبتة؟", (), group=taxa_group, top=150, need_arw=True, max_words=2)
    b.image_cat("trees", "أشجار", "🌳", wd("trees"), T("trees"), "شو هالشجرة؟", (), group=taxa_group, top=90, need_arw=True, max_words=2)
    b.image_cat("fruits", "فواكه وخضار", "🍎", only(wd("fruits") + wd("vegetables") + wd("fruits2") + wd("vegetables2"), r"(fruit|vegetable|berry|\bnut\b|legume|citrus|squash)", r"(فاكهة|فواكه|ثمرة|ثمار|خضار|خضروات|خضراوات|بقول)"), T("fruits"), "شو هاد؟", (), max_words=3)
    b.image_cat("spices", "بهارات وتوابل", "🌶️", only(wd("spices"), r"(spice|herb|seasoning)", r"(توابل|بهار|تابل|عشب)"), T("spices"), "شو هالبهار؟", (), max_words=3)
    b.image_cat("gems", "أحجار كريمة ومعادن", "💎", wd("gems"), T("gems"), "شو هالحجر؟", (), max_words=3)
    # الكوكبات (صور سما بخطوط باهتة) مستحيلة تنعرف من الصورة، فبنشيلها
    sp = [it for it in wd("planets_space") if not re.search(r"constellation|asterism", it.get("end") or "", re.I) and "كوكبة" not in (it.get("ard") or "")]
    b.image_cat("space", "الفضاء", "🪐", sp, T("space"), "شو هاد؟", (), top=60, min_items=8)

    # ---- أكل وأشياء ----
    DEMONYM = {"Italy": "Italian", "France": "French", "Spain": "Spanish", "Mexico": "Mexican", "Japan": "Japanese", "China": "Chinese",
               "India": "Indian", "Turkey": "Turkish", "Greece": "Greek", "Germany": "German", "United Kingdom": "British|English|Scottish|Welsh",
               "United States": "American", "Lebanon": "Lebanese", "Syria": "Syrian", "Egypt": "Egyptian", "Morocco": "Moroccan", "Tunisia": "Tunisian",
               "Algeria": "Algerian", "Iran": "Persian|Iranian", "Iraq": "Iraqi", "Saudi Arabia": "Saudi", "Jordan": "Jordanian", "Palestine": "Palestinian",
               "Thailand": "Thai", "Vietnam": "Vietnamese", "Korea": "Korean", "South Korea": "Korean", "Russia": "Russian", "Poland": "Polish",
               "Portugal": "Portuguese", "Brazil": "Brazilian", "Argentina": "Argentin", "Peru": "Peruvian", "Netherlands": "Dutch", "Belgium": "Belgian",
               "Austria": "Austrian", "Switzerland": "Swiss", "Sweden": "Swedish", "Hungary": "Hungarian", "Ireland": "Irish", "Indonesia": "Indonesian",
               "Philippines": "Filipino", "Malaysia": "Malaysian", "Pakistan": "Pakistani", "Ukraine": "Ukrainian", "Georgia": "Georgian",
               "Armenia": "Armenian", "Israel": "Israeli", "Cuba": "Cuban", "Colombia": "Colombian", "Chile": "Chilean", "Canada": "Canadian",
               "Australia": "Australian", "Denmark": "Danish", "Norway": "Norwegian", "Finland": "Finnish", "Czech Republic": "Czech", "Ethiopia": "Ethiopian",
               "Nigeria": "Nigerian", "Yemen": "Yemeni", "Afghanistan": "Afghan", "Bangladesh": "Bangladeshi", "Sri Lanka": "Sri Lankan"}

    def origin_of(it):
        v = lab1(it, "origin") or lab1(it, "country")
        if v not in countries():
            return None
        # لازم الوصف نفسه يأكد البلد (ويكيداتا أحياناً بتحط بلد غلط أو مختلف عليه)
        en = re.sub(r"^(People's Republic of |Republic of |Kingdom of |State of |the )", "", (countries()[v].get("en") or "").strip())
        dem = DEMONYM.get(en, "")
        pat = "|".join(x for x in [re.escape(en)] + ([dem] if dem else []) if x)
        e, a = it.get("end") if isinstance(it.get("end"), str) else "", it.get("ard") or ""
        if (pat and re.search(pat, e)) or v in a or (v[:-1] and len(v) > 4 and v[:-1] in a):
            return v
        return None
    origin_types = lambda w: [(f"من وين أصل {w}؟", origin_of, 1, lambda items: cat_countries(items, "origin") or cat_countries(items), near_in)]
    b.image_cat("food", "أكلات من العالم", "🍜", wd("dishes"), T("food"), "شو هالأكلة؟", origin_types("هالأكلة"))
    b.image_cat("desserts", "حلويات من العالم", "🍰", only(wd("desserts"), r"(dessert|sweet|cake|pastry|confection|cookie|biscuit|candy|ice cream|pudding|chocolate)", r"(حلو|حلوى|حلويات|كعك|كعكة|معجنات)"), T("desserts"), "شو هالحلو؟", origin_types("هالحلو"))
    b.image_cat("drinks", "مشروبات", "🥤", wd("drinks"), T("drinks"), "شو هالمشروب؟", origin_types("هالمشروب"))
    b.image_cat("instruments", "آلات موسيقية بالصور", "🎻", only(wd("instruments"), r"(musical instrument|instrument)", r"(آلة موسيقية|آلة)"), T("instruments"), "شو هالآلة؟", (), top=120, max_words=3)
    TL_NO = {"مطياف", "ساعة", "مدرس", "فارزة", "مقياس الزلازل"}
    tl = [it for it in only(wd("tools"), r"\b(tool|implement|utensil|instrument)\b", r"(أداة|عدة|أدوات)") if it["ar"] not in TL_NO]
    b.image_cat("tools", "أدوات وعدّة", "🔧", tl, T("tools"), "شو هالأداة؟", (), max_words=3, top=110)
    SG_NO = {"الكرة", "كرة القدم", "بوابة", "قميص بلا أكمام", "بنطال رياضة", "ميجار", "ثقالة", "لوح الثلج", "كرة"}
    sg = [it for it in only(wd("sportsgear"), r"(sport|athlet|ball|racket|equipment used)", r"(رياض|كرة|مضرب)") if it["ar"] not in SG_NO]
    b.image_cat("sportsgear", "أدوات رياضية", "🏸", sg, T("sportsgear"), "شو هاد؟", (), max_words=3)
    maker = [("مين الشركة المصنّعة؟", lambda it: lab1(it, "maker"), 1, lambda items: sorted({lab1(x, "maker") for x in items if lab1(x, "maker")}), None)]
    b.image_cat("planes", "طيارات ومركبات طايرة", "✈️", wd("aircraft") + wd("vehicles"), T("planes"), "شو هالطيارة؟", maker, group=lambda it: lab1(it, "maker"))
    b.image_cat("cars", "سيارات", "🚗", wd("car_models"), T("cars"), "شو هالسيارة؟", maker, group=lambda it: lab1(it, "maker"))
    inv = ()
    INV = (r"(device|machine|instrument|apparatus|tool|vehicle|engine|weapon|invention|medication|drug|vaccine|toy|appliance|camera|telephone|"
           r"computer|aircraft|vessel|lamp|clock|printing|radio|television|telescope|microscope|motor|battery|robot|rocket|gun)",
           r"(جهاز|آلة|أداة|اختراع|محرك|مركبة|دواء|لقاح|سلاح|لعبة|مصباح|ساعة|مطبعة|راديو|تلفاز|تلسكوب|مجهر|بطارية|صاروخ)")
    # اختراعات منتقاة باليد (بيانات ويكيداتا فيها كواكب واكتشافات ومفاهيم)، بأسماء دارجة
    INV_OK = {"حاسوب": "كمبيوتر", "هاتف": "تلفون", "سيارة بمحرك": "سيارة", "تلفزة": "تلفزيون", "دراجة هوائية ثنائية": "بسكليت (دراجة)",
              "ورق": "ورق", "هاتف محمول": "موبايل", "بيانو": "بيانو", "قلم رصاص": "قلم رصاص", "مقراب": "تلسكوب", "فأرة حاسوب": "ماوس",
              "مجهر": "مجهر (ميكروسكوب)", "محرك احتراق داخلي": "محرك احتراق داخلي", "مقياس الحرارة": "ميزان حرارة", "مكعب روبيك": "مكعب روبيك",
              "ساكسفون": "ساكسفون", "قرص مضغوط": "سي دي", "رادار": "رادار", "آلة الخياطة": "ماكينة خياطة", "آلة كاتبة": "آلة كاتبة",
              "مصباح متوهج": "لمبة", "مكنسة كهربائية": "مكنسة كهربا", "إشارة ضوئية": "إشارة مرور", "مقياس ضغط جوي": "بارومتر",
              "صراف آلي": "صراف آلي", "مكبر صوت": "سماعة (مكبر صوت)", "باربي": "دمية باربي", "فرن الأمواج الصغرية": "مايكرويف",
              "قيثارة كهربائية": "غيتار كهربائي", "ثنائي باعث للضوء": "لمبة ليد (LED)", "قلم حبر جاف": "قلم ناشف", "رمز استجابة سريعة": "رمز QR",
              "عدسة مكبرة": "عدسة مكبّرة", "قرص بلوراي": "قرص بلوراي", "سلم متحرك": "درج كهربائي",
              "آلة الطباعة": "مطبعة", "البيكار": "فرجار (بيكار)", "سماعة طبية": "سماعة طبيب", "محرك ديزل": "محرك ديزل", "مبراة": "برّاية",
              "مانع الصواعق": "مانعة صواعق", "ليغو": "مكعبات ليغو", "غسالة صحون": "جلاية صحون", "حوامة": "هوفركرافت (حوامة)",
              "سماعتا رأس": "سماعات راس", "دمية روسية": "دمية ماتريوشكا", "مشكال": "كاليدوسكوب", "أحجية الصور المقطوعة": "بازل",
              "قرص فونوغراف": "أسطوانة فونوغراف", "عداد غايغر": "عداد غايغر", "شوكة رنانة": "شوكة رنانة", "سلك شائك": "سلك شائك",
              "شريط سمعي": "شريط كاسيت", "بطاقة مثقبة": "بطاقة مثقّبة", "سودوكو": "سودوكو", "ترميز مورس": "شيفرة مورس", "دش": "دش (رشاش حمام)",
              "مدخرة": "بطارية قابلة للشحن", "سونار": "سونار", "كاميرا الساكن": "كاميرا"}
    invs = []
    for it in dedupe(wd("inventions")):
        if it["ar"] in INV_OK and it.get("img"):
            invs.append(dict(it, ar=INV_OK[it["ar"]]))
    invs = dedupe(invs)
    b.image_cat("inventions", "اختراعات غيّرت العالم", "💡", invs, T("inventions"), "شو هالاختراع؟", inv, max_words=4)
    cur = [("عملة أي دولة هاي؟", lambda it: lab1(it, "country") if lab1(it, "country") in countries() else None, 0, lambda items: sorted(countries().keys()), near_in)]
    b.image_cat("currency", "عملات العالم", "💵", wd("currencies"), T("currency"), "شو اسم هالعملة؟", cur, top=110)
    paint = [("مين رسم هاللوحة؟", lambda it: lab1(it, "creator"), 0, lambda items: sorted({lab1(x, "creator") for x in items if lab1(x, "creator")}), None),
             ("وين معروضة هاللوحة؟", lambda it: lab1(it, "collection"), 2,
              lambda items: sorted({lab1(x, "collection") for x in items if lab1(x, "collection")}), None)]
    b.image_cat("paintings", "لوحات فنية مشهورة", "🎨", wd("paintings"), T("paintings"), "شو اسم هاللوحة؟", paint, group=lambda it: lab1(it, "creator"))
    b.image_cat("costumes", "أزياء تقليدية", "👘", only(wd("costumes"), r"(traditional|national costume|folk)", r"(تقليدي|شعبي)"), T("costumes"), "شو اسم هاللبس؟", origin_types("هاللبس"))
    b.image_cat("dances", "رقصات من العالم", "💃", [it for it in wd("dances") if it["ar"] not in ("رقصة ألمانية", "كوتليون", "فاراندول", "رقص حديث", "رقص شعبي")], T("dances"), "شو اسم هالرقصة؟", origin_types("هالرقصة"))

    # ---- شعارات ----
    ctry = [("من وين هالشركة؟", lambda it: lab1(it, "country") if lab1(it, "country") in countries() else None, 1, cat_countries, near_in)]
    b.image_cat("carlogos", "شعارات السيارات", "🚘", wd("car_brands"), T("carlogos"), "شعار أي شركة سيارات هاد؟", ctry)
    b.image_cat("airlines", "شركات الطيران", "🛫", wd("airlines"), T("airlines"), "شعار أي شركة طيران هاد؟", ctry, group=lambda it: lab1(it, "country"))
    return b
