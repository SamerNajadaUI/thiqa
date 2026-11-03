#!/usr/bin/env python3
"""
أسئلة لعبة "جمع نقاط": كل قسم فيه أسئلة بأربع صعوبات، وكل سؤال إله 4 خيارات (الأول هو الصح بالملف).

- أسئلة مكتوبة باليد: engine/points_bank.txt
- أقسام بالصور (معالم، حيوانات، أكلات): الصورة من ويكيبيديا
- أعلام وعواصم: engine/points_countries.txt (الأعلام من flagcdn)
- كرة قدم وشعارات: من players.json وparty.json وcareer.json

الاستخدام: python engine/points_build.py   (بيكتب docs/games/points_q.json)
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
OUT = GAMES / "points_q.json"
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
def read_bank(cats: dict):
    cur, img_secs, cur_img = None, [], False
    for raw in (HERE / "points_bank.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or (line.startswith("#") and not line.startswith("## ")):
            continue
        if line.startswith("## "):
            parts = [p.strip() for p in line[3:].split("|")]
            cid, name, icon = parts[0], parts[1], parts[2]
            cur = cats.setdefault(cid, Cat(cid, name, icon))
            cur_img = len(parts) > 3 and parts[3] in ("img", "logo")
            if cur_img:
                img_secs.append((cur, parts[4], [], parts[3] == "logo"))
            continue
        f = [p.strip() for p in line.split("|")]
        if cur_img:
            img_secs[-1][2].append((int(f[0]), f[1], f[2]))
        else:
            if len(f) != 6:
                log(f"  سطر غلط: {line}")
                continue
            cur.add(f[0], f[1], f[2:6])
    return img_secs


def commons(u):
    m = re.search(r"/wikipedia/([a-z]+)/thumb/[^/]+/[^/]+/([^/?]+)/", u or "")
    host = "commons.wikimedia.org" if not m or m.group(1) == "commons" else f"{m.group(1)}.wikipedia.org"
    return f"https://{host}/wiki/Special:FilePath/{m.group(2)}?width=640" if m else u


def image_sections(img_secs):
    titles = [t for _, _, items, _ in img_secs for _, t, _ in items]
    logos = frozenset(t for _, _, items, lg in img_secs if lg for _, t, _ in items)
    imgs = wiki_images(titles, logos)
    for cat, tmpl, items, lg in img_secs:
        for d, t, ans in items:
            if not imgs.get(t) or (not lg and ("logo" in imgs[t].lower() or ".svg" in imgs[t].lower())):
                continue
            near = [a for dd, _, a in items if abs(dd - d) <= 1 and a != ans]
            wrong = pick3(ans, near) or pick3(ans, [a for _, _, a in items])
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


def main():
    cats: dict[str, Cat] = {}
    img_secs = read_bank(cats)
    image_sections(img_secs)
    countries(cats)
    football(cats)
    crests(cats)
    worldcup(cats)
    chronology(cats)
    order = ["football", "worldcup", "coaches", "crests", "stadiums", "nashama", "celebs", "flags", "capitals", "landmarks",
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
        out.append({"id": c.id, "name": c.name, "icon": c.icon, "qs": c.qs})
        log(f"  {c.icon} {c.name}: {len(c.qs)} سؤال {dict(sorted(per.items()))}")
    OUT.write_text(json.dumps({"generated": time.strftime("%Y-%m-%d"), "cats": out}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"points_q.json: {sum(len(c['qs']) for c in out)} سؤال بـ{len(out)} قسم")


if __name__ == "__main__":
    main()
