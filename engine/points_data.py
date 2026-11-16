#!/usr/bin/env python3
"""
أسئلة كتابية من بيانات Wikidata وplayers.json: عواصم، مين صار أول، قدّر الرقم، اكتشف الكذبة، مين أنا،
أفلام، ألعاب فيديو، تكنولوجيا، علوم، تاريخ، رياضات، الأردن، الدوريات، خمّن اللاعب، أعلام وخرائط وشعارات أندية.
القاعدة: الأشهر أول، والخيارات من نفس الصنف، وأي سؤال جوابه مش واحد بينشال.
"""
from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from points_gen import wd, lab1, labs, year, num, img_url, norm, with_levels, dedupe, score, countries, continent_of, ARAB_DESC_AR, clean

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
R = random.Random(9090)


def get(cats, Cat, cid, name, icon):
    if cid not in cats:
        cats[cid] = Cat(cid, name, icon)
    return cats[cid]


def wrong3(ans, pool, near=None, lv=2):
    na = norm(ans)
    out, seen = [], {na}
    pools = ([near] if near and lv >= 3 else []) + [pool]
    for p in pools:
        for x in R.sample(p, len(p)):
            if not x or norm(x) in seen:
                continue
            seen.add(norm(x))
            out.append(x)
            if len(out) == 3:
                return out
    return None


def fmt_num(n):
    n = int(round(n))
    if n >= 1_000_000:
        v = n / 1_000_000
        return (f"{v:.1f}".rstrip("0").rstrip(".") if v < 100 else f"{v:.0f}") + " مليون"
    if n >= 10_000:
        return f"{round(n / 1000):,} ألف".replace(",", "٬")
    return f"{n:,}".replace(",", "٬")


def num_opts(v, rel=(0.55, 0.75, 1.35, 1.8), rnd=1):
    """خيارات رقمية: الصح مقرّب، والغلط بفروقات واضحة (مش ±1)."""
    def r(x):
        if x >= 1_000_000:
            return round(x, -5)
        if x >= 10_000:
            return round(x, -3)
        if x >= 1000:
            return round(x, -2)
        if x >= 100:
            return round(x, -1)
        return round(x)
    right = r(v)
    cands = []
    for f in R.sample(list(rel), len(rel)):
        w = r(v * f)
        if w != right and w > 0 and w not in cands:
            cands.append(w)
    return right, cands[:3] if len(cands) >= 3 else None


# ---------- عواصم ودول ----------
CONT = ["آسيا", "أفريقيا", "أوروبا", "أمريكا الشمالية", "أمريكا الجنوبية", "أوقيانوسيا"]
CONT_FIX = {"إفريقيا": "أفريقيا", "قارة أفريقيا": "أفريقيا", "أستراليا": "أوقيانوسيا", "أوقيانيا": "أوقيانوسيا"}


def ccont(it):
    v = lab1(it, "continent")
    v = CONT_FIX.get(v, v) if v else None
    return v if v in CONT else None


def capitals(cats, Cat):
    c = get(cats, Cat, "capitals", "عواصم ودول", "🌍")
    C = with_levels([it for it in dedupe(wd("countries")) if lab1(it, "capital")])
    caps = {it["ar"]: lab1(it, "capital") for it in C}
    by_cont = defaultdict(list)
    for it in C:
        if ccont(it):
            by_cont[ccont(it)].append(it)
    allcaps = [v for v in caps.values() if v]
    for it in C:
        lv, n, cap = it["lv"], it["ar"], caps[it["ar"]]
        same = [x["ar"] for x in by_cont.get(ccont(it), []) if x is not it]
        w = wrong3(cap, allcaps, [caps[x] for x in same if caps.get(x)], lv)
        if w:
            c.add(lv, f"شو عاصمة {n}؟", [cap] + w)
        w = wrong3(n, [x["ar"] for x in C], same, lv)
        if w:
            c.add(min(4, lv + 1), f"{cap} عاصمة أي دولة؟", [n] + w)
        if ccont(it) and len(labs(it, "continent")) == 1:
            c.add(max(1, lv - 1), f"بأي قارة بتقع {n}؟", [ccont(it)] + R.sample([x for x in CONT if x != ccont(it)], 3))
        cur = lab1(it, "currency")
        if cur:
            pool = [lab1(x, "currency") for x in C if lab1(x, "currency") and lab1(x, "currency") != cur]
            near = [lab1(x, "currency") for x in by_cont.get(ccont(it), []) if lab1(x, "currency") and lab1(x, "currency") != cur]
            w = wrong3(cur, pool, near, lv)
            if w and not any(norm(cur.split()[0]) == norm(x.split()[0]) for x in w):
                c.add(min(4, lv + 1), f"شو عملة {n}؟", [cur] + w)
    big = [it for it in C if num(it, "area") and num(it, "pop")]
    for key, q in (("area", "أي دولة من هدول مساحتها أكبر؟"), ("pop", "أي دولة من هدول عدد سكانها أكثر؟")):
        for _ in range(140):
            four = R.sample(big[:150], 4)
            vals = sorted(four, key=lambda x: num(x, key), reverse=True)
            if num(vals[0], key) < num(vals[1], key) * 1.25:
                continue
            lv = 2 if num(vals[0], key) > num(vals[1], key) * 3 else 3 if num(vals[0], key) > num(vals[1], key) * 1.6 else 4
            c.add(lv, q, [vals[0]["ar"]] + [x["ar"] for x in vals[1:]])
    for it in C[:90]:
        dc = [d for d in (it.get("dialcode") or []) if re.fullmatch(r"\+\d{1,3}", d)]
        if len(dc) == 1 and (ARAB_DESC_AR.search(it.get("ard") or "") or it["ar"] in ("الأردن", "السعودية", "مصر", "الإمارات العربية المتحدة", "قطر", "الكويت")):
            others = [d for x in C for d in (x.get("dialcode") or []) if re.fullmatch(r"\+\d{1,3}", d) and d != dc[0]]
            c.add(3, f"شو رمز الاتصال الدولي لـ{it['ar']}؟", [dc[0]] + R.sample(sorted(set(others)), 3))


def flags_maps(cats, Cat):
    """أعلام ووين الدولة: صورة العلم/الخريطة ← الدولة، العاصمة، القارة."""
    C = with_levels([it for it in dedupe(wd("countries"))])
    names = [x["ar"] for x in C]
    caps = {it["ar"]: lab1(it, "capital") for it in C}
    by_cont = defaultdict(list)
    for it in C:
        by_cont[ccont(it)].append(it["ar"])
    f = get(cats, Cat, "flags", "أعلام الدول", "🏳️")
    g = get(cats, Cat, "globe", "وين هالدولة؟", "🗺️")
    for it in C:
        lv, n = it["lv"], it["ar"]
        near = [x for x in by_cont.get(ccont(it), []) if x != n]
        if it.get("img"):
            url = img_url(it["img"])
            w = wrong3(n, names, near, lv)
            if w:
                f.add(lv, "علم أي دولة هاد؟", [n] + w, url)
            if caps.get(n):
                w = wrong3(caps[n], [v for v in caps.values() if v], [caps[x] for x in near if caps.get(x)], lv)
                if w:
                    f.add(min(4, lv + 1), "شو عاصمة الدولة صاحبة هالعلم؟", [caps[n]] + w, url)
            if ccont(it) and len(labs(it, "continent")) == 1:
                f.add(max(1, lv - 1), "هالعلم لدولة بأي قارة؟", [ccont(it)] + R.sample([x for x in CONT if x != ccont(it)], 3), url)
        mp = it.get("map") or it.get("locator")
        if mp:
            url = img_url(mp)
            w = wrong3(n, names, near, max(lv, 2))
            if w:
                g.add(lv, "وين هالدولة على الخريطة؟", [n] + w, url)
            if caps.get(n):
                w = wrong3(caps[n], [v for v in caps.values() if v], [caps[x] for x in near if caps.get(x)], lv)
                if w:
                    g.add(min(4, lv + 1), "شو عاصمة الدولة اللي عليها اللون؟", [caps[n]] + w, url)
            if ccont(it) and len(labs(it, "continent")) == 1:
                g.add(max(1, lv - 1), "الدولة اللي عليها اللون بأي قارة؟", [ccont(it)] + R.sample([x for x in CONT if x != ccont(it)], 3), url)


# ---------- مين صار أول؟ ----------
def first(cats, Cat):
    c = get(cats, Cat, "first", "مين صار أول؟", "⏳")
    domains = [
        ("films", "published", "أي فيلم من هدول نزل أول؟", 70), ("videogames", "published", "أي لعبة فيديو من هدول نزلت أول؟", 45),
        ("tech_companies", "inception", "أي شركة من هدول تأسست أول؟", 40), ("websites_apps", "inception", "أي موقع أو تطبيق من هدول انطلق أول؟", 40),
        ("companies", "inception", "أي شركة من هدول تأسست أول؟", 70), ("landmarks", "inception", "أي معلم من هدول انبنى أول؟", 60),
        ("towers", "inception", "أي برج من هدول انبنى أول؟", 30), ("bridges", "inception", "أي جسر من هدول انبنى أول؟", 30),
        ("prog_langs", "inception", "أي لغة برمجة من هدول ظهرت أول؟", 40), ("tv_series", "published", "أي مسلسل من هدول نزل أول؟", 50),
        ("clubs", "inception", "أي نادي من هدول تأسس أول؟", 60), ("countries", "inception", "أي دولة من هدول استقلت أو تأسست بشكلها الحالي أول؟", 120),
    ]
    rnd = random.Random(44)
    domains = [d for d in domains if d[0] != "countries"]
    bump = {"clubs": 90, "towers": 45, "bridges": 40, "companies": 80, "websites_apps": 60}
    from points_gen import only

    def make(items, prop, q):
        items = with_levels(items)
        items.sort(key=lambda x: year(x, prop))
        # كل عنصر بيكون الجواب مرتين بالكثير: بفروقات مختلفة (أسهل/أصعب)
        for it in items:
            y0 = year(it, prop)
            later = [x for x in items if year(x, prop) >= y0 + 2]
            if len(later) < 3:
                continue
            tiers = [(25, 1), (12, 2)] if it["lv"] <= 2 else rnd.sample([(25, 1), (12, 2), (5, 3), (2, 4)], 2)
            for g, glv in tiers:
                for _ in range(60):
                    pool_ = [x for x in later if x["lv"] <= 2] if glv <= 2 and sum(1 for x in later if x["lv"] <= 2) >= 3 else later
                    three = rnd.sample(pool_, 3)
                    four = sorted([it] + three, key=lambda x: year(x, prop))
                    ys = [year(x, prop) for x in four]
                    gap = min(b_ - a_ for a_, b_ in zip(ys, ys[1:]))
                    if gap < g or (g < 25 and gap >= g * 2.5) or len({x["ar"] for x in four}) < 4:
                        continue
                    fame = round(sum(x["lv"] for x in four) / 4)
                    lv = min(4, max(glv, fame))
                    c.add(lv, q, [x["ar"] for x in four])
                    break

    for key, prop, q, min_sl in domains:
        min_sl = bump.get(key, min_sl)
        items = [it for it in dedupe(wd(key)) if it["sl"] >= min_sl and year(it, prop) and 1000 < year(it, prop) <= 2026]
        if len(items) >= 8:
            make(items, prop, q)
    people = [
        ("actors", r"\bactor|actress", "مين من هدول الممثلين انولد أول؟", 70),
        ("scientists", r"physicist|chemist|mathematician|biologist|astronomer|scientist|inventor|naturalist|engineer", "مين من هدول العلماء انولد أول؟", 70),
        ("singers", r"singer", "مين من هدول المطربين انولد أول؟", 60),
        ("historic_art", r"painter|sculptor|composer|writer|poet|novelist|playwright|artist", "مين من هدول الفنانين والأدباء انولد أول؟", 70),
        ("athletes", r".", "مين من هدول الرياضيين انولد أول؟", 50),
        ("coaches", r"football|soccer", "مين من هدول نجوم الكرة انولد أول؟", 45),
    ]
    for key, en, q, min_sl in people:
        items = [it for it in only(dedupe(wd(key)), en=en) if it["sl"] >= min_sl and it.get("arw") and year(it, "born") and 1000 < year(it, "born") <= 2010
                 and len(it["ar"].split()) <= 4]
        if len(items) >= 8:
            make(items[:220], "born", q)


# ---------- قدّر الرقم ----------
def estimate(cats, Cat):
    c = get(cats, Cat, "estimate", "قدّر الرقم", "🔢")
    jobs = [
        ("mountains", "elev", "قديش ارتفاع {n} تقريباً (بالمتر)؟", 60, 160),
        ("countries", "pop", "قديش عدد سكان {n} تقريباً؟", 0, 150),
        ("countries", "area", "قديش مساحة {n} تقريباً (كم²)؟", 0, 120),
        ("cities", "pop", "قديش عدد سكان مدينة {n} تقريباً؟", 120, 140),
        ("stadiums", "capacity", "كم متفرج بيتّسع {n} تقريباً؟", 60, 90),
        ("lakes_rivers", "length", "قديش طول {n} تقريباً (كم)؟", 80, 60),
        ("towers", "height", "قديش ارتفاع {n} تقريباً (بالمتر)؟", 40, 80),
        ("bridges", "length", "قديش طول {n} تقريباً (بالمتر)؟", 40, 50),
    ]
    for key, prop, q, min_sl, cap in jobs:
        items = with_levels([it for it in dedupe(wd(key)) if it["sl"] >= min_sl and it.get("arw") and num(it, prop) and num(it, prop) > 0][:cap])
        for it in items:
            v = num(it, prop)
            if prop == "length" and key == "lakes_rivers":
                v = v  # بالكيلومتر بويكيداتا غالباً
            right, wr = num_opts(v)
            if not wr:
                continue
            fm = fmt_num if prop in ("pop", "area", "capacity") else (lambda x: f"{int(x):,}".replace(",", "٬"))
            c.add(min(4, it["lv"] + 1), q.format(n=it["ar"]), [fm(right)] + [fm(x) for x in wr])


# ---------- اكتشف الكذبة ----------
def lies(cats, Cat):
    c = get(cats, Cat, "lies", "اكتشف الكذبة", "🤥")
    C = [it for it in dedupe(wd("countries")) if lab1(it, "capital")][:150]
    caps = {it["ar"]: lab1(it, "capital") for it in C}
    by_cont = defaultdict(list)
    for it in C:
        by_cont[ccont(it)].append(it["ar"])
    facts = []   # (صح، غلط محتمل)
    for it in C:
        n = it["ar"]
        near = [x for x in by_cont.get(ccont(it), []) if x != n and caps.get(x)]
        if near:
            fake = R.choice(near)
            facts.append((f"عاصمة {n} هي {caps[n]}", f"عاصمة {n} هي {caps[fake]}", "cap"))
        if ccont(it) and len(labs(it, "continent")) == 1:
            facts.append((f"{n} بتقع بقارة {ccont(it)}", f"{n} بتقع بقارة {R.choice([x for x in CONT if x != ccont(it)])}", "cont"))
    F = [it for it in dedupe(wd("films")) if lab1(it, "director") and year(it, "published")][:150]
    dirs = [lab1(x, "director") for x in F]
    for it in F:
        d = lab1(it, "director")
        facts.append((f"فيلم «{it['ar']}» من إخراج {d}", f"فيلم «{it['ar']}» من إخراج {R.choice([x for x in dirs if x != d])}", "film"))
        y = year(it, "published")
        facts.append((f"فيلم «{it['ar']}» نزل سنة {y}", f"فيلم «{it['ar']}» نزل سنة {y + R.choice([-12, -8, 7, 11])}", "film"))
    E = [it for it in dedupe(wd("elements")) if (it.get("symbol") or [None])[0]][:80]
    syms = [it["symbol"][0] for it in E]
    for it in E:
        s = it["symbol"][0]
        facts.append((f"رمز {it['ar']} الكيميائي {s}", f"رمز {it['ar']} الكيميائي {R.choice([x for x in syms if x != s and x[0] == s[0]] or [x for x in syms if x != s])}", "el"))
    rnd = random.Random(12)
    for i in range(700):
        trues = rnd.sample(facts, 3)
        lie = rnd.choice(facts)
        if lie in trues or any(t[0].split(" ")[1] == lie[1].split(" ")[1] for t in trues):
            continue
        st = [t[0] for t in trues]
        if len(" ".join(st + [lie[1]])) > 220:
            continue
        lv = 2 if lie[2] in ("cap", "cont") else 3 if lie[2] == "el" else 4
        c.add(lv, "وين الكذبة؟", [lie[1]] + st)
        if len(c.qs) > 700:
            break


# ---------- مين أنا؟ ----------
def whoami(cats, Cat):
    c = get(cats, Cat, "whoami", "مين أنا؟", "🕵️")
    C = with_levels([it for it in dedupe(wd("countries")) if lab1(it, "currency") and ccont(it)][:160])
    by_cont = defaultdict(list)
    for it in C:
        by_cont[ccont(it)].append(it["ar"])
    for it in C:
        cur, cont, pop = lab1(it, "currency"), ccont(it), num(it, "pop")
        if not pop or norm(it["ar"][:3]) in norm(cur):
            continue
        near = [x for x in by_cont[cont] if x != it["ar"]]
        if len(near) < 3:
            continue
        c.add(it["lv"], f"أنا دولة بقارة {cont}، عملتي «{cur}»، وعدد سكاني حوالي {fmt_num(pop)}. مين أنا؟", [it["ar"]] + R.sample(near, 3))
    people = [("scientists", "عالم"), ("historic_pol", "شخصية تاريخية"), ("historic_art", "شخصية تاريخية"), ("actors", "ممثل"), ("singers", "مطرب"),
              ("athletes", "بطل رياضي"), ("historic_arab", "شخصية عربية")]
    for key, _ in people:
        P = with_levels([it for it in dedupe(wd(key)) if it.get("ard") and year(it, "born") and 10 < len(it["ard"]) < 90][:160])
        for it in P:
            d = re.sub(r"\s+", " ", it["ard"]).strip(" .،")
            toks = [t for t in it["ar"].split() if len(t) > 2]
            if any(t in d for t in toks):
                continue
            sg = (it.get("gender") or [None])[0]
            pool = [x["ar"] for x in P if x is not it and (x.get("gender") or [None])[0] == sg and abs((year(x, "born") or 0) - year(it, "born")) < 150]
            if len(pool) < 3:
                continue
            verb = "انولدت"
            c.add(min(4, it["lv"] + 1), f"أنا {d}، {verb} سنة {year(it, 'born')}. مين أنا؟", [it["ar"]] + R.sample(pool, 3))
    L = with_levels([it for it in dedupe(wd("landmarks") + wd("whs")) if lab1(it, "city") and lab1(it, "country") and it.get("arw") and it["sl"] >= 70][:90])
    for it in L:
        city, ctry = lab1(it, "city"), lab1(it, "country")
        if norm(city) in norm(it["ar"]) or norm(it["ar"]) in norm(city) or re.search(r"(قضاء|محافظة|مقاطعة|ولاية|عمالة|كانتون|بلدية|مترو|إقليم|منطقة)", city):
            continue
        near = [x["ar"] for x in L if x is not it and lab1(x, "country") == ctry] or [x["ar"] for x in L if x is not it]
        pool = near if len(near) >= 3 else [x["ar"] for x in L if x is not it]
        c.add(min(4, it["lv"] + 1), f"أنا معلم مشهور بمدينة {city} بـ{ctry}. مين أنا؟", [it["ar"]] + R.sample(pool, 3))


# ---------- أفلام ومسلسلات ----------
def movies(cats, Cat):
    c = get(cats, Cat, "movies", "أفلام ومسلسلات", "🎬")
    F = with_levels(dedupe(wd("films")) + [x for x in dedupe(wd("arab_films")) if ARAB_DESC_AR.search(x.get("ard") or "")])
    dirs = [lab1(x, "director") for x in F if lab1(x, "director")]
    for it in F:
        kind = "مسلسل" if re.search(r"مسلسل", it.get("ard") or "") else "فيلم"
        d = lab1(it, "director")
        if d and dirs.count(d) >= 1:
            w = wrong3(d, sorted(set(dirs)), None, it["lv"])
            if w:
                c.add(min(4, it["lv"] + 1), f"مين مخرج {kind} «{it['ar']}»؟", [d] + w)
        y = year(it, "published")
        if y and 1930 < y <= 2026:
            c.add(min(4, it["lv"] + 1), f"بأي سنة نزل {kind} «{it['ar']}»؟", [str(y)] + [str(y + k) for k in R.sample([-9, -5, -3, 3, 6, 10], 3)])
    T = with_levels(dedupe(wd("tv_series")))
    origins = sorted({lab1(x, "origin") for x in T if lab1(x, "origin")})
    for it in T:
        o = lab1(it, "origin")
        if o and len(origins) >= 4:
            c.add(it["lv"], f"مسلسل «{it['ar']}» من أي دولة؟", [o] + R.sample([x for x in origins if x != o], 3))


# ---------- ألعاب فيديو ----------
def videogames(cats, Cat):
    c = get(cats, Cat, "videogames", "ألعاب فيديو", "🎮")
    G = with_levels(dedupe(wd("videogames")))
    devs = sorted({lab1(x, "developer") for x in G if lab1(x, "developer")})
    sers = sorted({lab1(x, "series") for x in G if lab1(x, "series")})
    for it in G:
        d = lab1(it, "developer")
        if d and len(devs) > 4:
            c.add(min(4, it["lv"] + 1), f"مين طوّر لعبة «{it['ar']}»؟", [d] + R.sample([x for x in devs if x != d], 3))
        y = year(it, "published")
        if y and 1970 < y <= 2026:
            c.add(min(4, it["lv"] + 1), f"بأي سنة نزلت لعبة «{it['ar']}»؟", [str(y)] + [str(y + k) for k in R.sample([-6, -4, -2, 2, 3, 5], 3)])
        s = lab1(it, "series")
        if s and norm(s) not in norm(it["ar"]) and len(sers) > 4:
            c.add(it["lv"], f"لعبة «{it['ar']}» من أي سلسلة؟", [s] + R.sample([x for x in sers if x != s], 3))


# ---------- تكنولوجيا ----------
def tech(cats, Cat):
    c = get(cats, Cat, "tech", "تكنولوجيا وتطبيقات", "💻")
    for key, noun in (("tech_companies", "شركة"), ("websites_apps", "منصة"), ("companies", "شركة")):
        X = with_levels([it for it in dedupe(wd(key)) if it["sl"] >= 50])
        founders = sorted({f for x in X for f in labs(x, "founder")})
        for it in X:
            fs = labs(it, "founder")
            if fs:
                pool = [f for f in founders if f not in fs]
                if len(pool) >= 3:
                    c.add(min(4, it["lv"] + 1), f"مين من هدول من مؤسسين {noun} «{it['ar']}»؟", [fs[0]] + R.sample(pool, 3))
            y = year(it, "inception")
            if y and 1800 < y <= 2026:
                c.add(min(4, it["lv"] + 1), f"بأي سنة تأسست {noun} «{it['ar']}»؟", [str(y)] + [str(y + k) for k in R.sample([-8, -4, -2, 2, 4, 7], 3)])
            ct = lab1(it, "country")
            if ct and ct in countries():
                ctries = sorted({lab1(x, "country") for x in X if lab1(x, "country") in countries()} - {ct})
                if len(ctries) >= 3:
                    c.add(it["lv"], f"{noun} «{it['ar']}» من أي دولة؟", [ct] + R.sample(ctries, 3))
    L = with_levels(dedupe(wd("prog_langs")))
    for it in L:
        y = year(it, "inception")
        if y:
            c.add(4, f"بأي سنة ظهرت لغة البرمجة «{it['ar']}»؟", [str(y)] + [str(y + k) for k in R.sample([-7, -4, -2, 3, 5, 9], 3)])


# ---------- علوم ----------
def science(cats, Cat):
    c = get(cats, Cat, "science", "علوم", "🔬")
    E = with_levels([it for it in dedupe(wd("elements")) if (it.get("symbol") or [None])[0] and num(it, "atomic")])
    syms = [x["symbol"][0] for x in E]
    names = [x["ar"] for x in E]
    for it in E:
        s, z, n = it["symbol"][0], int(num(it, "atomic")), it["ar"]
        lv = it["lv"]
        same_first = [x for x in syms if x != s and x[0] == s[0]]
        c.add(lv, f"شو الرمز الكيميائي لعنصر {n}؟", [s] + (R.sample(same_first, 3) if len(same_first) >= 3 else R.sample([x for x in syms if x != s], 3)))
        c.add(min(4, lv + 1), f"أي عنصر رمزه الكيميائي «{s}»؟", [n] + R.sample([x for x in names if x != n], 3))
        if z <= 30 or lv <= 2:
            c.add(4 if z > 10 else 3, f"شو العدد الذري لعنصر {n}؟", [str(z)] + [str(z + k) for k in R.sample([-3, -2, -1, 1, 2, 4], 3) if z + k > 0][:3])
    for it in E:
        z = int(num(it, "atomic"))
        if z <= 20:
            c.add(3, f"أي عنصر عدده الذري {z}؟", [it["ar"]] + R.sample([x["ar"] for x in E if x is not it and abs(int(num(x, 'atomic')) - z) <= 6], 3))


# ---------- تاريخ ----------
def history(cats, Cat):
    c = get(cats, Cat, "history", "تاريخ", "📜")
    P = with_levels([it for it in dedupe(wd("historic_pol") + wd("historic_art") + wd("historic_arab") + wd("islamic_people")) if year(it, "died") and year(it, "born")])
    for it in P:
        b_, d_ = year(it, "born"), year(it, "died")
        cen = (d_ - 1) // 100 + 1 if d_ > 0 else None
        if cen and 1 <= cen <= 21:
            opts = sorted({cen, max(1, cen - 1), cen + 1 if cen < 21 else cen - 2, max(1, cen - 2) if cen > 2 else cen + 2} - {0})
            opts = [o for o in opts if o != cen][:3]
            if len(opts) == 3:
                c.add(min(4, it["lv"] + 1), f"بأي قرن توفي {it['ar']}؟", [f"القرن {cen}"] + [f"القرن {o}" for o in opts])
    O = with_levels(dedupe(wd("olympics")))
    for it in O:
        ct, y = lab1(it, "city"), year(it, "point_time") or year(it, "start")
        if ct and y:
            pool = sorted({lab1(x, "city") for x in O if lab1(x, "city")} - {ct})
            if len(pool) >= 3:
                cats_s = get(cats, Cat, "sports", "رياضات ثانية", "🏅")
                cats_s.add(2 if y >= 1990 else 3, f"وين انقامت الألعاب الأولمبية سنة {y}؟", [ct] + R.sample(pool, 3))


# ---------- الأردن ----------
def jordan(cats, Cat):
    c = get(cats, Cat, "jocities", "مدن ومحافظات أردنية", "🏘️")
    J = with_levels([it for it in dedupe(wd("jordan_places"))])
    govs = sorted({lab1(x, "city") for x in J if lab1(x, "city") and lab1(x, "city").startswith("محافظة")})
    for it in J:
        g = lab1(it, "city")
        if g and g.startswith("محافظة") and norm(g.replace("محافظة", "")) not in norm(it["ar"]) and len(govs) >= 4:
            c.add(it["lv"], f"«{it['ar']}» بأي محافظة؟", [g] + R.sample([x for x in govs if x != g], 3))
    G = dedupe(wd("jordan_gov"))
    for it in G:
        cap = lab1(it, "capital")
        if cap:
            c.add(2, f"شو مركز {it['ar']}؟", [cap] + R.sample([lab1(x, "capital") for x in G if lab1(x, "capital") and x is not it], 3))


# ---------- الدوريات: مين فاز بالموسم؟ ----------
LEAGUE_CAT = {"دوري أبطال أوروبا": "ucl", "الدوري الإنجليزي الممتاز": "epl", "الدوري الإسباني": "europe", "الدوري الإيطالي": "europe",
              "الدوري الألماني": "europe", "الدوري الفرنسي": "europe", "الدوري الهولندي": "europe", "الدوري البرتغالي": "europe"}


def leagues(cats, Cat):
    S = dedupe(wd("league_seasons"))
    by = defaultdict(list)
    for it in S:
        lg = lab1(it, "season_of")
        w = lab1(it, "winner")
        y = year(it, "start")
        if lg and w and y and y >= 1955:
            by[lg].append((y, w, it))
    names = {"ucl": ("دوري أبطال أوروبا", "🏆"), "epl": ("الدوري الإنجليزي", "🦁"), "europe": ("الدوريات الأوروبية", "🇪🇺"), "arabfoot": ("كرة عربية وخليجية", "🌙")}
    for lg, rows in by.items():
        key = None
        for k, v in LEAGUE_CAT.items():
            if k in lg or lg in k:
                key = v
        if not key:
            key = "arabfoot" if re.search(r"(السعودي|المصري|المغربي|التونسي|الجزائري|القطري|الإماراتي|الأردني|الكويتي|العراقي|العربي|الخليج)", lg) else None
        if not key:
            continue
        c = get(cats, Cat, key, *names[key])
        winners = sorted({w for _, w, _ in rows})
        cnt = Counter(w for _, w, _ in rows)
        for y, w, it in rows:
            if len(winners) < 4:
                continue
            lv = 1 if y >= 2015 and cnt[w] >= 3 else 2 if y >= 2005 else 3 if y >= 1990 else 4
            season = f"{y}/{str(y + 1)[2:]}"
            c.add(lv, f"مين فاز بـ{lg} موسم {season}؟", [w] + R.sample([x for x in winners if x != w], 3))
        for w, n in cnt.most_common(12):
            if n >= 2:
                opts = sorted({n - 2, n - 1, n + 1, n + 2} - {n, 0})
                c.add(3, f"كم مرة فاز {w} بـ{lg} (من 1955 لحد آخر موسم مسجّل)؟", [str(n)] + [str(o) for o in R.sample(opts, 3)])


# ---------- خمّن اللاعب + كورة من players.json ----------
def players_text(cats, Cat):
    PL = json.loads((ROOT / "docs" / "games" / "players.json").read_text(encoding="utf-8"))["players"]
    P = [p for p in PL if p.get("a") and not re.search(r"[A-Za-z]", p["a"]) and p.get("nat") and p.get("c") and p.get("lv")]
    gp = get(cats, Cat, "guessplayer", "خمّن اللاعب", "🕵️")
    fb = get(cats, Cat, "football", "كرة قدم", "⚽")
    club = lambda s: re.sub(r"^(نادي|ريال|إف سي)\s+", "", s)
    by_nat = defaultdict(list)
    for p in P:
        by_nat[p["nat"][0]].append(p)
    rnd = random.Random(3)
    for p in sorted(P, key=lambda x: x["lv"]):
        if p["lv"] > 3:
            continue
        clubs = [club(c[0]) for c in p["c"]][:4]
        if len(clubs) < 2:
            continue
        pos = (p.get("pos") or ["لاعب"])[0]
        clue = f"لاعب {pos} من {p['nat'][0]}، لعب بـ{'، '.join(clubs[:3])}" + (f"، وانولد سنة {p['by']}" if p.get("by") else "") + ". مين هو؟"
        same = [x["a"] for x in by_nat[p["nat"][0]] if x is not p and x["lv"] <= p["lv"] + 1]
        if len(same) < 3:
            same = [x["a"] for x in P if x is not p and x["lv"] == p["lv"] and (x.get("pos") or [""])[0] == pos]
        if len(same) >= 3:
            gp.add(p["lv"], clue, [p["a"]] + rnd.sample(same, 3))
        if p.get("ucl") and p["lv"] <= 2:
            n = len(p["ucl"])
            fb.add(3, f"كم مرة فاز {p['a']} بدوري أبطال أوروبا (كلاعب)؟", [str(n)] + [str(x) for x in rnd.sample(sorted({1, 2, 3, 4, 5, 6} - {n}), 3)])
        if p.get("h") and p["lv"] <= 2:
            others = [x for x in P if x is not p and x["lv"] <= 2 and x.get("h") and abs(x["h"] - p["h"]) >= 8]
            if len(others) >= 3:
                three = rnd.sample(others, 3)
                if all(x["h"] < p["h"] for x in three):
                    fb.add(3, "مين الأطول بين هدول اللاعبين؟", [p["a"]] + [x["a"] for x in three])
        if p.get("wc") and p["lv"] <= 2:
            pool = [x["a"] for x in P if x["lv"] <= 2 and not x.get("wc") and (x.get("pos") or [""])[0] == pos]
            if len(pool) >= 3:
                fb.add(2, "مين من هدول فاز بكأس العالم؟", [p["a"]] + rnd.sample(pool, 3))


# ---------- شعارات من Simple Icons (رموز بدون كتابة) ----------
LOGO_Q = {"applogos": ("شو هالتطبيق؟", "شعارات تطبيقات", "📲"), "techlogos": ("شعار أي شركة أو تقنية هاد؟", "شعارات شركات تقنية", "🖥️"),
          "brands": ("شعار أي ماركة؟", "شعارات ماركات ومطاعم", "🏷️"), "carlogos": ("شعار أي شركة سيارات هاد؟", "شعارات السيارات", "🚘"),
          "airlines": ("شعار أي شركة طيران هاد؟", "شركات الطيران", "🛫"), "orglogos": ("شعار مين هاد؟", "شعارات منظمات وبطولات", "🌐")}


def logos(cats, Cat):
    rows = [l.split("|") for l in (HERE / "data" / "logos.txt").read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    by = defaultdict(list)
    for slug, ar, cid, d in rows:
        if (ROOT / "docs" / "games" / "pq" / "logos" / f"{slug}.svg").exists():
            by[cid].append((slug, ar, int(d)))
    for cid, items in by.items():
        q, name, icon = LOGO_Q[cid]
        c = get(cats, Cat, cid, name, icon)
        pool = sorted({ar for _, ar, _ in items} | {x[2][0] for x in c.qs})
        have = {x[2][0] for x in c.qs}
        for slug, ar, d in items:
            if ar in have:
                continue
            w = wrong3(ar, [x for x in pool if x != ar])
            if w:
                c.add(d, q, [ar] + w, f"pq/logos/{slug}.svg")


# ---------- رياضات: الأولمبياد + رياضة كل بطل ----------
OLYMPICS = [(1896, "أثينا"), (1900, "باريس"), (1904, "سانت لويس"), (1908, "لندن"), (1912, "ستوكهولم"), (1920, "أنتويرب"), (1924, "باريس"),
            (1928, "أمستردام"), (1932, "لوس أنجلوس"), (1936, "برلين"), (1948, "لندن"), (1952, "هلسنكي"), (1956, "ملبورن"), (1960, "روما"),
            (1964, "طوكيو"), (1968, "مكسيكو سيتي"), (1972, "ميونخ"), (1976, "مونتريال"), (1980, "موسكو"), (1984, "لوس أنجلوس"), (1988, "سيول"),
            (1992, "برشلونة"), (1996, "أتلانتا"), (2000, "سيدني"), (2004, "أثينا"), (2008, "بكين"), (2012, "لندن"), (2016, "ريو دي جانيرو"),
            (2020, "طوكيو"), (2024, "باريس"), (2028, "لوس أنجلوس"), (2032, "بريزبن")]


def sports(cats, Cat):
    c = get(cats, Cat, "sports", "رياضات ثانية", "🏅")
    hosts = sorted({h for _, h in OLYMPICS})
    cnt = Counter(h for _, h in OLYMPICS)
    for y, h in OLYMPICS:
        lv = 1 if y >= 2012 else 2 if y >= 1988 else 3 if y >= 1956 else 4
        c.add(lv, f"وين انقامت (أو رح تنقام) الألعاب الأولمبية الصيفية سنة {y}؟", [h] + R.sample([x for x in hosts if x != h], 3))
        if cnt[h] == 1:
            ys = [str(x) for x, hh in OLYMPICS if hh != h and abs(x - y) <= 24]
            c.add(min(4, lv + 1), f"بأي سنة استضافت {h} الألعاب الأولمبية الصيفية؟", [str(y)] + R.sample(ys, 3))
    A = with_levels([it for it in dedupe(wd("athletes")) if lab1(it, "sport")][:220])
    sports_ = sorted({lab1(x, "sport") for x in A})
    for it in A:
        sp = lab1(it, "sport")
        w = [x for x in sports_ if x != sp]
        if len(w) >= 3:
            c.add(it["lv"], f"{it['ar']}: شو رياضته؟", [sp] + R.sample(w, 3))


ADJ2C = {"مصري": "مصر", "سوري": "سوريا", "لبناني": "لبنان", "أردني": "الأردن", "سعودي": "السعودية", "كويتي": "الكويت", "عراقي": "العراق",
         "مغربي": "المغرب", "جزائري": "الجزائر", "تونسي": "تونس", "إماراتي": "الإمارات العربية المتحدة", "فلسطيني": "فلسطين", "قطري": "قطر",
         "بحريني": "البحرين", "عماني": "سلطنة عمان", "يمني": "اليمن", "سوداني": "السودان", "ليبي": "ليبيا"}
SHORT = {"الإمارات العربية المتحدة": "الإمارات", "سلطنة عمان": "عُمان"}


def singers_text(cats, Cat):
    """مطربين عرب: من وين؟ مين فيهم من البلد الفلاني؟ مين الأكبر؟ (بس اللي إله جنسية عربية وحدة واضحة)."""
    from points_gen import desc, ARAB_AR
    c = get(cats, Cat, "singers", "مطربين وأغاني عربية", "🎵")
    S = []
    for it in dedupe(wd("singers_arab") + wd("singers")):
        if not re.search(r"مغن|مطرب", it.get("ard") or "") or (it.get("sl") or 0) < 8 or len(it["ar"].split()) > 3:
            continue
        if re.search(r"(فرنسي|بلجيكي|أمريكي|أميركي|بريطاني|كندي|سويدي|هولندي|ألماني|إسرائيلي|أرمني|إيطالي|إسباني|تركي|إيراني|يوناني|برازيلي|أسترالي)", it.get("ard") or ""):
            continue
        if re.search(r"(Canadian|American|French|Belgian|British|Swedish|Dutch|German|Israeli|Armenian|Italian|Spanish|Turkish)", it.get("end") or ""):
            continue
        arabs = {x.split(":", 1)[1] for x in it.get("citizen", []) if x.split(":", 1)[1] in ARAB_AR}
        m = re.search("(" + "|".join(ADJ2C) + ")", it.get("ard") or "")
        if len(arabs) != 1:
            continue
        ctry = next(iter(arabs))
        if not m or ADJ2C[m.group(1)] != ctry:
            continue
        it["_c"] = ctry
        it["_f"] = (it.get("gender") or [None])[0] == "Q6581072"
        S.append(it)
    # الشهرة عندنا: الشام ومصر والخليج والعراق أعرف من المغرب العربي (اللي ويكيبيديات أوروبا بتكبّرهم)
    EAST = {"الأردن", "فلسطين", "لبنان", "سوريا", "مصر", "العراق", "السعودية", "الكويت", "الإمارات العربية المتحدة", "قطر", "البحرين", "سلطنة عمان", "اليمن"}
    for it in S:
        it["_sl0"] = it.get("sl", 0)
        it["sl"] = it["_sl0"] * (1.7 if it["_c"] in EAST else 0.55)
    S = with_levels(S)
    allc = sorted({x["_c"] for x in S})
    sh = lambda x: SHORT.get(x, x)
    for it in S:
        lv, f = it["lv"], it["_f"]
        w = [x for x in allc if x != it["_c"]]
        if len(w) >= 3:
            c.add(lv, f"{'المطربة' if f else 'المطرب'} {it['ar']}: من وين؟", [sh(it["_c"])] + [sh(x) for x in R.sample(w, 3)])
        others = [x["ar"] for x in S if x["_c"] != it["_c"] and x["_f"] == f and x["lv"] <= max(2, lv)]
        if len(others) >= 3 and not re.search("(" + "|".join(ADJ2C) + ")", it["ar"]):
            c.add(min(4, lv + 1), f"مين {'فيهن مطربة' if f else 'فيهم مطرب'} من {sh(it['_c'])}؟", [it["ar"]] + R.sample(others, 3))
    # مين الأكبر عمراً (فرق 6 سنين على الأقل بين كل اثنين)
    B = [x for x in S if year(x, "born") and x["lv"] <= 3]
    for _ in range(260):
        grp = R.sample(B, 4)
        ys = sorted(year(x, "born") for x in grp)
        if any(b - a < 6 for a, b in zip(ys, ys[1:])):
            continue
        old = min(grp, key=lambda x: year(x, "born"))
        c.add(4 if max(x["lv"] for x in grp) >= 3 else 3, "مين فيهم الأكبر عمراً (انولد أول)؟", [old["ar"]] + [x["ar"] for x in grp if x is not old])


def mix(cats, Cat, cid, name, icon, sources, target):
    """قسم منوّع: من أسئلة الأقسام الكتابية الثانية (بدون صور)، لحد الهدف."""
    c = get(cats, Cat, cid, name, icon)
    pool = [q for s_ in sources if s_ in cats for q in cats[s_].qs if len(q) == 3]
    R.shuffle(pool)
    per = Counter(q[0] for q in c.qs)
    have = {(q[1], q[2][0]) for q in c.qs}
    gen = Counter(q[1] for q in pool)
    for q in pool:
        if len(c.qs) >= target:
            break
        if per[q[0]] >= target // 4 + 20 or (q[1], q[2][0]) in have or gen[q[1]] >= 15:
            continue
        if c.add(q[0], q[1], q[2]):
            per[q[0]] += 1
            have.add((q[1], q[2][0]))


def generate(cats, Cat):
    for fn in (logos, sports, singers_text, capitals, flags_maps, first, estimate, lies, whoami, movies, videogames, tech, science, history, jordan, leagues, players_text):
        try:
            fn(cats, Cat)
        except Exception as e:   # قسم واحد ما بيوقف البناء كله
            import sys, traceback
            print(f"  ⚠️ {fn.__name__}: {e}", file=sys.stderr)
            traceback.print_exc()
    mix(cats, Cat, "general", "معلومات عامة", "🧠", ["capitals", "science", "history", "tech", "first", "estimate", "whoami", "movies", "islamic",
                                                     "worldcup", "videogames", "translate", "proverbs"], 1050)
