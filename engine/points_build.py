#!/usr/bin/env python3
"""
أسئلة لعبة "جمع نقاط": كل قسم فيه أسئلة بأربع صعوبات، وكل سؤال إله 4 خيارات (الأول هو الصح بالملف).

- أسئلة مكتوبة باليد: engine/points_bank.txt
- أقسام بالصور (معالم، حيوانات، أكلات): الصورة من ويكيبيديا
- أعلام وعواصم: engine/points_countries.txt (الأعلام من flagcdn)
- كرة قدم وشعارات: من players.json وparty.json وcareer.json

الاستخدام: python engine/points_build.py   (بيكتب docs/games/pq/index.json + pq/<قسم>.json)
"""
from __future__ import annotations

import json
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
HERE = Path(__file__).resolve().parent
GAMES = ROOT / "docs" / "games"
OUT = GAMES / "points_q.json"   # القديم (ملف واحد)، بينمسح
PQ = GAMES / "pq"
IMG_CACHE = GAMES / "points_img.json"
UA = "AbuOdehGame/1.0 (https://github.com/SamerNajadaUI/thiqa)"
R = random.Random(2026)


def log(m):
    print(m, file=sys.stderr, flush=True)


class Cat:
    def __init__(self, cid, name, icon):
        self.id, self.name, self.icon = cid, name, icon
        self.qs: list = []
        self.seen: set = set()

    def add(self, d, q, opts, img=None):
        opts = [str(o).strip() for o in opts]
        key = (q, img, tuple(sorted(opts)) if not img else "")
        if len(opts) != 4 or len(set(opts)) != 4 or not all(opts) or key in self.seen:
            return False
        self.seen.add(key)
        self.qs.append([int(d), q, opts] + ([img] if img else []))
        return True


def pick3(correct, pool, key=None):
    """3 أجوبة غلط من القائمة، بدون تكرار ولا الجواب الصح."""
    out, seen = [], {correct}
    for x in R.sample(pool, len(pool)):
        if x not in seen:
            out.append(x); seen.add(x)
        if len(out) == 3:
            break
    return out if len(out) == 3 else None


# ---------- صور ويكيبيديا ----------
def wiki_images(titles, logos=frozenset()):
    cache = {}
    try:
        cache = json.loads(IMG_CACHE.read_text(encoding="utf-8"))
    except Exception:
        pass
    bad = lambda u: not u or "logo" in u.lower() or ".svg" in u.lower()
    is_logo = lambda u: bool(u) and bool(re.search(r"(logo|icon|wordmark)", u, re.I))
    for t in titles:
        lang, page = (t.split(":", 1) if t.startswith("ar:") else ("en", t))
        if t in logos:   # شعارات التطبيقات: بدنا ملف الشعار نفسه، مش صورة شاشة
            if is_logo(cache.get(t)):
                continue
            cache.pop(t, None)
            try:
                url = f"https://{lang}.wikipedia.org/api/rest_v1/page/media-list/" + urllib.parse.quote(page.replace(" ", "_"), safe="")
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=20) as r:
                    items = json.loads(r.read().decode("utf-8")).get("items", [])
                for it in items:
                    srcs = it.get("srcset") or []
                    src = srcs[0]["src"] if srcs else None
                    title = it.get("title") or ""
                    if it.get("type") == "image" and src and is_logo(title) and not re.search(r"(wordmark|text)", title, re.I):
                        src = ("https:" + src) if src.startswith("//") else src
                        cache[t] = re.sub(r"/(\d+)px-", "/640px-", src)
                        break
                if t not in cache:
                    log(f"  بدون شعار: {t}")
            except Exception as e:
                log(f"  شعار {t}: {e}")
            time.sleep(0.2)
            continue
        if cache.get(t) and not bad(cache[t]):
            continue
        if cache.get(t):   # الصورة الأساسية شعار: بنجيب أول صورة حقيقية من المقالة
            try:
                url = f"https://{lang}.wikipedia.org/api/rest_v1/page/media-list/" + urllib.parse.quote(page.replace(" ", "_"), safe="")
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=20) as r:
                    items = json.loads(r.read().decode("utf-8")).get("items", [])
                for it in items:
                    srcs = it.get("srcset") or []
                    src = srcs[0]["src"] if srcs else None
                    if it.get("type") == "image" and src and not bad(src) and not re.search(r"(map|flag|coat|seal|icon)", src, re.I):
                        src = ("https:" + src) if src.startswith("//") else src
                        cache[t] = re.sub(r"/(\d+)px-", "/640px-", src)
                        break
                else:
                    cache.pop(t, None)
            except Exception as e:
                log(f"  media-list {t}: {e}")
                cache.pop(t, None)
            time.sleep(0.2)
            continue
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(page.replace(" ", "_"), safe="")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.loads(r.read().decode("utf-8"))
            src = (d.get("thumbnail") or {}).get("source") or (d.get("originalimage") or {}).get("source")
            if src:
                src = re.sub(r"/(\d+)px-", "/640px-", src)
                cache[t] = src
            else:
                log(f"  بدون صورة: {t}")
        except Exception as e:
            log(f"  ما زبطت الصورة: {t} ({e})")
        time.sleep(0.2)
    try:
        IMG_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
    except Exception:
        pass
    return cache


# ---------- البنك المكتوب ----------
def bank_lines():
    """البنك القديم + ملفات engine/bank/*.txt (نفس الصيغة)."""
    yield from (HERE / "points_bank.txt").read_text(encoding="utf-8").splitlines()
    for f in sorted((HERE / "bank").glob("*.txt")):
        yield from f.read_text(encoding="utf-8").splitlines()


def read_bank(cats: dict):
    cur, img_secs, cur_img = None, [], False
    for raw in bank_lines():
        line = raw.strip()
        if not line or (line.startswith("#") and not line.startswith("## ")):
            continue
        if line.startswith("## "):
            parts = [p.strip() for p in line[3:].split("|")]
            cid, name, icon = parts[0], parts[1], parts[2]
            cur = cats.setdefault(cid, Cat(cid, name, icon))
            cur_img = len(parts) > 3 and parts[3] in ("img", "logo", "file")
            if cur_img:
                img_secs.append((cur, parts[4], [], parts[3]))
            continue
        f = [p.strip() for p in line.split("|")]
        if cur_img:
            img_secs[-1][2].append((int(f[0]), f[1], f[2], f[3] if len(f) > 3 else ""))   # الرابع: f = أنثى
        else:
            if len(f) != 6:
                log(f"  سطر غلط: {line}")
                continue
            cur.add(f[0], f[1], f[2:6])
    return img_secs


FILES_CACHE = GAMES / "points_files.json"


def commons_files(names):
    """ملفات Commons بأسمائها (زي خرائط الدول): بنتأكد إنها موجودة، وبنرجّع رابط بحجم 640."""
    cache = {}
    try:
        cache = json.loads(FILES_CACHE.read_text(encoding="utf-8"))
    except Exception:
        pass
    todo = [n for n in names if n not in cache]
    for i in range(0, len(todo), 40):
        chunk = todo[i:i + 40]
        try:
            q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 640,
                                        "titles": "|".join("File:" + n for n in chunk)})
            req = urllib.request.Request(f"https://commons.wikimedia.org/w/api.php?{q}", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode("utf-8"))["query"]
            norm = {x["to"]: x["from"] for x in d.get("normalized", [])}
            for p in d.get("pages", {}).values():
                info = (p.get("imageinfo") or [{}])[0]
                name = norm.get(p.get("title"), p.get("title", ""))[5:]
                if info.get("url"):
                    cache[name] = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(name.replace(" ", "_")) + "?width=640"
                else:
                    log(f"  ملف مش موجود: {name}")
        except Exception as e:
            log(f"  ملفات Commons: {e}")
        time.sleep(0.5)
    try:
        FILES_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
    except Exception:
        pass
    return cache


def commons(u):
    m = re.search(r"/wikipedia/([a-z]+)/thumb/[^/]+/[^/]+/([^/?]+)/", u or "")
    host = "commons.wikimedia.org" if not m or m.group(1) == "commons" else f"{m.group(1)}.wikipedia.org"
    return f"https://{host}/wiki/Special:FilePath/{m.group(2)}?width=640" if m else u


def image_sections(img_secs):
    titles = [it[1] for _, _, items, k in img_secs if k != "file" for it in items]
    logos = frozenset(it[1] for _, _, items, k in img_secs if k == "logo" for it in items)
    wiki = wiki_images(titles, logos)
    files = commons_files([it[1] for _, _, items, kk in img_secs if kk == "file" for it in items])
    for cat, tmpl, items, kind in img_secs:
        imgs = files if kind == "file" else wiki
        lg = kind != "img"
        ok = [it for it in items if imgs.get(it[1])]
        for d, t, ans, g in items:
            if not imgs.get(t) or (not lg and ("logo" in imgs[t].lower() or ".svg" in imgs[t].lower())):
                continue
            # الخيارات من نفس الجنس (صورة بنت = أسماء بنات) ومن صعوبة قريبة
            same = [x for x in ok if x[3] == g and x[2] != ans]
            near = [x[2] for x in same if abs(x[0] - d) <= 1]
            wrong = pick3(ans, near) or pick3(ans, [x[2] for x in same])
            if not wrong and not g:
                wrong = pick3(ans, [x[2] for x in items if x[3] == g])
            if wrong:
                cat.add(d, tmpl, [ans] + wrong, commons(imgs[t]))


# ---------- أعلام وعواصم ----------
def countries(cats):
    rows = []
    for line in (HERE / "points_countries.txt").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            iso, name, cap, cont, d = [x.strip() for x in line.split("|")]
            rows.append({"iso": iso, "n": name, "c": cap, "k": cont, "d": int(d)})
    flags = cats.setdefault("flags", Cat("flags", "أعلام الدول", "🏳️"))
    caps = cats.setdefault("capitals", Cat("capitals", "عواصم ودول", "🌍"))
    for r in rows:
        same = [x["n"] for x in rows if x["k"] == r["k"] and x is not r]
        near = [x["n"] for x in rows if x["k"] == r["k"] and abs(x["d"] - r["d"]) <= 1 and x is not r]
        w = pick3(r["n"], near if len(near) >= 3 else same)
        if w:
            flags.add(r["d"], "علم أي دولة هاد؟", [r["n"]] + w, f"https://flagcdn.com/w640/{r['iso']}.png")
        if r["c"] != r["n"]:
            capsame = [x["c"] for x in rows if x["k"] == r["k"] and x is not r and x["c"] != x["n"]]
            w = pick3(r["c"], capsame)
            if w:
                caps.add(r["d"], f"شو عاصمة {r['n']}؟", [r["c"]] + w)
            w = pick3(r["n"], same)
            if w and r["d"] >= 2:
                caps.add(min(4, r["d"] + 1) if r["d"] >= 3 else r["d"], f"«{r['c']}» عاصمة أي دولة؟", [r["n"]] + w)


# ---------- كرة القدم ----------
def main_nt(p):
    for n in p.get("nt") or []:
        if n and n[0] and not re.search(r"( ب|تحت|الأولمبي|للشباب|الرديف|\d)", n[0]):
            return n[0].replace(" لكرة القدم", "")
    return None


def football(cats):
    try:
        P = json.loads((GAMES / "players.json").read_text(encoding="utf-8"))
    except Exception as e:
        log(f"  players.json: {e}")
        return
    fb = cats.setdefault("football", Cat("football", "كرة قدم", "⚽"))
    far = re.compile(r"(ياباني|صيني|كوري|أسترالي|هندي|تايلاند)")
    # اللاعبين المعروفين بس: المستوى 1 لـ3 (الرابع نادر كثير)، وبدون دوريات شرق آسيا البعيدة عن جمهورنا
    ps = [p for p in P["players"] if p.get("a") and p.get("lv") in (1, 2, 3) and re.search(r"[\u0600-\u06FF]", p["a"])
          and not (p["lv"] >= 2 and far.search(p.get("lg") or "")) and main_nt(p)]   # بدون منتخب = غالباً مدرب أو مش لاعب معروف
    by_lv = defaultdict(list)
    for p in ps:
        by_lv[p["lv"]].append(p)
    group = lambda p: "gk" if any("حارس" in x for x in p.get("pos") or []) else "x"
    counts = Counter()
    for lv in (1, 2, 3):
        for p in R.sample(by_lv[lv], len(by_lv[lv])):
            d = lv + (1 if lv == 3 else 0)   # المستوى 3 = صعب جداً
            # مين هاللاعب (صورة)
            if p.get("img") and counts[("img", d)] < 90:
                pool = [x["a"] for x in by_lv[lv] + by_lv.get(lv + 1, []) if group(x) == group(p) and x["a"] != p["a"]]
                w = pick3(p["a"], pool)
                if w and fb.add(d, "مين هاللاعب؟", [p["a"]] + w, p["img"]):
                    counts[("img", d)] += 1
            # المنتخب
            nt = main_nt(p)
            if nt and counts[("nt", d)] < 25:
                nts = list({main_nt(x) for x in ps} - {nt, None})
                w = pick3(nt, nts)
                if w and fb.add(min(4, d + 1), f"لأي منتخب لعب {p['a']}؟", [nt] + w):
                    counts[("nt", d)] += 1
            # نادي من مسيرته
            clubs = [c[0] for c in p.get("c") or []]
            if len(clubs) >= 2 and counts[("club", d)] < 25:
                big = [c for c, (lg, n) in P.get("clubs", {}).items() if n >= 40 and c not in clubs]
                w = pick3(R.choice(clubs), big)
                if w:
                    right = [c for c in clubs if c not in w][0]
                    if fb.add(min(4, d + 1), f"بأي نادي من هدول لعب {p['a']}؟", [right] + w):
                        counts[("club", d)] += 1
    log(f"  كرة قدم مولّدة: {dict(counts)}")


def crests(cats):
    cr = cats.setdefault("crests", Cat("crests", "شعارات الأندية", "🛡️"))
    logos = {}
    league = {}
    try:
        pj = json.loads((GAMES / "party.json").read_text(encoding="utf-8"))
        logos.update(pj.get("logos", {}))
    except Exception:
        pass
    fame = Counter()
    try:
        P = json.loads((GAMES / "players.json").read_text(encoding="utf-8"))
        for c, (lg, n) in P.get("clubs", {}).items():
            fame[c] = n
            league[c] = lg
    except Exception:
        pass
    try:
        cj = json.loads((GAMES / "career.json").read_text(encoding="utf-8"))
        for p in cj["players"]:
            for c in p["c"]:
                if c[3].startswith("e:") and c[0] not in logos:
                    logos[c[0]] = c[3][2:]
                fame[c[0]] += 3
    except Exception:
        pass
    clubs = [c for c in sorted(logos, key=lambda c: -fame[c]) if re.search(r"[\u0600-\u06FF]", c)][:200]
    n = len(clubs)
    for i, c in enumerate(clubs):
        d = 1 if i < 25 else 2 if i < 70 else 3 if i < 140 else 4
        same = [x for x in clubs if league.get(x) and league.get(x) == league.get(c) and x != c]
        near = [x for j, x in enumerate(clubs) if abs(j - i) <= 40 and x != c]
        w = pick3(c, same if len(same) >= 3 and d >= 2 else near)
        if w:
            cr.add(d, "لأي نادي هالشعار؟", [c] + w, f"https://a.espncdn.com/combiner/i?img=/i/teamlogos/soccer/500/{logos[c]}.png&h=320&w=320")
    log(f"  شعارات: {n} نادي")



# ---------- مين صار أول؟ (أحداث واختراعات بسنينها) ----------
EVENTS = [
    ("اختراع الطباعة (غوتنبرغ)", 1440), ("اكتشاف أمريكا (كولومبوس)", 1492), ("اختراع التلفون", 1876), ("اختراع المصباح الكهربائي", 1879),
    ("أول طيارة (الأخوين رايت)", 1903), ("أول كأس عالم", 1930), ("الحرب العالمية الأولى", 1914), ("الحرب العالمية الثانية", 1939),
    ("استقلال الأردن", 1946), ("تأسيس إمارة شرق الأردن", 1921), ("الثورة العربية الكبرى", 1916), ("معركة الكرامة", 1968),
    ("أول إنسان على القمر", 1969), ("أول إنسان بالفضاء", 1961), ("سقوط جدار برلين", 1989), ("انطلاق فيسبوك", 2004),
    ("انطلاق يوتيوب", 2005), ("أول آيفون", 2007), ("انطلاق واتساب", 2009), ("انطلاق إنستغرام", 2010), ("انطلاق تيك توك", 2016),
    ("أول بلايستيشن", 1994), ("أول جهاز ويندوز 95", 1995), ("تأسيس جوجل", 1998), ("تأسيس مايكروسوفت", 1975), ("تأسيس آبل", 1976),
    ("اكتشاف البنسلين", 1928), ("اختراع التلفزيون", 1927), ("اختراع الراديو", 1895), ("غرق تايتانيك", 1912), ("افتتاح قناة السويس", 1869),
    ("بناء برج إيفل", 1889), ("افتتاح برج خليفة", 2010), ("كأس العالم بقطر", 2022), ("فوز إسبانيا بكأس العالم", 2010),
    ("فوز فرنسا بأول كأس عالم", 1998), ("أول دوري أبطال أوروبا", 1956), ("أول أولمبياد حديثة", 1896), ("فتح القسطنطينية", 1453),
    ("معركة حطين", 1187), ("معركة اليرموك", 636), ("الهجرة النبوية", 622), ("سقوط غرناطة", 1492), ("بناء قبة الصخرة", 691),
    ("تأسيس بغداد", 762), ("الثورة الفرنسية", 1789), ("استقلال أمريكا", 1776), ("اختراع السيارة (بنز)", 1886), ("أول قمر صناعي (سبوتنيك)", 1957),
    ("اختراع الإنترنت (الويب)", 1989), ("أول رسالة SMS", 1992), ("انطلاق جيميل", 2004), ("انطلاق نتفليكس للبث", 2007), ("انطلاق ChatGPT", 2022),
    ("انتشار كورونا", 2020), ("تأهل الأردن لكأس العالم", 2025), ("نهائي الأردن بكأس آسيا", 2024), ("ميسي يفوز بكأس العالم", 2022),
    ("رونالدو ينتقل للنصر", 2023), ("ميسي ينتقل لإنتر ميامي", 2023), ("أول ماينكرافت", 2011), ("أول سوبر ماريو", 1985),
]


def chronology(cats):
    c = cats.setdefault("first", Cat("first", "مين صار أول؟", "🕰️"))
    seen = 0
    per = Counter()
    for _ in range(60000):
        if all(per[d] >= 40 for d in (1, 2, 3, 4)):
            break
        picks = R.sample(EVENTS, 4)
        ys = sorted(y for _, y in picks)
        if len(set(ys)) < 4:
            continue
        gap = ys[1] - ys[0]
        d = 1 if gap >= 60 else 2 if gap >= 20 else 3 if gap >= 6 else 4
        if per[d] >= 40:
            continue
        first = min(picks, key=lambda e: e[1])
        others = [e[0] for e in picks if e is not first]
        if c.add(d, "مين صار أول؟", [first[0]] + others):
            per[d] += 1
        seen += 1


def worldcup(cats):
    try:
        import football_q as fq
    except Exception as e:
        log(f"  كأس العالم: {e}")
        return
    c = cats.setdefault("worldcup", Cat("worldcup", "كأس العالم", "🏆"))
    champs = sorted({w for _, _, w, *_ in fq.WC})
    hosts = sorted({h for _, h, *_ in fq.WC})
    scorers = sorted({v[0] for v in fq.WC_TOP.values()})
    for y, host, win, *_ in fq.WC:
        d = 1 if y >= 2006 else 2 if y >= 1982 else 3 if y >= 1954 else 4
        w = pick3(win, champs)
        if w:
            c.add(d, f"مين فاز بكأس العالم {y}؟", [win] + w)
        w = pick3(host, hosts)
        if w and host != win:
            c.add(min(4, d + 1), f"وين انقامت كأس العالم {y}؟", [host] + w)
        top = fq.WC_TOP.get(y)
        if top:
            w = pick3(top[0], scorers)
            if w:
                c.add(min(4, d + 1), f"مين هداف كأس العالم {y}؟", [top[0]] + w)


# ---------- زووم ومموّهة: نفس صور الأقسام الثانية بس بتأثير ----------
def zoom_blur(cats):
    """زووم ومموّهة: نفس صور أسئلة «شو اسمه؟» من أقسام الصور، بتأثير بيوضح مع الوقت."""
    skip = re.compile(r"(بأي دولة|بأي مدينة|من وين|مين رسم|وين معروضة|الشركة المصنّعة|مين اخترعه|عملة أي|لأي نادي|شو رياضة|أصل)")

    def pool(ids):
        out = []
        for cid in ids:
            c = cats.get(cid)
            if c:
                out += [q for q in c.qs if len(q) > 3 and q[3] and q[3].startswith("http") and not skip.search(q[1]) and "flagcdn" not in q[3]]
        return out
    for cid, name, icon, pref, ids in (("zoom", "زووم", "🔍", "zoom:", ["celebs", "landmarks", "applogos", "brands", "carlogos", "football", "animals", "actors",
                                                                       "cities", "towers", "fruits", "athletes", "singerspics", "techlogos", "airlines", "cars"]),
                                       ("blur", "صورة مموّهة", "🌫️", "blur:", ["animals", "food", "cars", "landmarks", "celebs", "plants", "pets", "birds", "actors",
                                                                               "desserts", "castles", "historic", "arabplayers", "instruments", "dinos", "sealife"])):
        c = cats.setdefault(cid, Cat(cid, name, icon))
        qs = pool(ids)
        R.shuffle(qs)
        per = Counter(q[0] for q in c.qs)
        seen = {q[2][0] for q in c.qs}
        for q in qs:
            d = q[0]
            if per[d] >= 270 or q[2][0] in seen:
                continue
            if c.add(d, q[1].replace("؟", "") + " (" + ("مقرّبة" if pref == "zoom:" else "مموّهة") + ")؟", q[2], pref + q[3]):
                per[d] += 1
                seen.add(q[2][0])


# ---------- قدّر الرقم: من أسئلة الرقم الأقرب، بخيارات ----------
def estimate(cats):
    c = cats.setdefault("estimate", Cat("estimate", "قدّر الرقم", "📊"))
    rows = []
    # الأسئلة المكتوبة باليد بلعبة الرقم الأقرب (معروفة ومسلّية)، مش المولّدة من Wikidata
    try:
        html = (GAMES / "numbers.html").read_text(encoding="utf-8")
        line = next(l for l in html.splitlines() if l.startswith("const QUESTIONS = "))
        for cat, qs in json.loads(line[len("const QUESTIONS = "):].rstrip().rstrip(";")).items():
            rows += [(cat, q) for q in qs]
    except Exception as e:
        log(f"  الأرقام: {e}")
    R.shuffle(rows)

    def fmt(x, year=False):
        return str(x) if year else (f"{x:,}" if isinstance(x, int) else f"{x:g}")

    per = Counter()
    for cat, (q, a, unit, note) in rows:
        if all(per[d] >= 40 for d in (1, 2, 3, 4)):
            break
        if not isinstance(a, (int, float)) or a <= 0:
            continue
        year = isinstance(a, int) and 1000 <= a <= 2100 and "سنة" in q
        if year:
            offs = R.sample([-40, -25, -15, -8, 8, 15, 25, 40], 3)
            wrong = [a + o for o in offs if a + o <= 2026]
            d = 2 if a >= 1950 else 3 if a >= 1800 else 4
        else:
            f = R.choice([(0.5, 2, 3), (0.25, 0.5, 2), (2, 3, 0.5), (0.1, 10, 3)])
            wrong = []
            for k in f:
                v = a * k
                v = int(round(v, -int(len(str(int(v))) - 2))) if v >= 100 else (round(v, 1) if v < 10 else int(round(v)))
                wrong.append(v)
            d = 1 if f[0] == 0.1 else 2 if 0.25 in f else 3
        if len({a, *wrong}) < 4 or len(wrong) < 3:
            continue
        if per[d] >= 40:
            continue
        u = f" ({unit})" if unit and unit not in q else ""
        if c.add(d, q + u, [fmt(a, year)] + [fmt(w, year) for w in wrong[:3]]):
            per[d] += 1
    log(f"  قدّر الرقم: {dict(per)}")


# ---------- لاعبين عرب بالصور ----------
ARAB = {"الأردن", "السعودية", "مصر", "الإمارات", "قطر", "الكويت", "البحرين", "عُمان", "سلطنة عمان", "العراق", "سوريا", "لبنان", "فلسطين",
        "المغرب", "الجزائر", "تونس", "ليبيا", "السودان", "اليمن", "موريتانيا"}


def arab_players(cats):
    try:
        P = json.loads((GAMES / "players.json").read_text(encoding="utf-8"))
    except Exception:
        return
    c = cats.setdefault("arabplayers", Cat("arabplayers", "لاعبين عرب بالصور", "🌍"))
    ps = [p for p in P["players"] if p.get("img") and p.get("a") and set(p.get("nat") or []) & ARAB and main_nt(p)]
    ps.sort(key=lambda p: (p.get("lv") or 9, p.get("r") or 0))
    names = [p["a"] for p in ps]
    for k, p in enumerate(ps[:80]):
        d = 1 + min(3, k * 4 // max(1, min(80, len(ps))))
        near = names[max(0, k - 15):k + 15]
        w = pick3(p["a"], near) or pick3(p["a"], names)
        if w:
            c.add(d, "مين هاللاعب العربي؟", [p["a"]] + w, p["img"])
    log(f"  لاعبين عرب: {len(ps)}")


# ---------- حسبة سريعة ----------
def quick_math(cats):
    """حسبة سريعة: قوالب كثيرة بخيارات قريبة ومقنعة (أغلاط شائعة)، 260 سؤال لكل مستوى تقريباً."""
    c = cats.setdefault("math", Cat("math", "حسبة سريعة", "🧮"))
    rnd = random.Random(7)

    def fmt(v):
        if isinstance(v, float):
            v = round(v, 2)
            if v == int(v):
                v = int(v)
        return f"{v:,}" if isinstance(v, int) and abs(v) >= 10000 else str(v)

    def opts(a, cands=(), spread=None):
        """الجواب + 3 خيارات: أول إشي من الأغلاط الشائعة، بعدين قريبة."""
        out = []
        for v in cands:
            if v != a and v not in out and (not isinstance(v, (int, float)) or v >= 0):
                out.append(v)
        sp = spread or max(2, abs(a) // 8 if isinstance(a, int) else 2)
        tries = 0
        while len(out) < 3 and tries < 200:
            tries += 1
            v = a + rnd.choice([-1, 1]) * rnd.randint(1, sp)
            if v != a and v not in out and v >= 0:
                out.append(v)
        rnd.shuffle(out)
        return [fmt(a)] + [fmt(v) for v in out[:3]]

    texts = {q[1] for q in c.qs}

    def add(lv, q, a, cands=(), spread=None):
        if q not in texts and c.add(lv, q, opts(a, cands, spread)):
            texts.add(q)

    T = {1: [], 2: [], 3: [], 4: []}

    def t(lv):
        def deco(fn):
            T[lv].append(fn)
            return fn
        return deco

    @t(1)
    def mul_small():
        x, y = rnd.randint(2, 10), rnd.randint(2, 10)
        add(1, f"كم {x} × {y}؟", x * y, [x * y + x, x * y - y, x * (y + 1), (x - 1) * y])

    @t(1)
    def add2():
        a, b = rnd.randint(12, 89), rnd.randint(11, 59)
        add(1, f"كم {a} + {b}؟", a + b, [a + b + 10, a + b - 10, a + b + 1, a + b - 1])

    @t(1)
    def sub2():
        a = rnd.randint(40, 120); b = rnd.randint(11, a - 5)
        add(1, f"كم {a} − {b}؟", a - b, [a - b + 10, a - b - 10, a - b + 2, a - b - 1])

    @t(1)
    def half():
        n = rnd.randrange(20, 400, 2)
        add(1, f"قديش نص الـ{n}؟", n // 2, [n // 2 + 10, n // 2 - 5, n // 4, n // 2 + 2])

    @t(1)
    def double():
        n = rnd.randint(13, 260)
        add(1, f"قديش ضعف الـ{n}؟", 2 * n, [2 * n + 10, 2 * n - 2, 2 * n + 2, n + 20])

    @t(1)
    def div_small():
        y = rnd.randint(2, 9); x = y * rnd.randint(2, 12)
        add(1, f"كم {x} ÷ {y}؟", x // y, [x // y + 1, x // y - 1, x // y + 2])

    @t(1)
    def minutes():
        h = rnd.randint(2, 9)
        add(1, f"كم دقيقة بـ{h} ساعات؟", h * 60, [h * 60 + 60, h * 60 - 60, h * 100, h * 60 + 30])

    @t(1)
    def money1():
        p = rnd.choice([2, 3, 5, 10]); n = rnd.randint(3, 9)
        add(1, f"إذا السندويشة بـ{p} دنانير، قديش حق {n} سندويشات؟", p * n, [p * n + p, p * n - p, p + n])

    @t(1)
    def change():
        price = rnd.randint(3, 18); paid = rnd.choice([20, 50])
        add(1, f"اشتريت إشي بـ{price} دينار ودفعت {paid}، قديش الباقي؟", paid - price, [paid - price + 1, paid - price - 1, paid - price + 10])

    @t(1)
    def days_weeks():
        w = rnd.randint(2, 12)
        add(1, f"كم يوم بـ{w} أسابيع؟", w * 7, [w * 7 + 7, w * 7 - 7, w * 5, w * 7 + 1])

    @t(2)
    def mul_mid():
        x, y = rnd.randint(11, 25), rnd.randint(3, 9)
        add(2, f"كم {x} × {y}؟", x * y, [x * y + y, x * y - x, x * y + 10, (x + 1) * y])

    @t(2)
    def pct_easy():
        p = rnd.choice([10, 20, 25, 50, 75]); n = rnd.choice([40, 60, 80, 120, 160, 200, 240, 360, 400, 480])
        if n * p % 100:
            return
        a = n * p // 100
        add(2, f"كم {p}% من {n}؟", a, [a + 10, a - 10 if a > 10 else a + 20, n * (100 - p) // 100, a + 5])

    @t(2)
    def min_half():
        h = rnd.randint(2, 7)
        add(2, f"كم دقيقة بـ{h} ساعات ونص؟", h * 60 + 30, [h * 60 + 50, h * 60, h * 60 + 60, h * 60 + 15])

    @t(2)
    def secs():
        m = rnd.randint(2, 15)
        add(2, f"كم ثانية بـ{m} دقايق؟", m * 60, [m * 60 + 60, m * 100, m * 60 - 60, m * 60 + 30])

    @t(2)
    def add3():
        a, b, c_ = rnd.randint(15, 99), rnd.randint(15, 99), rnd.randint(15, 99)
        s_ = a + b + c_
        add(2, f"كم {a} + {b} + {c_}؟", s_, [s_ + 10, s_ - 10, s_ + 1, s_ - 2])

    @t(2)
    def discount():
        price = rnd.choice([20, 40, 50, 60, 80, 100, 120, 150, 200]); p = rnd.choice([10, 20, 25, 50])
        if price * p % 100:
            return
        after = price - price * p // 100
        add(2, f"بلوزة سعرها {price} دينار وعليها خصم {p}%، قديش صار سعرها؟", after, [price * p // 100, after + 5, after - 5, price - p])

    @t(2)
    def age():
        y = rnd.randint(1975, 2012)
        add(2, f"واحد مخلوق سنة {y}، قديش عمره بآخر سنة 2026؟", 2026 - y, [2025 - y, 2027 - y, 2026 - y + 10])

    @t(2)
    def avg3():
        b = rnd.randint(10, 60); d = rnd.randint(2, 15)
        a, c_ = b - d, b + d
        add(2, f"قديش معدّل {a} و{b} و{c_}؟", b, [b + 1, b - 1, b + d, b - d // 2 if d > 2 else b + 2])

    @t(2)
    def square_small():
        a = rnd.randint(11, 20)
        add(2, f"كم {a} تربيع ({a}×{a})؟", a * a, [a * a + a, a * a - a, a * a + 10, a * 2])

    @t(2)
    def sqrt_small():
        a = rnd.randint(4, 20)
        add(2, f"قديش الجذر التربيعي لـ{a * a}؟", a, [a + 1, a - 1, a * 2, a + 2])

    @t(2)
    def goals():
        g = rnd.randint(18, 40); m = rnd.choice([2, 3])
        tot = g * m
        add(2, f"لاعب سجّل {tot} هدف بـ{m} مواسم بالتساوي، قديش سجّل بكل موسم؟", g, [g + 2, g - 2, g + 5, tot - g])

    @t(3)
    def mul_big():
        a = rnd.randint(21, 99); b = rnd.randint(11, 39)
        p_ = a * b
        add(3, f"كم {a} × {b}؟", p_, [p_ + 10, p_ - 10, p_ + a, p_ - b, p_ + 100])

    @t(3)
    def pct_mid():
        p = rnd.choice([5, 15, 30, 35, 40, 60, 70]); n = rnd.choice([60, 80, 120, 140, 180, 220, 260, 300, 420, 500])
        if n * p % 100:
            return
        a = n * p // 100
        add(3, f"كم {p}% من {n}؟", a, [a + 5, a - 5, a + 10, n * (100 - p) // 100])

    @t(3)
    def ratio():
        q, pr = rnd.randint(3, 6), rnd.choice([2, 3, 4, 5, 6])
        n = q * rnd.randint(3, 7)
        a = pr * n // q
        add(3, f"إذا {q} أقلام حقهم {pr} دنانير، قديش حق {n} قلم؟", a, [a + pr, a - pr, pr * n, a + 1])

    @t(3)
    def speed():
        sp, tm = rnd.choice([60, 70, 80, 90, 100, 110, 120]), rnd.choice([2, 3, 4, 5])
        add(3, f"سيارة ماشية {sp} كم بالساعة، قديش بتقطع بـ{tm} ساعات؟", sp * tm, [sp * tm + sp, sp * tm - sp, sp * tm + 20])

    @t(3)
    def speed_half():
        sp = rnd.choice([60, 80, 100, 120]); tm = rnd.randint(1, 3)
        a = sp * tm + sp // 2
        add(3, f"سيارة ماشية {sp} كم بالساعة، قديش بتقطع بـ{tm} ساعة ونص؟", a, [sp * tm, a + sp // 2, a + 10, a - 20])

    @t(3)
    def time_end():
        h = rnd.randint(1, 10); m = rnd.choice([10, 15, 20, 25, 35, 40, 45, 50]); dur = rnd.choice([45, 50, 75, 90, 105, 120, 135])
        tot = h * 60 + m + dur
        H, M = tot // 60, tot % 60
        H12 = (H - 1) % 12 + 1
        ans = f"{H12}:{M:02d}"
        alts = set()
        for dh, dm in [(1, 0), (-1, 0), (0, 10), (0, -10), (0, 15), (0, -5)]:
            tt = tot + dh * 60 + dm
            hh = ((tt // 60) - 1) % 12 + 1
            alts.add(f"{hh}:{tt % 60:02d}")
        alts.discard(ans)
        qq = f"مباراة بلشت الساعة {h}:{m:02d} وطوّلت {dur} دقيقة، إيمتى خلصت؟"
        if qq not in texts and c.add(3, qq, [ans] + rnd.sample(sorted(alts), 3)):
            texts.add(qq)

    @t(3)
    def sum_n():
        n = rnd.choice([10, 12, 15, 16, 18, 20, 24, 25, 30])
        a = n * (n + 1) // 2
        add(3, f"كم مجموع الأعداد من 1 لـ{n}؟", a, [n * n // 2, a + n, a - n, a + 10])

    @t(3)
    def div_mid():
        y = rnd.randint(6, 19); q = rnd.randint(12, 45)
        x = y * q
        add(3, f"كم {x} ÷ {y}؟", q, [q + 1, q - 1, q + 2, q + 10])

    @t(3)
    def frac():
        d = rnd.choice([3, 4, 5, 8]); k = rnd.randint(1, d - 1); n = d * rnd.randint(5, 40)
        a = n * k // d
        names = {(1, 3): "ثلث", (2, 3): "ثلثين", (1, 4): "ربع", (3, 4): "ثلاث أرباع", (1, 5): "خُمس", (2, 5): "خُمسين",
                 (3, 5): "ثلاث أخماس", (4, 5): "أربع أخماس", (1, 8): "ثُمن", (3, 8): "ثلاث أثمان", (5, 8): "خمس أثمان", (7, 8): "سبع أثمان"}
        nm = names.get((k, d))
        if not nm:
            return
        add(3, f"قديش {nm} الـ{n}؟", a, [n // d, a + n // d, a - n // d if a > n // d else a + 2 * (n // d), a + 1])

    @t(3)
    def neg():
        a = rnd.randint(5, 40); b = rnd.randint(a + 3, a + 50)
        qq = f"كم {a} − {b}؟"
        if qq not in texts and c.add(3, qq, [str(a - b), str(b - a), str(a - b - 10), str(a - b + 2)]):
            texts.add(qq)

    @t(3)
    def hours_days():
        d = rnd.randint(2, 9)
        add(3, f"كم ساعة بـ{d} أيام؟", d * 24, [d * 24 + 24, d * 20, d * 24 - 12, d * 12])

    @t(4)
    def sq_big():
        a = rnd.randint(21, 49)
        add(4, f"كم {a} تربيع؟", a * a, [a * a + a, a * a - a, a * a + 10, (a + 1) * (a - 1) if (a + 1) * (a - 1) != a * a else a * a + 2])

    @t(4)
    def pct_hard():
        p = rnd.choice([12, 15, 35, 45, 65, 85]); n = rnd.choice([40, 60, 80, 120, 140, 220, 260, 380, 440, 600])
        v = n * p / 100
        if v != int(v):
            return
        a = int(v)
        add(4, f"كم {p}% من {n}؟", a, [a + 3, a - 3, a + 9, n * (100 - p) // 100 if n * (100 - p) % 100 == 0 else a + 6])

    @t(4)
    def mul3():
        a = rnd.randint(101, 499); b = rnd.randint(3, 9)
        add(4, f"كم {a} × {b}؟", a * b, [a * b + b * 10, a * b - b, a * b + 100, a * b - 100])

    @t(4)
    def compound():
        a, b, c_ = rnd.randint(3, 12), rnd.randint(2, 9), rnd.randint(2, 20)
        v = a * b + c_
        add(4, f"كم {c_} + {a} × {b}؟ (انتبه للترتيب)", v, [(a + c_) * b, v + 1, v - b, v + 10])

    @t(4)
    def compound2():
        a, b, c_ = rnd.randint(20, 60), rnd.randint(2, 9), rnd.randint(2, 6)
        v = a - b * c_
        add(4, f"كم {a} − {b} × {c_}؟", v, [(a - b) * c_, v + c_, v - 1, v + 10])

    @t(4)
    def increase():
        n = rnd.choice([40, 50, 80, 120, 150, 200, 250, 400]); p = rnd.choice([10, 20, 25, 30, 50])
        if n * p % 100:
            return
        a = n + n * p // 100
        add(4, f"راتب {n} دينار زاد {p}%، قديش صار؟", a, [n + p, n * p // 100, a + 10, a - 5])

    @t(4)
    def wins():
        w, d, l = rnd.randint(8, 28), rnd.randint(2, 12), rnd.randint(1, 10)
        pts = w * 3 + d
        add(4, f"فريق فاز {w} مرة وتعادل {d} وخسر {l}، قديش نقاطه (الفوز 3 والتعادل 1)؟", pts, [w * 3, pts + d, pts - l, w * 2 + d])

    @t(4)
    def seq_sum():
        a = rnd.randint(2, 12); dlt = rnd.randint(2, 7); n = 5
        terms = [a + i * dlt for i in range(n)]
        s_ = sum(terms)
        add(4, f"كم {' + '.join(map(str, terms))}؟", s_, [s_ + dlt, s_ - dlt, s_ + 10, s_ - 5])

    @t(4)
    def minutes_to():
        dur = rnd.randint(70, 250)
        def hm(H, M):
            hs = "ساعة" if H == 1 else "ساعتين" if H == 2 else f"{H} ساعات"
            return f"{hs} و{M} دقيقة" if M else hs
        H, M = dur // 60, dur % 60
        if not M or M == 20:
            return
        ans = hm(H, M)
        alts = {hm(H, (M + 10) % 60 or 5), hm(H + 1, M), hm(max(1, H - 1), M), hm(H, abs(M - 20) or 15)}
        alts.discard(ans)
        qq = f"كم ساعة ودقيقة بـ{dur} دقيقة؟"
        if qq not in texts and c.add(4, qq, [ans] + rnd.sample(sorted(alts), 3)):
            texts.add(qq)

    @t(4)
    def double_time():
        start = rnd.choice([1, 2, 3, 5, 10])
        steps = rnd.randint(4, 7)
        a = start * (2 ** steps)
        add(4, f"عدد بيتضاعف كل ساعة، بلش {start}، قديش بصير بعد {steps} ساعات؟", a, [start * 2 * steps, a // 2, a * 2, a + start])

    @t(4)
    def rect():
        w, h = rnd.randint(6, 25), rnd.randint(6, 25)
        if w == h:
            return
        add(4, f"غرفة طولها {w} متر وعرضها {h}، قديش مساحتها؟", w * h, [2 * (w + h), w * h + w, w * h - h, w + h])

    @t(4)
    def perim():
        w, h = rnd.randint(8, 60), rnd.randint(8, 60)
        if w == h:
            return
        add(4, f"ملعب طوله {w} وعرضه {h}، قديش محيطه؟", 2 * (w + h), [w * h, w + h, 2 * (w + h) + 10, 2 * w + h])

    for lv, fns in T.items():
        goal = 270
        tries = 0
        while sum(1 for q in c.qs if q[0] == lv) < goal and tries < 40000:
            tries += 1
            rnd.choice(fns)()


def main():
    cats: dict[str, Cat] = {}
    img_secs = read_bank(cats)
    image_sections(img_secs)
    countries(cats)
    football(cats)
    crests(cats)
    worldcup(cats)
    chronology(cats)
    estimate(cats)
    arab_players(cats)
    quick_math(cats)
    import points_text
    import points_gen
    import points_data
    points_text.generate(cats, Cat)
    points_gen.generate(cats, Cat, target)
    points_data.generate(cats, Cat)
    zoom_blur(cats)
    order = ["globe", "arabplayers", "actors", "scientists", "cities", "castles", "mosques", "dinos", "sealife",
             "insects", "fruits", "drinks", "costumes", "space", "translate", "nicknames", "whoami", "math", "zoom", "blur", "emoji",
             "lies", "estimate", "childhood", "carlogos", "airlines", "brands", "pets", "plants", "instruments", "currency", "singerspics", "football", "worldcup", "coaches", "crests", "stadiums", "nashama", "celebs", "flags", "capitals", "landmarks",
             "historic", "animals", "food", "jofood", "cars", "movies", "cartoons", "singers", "videogames", "tech", "general",
             "science", "history", "first", "islamic", "proverbs", "dialects", "riddles", "jordan", "jocities", "sports"]
    out = []
    for cid in order + [c for c in cats if c not in order]:
        c = cats.get(cid)
        if not c:
            continue
        per = Counter(q[0] for q in c.qs)
        if min(per.get(d, 0) for d in (1, 2, 3, 4)) < 2:
            log(f"  ⚠️ {c.name}: ناقص أسئلة {dict(per)}")
            continue
        out.append(c)
        log(f"  {c.icon} {c.name}: {len(c.qs)} سؤال {dict(sorted(per.items()))}")
    write_split(out)
    log(f"pq/: {sum(len(c.qs) for c in out)} سؤال بـ{len(out)} قسم")


# هدف كل قسم (طلب سامر 2026-11-16): اللي كان فيه 50 سؤال أو أكثر = 1000، والباقي = 500 على الأقل
BIG = {"math", "zoom", "blur", "estimate", "football", "worldcup", "crests", "celebs", "flags", "capitals", "historic", "general", "science",
       "history", "first", "islamic", "riddles", "jordan", "sports", "wrestlers"}


def target(cid):
    return 1000 if cid in BIG else 500


def kind_of(c):
    imgs = [q[3] for q in c.qs if len(q) > 3 and q[3]]
    if not imgs:
        return "txt"
    return "fx" if sum(1 for u in imgs if u.startswith(("zoom:", "blur:"))) > len(imgs) / 2 else "img"


def clean_dups(c):
    """ضد التكرار: نفس السؤال بنفس الجواب مرة وحدة بس (حتى لو الخيارات غير).
    السؤال العام («مين صار أول؟»، «وين الكذبة؟») مسموح مرتين لنفس الجواب بخيارات مختلفة.
    والتلميح النصي اللي بينطبق على أكثر من جواب (مثلاً «أنا لاعب سلة أمريكي انولدت 1963») بينشال كله لأنه مش واضح."""
    by_q = Counter(q[1] for q in c.qs)
    answers = defaultdict(set)
    for q in c.qs:
        answers[(q[1], q[3] if len(q) > 3 else None)].add(q[2][0])
    cnt = Counter()
    out = []
    for q in c.qs:
        img = q[3] if len(q) > 3 else None
        generic = by_q[q[1]] >= 15
        ans = str(q[2][0])
        # الجواب مكتوب بالسؤال = سؤال مكشوف (إلا «هاد ولا هاد؟» وحزازير الخدعة)
        if img is None and len(ans) > 2 and ans in q[1] and " ولا " not in q[1] and c.id != "riddles":
            continue
        if not generic and img is None and len(answers[(q[1], None)]) > 1:
            continue
        k = (q[1], q[2][0], img)
        cnt[k] += 1
        if cnt[k] > (2 if generic else 1):
            continue
        if img:  # نفس الصورة بنفس الجواب (حتى لو صيغة السؤال غير) = نفس السؤال
            k2 = ("img", img, q[2][0])
            cnt[k2] += 1
            if cnt[k2] > 1:
                continue
        out.append(q)
    dropped = len(c.qs) - len(out)
    c.qs = out
    return dropped


def write_split(cats):
    """كل قسم بملف لحاله (docs/games/pq/<id>.json) + فهرس صغير، عشان اللعبة تنزّل بس الأقسام اللي انختارت."""
    PQ.mkdir(exist_ok=True)
    for c in cats:
        n = clean_dups(c)
        if n:
            log(f"  {c.id}: شلنا {n} مكرر")
    keep = set()
    index = []
    for c in cats:
        f = PQ / f"{c.id}.json"
        f.write_text(json.dumps({"id": c.id, "qs": c.qs}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        keep.add(f.name)
        index.append({"id": c.id, "name": c.name, "icon": c.icon, "n": len(c.qs), "k": kind_of(c)})
    (PQ / "index.json").write_text(json.dumps({"generated": time.strftime("%Y-%m-%d"), "cats": index}, ensure_ascii=False, separators=(",", ":")),
                                    encoding="utf-8")
    keep.add("index.json")
    for f in PQ.glob("*.json"):
        if f.name not in keep:
            f.unlink()
    if OUT.exists():
        OUT.unlink()


if __name__ == "__main__":
    main()
