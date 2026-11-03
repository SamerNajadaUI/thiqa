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
            cur_img = len(parts) > 3 and parts[3] in ("img", "logo", "audio", "audiom", "video")
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


AUDIO_CACHE = GAMES / "points_audio.json"


VIDEO_CACHE = GAMES / "points_video.json"


def commons_media(terms, kind):
    """أصوات وفيديوهات من Wikimedia Commons.
    audio: أصوات (بدون موسيقى وأغاني)، audiom: آلات موسيقية (مسموح موسيقى)، video: فيديو قصير.
    الصوت بناخذه mp3 (بيشتغل على الآيفون)، والفيديو بنفضّل mp4 وإلا webm صغير."""
    path = VIDEO_CACHE if kind == "video" else AUDIO_CACHE
    pre = {"audio": "", "audiom": "m:", "video": ""}[kind]
    cache = {}
    try:
        cache = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    api = "https://commons.wikimedia.org/w/api.php"
    out = {}
    nomusic = r"(pronunc|spoken|speech|wikipedia|interview|navy|lecture|article|podcast|anthem|hymn|news|trailer|ad\b|commercial" + (r"|music|song)" if kind == "audio" else ")")
    for term in terms:
        key = pre + term
        if cache.get(key):
            out[term] = cache[key]
            continue
        try:
            ft = "video" if kind == "video" else "audio"
            q = urllib.parse.urlencode({"action": "query", "format": "json", "list": "search", "srnamespace": 6, "srlimit": 12,
                                        "srsearch": f"{term} filetype:{ft}"})
            req = urllib.request.Request(f"{api}?{q}", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                hits = [h["title"] for h in json.loads(r.read().decode("utf-8")).get("query", {}).get("search", [])]
            word = term.split()[0].lower()
            # بدون ملفات النطق (De-Zebra.ogg، LL-Q...) والمقابلات والأخبار
            hits = [h for h in hits if word in h.lower()
                    and not re.match(r"^File:([A-Za-z]{2,3}(-[A-Za-z]{2,4})?-|IDWIKI|LL-Q|User\d)", h)
                    and not re.search(nomusic, h, re.I)]
            url = None
            for h in hits[:4]:
                q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "videoinfo", "viprop": "url|derivatives|size", "titles": h})
                req = urllib.request.Request(f"{api}?{q}", headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=20) as r:
                    pages = json.loads(r.read().decode("utf-8")).get("query", {}).get("pages", {})
                info = (next(iter(pages.values()), {}).get("videoinfo") or [{}])[0]
                ders = info.get("derivatives", [])
                if kind == "video":
                    dur = float(info.get("duration") or 0)
                    if dur and dur > 240:   # فيديو طويل كثير: بنتجاهله
                        continue
                    mp4 = [d["src"] for d in ders if "mp4" in (d.get("type", "") + d.get("src", "")).lower()]
                    webm = sorted([d for d in ders if "webm" in d.get("src", "") and d.get("height")], key=lambda d: abs(int(d["height"]) - 480))
                    url = mp4[0] if mp4 else (webm[0]["src"] if webm else (info.get("url") if re.search(r"\.(mp4|webm)$", info.get("url", ""), re.I) else None))
                else:
                    mp3 = [d["src"] for d in ders if "mp3" in (d.get("type", "") + d.get("src", "")).lower()]
                    url = mp3[0] if mp3 else (info.get("url") if re.search(r"\.(mp3|wav)$", info.get("url", ""), re.I) else None)
                if url:
                    log(f"  {kind} {term}: {h}")
                    break
            if url:
                cache[key] = url
                out[term] = url
            else:
                log(f"  بدون {kind}: {term}")
        except Exception as e:
            log(f"  {kind} {term}: {e}")
        time.sleep(0.3)
    try:
        path.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
    except Exception:
        pass
    return out


def commons(u):
    m = re.search(r"/wikipedia/([a-z]+)/thumb/[^/]+/[^/]+/([^/?]+)/", u or "")
    host = "commons.wikimedia.org" if not m or m.group(1) == "commons" else f"{m.group(1)}.wikipedia.org"
    return f"https://{host}/wiki/Special:FilePath/{m.group(2)}?width=640" if m else u


def image_sections(img_secs):
    MEDIA = ("audio", "audiom", "video")
    titles = [it[1] for _, _, items, k in img_secs if k not in MEDIA for it in items]
    logos = frozenset(it[1] for _, _, items, k in img_secs if k == "logo" for it in items)
    wiki = wiki_images(titles, logos)
    media = {k: commons_media([it[1] for _, _, items, kk in img_secs if kk == k for it in items], k) for k in MEDIA}
    for cat, tmpl, items, kind in img_secs:
        imgs = media[kind] if kind in MEDIA else wiki
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
                media_src = ("audio:" + imgs[t]) if kind in ("audio", "audiom") else ("video:" + imgs[t]) if kind == "video" else commons(imgs[t])
                cat.add(d, tmpl, [ans] + wrong, media_src)


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
    def pool(ids):
        out = []
        for cid in ids:
            c = cats.get(cid)
            if c:
                out += [q for q in c.qs if len(q) > 3 and q[3] and not q[3].startswith(("audio:", "video:"))]
        return out
    for cid, name, icon, pref, ids in (("zoom", "زووم", "🔍", "zoom:", ["celebs", "landmarks", "applogos", "brands", "carlogos", "football", "animals"]),
                                       ("blur", "صورة مموّهة", "🌫️", "blur:", ["animals", "food", "cars", "landmarks", "celebs", "plants", "pets"])):
        c = cats.setdefault(cid, Cat(cid, name, icon))
        qs = pool(ids)
        R.shuffle(qs)
        per = Counter()
        for q in qs:
            d = q[0]
            if per[d] >= 14:
                continue
            if c.add(d, q[1].replace("؟", "") + " (" + ("مقرّبة" if pref == "zoom:" else "مموّهة") + ")؟", q[2], pref + q[3]):
                per[d] += 1


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


def main():
    cats: dict[str, Cat] = {}
    img_secs = read_bank(cats)
    image_sections(img_secs)
    countries(cats)
    football(cats)
    crests(cats)
    worldcup(cats)
    chronology(cats)
    zoom_blur(cats)
    estimate(cats)
    order = ["sounds", "soundslife", "soundsbirds", "soundsinstr", "vidanimals", "vidnature", "vidsports", "zoom", "blur", "emoji",
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
        out.append({"id": c.id, "name": c.name, "icon": c.icon, "qs": c.qs})
        log(f"  {c.icon} {c.name}: {len(c.qs)} سؤال {dict(sorted(per.items()))}")
    OUT.write_text(json.dumps({"generated": time.strftime("%Y-%m-%d"), "cats": out}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"points_q.json: {sum(len(c['qs']) for c in out)} سؤال بـ{len(out)} قسم")


if __name__ == "__main__":
    main()
