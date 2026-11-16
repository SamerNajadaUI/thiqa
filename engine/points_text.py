#!/usr/bin/env python3
"""
أسئلة كتابية من بيانات محلية (engine/data): ترجمة، أمثال، لهجات، كأس العالم، القرآن، ألغاز وسلاسل.
كل مولّد بيضيف للقسم عن طريق Cat.add (اللي بيمنع التكرار وبيتأكد من 4 خيارات مختلفة).
"""
from __future__ import annotations

import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
ROOT = HERE.parent
R = random.Random(2611)


def rows(name):
    out = []
    for line in (DATA / name).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append([x.strip() for x in line.split("|")])
    return out


def words(s):
    return set(re.findall(r"[؀-ۿ]{3,}", s))


def far_from(ans, pool, k=3, key=lambda x: x, max_overlap=0.25, bad=None):
    """خيارات غلط بعيدة بالمعنى عن الجواب (عشان ما يصير في جوابين صح)."""
    wa = words(key(ans))
    out = []
    for x in R.sample(pool, len(pool)):
        if key(x) == key(ans) or x in out or (bad and bad(x)):
            continue
        wx = words(key(x))
        if wa and wx and len(wa & wx) / max(1, min(len(wa), len(wx))) > max_overlap:
            continue
        out.append(x)
        if len(out) == k:
            return out
    return None


def get(cats, Cat, cid, name, icon):
    if cid not in cats:
        cats[cid] = Cat(cid, name, icon)
    return cats[cid]


# ---------- ترجمها ----------
def translate(cats, Cat):
    c = get(cats, Cat, "translate", "ترجمها", "🔤")
    W = [(int(d), en, ar, g) for d, en, ar, g in rows("words.txt")]
    by = defaultdict(list)
    for w in W:
        by[w[3]].append(w)
    for d, en, ar, g in W:
        same = [x for x in by[g] if x[1] != en]
        other = [x for x in W if x[3] != g]
        pool = same if d >= 2 and len(same) >= 3 else other
        wr = R.sample([x for x in pool if x[2] != ar], 3)
        c.add(d, f"شو معنى كلمة «{en.capitalize()}»؟", [ar] + [x[2] for x in wr])
        wr = R.sample([x for x in (same if len(same) >= 3 else other) if x[1] != en], 3)
        c.add(min(4, d + (1 if d <= 2 else 0)), f"كيف بنقول «{ar}» بالإنجليزي؟", [en.capitalize()] + [x[1].capitalize() for x in wr])


# ---------- أمثال ----------
SAME_MEANING = [
    {"على نفسها", "جاجة حفرت"}, {"ابن الوز", "من شابه أباه"}, {"كل إناء", "كل ما في القدر"},
    {"عصفور باليد", "بيضة اليوم", "اللي بتعرفه"}, {"سبق السيف", "وصل", "في الصيف"}, {"أعطي الخبز لخبّازه", "أعطِ القوس"},
    {"الطيور على أشكالها", "كل غريب", "وافق شن"}, {"اللي بيته من زجاج", "الجمل ما بيشوف"}, {"لا تبيع جلد الدب", "لا تقول فول"},
    {"الشمس", "اللي ما بيشوف من الغربال"}, {"ما بيصح", "بكرا بيذوب التلج"}, {"اللي بيزرع", "كل شاة"}, {"ضربتين", "فوق الموت"},
    {"المصاري", "الصيت"}, {"اسمع كلام اللي بيبكّيك", "الحق"}, {"عند البطون", "الجوع"}, {"الكلب اللي بيعوي", "زي الطبل"},
    {"من برّا رخام", "ما كل ما يلمع"}, {"الأقارب", "دود الخل"}, {"يا داخل بين البصلة وقشرتها", "اللي بيتدخّل بما لا يعنيه"},
    {"الفاضي", "قلّة الشغل"}, {"أهل مكة", "ما بيحرث الأرض"}, {"الحاجة", "الشاطرة"}, {"الوقت", "لا تأجّل عمل اليوم", "اضرب الحديد"},
    {"كل تأخيرة", "خيرها"}, {"في التأني السلامة", "يا مستعجل"}, {"الدنيا", "يوم إلك"}, {"اتّقِ شرّ", "جزاء", "البير اللي بتشرب منه"},
    {"إذا كان الكلام من فضة", "خير الكلام"}, {"الصبر", "اللي بيصبر"}, {"اللي ما بيطول العنب", "اللي ما بيعرف يرقص"},
    {"العين", "الإيد اللي ما بتقدر تعضّها"}, {"حبل الكذب", "الكذب"}, {"البعيد عن العين", "الغايب عن العين"},
]


def same_group(a1, a2):
    return any(a1 in g and a2 in g for g in SAME_MEANING)


def proverbs(cats, Cat):
    c = get(cats, Cat, "proverbs", "أمثال شعبية", "🗣️")
    P = [(int(d), a, b, m) for d, a, b, m in rows("proverbs.txt")]
    mean_of = {x[3]: x[1] for x in P}
    for d, a, b, m in P:
        ends = [x[2] for x in P if x[2] != b and abs(len(x[2]) - len(b)) <= max(6, len(b) // 2)]
        wr = far_from(b, ends) or far_from(b, [x[2] for x in P if x[2] != b])
        if wr:
            c.add(d, f"كمّل المثل: «{a}...»", [b] + wr)
        wr = far_from(m, [x[3] for x in P if x[3] != m and not same_group(a, x[1])], max_overlap=0.2)
        if wr:
            c.add(min(4, d + 1), f"شو معنى المثل: «{a} {b}»؟", [m] + wr)
        full = f"{a} {b}"
        others = [f"{x[1]} {x[2]}" for x in P if x[1] != a and len(f"{x[1]} {x[2]}") <= 44]
        wr = far_from((d, a, b, m), [x for x in P if x[1] != a and not same_group(a, x[1]) and len(f"{x[1]} {x[2]}") <= 44], key=lambda x: x[3], max_overlap=0.2)
        if wr and len(full) <= 44:
            c.add(min(4, d + 1), f"أي مثل معناه: «{m}»؟", [full] + [f"{x[1]} {x[2]}" for x in wr])


# ---------- لهجات ----------
REGION = {"المصري": "nile", "السوداني": "nile", "المغربي": "maghreb", "الجزائري": "maghreb", "التونسي": "maghreb", "الليبي": "maghreb",
          "العراقي": "gulf", "الخليجي": "gulf", "الكويتي": "gulf", "الإماراتي": "gulf", "الحجازي (السعودي)": "gulf", "النجدي (السعودي)": "gulf",
          "السعودي": "gulf", "اليمني": "gulf", "اللبناني": "levant", "السوري": "levant", "الأردني": "levant"}
REGION_MAIN = {"nile": ["المصري", "السوداني"], "maghreb": ["المغربي", "الجزائري", "التونسي"], "gulf": ["العراقي", "الخليجي", "اليمني"],
               "levant": ["اللبناني", "السوري", "الأردني"]}


def bi(dl):
    return "بال" + dl[2:] if dl.startswith("ال") else "بـ" + dl


def dialects(cats, Cat):
    c = get(cats, Cat, "dialects", "لهجات عربية", "💬")
    D = [(int(d), w, dl, m) for d, w, dl, m in rows("dialects.txt")]
    for d, w, dl, m in D:
        mean_pool = [x[3] for x in D if x[3] != m]
        wr = far_from(m, mean_pool, max_overlap=0.2)
        if wr and dl != "الأردني":
            c.add(d, f"شو يعني «{w}» {bi(dl)}؟", [m] + wr)
        elif wr:
            c.add(d, f"شو يعني «{w}» بالأردني؟", [m] + wr)
        # العكس: كيف بيقولوها؟ الخيارات كلمات معناها مختلف
        alt = [x[1] for x in D if words(x[3]).isdisjoint(words(m)) and x[3] != m and x[1] != w]
        if len(alt) >= 3 and dl != "الأردني":
            c.add(min(4, d + 1), f"شو بيقولوا {bi(dl)} على «{m.split('،')[0]}»؟", [w] + R.sample(alt, 3))
        # من وين الكلمة؟ الخيارات من مناطق ثانية (عشان ما تكون الكلمة مستعملة عندهم كمان)
        reg = REGION.get(dl)
        if reg and dl != "الأردني":
            others = [R.choice(v) for k, v in REGION_MAIN.items() if k != reg]
            if len(others) == 3:
                c.add(min(4, d + 1), f"كلمة «{w}» بمعنى «{m.split('،')[0]}»، من أي لهجة؟", [dl.replace("الحجازي (السعودي)", "السعودي").replace("النجدي (السعودي)", "السعودي")] + others)


# ---------- كأس العالم ----------
TEAM_AR = {"Algeria": "الجزائر", "Angola": "أنغولا", "Argentina": "الأرجنتين", "Australia": "أستراليا", "Austria": "النمسا", "Belgium": "بلجيكا",
           "Bolivia": "بوليفيا", "Bosnia and Herzegovina": "البوسنة والهرسك", "Brazil": "البرازيل", "Bulgaria": "بلغاريا", "Cameroon": "الكاميرون",
           "Canada": "كندا", "Chile": "تشيلي", "China": "الصين", "Colombia": "كولومبيا", "Costa Rica": "كوستاريكا", "Croatia": "كرواتيا", "Cuba": "كوبا",
           "Czech Republic": "التشيك", "Czechoslovakia": "تشيكوسلوفاكيا", "Denmark": "الدنمارك", "Dutch East Indies": "جزر الهند الشرقية الهولندية",
           "East Germany": "ألمانيا الشرقية", "Ecuador": "الإكوادور", "Egypt": "مصر", "El Salvador": "السلفادور", "England": "إنجلترا", "France": "فرنسا",
           "Germany": "ألمانيا", "Ghana": "غانا", "Greece": "اليونان", "Haiti": "هايتي", "Honduras": "هندوراس", "Hungary": "المجر", "Iceland": "آيسلندا",
           "Iran": "إيران", "Iraq": "العراق", "Israel": "إسرائيل", "Italy": "إيطاليا", "Ivory Coast": "ساحل العاج", "Jamaica": "جامايكا", "Japan": "اليابان",
           "Kuwait": "الكويت", "Mexico": "المكسيك", "Morocco": "المغرب", "Netherlands": "هولندا", "New Zealand": "نيوزيلندا", "Nigeria": "نيجيريا",
           "North Korea": "كوريا الشمالية", "Northern Ireland": "أيرلندا الشمالية", "Norway": "النرويج", "Panama": "بنما", "Paraguay": "باراغواي",
           "Peru": "بيرو", "Poland": "بولندا", "Portugal": "البرتغال", "Qatar": "قطر", "Republic of Ireland": "أيرلندا", "Romania": "رومانيا",
           "Russia": "روسيا", "Saudi Arabia": "السعودية", "Scotland": "اسكتلندا", "Senegal": "السنغال", "Serbia": "صربيا",
           "Serbia and Montenegro": "صربيا والجبل الأسود", "Slovakia": "سلوفاكيا", "Slovenia": "سلوفينيا", "South Africa": "جنوب أفريقيا",
           "South Korea": "كوريا الجنوبية", "Soviet Union": "الاتحاد السوفيتي", "Spain": "إسبانيا", "Sweden": "السويد", "Switzerland": "سويسرا",
           "Togo": "توغو", "Trinidad and Tobago": "ترينيداد وتوباغو", "Tunisia": "تونس", "Turkey": "تركيا", "Ukraine": "أوكرانيا",
           "United Arab Emirates": "الإمارات", "United States": "أمريكا", "Uruguay": "الأوروغواي", "Wales": "ويلز", "West Germany": "ألمانيا الغربية",
           "Yugoslavia": "يوغوسلافيا", "Zaire": "زائير"}
HOST_AR = dict(TEAM_AR, **{"South Korea, Japan": "كوريا الجنوبية واليابان"})
LEGENDS = {"P-77939": "جوست فونتين", "P-07028": "شاندور كوتشيش", "P-08136": "هيلموت ران", "P-45310": "فافا", "P-49381": "أديمير",
           "P-09730": "ليونيداس", "P-56486": "غييرمو ستابيلي", "P-85778": "ريفيلينو", "P-49502": "لوثار ماتيوس", "P-46080": "غارينشا",
           "P-12676": "فيرينتس بوشكاش", "P-38164": "ماريو زاغالو", "P-25829": "كارلوس ألبيرتو", "P-38873": "خوان ألبيرتو سكيافينو",
           "P-65885": "سيلفيو بيولا", "P-35736": "فالكاو", "P-96621": "أماريلدو", "P-07171": "هارالد شوماخر", "P-34233": "مارتن بيترز",
           "P-18523": "أوسكار ميغيز", "P-63184": "هانز شيفر", "P-05766": "ماكس مورلوك"}
AWARD_Q = {"Golden Boot": ("مين هدّاف كأس العالم {y}؟", 2), "Golden Ball": ("مين أخذ جائزة أفضل لاعب (الكرة الذهبية) بكأس العالم {y}؟", 2),
           "Golden Glove": ("مين أخذ جائزة أفضل حارس بكأس العالم {y}؟", 3), "Best Young Player": ("مين أخذ جائزة أفضل لاعب شاب بكأس العالم {y}؟", 3),
           "Silver Ball": ("مين أخذ الكرة الفضية (ثاني أفضل لاعب) بكأس العالم {y}؟", 4), "Silver Boot": ("مين أخذ الحذاء الفضي (ثاني هدّاف) بكأس العالم {y}؟", 4)}
STAGE_AR = {"final": "النهائي", "semi-finals": "نص النهائي", "quarter-finals": "ربع النهائي", "round of 16": "دور الـ16", "third-place match": "مباراة المركز الثالث"}


def strip(s):
    return "".join(ch for ch in unicodedata.normalize("NFD", s or "") if unicodedata.category(ch) != "Mn").lower().strip()


def worldcup(cats, Cat):
    c = get(cats, Cat, "worldcup", "كأس العالم", "🏆")
    W = json.loads((DATA / "worldcup.json").read_text(encoding="utf-8"))
    PL = json.loads((ROOT / "docs" / "games" / "players.json").read_text(encoding="utf-8"))["players"]
    byname = {strip(p["n"]): p["a"] for p in PL if p.get("n") and p.get("a")}

    def pname(pid):
        if pid in LEGENDS:
            return LEGENDS[pid]
        p = W["players"].get(pid)
        if not p:
            return None
        g = "" if p["g"] == "not applicable" else p["g"]
        return byname.get(strip(f"{g} {p['f']}".strip())) or (byname.get(strip(p["f"])) if not g else None)

    year = {t["tournament_id"]: int(t["year"]) for t in W["tournaments"]}
    G = defaultdict(list)
    for g in W["goals"]:
        G[g["match_id"]].append(g)
    era = defaultdict(list)
    for g in W["goals"]:
        nm = pname(g["player_id"])
        if nm and g["own_goal"] == "0":
            era[nm].append(year[g["tournament_id"]])
    T = sorted(W["tournaments"], key=lambda t: int(t["year"]))
    winners = [TEAM_AR.get(t["winner"], t["winner"]) for t in T]
    champs = sorted(set(winners))
    big = ["البرازيل", "ألمانيا", "إيطاليا", "الأرجنتين", "فرنسا", "إنجلترا", "إسبانيا", "هولندا", "الأوروغواي", "ألمانيا الغربية", "كرواتيا", "البرتغال"]
    hosts_all = sorted({HOST_AR.get(t["host_country"], t["host_country"]) for t in T})
    pos = defaultdict(dict)
    for s in W["standings"]:
        pos[s["tournament_id"]][int(s["position"])] = TEAM_AR.get(s["team_name"], s["team_name"])
    for t in T:
        y, tid = int(t["year"]), t["tournament_id"]
        w = TEAM_AR.get(t["winner"], t["winner"])
        d = 1 if y >= 1998 else 2 if y >= 1970 else 3
        bigy = [x for x in big if x != w and x != ("ألمانيا" if y < 1991 else "ألمانيا الغربية")]
        c.add(d, f"مين فاز بكأس العالم {y}؟", [w] + R.sample(bigy, 3))
        h = HOST_AR.get(t["host_country"], t["host_country"])
        c.add(min(4, d + (0 if y >= 1990 else 1)), f"وين انلعب كأس العالم {y}؟", [h] + R.sample([x for x in hosts_all if x != h and h not in x and x not in h], 3))
        if 2 in pos[tid]:
            ru = pos[tid][2]
            c.add(min(4, d + 1), f"مين خسر نهائي كأس العالم {y}؟", [ru] + R.sample([x for x in bigy if x not in (ru, w)], 3))
        if 3 in pos[tid]:
            th = pos[tid][3]
            c.add(min(4, d + 2), f"مين أخذ المركز الثالث بكأس العالم {y}؟", [th] + R.sample([x for x in big + ["السويد", "بولندا", "تركيا", "المغرب", "بلجيكا"]
                                                                                              if x not in (th, w, pos[tid].get(2))], 3))
    # كم مرة فاز؟ وأول مرة؟
    one = lambda x: "ألمانيا" if x == "ألمانيا الغربية" else x
    cnt = Counter(one(w) for w in winners)
    for team, n in cnt.items():
        firsty = min(int(t["year"]) for t in T if one(TEAM_AR.get(t["winner"])) == team)
        opts = sorted({n, n + 1, max(1, n - 1), n + 2} - {0})
        while len(opts) < 4:
            opts.append(max(opts) + 1)
        c.add(2 if team in ("البرازيل", "الأرجنتين", "فرنسا") else 3, f"كم مرة فاز منتخب {team} بكأس العالم (لحد 2022)؟" + (" (مع ألقاب ألمانيا الغربية)" if team == "ألمانيا" else ""),
              [str(n)] + [str(x) for x in opts if x != n][:3])
        ys = sorted({int(t["year"]) for t in T} - {firsty}, key=lambda x: abs(x - firsty))[:6]
        c.add(3, f"بأي سنة فاز منتخب {team} بكأس العالم لأول مرة؟", [str(firsty)] + [str(x) for x in R.sample(ys, 3)])
    # جوائز
    aw = defaultdict(list)
    for a in W["awards"]:
        aw[a["award_name"]].append(a)
    for name, (tpl, d) in AWARD_Q.items():
        lst = [(year[a["tournament_id"]], pname(a["player_id"])) for a in aw[name] if a["shared"] == "0"]
        lst = [(y, n) for y, n in lst if n]
        pool = [n for _, n in lst]
        for y, n in lst:
            near = [x for yy, x in lst if x != n and abs(yy - y) <= 16]
            near += [x for x, ys in era.items() if x != n and x not in near and any(abs(v - y) <= 4 for v in ys)][:8]
            wr = (R.sample(near, 3) if len(near) >= 3 else None) or R.sample([x for x in pool if x != n], 3)
            c.add(min(4, d + (1 if y < 1970 else 0)), tpl.format(y=y), [n] + wr)
    # الهدافين التاريخيين
    goals = Counter(g["player_id"] for g in W["goals"] if g["own_goal"] == "0")
    KNOWN = {"P-77939", "P-07028", "P-12676", "P-46080", "P-09730", "P-45310"}
    top = [(pid, n) for pid, n in goals.most_common(80) if pname(pid) and (pid in KNOWN or pid not in LEGENDS)]
    tnames = [pname(pid) for pid, _ in top]
    for pid, n in top[:40]:
        nm = pname(pid)
        opts = sorted({n - 2, n - 1, n + 1, n + 2} - {n}, key=lambda x: R.random())[:3]
        c.add(3 if n >= 10 else 4, f"كم هدف سجّل {nm} بكؤوس العالم كلها (لحد 2022)؟", [str(n)] + [str(x) for x in opts if x > 0][:3])
    c.add(2, "مين الهدّاف التاريخي لكأس العالم (16 هدف)؟", ["ميروسلاف كلوزه", "رونالدو", "غيرد مولر", "جوست فونتين"])
    # المباريات الكبيرة: النتيجة، ومين أقصى مين، ومين سجّل بالنهائي
    PART = defaultdict(set)
    for m in W["matches"]:
        for k in ("home_team_name", "away_team_name"):
            if TEAM_AR.get(m[k]):
                PART[year[m["tournament_id"]]].add(TEAM_AR[m[k]])
    TEAM_ERA = defaultdict(list)   # الهدافين مع منتخباتهم
    for g in W["goals"]:
        nm = pname(g["player_id"])
        if nm and g["own_goal"] == "0":
            TEAM_ERA[TEAM_AR.get(g["player_team_name"], "")].append((nm, year[g["tournament_id"]]))
    KO_AT = {"semi-finals": "بنص النهائي", "quarter-finals": "بربع النهائي", "round of 16": "بدور الـ16"}
    ARABT = ("المغرب", "السعودية", "تونس", "الجزائر", "مصر", "قطر", "العراق", "الكويت", "الإمارات")

    def result(h, a, hs, as_, pen=None):
        if hs == as_:
            return f"تعادل {hs}-{as_}" + (f" وفاز {pen} بالترجيح" if pen else "")
        return f"فوز {h if hs > as_ else a} {max(hs, as_)}-{min(hs, as_)}"

    for m in W["matches"]:
        st = m["stage_name"]
        y = year[m["tournament_id"]]
        h, a = TEAM_AR.get(m["home_team_name"]), TEAM_AR.get(m["away_team_name"])
        if not h or not a:
            continue
        hs, as_ = int(m["home_team_score"]), int(m["away_team_score"])
        arab = h in ARABT or a in ARABT
        bigm = h in big or a in big
        ko = st in STAGE_AR
        if not (st == "final" or (ko and bigm and y >= 1970) or (arab and y >= 1970)):
            continue
        pen = None
        if m["penalty_shootout"] == "1":
            try:
                pen = h if int(m["home_team_score_penalties"]) > int(m["away_team_score_penalties"]) else a
            except Exception:
                pen = None
        right = result(h, a, hs, as_, pen)
        alts = set()
        for dh, da in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (2, 0), (0, 2)):
            x, z = hs + dh, as_ + da
            if x >= 0 and z >= 0:
                alts.add(result(h, a, x, z))
        alts.add(result(h, a, as_, hs))
        alts.discard(right)
        alts = [x for x in alts if not (hs == as_ and x.startswith("تعادل") and str(hs) in x)]
        stage = STAGE_AR.get(st, "دور المجموعات")
        d = 2 if (st == "final" and y >= 1994) or (arab and y >= 2018) else 3 if st in ("final", "semi-finals") or arab else 4
        if len(alts) >= 3:
            c.add(d, f"شو كانت نتيجة {h} و{a} ({stage}، كأس العالم {y})؟", [right] + R.sample(sorted(alts), 3))
        if st in KO_AT:
            win = pen if hs == as_ else (h if hs > as_ else a)
            lose = a if win == h else h
            if win and (lose in big or lose in ARABT):
                pool = sorted(PART[y] - {win, lose})
                if len(pool) >= 3:
                    c.add(2 if y >= 2010 else 3, f"مين أقصى {lose} {KO_AT[st]} بكأس العالم {y}؟", [win] + R.sample(pool, 3))
        if st == "final":
            sc = {pname(g["player_id"]) for g in G[m["match_id"]] if g["own_goal"] == "0"} - {None}
            for nm in sc:
                near = sorted({x for t in (h, a) for x, yy in TEAM_ERA[t] if x not in sc and abs(yy - y) <= 12})
                if len(near) < 3:
                    near = [x for x, ys in era.items() if x not in sc and any(abs(yy - y) <= 8 for yy in ys)]
                if len(near) >= 3:
                    c.add(3, f"مين سجّل بنهائي كأس العالم {y} ({h} ضد {a})؟", [nm] + R.sample(near, 3))
    # عدد المنتخبات المشاركة
    for t in T:
        n = int(t["count_teams"])
        yy = int(t["year"])
        choices = (13, 14, 15, 16, 24) if yy < 1982 else (16, 24, 32, 20) if yy < 1998 else (24, 32, 36, 48)
        c.add(4 if yy < 1998 else 3, f"كم منتخب شارك بكأس العالم {yy}؟", [str(n)] + [str(x) for x in R.sample([v for v in choices if v != n], 3)])
    # مين ما فاز ولا مرة؟
    never = ["هولندا", "البرتغال", "بلجيكا", "كرواتيا", "المكسيك", "السويد", "المجر", "تشيكوسلوفاكيا", "الدنمارك", "كولومبيا"]
    for x in never:
        c.add(2, "أي منتخب من هدول عمره ما فاز بكأس العالم (لحد 2022)؟", [x] + R.sample(["البرازيل", "ألمانيا", "إيطاليا", "الأرجنتين", "فرنسا", "إسبانيا", "إنجلترا", "الأوروغواي"], 3))
    for x in ["إنجلترا", "إسبانيا", "فرنسا", "الأوروغواي", "الأرجنتين", "إيطاليا"]:
        c.add(2, "أي منتخب من هدول فاز بكأس العالم؟", [x] + R.sample(never, 3))
    # حقائق ثابتة
    facts = [
        (1, "أي دولة فازت بكأس العالم أكثر شي؟", "البرازيل", ["ألمانيا", "إيطاليا", "الأرجنتين"]),
        (1, "مين فاز بكأس العالم 2022 بقطر؟", "الأرجنتين", ["فرنسا", "كرواتيا", "المغرب"]),
        (1, "أي منتخب عربي وصل نص نهائي كأس العالم 2022؟", "المغرب", ["تونس", "السعودية", "قطر"]),
        (2, "مين فازت عليه السعودية 2-1 بكأس العالم 2022؟", "الأرجنتين", ["البرازيل", "فرنسا", "ألمانيا"]),
        (2, "بأي سنة انلعب أول كأس عالم؟", "1930", ["1920", "1934", "1950"]),
        (2, "وين انلعب أول كأس عالم سنة 1930؟", "الأوروغواي", ["البرازيل", "إيطاليا", "فرنسا"]),
        (2, "كم منتخب شارك بكأس العالم 2022؟", "32", ["24", "48", "36"]),
        (1, "كم منتخب رح يشارك بكأس العالم 2026؟", "48", ["32", "40", "64"]),
        (1, "مين الدول اللي استضافت كأس العالم 2026؟", "أمريكا وكندا والمكسيك", ["أمريكا لحالها", "كندا والمكسيك", "أمريكا والبرازيل"]),
        (1, "أي منتخب عربي تأهل لكأس العالم 2026 لأول مرة بتاريخه؟", "الأردن", ["العراق", "الإمارات", "عُمان"]),
        (2, "كم مرة انلعب كأس العالم بالوطن العربي لحد 2022؟", "مرة وحدة (قطر 2022)", ["ولا مرة", "مرتين", "ثلاث مرات"]),
        (2, "مين أول منتخب عربي يفوز بمباراة بكأس العالم؟", "تونس (1978)", ["المغرب (1986)", "الجزائر (1982)", "السعودية (1994)"]),
        (3, "مين أول منتخب عربي وأفريقي يتصدّر مجموعته بكأس العالم؟", "المغرب (1986)", ["الجزائر (1982)", "تونس (1978)", "مصر (1990)"]),
        (2, "أي منتخب عربي فاز على ألمانيا الغربية بكأس العالم 1982؟", "الجزائر", ["المغرب", "تونس", "الكويت"]),
        (3, "مين سجّل هدف السعودية الشهير بمرمى بلجيكا بكأس العالم 1994؟", "سعيد العويران", ["سامي الجابر", "ماجد عبدالله", "فهد الغشيان"]),
        (2, "مين الحارس المغربي اللي تألق بكأس العالم 2022؟", "ياسين بونو", ["منير المحمدي", "بادو الزاكي", "أنس الزنيتي"]),
        (1, "مين قائد الأرجنتين اللي رفع كأس العالم 2022؟", "ليونيل ميسي", ["دي ماريا", "أوتاميندي", "مارتينيز"]),
        (2, "مين سجّل هاتريك بنهائي كأس العالم 2022؟", "كيليان مبابي", ["ليونيل ميسي", "أوليفييه جيرو", "أنخيل دي ماريا"]),
        (2, "مين حارس الأرجنتين بطل كأس العالم 2022؟", "إيميليانو مارتينيز", ["فرانكو أرماني", "سيرجيو روميرو", "خيرونيمو رولي"]),
        (2, "كم مرة فاز بيليه بكأس العالم؟", "3", ["2", "1", "4"]),
        (3, "مين اللاعب الوحيد اللي فاز بكأس العالم كلاعب ومدرب وكابتن؟", "فرانز بيكنباور", ["ديدييه ديشامب", "ماريو زاغالو", "يوهان كرويف"]),
        (2, "مين مدرب فرنسا بطل كأس العالم 2018؟", "ديدييه ديشامب", ["زين الدين زيدان", "لوران بلان", "أرسين فينغر"]),
        (2, "مين نطح ماتيراتزي بنهائي كأس العالم 2006؟", "زين الدين زيدان", ["تيري هنري", "فرانك ريبيري", "باتريك فييرا"]),
        (2, "مين سجّل هدف «يد الله» بكأس العالم 1986؟", "دييغو مارادونا", ["بيليه", "ماريو كيمبس", "غاري لينيكر"]),
        (2, "مين سجّل هدف فوز إسبانيا بنهائي 2010؟", "أندريس إنييستا", ["دافيد فيا", "تشافي", "فرناندو توريس"]),
        (2, "مين سجّل هدف ألمانيا بنهائي 2014 ضد الأرجنتين؟", "ماريو غوتزه", ["توماس مولر", "ميروسلاف كلوزه", "أندريه شورله"]),
        (2, "قديش انتهت مباراة البرازيل وألمانيا بنص نهائي 2014؟", "1-7 لألمانيا", ["0-3 لألمانيا", "2-1 للبرازيل", "1-4 لألمانيا"]),
        (3, "شو اسم كرة كأس العالم 2022؟", "الرحلة", ["جابولاني", "برازوكا", "تيلستار"]),
        (3, "شو اسم تميمة كأس العالم 2022؟", "لعيب", ["زاكومي", "فوليكو", "زابيفاكا"]),
        (3, "أي ملعب استضاف نهائي كأس العالم 2022؟", "استاد لوسيل", ["استاد البيت", "استاد خليفة الدولي", "استاد الثمامة"]),
        (3, "مين أكثر لاعب لعب مباريات بكأس العالم (لحد 2022)؟", "ليونيل ميسي", ["لوثار ماتيوس", "ميروسلاف كلوزه", "كريستيانو رونالدو"]),
        (3, "مين أول لاعب سجّل بخمس نسخ من كأس العالم؟", "كريستيانو رونالدو", ["ليونيل ميسي", "بيليه", "ميروسلاف كلوزه"]),
        (2, "أي منتخب فاز بكأس العالم 2018؟", "فرنسا", ["كرواتيا", "بلجيكا", "إنجلترا"]),
        (3, "مين خسر نهائي كأس العالم 2018؟", "كرواتيا", ["بلجيكا", "إنجلترا", "الأرجنتين"]),
        (3, "كم منتخب عربي شارك بكأس العالم 2022؟", "4", ["3", "5", "2"]),
        (4, "مين المنتخبات العربية اللي شاركت بكأس العالم 2022؟", "قطر والسعودية وتونس والمغرب", ["قطر والسعودية ومصر والمغرب",
                                                                                                "السعودية وتونس والجزائر والمغرب", "قطر والعراق وتونس والمغرب"]),
        (3, "مين فاز على تونس 1-0 بكأس العالم 2022؟", "تونس فازت على فرنسا 1-0", ["فرنسا فازت 1-0", "تعادلوا 1-1", "أستراليا فازت 2-0"]),
        (2, "مين أقصى إسبانيا والبرتغال بكأس العالم 2022؟", "المغرب", ["فرنسا", "كرواتيا", "البرازيل"]),
        (3, "بأي سنة شاركت مصر لأول مرة بكأس العالم؟", "1934", ["1990", "1950", "2018"]),
        (4, "مين أول منتخب عربي شارك بكأس العالم؟", "مصر (1934)", ["المغرب (1970)", "تونس (1978)", "الكويت (1982)"]),
        (3, "بأي كأس عالم شاركت الكويت؟", "1982", ["1986", "1990", "1978"]),
        (3, "بأي كأس عالم شارك العراق؟", "1986", ["1982", "1990", "1994"]),
        (3, "بأي كأس عالم شاركت الإمارات؟", "1990", ["1986", "1994", "1998"]),
        (2, "بأي سنة وصلت السعودية لدور الـ16 بكأس العالم؟", "1994", ["1998", "2002", "2018"]),
    ]
    for d, q, a, w in facts:
        c.add(d, q, [a] + w)


# ---------- إسلامية: القرآن ----------
DISPUTED = {13, 22, 47, 55, 57, 61, 64, 76, 83, 98, 99, 110, 112, 113, 114}


def quran(cats, Cat):
    c = get(cats, Cat, "islamic", "إسلامية", "🕌")
    S = json.loads((DATA / "surahs.json").read_text(encoding="utf-8"))
    by_n = {s["n"]: s for s in S}
    names = [s["ar"] for s in S]
    famous = {1, 2, 3, 4, 5, 6, 7, 9, 10, 12, 18, 19, 20, 24, 36, 55, 56, 67, 78, 93, 94, 97, 103, 108, 109, 110, 111, 112, 113, 114, 17, 31, 32, 48, 49, 62, 63, 71, 72, 73, 74, 96, 105, 106, 107}
    for s in S:
        n, nm, v = s["n"], s["ar"], s["v"]
        d = 1 if n in (1, 2, 112, 113, 114, 36, 18, 67, 108, 103) else 2 if n in famous else 3 if n <= 30 or n >= 78 else 4
        near = [x for x in range(max(1, n - 4), min(114, n + 4) + 1) if x != n]
        if len(near) < 5:
            near = [x for x in range(max(1, n - 6), min(114, n + 6) + 1) if x != n]
        c.add(min(4, d + 1), f"شو ترتيب سورة {nm} بالمصحف؟", [str(n)] + [str(x) for x in R.sample(near, 3)])
        c.add(min(4, d + 1), f"شو اسم السورة رقم {n} بالمصحف؟", [nm] + [by_n[x]["ar"] for x in R.sample(near, 3)])
        if n < 114:
            nxt = by_n[n + 1]["ar"]
            c.add(min(4, d + 1), f"شو السورة اللي بتيجي بعد سورة {nm}؟", [nxt] + [by_n[x]["ar"] for x in R.sample([y for y in near if y != n + 1], 3)])
        vs = sorted({v - 3, v - 2, v - 1, v + 1, v + 2, v + 3} - {v, 0}) if v < 20 else sorted({v - 10, v - 5, v + 5, v + 10, v - 8, v + 8})
        vs = [x for x in vs if x > 0]
        if n in famous or v <= 20:
            c.add(min(4, d + (0 if v <= 10 else 1)), f"كم آية بسورة {nm}؟", [str(v)] + [str(x) for x in R.sample(vs, 3)])
        if n not in DISPUTED:
            same = [x for x in S if x["place"] != s["place"] and x["n"] not in DISPUTED]
            others = [x["ar"] for x in S if x["place"] == s["place"] and x["n"] != n and x["n"] not in DISPUTED]
            if s["place"] == "مدنية":
                c.add(min(4, d + 1), "أي سورة من هدول مدنية؟", [nm] + R.sample([x["ar"] for x in S if x["place"] == "مكية" and x["n"] not in DISPUTED and x["n"] in famous], 3))
            elif n in famous:
                c.add(min(4, d + 1), "أي سورة من هدول مكية؟", [nm] + R.sample([x["ar"] for x in S if x["place"] == "مدنية" and x["n"] not in DISPUTED], 3))
    facts = [
        (1, "كم سورة بالقرآن الكريم؟", "114", ["110", "120", "100"]), (1, "شو أطول سورة بالقرآن؟", "البقرة", ["آل عمران", "النساء", "الأعراف"]),
        (1, "شو أقصر سورة بالقرآن؟", "الكوثر", ["الإخلاص", "العصر", "النصر"]), (1, "شو أول سورة بالمصحف؟", "الفاتحة", ["البقرة", "العلق", "الناس"]),
        (1, "شو آخر سورة بالمصحف؟", "الناس", ["الفلق", "الإخلاص", "المسد"]), (2, "شو أول سورة نزلت (أول آيات نزلت)؟", "العلق", ["الفاتحة", "المدثر", "القلم"]),
        (2, "أي سورة ما بتبلّش بالبسملة؟", "التوبة", ["الأنفال", "النمل", "الفاتحة"]), (2, "أي سورة فيها البسملة مرتين؟", "النمل", ["التوبة", "البقرة", "الفاتحة"]),
        (2, "شو السورة اللي بتسمّى «قلب القرآن»؟", "يس", ["الفاتحة", "الرحمن", "الملك"]), (2, "شو السورة اللي بتسمّى «عروس القرآن»؟", "الرحمن", ["يس", "مريم", "الواقعة"]),
        (2, "شو السورة اللي بتسمّى «أم الكتاب»؟", "الفاتحة", ["البقرة", "الإخلاص", "يس"]), (2, "أي سورة بتعدل ثلث القرآن؟", "الإخلاص", ["الفاتحة", "الكوثر", "يس"]),
        (2, "أي سورة بتنقرأ يوم الجمعة؟", "الكهف", ["يس", "الملك", "مريم"]), (2, "أي سورة اسمها على اسم امرأة؟", "مريم", ["النساء", "النور", "الحجرات"]),
        (2, "كم جزء بالقرآن الكريم؟", "30", ["60", "20", "114"]), (2, "كم حزب بالقرآن الكريم؟", "60", ["30", "120", "40"]),
        (3, "كم آية بالقرآن الكريم (بعدّ حفص)؟", "6236", ["6666", "6000", "6348"]), (2, "أطول آية بالقرآن هي آية...", "الدَّين (البقرة 282)", ["الكرسي", "النور", "الإسراء"]),
        (2, "أعظم آية بالقرآن هي آية...", "الكرسي", ["الدَّين", "النور", "البسملة"]), (3, "بأي سورة آية الكرسي؟", "البقرة", ["آل عمران", "النساء", "الكهف"]),
        (3, "كم سورة مدنية بالقرآن (حسب المصحف المتداول)؟", "28", ["86", "14", "40"]), (2, "شو السورة اللي بتنقرأ قبل النوم وبتنجّي من عذاب القبر؟", "الملك", ["يس", "الكهف", "الواقعة"]),
        (3, "شو السورة اللي سمّيت على اسم معدن؟", "الحديد", ["الذهب", "النحاس", "الفضة"]), (3, "أي سورة من هدول اسمها على اسم حشرة؟", "النمل", ["الفيل", "البقرة", "الأنعام"]),
        (3, "أي حيوان من هدول إله سورة باسمه؟", "الفيل", ["الحصان", "الجمل", "الأسد"]),
        (2, "أي نبي إله سورة باسمه؟", "يوسف", ["موسى", "عيسى", "سليمان"]), (3, "كم مرة انذكر اسم محمد ﷺ بالقرآن؟", "4", ["5", "3", "25"]),
        (3, "مين النبي اللي انذكر اسمه أكثر شي بالقرآن؟", "موسى", ["إبراهيم", "عيسى", "نوح"]), (2, "مين الصحابي الوحيد اللي انذكر اسمه بالقرآن؟", "زيد بن حارثة", ["أبو بكر الصديق", "عمر بن الخطاب", "علي بن أبي طالب"]),
        (2, "أي سورة فيها قصة أصحاب الكهف؟", "الكهف", ["يس", "مريم", "طه"]), (2, "أي سورة فيها قصة يوسف كاملة؟", "يوسف", ["هود", "القصص", "طه"]),
        (3, "أي سورة فيها قصة البقرة اللي أمر الله بني إسرائيل يذبحوها؟", "البقرة", ["الأعراف", "طه", "المائدة"]),
        (3, "أي سورة بتسمّى «سورة المائدة» على اسم...", "المائدة اللي نزلت على أصحاب عيسى", ["مائدة الرسول ﷺ", "مائدة إبراهيم", "مائدة سليمان"]),
    ]
    for d, q, a, w in facts:
        if w and all(w):
            c.add(d, q, [a] + w)


# ---------- ألغاز: سلاسل أرقام + مين الغريب ----------
def sequences(cats, Cat):
    c = get(cats, Cat, "riddles", "قصص وألغاز", "🧩")
    rnd = random.Random(77)

    def add(d, seq, ans, spread=None):
        spread = spread or max(2, abs(ans) // 6 + 1)
        cand = {ans + k for k in (-2 * spread, -spread, spread, 2 * spread, spread + 1, -spread - 1)} - {ans}
        opts = [str(x) for x in rnd.sample(sorted(cand), 3)]
        c.add(d, "كمّل السلسلة: " + "، ".join(map(str, seq)) + "، ...؟", [str(ans)] + opts)

    for a in range(1, 30, 2):
        for step in (2, 3, 5, 10):
            if rnd.random() < 0.5:
                s = [a + step * i for i in range(5)]
                add(1, s[:4], s[4], step)
    for a in (1, 2, 3, 5):
        for r in (2, 3):
            s = [a * r ** i for i in range(6)]
            add(2, s[:4], s[4])
    for k in range(1, 9):
        s = [(k + i) ** 2 for i in range(5)]
        add(2, s[:4], s[4])
    for a, b in ((1, 1), (2, 3), (1, 3), (3, 4), (2, 5), (1, 4)):
        s = [a, b]
        while len(s) < 7:
            s.append(s[-1] + s[-2])
        add(3, s[:5], s[5])
    for a in (2, 5, 10, 3, 7, 4):
        s = [a]
        for i in range(1, 6):
            s.append(s[-1] + i)
        add(3, s[:5], s[5])
        s = [a]
        for i in range(1, 6):
            s.append(s[-1] * 2 + 1)
        add(4, s[:4], s[4])
        s = [a, a + 3, a + 1, a + 4, a + 2, a + 5, a + 3]
        add(4, s[:6], s[6], 1)
    for k in (1, 2, 3):
        s = [(k + i) ** 3 for i in range(5)]
        add(4, s[:4], s[4])
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    for i in range(0, 6):
        add(4, primes[i:i + 5], primes[i + 5], 1)


def odd_one_out(cats, Cat):
    c = get(cats, Cat, "riddles", "قصص وألغاز", "🧩")
    W = [(int(d), en, ar, g) for d, en, ar, g in rows("words.txt")]
    by = defaultdict(list)
    for w in W:
        if "(" not in w[2] and " " not in w[2]:
            by[w[3]].append(w)
    NAME = {"food": "أكل", "animal": "حيوانات", "body": "أعضاء جسم", "home": "أغراض بيت", "nature": "طبيعة", "color": "ألوان", "family": "قرايب",
            "job": "مهن", "place": "أماكن", "transport": "مواصلات", "verb": "أفعال", "adj": "صفات", "time": "وقت", "school": "أغراض مدرسة",
            "clothes": "أواعي", "sport": "كورة", "tech": "تكنولوجيا"}
    groups = [g for g in by if len(by[g]) >= 6 and g not in ("verb", "adj")]
    rnd = random.Random(5)
    used = Counter()
    AMBIG = [{"clothes", "sport"}, {"nature", "place"}, {"home", "school"}, {"tech", "school"}, {"tech", "home"}, {"food", "nature"},
             {"animal", "nature"}, {"family", "job"}, {"transport", "place"}, {"time", "nature"}, {"school", "job"}, {"sport", "place"}]
    for i in range(1200):
        g1, g2 = rnd.sample(groups, 2)
        if {g1, g2} in AMBIG:
            continue
        three = rnd.sample(by[g1], 3)
        odd = rnd.choice(by[g2])
        if used[odd[2]] >= 2:
            continue
        d = max(1, min(4, round(sum(x[0] for x in three + [odd]) / 4)))
        if c.add(d, "مين الغريب بينهم؟", [odd[2]] + [x[2] for x in three]):
            used[odd[2]] += 1


# ---------- ألغاز أيام ووقت وأعمار (مولّدة ومحسوبة) ----------
DAYS = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
MONTHS = ["كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران", "تموز", "آب", "أيلول", "تشرين الأول", "تشرين الثاني", "كانون الأول"]


def logic_puzzles(cats, Cat):
    c = get(cats, Cat, "riddles", "قصص وألغاز", "🧩")
    rnd = random.Random(31)
    REL = [(-1, "مبارح"), (-2, "أول مبارح"), (1, "بكرا"), (2, "بعد بكرا")]
    for i, today in enumerate(DAYS):
        for off, word in REL:
            known = DAYS[(i + off) % 7]
            for off2, word2 in REL:
                if off2 == off:
                    continue
                ans = DAYS[(i + off2) % 7]
                wr = [d for d in DAYS if d != ans]
                d = 2 if abs(off) + abs(off2) <= 2 else 3
                c.add(d, f"إذا {word} كان {known}، شو {word2}؟" if off < 0 else f"إذا {word} {known}، شو {word2}؟", [ans] + rnd.sample(wr, 3))
    for i, m in enumerate(MONTHS):
        for k in (3, 5, 7):
            ans = MONTHS[(i + k) % 12]
            c.add(3 if k == 3 else 4, f"إذا هسّا شهر {m}، شو الشهر بعد {k} شهور؟", [ans] + rnd.sample([x for x in MONTHS if x != ans], 3))
    for h in range(1, 13):
        for add_h in (5, 10, 15, 30):
            ans = (h + add_h - 1) % 12 + 1
            c.add(2 if add_h < 12 else 3, f"الساعة هسّا {h}، كم بتصير الساعة بعد {add_h} ساعة؟ (على الساعة العادية 1-12)",
                  [str(ans)] + [str(x) for x in rnd.sample([v for v in range(1, 13) if v != ans], 3)])
    male, female = ["أحمد", "خالد", "عمر", "يزن"], ["سارة", "ليلى", "رنا", "دانا"]
    yrs = lambda n: "سنة" if n == 1 else "سنتين" if n == 2 else f"{n} سنين" if n <= 10 else f"{n} سنة"
    for _ in range(90):
        a, b = rnd.sample(male + female, 2)
        kid, mult, after = rnd.randint(3, 12), rnd.choice([2, 3]), rnd.choice([2, 5, 10])
        ans = kid * mult + after
        now_ = kid * mult
        wr = [x for x in dict.fromkeys([now_, ans + 1, ans - 1, kid + after, ans + 2]) if x != ans and x > 0][:3]
        her = "عمرها" if b in female else "عمره"
        c.add(3, f"عمر {a} {'ضعف' if mult == 2 else 'ثلاث أضعاف'} عمر {b}، و{b} {her} {yrs(kid)}. قديش رح يصير عمر {a} بعد {yrs(after)}؟",
              [str(ans)] + [str(x) for x in wr])

    # بعد كم يوم / قبل كم يوم
    for i, today in enumerate(DAYS):
        unit = lambda n: "يومين" if n == 2 else f"{n} أيام" if n <= 10 else f"{n} يوم"
        for n in (3, 4, 5, 8, 9, 10, 12, 15, 20, 30, 100):
            ans = DAYS[(i + n) % 7]
            c.add(2 if n <= 5 else 3 if n <= 15 else 4, f"إذا اليوم {today}، شو رح يكون اليوم بعد {unit(n)}؟", [ans] + rnd.sample([x for x in DAYS if x != ans], 3))
        for n in (2, 3, 6, 8, 10, 14, 21):
            ans = DAYS[(i - n) % 7]
            c.add(2 if n <= 3 else 3 if n <= 10 else 2, f"إذا اليوم {today}، شو كان اليوم قبل {unit(n)}؟", [ans] + rnd.sample([x for x in DAYS if x != ans], 3))
    # عدّ المصاري
    for _ in range(160):
        a, b, k = rnd.randint(1, 6), rnd.randint(1, 6), rnd.choice([(5, 10), (10, 20), (1, 5), (20, 50)])
        ans = a * k[0] + b * k[1]
        wr = [v for v in dict.fromkeys([ans + k[0], ans - k[0], ans + k[1], (a + b) * k[1], a * k[1] + b * k[0]]) if v != ans and v > 0][:3]
        if len(wr) == 3:
            c.add(2 if ans <= 40 else 3, f"معك {a} ورقات فئة {k[0]} دنانير و{b} ورقات فئة {k[1]}. قديش معك بالمجموع؟", [str(ans)] + [str(v) for v in wr])
    # حزازير أرقام: عدد إذا ضربته بكذا وضفت كذا...
    for _ in range(420):
        x, a, b = rnd.randint(2, 15), rnd.randint(2, 6), rnd.randint(1, 12)
        y = x * a + b
        offs = rnd.sample([-3, -2, -1, 1, 2, 3, 4], 5)
        wr = [v for v in dict.fromkeys([x + o for o in offs]) if v != x and v > 0][:3]
        c.add(2 if x < 8 and a <= 3 else 3, f"عدد إذا ضربته بـ{a} وضفتله {b} بيصير {y}. شو هو؟", [str(x)] + [str(v) for v in wr])
    # سلاسل حروف (الترتيب الهجائي)
    AB = list("أبتثجحخدذرزسشصضطظعغفقكلمنهوي")
    for step in (1, 2, 3):
        for st in range(0, len(AB) - 5 * step, 2):
            seq = AB[st:st + 5 * step:step]
            if len(seq) < 5:
                continue
            ans = seq[4]
            wr = [ch for ch in AB if ch != ans and abs(AB.index(ch) - AB.index(ans)) <= 3][:6]
            c.add(2 if step == 1 else 3 if step == 2 else 4, "كمّل السلسلة: " + "، ".join(seq[:4]) + "، ...؟ (حسب ترتيب الحروف أ ب ت)",
                  [ans] + rnd.sample(wr, 3))
    for _ in range(60):
        n = rnd.choice([3, 4, 5, 6])
        legs = rnd.choice([(2, "جاجات"), (4, "خواريف")])
        m = rnd.choice([2, 3, 4, 5])
        ans = n * legs[0] + m * (4 if legs[0] == 2 else 2)
        other = "خواريف" if legs[0] == 2 else "جاجات"
        c.add(3, f"بالمزرعة {n} {legs[1]} و{m} {other}. كم رجل بالمجموع؟", [str(ans)] + [str(x) for x in rnd.sample([ans - 2, ans + 2, ans + 4, ans - 4, (n + m) * 4, (n + m) * 2], 4) if x != ans][:3])


# ---------- ألقاب ----------
NICK_Q = {"player": ("مين اللاعب اللي لقبه «{n}»؟", "شو لقب اللاعب {w}؟"), "club": ("أي نادي لقبه «{n}»؟", "شو لقب نادي {w}؟"),
          "team": ("أي منتخب لقبه «{n}»؟", "شو لقب {w}؟"), "place": ("شو المكان اللي لقبه «{n}»؟", "شو لقب {w}؟"),
          "history": ("مين الشخصية التاريخية اللي لقبها «{n}»؟", "شو لقب {w}؟"), "art": ("مين الفنان/الأديب اللي لقبه «{n}»؟", "شو لقب {w}؟"),
          "animal": ("أي حيوان لقبه «{n}»؟", "شو لقب {w}؟"), "space": ("أي كوكب لقبه «{n}»؟", "شو لقب كوكب {w}؟")}


def nicknames(cats, Cat):
    c = get(cats, Cat, "nicknames", "ألقاب", "🏷️")
    N = [(int(d), n, w, t) for d, n, w, t in rows("nicknames.txt")]
    for d, n, w, t in N:
        same = [x for x in N if x[3] == t]
        holders = sorted({x[2] for x in same if x[2] != w})
        nicks = sorted({x[1] for x in same if x[2] != w and x[1] != n})
        if len(holders) >= 3:
            q1, q2 = NICK_Q[t]
            c.add(d, q1.format(n=n), [w] + R.sample(holders, 3))
            if len(nicks) >= 3:
                c.add(min(4, d + 1), q2.format(w=w), [n] + R.sample(nicks, 3))


def generate(cats, Cat):
    translate(cats, Cat)
    proverbs(cats, Cat)
    dialects(cats, Cat)
    worldcup(cats, Cat)
    quran(cats, Cat)
    sequences(cats, Cat)
    odd_one_out(cats, Cat)
    logic_puzzles(cats, Cat)
    nicknames(cats, Cat)
