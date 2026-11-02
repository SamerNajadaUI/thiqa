#!/usr/bin/env python3
"""
قسم "كرة قدم" بلعبة الرقم الأقرب: آلاف الأسئلة اللي جوابها رقم، من بيانات حقيقية.

- لاعبين مشهورين (عرب وعالميين): سنة الميلاد، سنة الانضمام لنادي، كم سنة لعب معه، أهدافه ومبارياته بالدوري،
  مبارياته وأهدافه الدولية، طوله، رقم قميصه، عمره لما انضم لنادي كبير، كأس العالم ودوري الأبطال.
- أندية مشهورة: سنة التأسيس، سعة الملعب، كم مرة فازت بدوري الأبطال.
- كأس العالم: أهداف كل نسخة، عدد المنتخبات، الهدافين، المستضيفين، النهائيات.
- أسئلة مكتوبة بالإيد عن ميسي ورونالدو والعرب والأردن.

بيتشغّل من engine/players.py، وبيكتب docs/games/football_q.json
"""
from __future__ import annotations

import json
import random
import re
import time
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "games" / "football_q.json"

# ---------------------------------------------------------------- كأس العالم (أرقام ثابتة)
WC = [  # سنة، المستضيف، البطل، أهداف البطولة، عدد المنتخبات، أهداف النهائي
    (1930, "الأوروغواي", "الأوروغواي", 70, 13, 6), (1934, "إيطاليا", "إيطاليا", 70, 16, 3), (1938, "فرنسا", "إيطاليا", 84, 15, 6),
    (1950, "البرازيل", "الأوروغواي", 88, 13, 3), (1954, "سويسرا", "ألمانيا الغربية", 140, 16, 5), (1958, "السويد", "البرازيل", 126, 16, 7),
    (1962, "تشيلي", "البرازيل", 89, 16, 4), (1966, "إنجلترا", "إنجلترا", 89, 16, 6), (1970, "المكسيك", "البرازيل", 95, 16, 5),
    (1974, "ألمانيا الغربية", "ألمانيا الغربية", 97, 16, 3), (1978, "الأرجنتين", "الأرجنتين", 102, 16, 4), (1982, "إسبانيا", "إيطاليا", 146, 24, 4),
    (1986, "المكسيك", "الأرجنتين", 132, 24, 5), (1990, "إيطاليا", "ألمانيا الغربية", 115, 24, 1), (1994, "الولايات المتحدة", "البرازيل", 141, 24, 0),
    (1998, "فرنسا", "فرنسا", 171, 32, 3), (2002, "كوريا الجنوبية واليابان", "البرازيل", 161, 32, 2), (2006, "ألمانيا", "إيطاليا", 147, 32, 2),
    (2010, "جنوب إفريقيا", "إسبانيا", 145, 32, 1), (2014, "البرازيل", "ألمانيا", 171, 32, 1), (2018, "روسيا", "فرنسا", 169, 32, 6),
    (2022, "قطر", "الأرجنتين", 172, 32, 6),
]
WC_TOP = {  # سنة: (الهداف، أهدافه)
    1930: ("غييرمو ستابيلي", 8), 1934: ("أولدريخ نيدلي", 5), 1938: ("ليونيداس", 7), 1954: ("ساندور كوتشيش", 11),
    1958: ("جوست فونتين", 13), 1966: ("أوزيبيو", 9), 1970: ("غيرد مولر", 10), 1974: ("غجيغوج لاتو", 7), 1978: ("ماريو كيمبس", 6),
    1982: ("باولو روسي", 6), 1986: ("غاري لينيكر", 6), 1990: ("سالفاتوري سكيلاتشي", 6), 1998: ("دافور شوكر", 6),
    2002: ("رونالدو البرازيلي", 8), 2006: ("ميروسلاف كلوزه", 5), 2014: ("خاميس رودريغيز", 6), 2018: ("هاري كين", 6), 2022: ("كيليان مبابي", 8),
}

HAND = [
    # ميسي ورونالدو
    ["كم كرة ذهبية فاز فيها ميسي؟", 8, "كرات", "رقم قياسي"],
    ["كم كرة ذهبية فاز فيها كريستيانو رونالدو؟", 5, "كرات", ""],
    ["كم هدف سجّل ميسي مع برشلونة بكل البطولات؟", 672, "هدف", "الهداف التاريخي للنادي"],
    ["كم هدف سجّل كريستيانو رونالدو مع ريال مدريد بكل البطولات؟", 450, "هدف", "الهداف التاريخي للنادي"],
    ["كم مباراة لعب ميسي مع برشلونة بكل البطولات؟", 778, "مباراة", ""],
    ["كم سنة لعب ميسي مع الفريق الأول ببرشلونة؟", 17, "سنة", "من 2004 لـ2021"],
    ["كم سنة لعب رونالدو مع ريال مدريد؟", 9, "سنين", "من 2009 لـ2018"],
    ["كم هدف رسمي وصل رونالدو لما احتفل بهدفه التاريخي سنة 2024؟", 900, "هدف", "أول لاعب بيوصلها"],
    ["كم مرة فاز ميسي بكوبا أمريكا لحد 2024؟", 2, "مرتين", "2021 و2024"],
    ["كم كأس عالم شارك فيها ميسي لحد 2022؟", 5, "بطولات", ""],
    ["بكم كأس عالم سجّل رونالدو؟", 5, "بطولات", "أول لاعب بيسجل بخمس نسخ"],
    ["كم كان عمر ميسي لما فاز بكأس العالم 2022؟", 35, "سنة", ""],
    ["بأي سنة انتقل رونالدو لنادي النصر السعودي؟", 2023, "", "كانون الثاني"],
    ["بأي سنة انتقل ميسي لإنتر ميامي؟", 2023, "", ""],
    ["كم مليون يورو كانت صفقة رونالدو من مانشستر يونايتد لريال مدريد سنة 2009؟", 94, "مليون يورو", "كانت الأغلى بالعالم وقتها"],
    ["كم مليون يورو كانت صفقة نيمار من برشلونة لباريس سان جيرمان؟", 222, "مليون يورو", "الأغلى بالتاريخ"],
    ["كم هدف سجّل ميسي بسنة 2012؟", 91, "هدف", "رقم قياسي بسنة وحدة"],
    ["كم هدف سجّل رونالدو بموسم 2014–15 مع ريال مدريد بكل البطولات؟", 61, "هدف", ""],
    ["كم مرة فاز رونالدو بدوري أبطال أوروبا؟", 5, "مرات", "1 مع مانشستر يونايتد و4 مع ريال مدريد"],
    ["كم مرة فاز ميسي بدوري أبطال أوروبا؟", 4, "مرات", "كلها مع برشلونة"],
    # كأس العالم والهدافين
    ["كم هدف سجّل ميروسلاف كلوزه بكؤوس العالم كلها؟", 16, "هدف", "الهداف التاريخي"],
    ["كم هدف سجّل ميسي بكأس العالم 2022؟", 7, "أهداف", ""],
    ["كم منتخب رح يشارك بكأس العالم 2026؟", 48, "منتخب", "أول مرة بـ48"],
    ["كم دولة مستضيفة لكأس العالم 2026؟", 3, "دول", "أمريكا وكندا والمكسيك"],
    ["كم هدف انسجل بأكبر فوز بتاريخ كأس العالم (المجر على السلفادور 1982)؟", 10, "أهداف", "10–1"],
    ["كم هدف سجّل أوليغ سالينكو بمباراة وحدة بكأس العالم 1994؟", 5, "أهداف", "رقم قياسي لمباراة"],
    ["كم كانت نتيجة ألمانيا على البرازيل بنصف نهائي 2014 (أهداف ألمانيا)؟", 7, "أهداف", "7–1"],
    ["كم كان عمر بيليه لما فاز بأول كأس عالم؟", 17, "سنة", "1958"],
    ["كم كأس عالم فاز فيها بيليه كلاعب؟", 3, "مرات", "1958 و1962 و1970"],
    ["كم هدف سجّل مارادونا بكأس العالم 1986؟", 5, "أهداف", "ومنهم هدف اليد"],
    ["بأي سنة سجّل مارادونا هدف اليد المشهور؟", 1986, "", "على إنجلترا"],
    ["بأي سنة نطح زيدان ماتيراتزي بنهائي كأس العالم؟", 2006, "", ""],
    # العرب
    ["بأي سنة وصل المغرب لنصف نهائي كأس العالم؟", 2022, "", "أول منتخب عربي وإفريقي"],
    ["بأي سنة فازت السعودية على الأرجنتين بكأس العالم؟", 2022, "", "2–1"],
    ["بأي سنة سجّل سعيد العويران هدفه التاريخي على بلجيكا بكأس العالم؟", 1994, "", ""],
    ["بأي سنة شاركت مصر أول مرة بكأس العالم؟", 1934, "", "أول منتخب عربي وإفريقي"],
    ["كم مرة شاركت مصر بكأس العالم لحد 2022؟", 3, "مرات", "1934 و1990 و2018"],
    ["كم مرة شاركت السعودية بكأس العالم لحد 2022؟", 6, "مرات", ""],
    ["كم مرة شارك المغرب بكأس العالم لحد 2022؟", 6, "مرات", ""],
    ["كم مرة شاركت تونس بكأس العالم لحد 2022؟", 6, "مرات", ""],
    ["بأي سنة فازت الجزائر بأول كأس أمم إفريقيا إلها؟", 1990, "", ""],
    ["كم مرة فازت مصر بكأس أمم إفريقيا؟", 7, "مرات", "أكثر منتخب"],
    ["كم مرة فازت قطر بكأس آسيا لحد 2024؟", 2, "مرتين", "2019 و2023"],
    ["كم مرة فاز العراق بكأس آسيا؟", 1, "مرة", "2007"],
    ["كم مرة فاز الأهلي المصري بدوري أبطال إفريقيا لحد 2025؟", 12, "مرة", ""],
    ["كم مرة فاز الهلال السعودي بدوري أبطال آسيا؟", 4, "مرات", ""],
    ["كم مباراة متتالية فاز فيها الهلال السعودي برقمه القياسي العالمي سنة 2023؟", 34, "مباراة", ""],
    ["كم هدف سجّل محمد صلاح بالدوري الإنجليزي بموسم 2017–18؟", 32, "هدف", "رقم قياسي وقتها لموسم من 38 مباراة"],
    ["كم مرة فاز محمد صلاح بلقب هداف الدوري الإنجليزي لحد 2025؟", 4, "مرات", ""],
    # الأردن
    ["بأي سنة وصل منتخب الأردن لنهائي كأس آسيا؟", 2024, "", "بطولة كأس آسيا 2023 بقطر"],
    ["بأي سنة تأهل منتخب الأردن لكأس العالم لأول مرة؟", 2025, "", "لنسخة 2026"],
    ["كم هدف انسجل بنهائي كأس آسيا بين الأردن وقطر (المجموع)؟", 4, "أهداف", "قطر 3 والأردن 1"],
    ["بأي سنة تأسس نادي الفيصلي الأردني؟", 1932, "", ""],
    ["بأي سنة تأسس نادي الوحدات؟", 1956, "", ""],
    ["كم مرة وصل الأردن لربع نهائي كأس آسيا قبل 2023؟", 2, "مرتين", "2004 و2011"],
    ["بأي سنة سجّل الأردن أول مشاركة إله بكأس آسيا؟", 2004, "", "ووصل لربع النهائي"],
    # عام
    ["كم مرة فاز ريال مدريد بدوري أبطال أوروبا لحد 2024؟", 15, "مرة", "أكثر نادي"],
    ["كم نقطة جمع مانشستر سيتي بالدوري الإنجليزي موسم 2017–18؟", 100, "نقطة", "رقم قياسي"],
    ["كم مباراة لعب آرسنال بدون خسارة بموسم 2003–04 بالدوري؟", 38, "مباراة", ""],
    ["كم هدف سجّل هالاند بالدوري الإنجليزي بأول موسم إله؟", 36, "هدف", "رقم قياسي"],
    ["كم هدف سجّل آلن شيرر بالدوري الإنجليزي الممتاز؟", 260, "هدف", "الهداف التاريخي"],
    ["كم هدف سجّل كريستيانو رونالدو بدوري أبطال أوروبا؟", 140, "هدف", "الهداف التاريخي"],
    ["كم هدف سجّل ليفاندوفسكي بالدوري الألماني بموسم 2020–21؟", 41, "هدف", "رقم قياسي"],
    ["كم هدف سجّل ليفاندوفسكي ضد فولفسبورغ بـ9 دقائق سنة 2015؟", 5, "أهداف", ""],
    ["كم سنة درّب أليكس فيرغسون مانشستر يونايتد؟", 26, "سنة", "من 1986 لـ2013"],
    ["كم لقب دوري إنجليزي فاز فيه فيرغسون مع مانشستر يونايتد؟", 13, "لقب", ""],
    ["كم مرة فاز كارلو أنشيلوتي بدوري أبطال أوروبا كمدرب؟", 5, "مرات", "رقم قياسي"],
    ["كم لاعب بيكونوا بقائمة المنتخب بكأس العالم 2022؟", 26, "لاعب", ""],
    ["كم ثانية بتاخذ أسرع هدف بتاريخ كأس العالم (هاكان شكور 2002)؟", 11, "ثانية", "10.8 ثانية"],
]


def _clean(x):
    return re.sub(r"\s*\([^)]*\)\s*$", "", x or "").strip()


def _al(name: str) -> str:
    """"لـ" قبل الاسم: لنادي، للأهلي..."""
    if not name:
        return name
    if name.startswith("ال"):
        return "لل" + name[2:]
    return ("ل" if re.match(r"[\u0600-\u06FF]", name) else "لـ") + name


def _nt(name):
    x = re.sub(r"\s*(الوطني\s*)?لكرة القدم.*$", "", _clean(name))
    x = re.sub(r"\s+للرجال$", "", x).strip()
    return x if x.startswith("منتخب") else "منتخب " + x


def build(raw: dict, ids: list[str], col: dict, wins: dict, team_names: dict, is_youth, sparql, qid, v, year, log, NOW_YEAR: int) -> None:
    rnd = random.Random(2026)
    qs: list[list] = []
    seen = set()

    def add(q, a, unit="", note=""):
        if a is None or q in seen:
            return
        if isinstance(a, float) and a.is_integer():
            a = int(a)
        seen.add(q)
        qs.append([q, a, unit, note])

    for q in HAND:
        add(*q)

    # ---------------- كأس العالم
    first_win = {}
    for y, host, champ, goals, teams, final in WC:
        add(f"كم هدف انسجل بكأس العالم {y} كلها؟", goals, "هدف", f"بـ{host}")
        add(f"كم منتخب شارك بكأس العالم {y}؟", teams, "منتخب", f"بـ{host}")
        add(f"كم هدف انسجل بنهائي كأس العالم {y} (المجموع)؟", final, "أهداف", f"والبطل {champ}")
        first_win.setdefault(champ, y)
        if y in WC_TOP:
            n, g = WC_TOP[y]
            add(f"كم هدف سجّل {n}، هداف كأس العالم {y}؟", g, "أهداف", "")
    hosts = defaultdict(list)
    for y, host, *_ in WC:
        hosts[host].append(y)
    for host, ys in hosts.items():
        add(f"بأي سنة استضافت {host} كأس العالم{' أول مرة' if len(ys) > 1 else ''}؟", ys[0], "", "")
    for champ, y in first_win.items():
        add(f"بأي سنة فازت {champ} بكأس العالم لأول مرة؟", y, "", "")
    champs = defaultdict(int)
    for _, _, c, *_ in WC:
        champs["ألمانيا" if c == "ألمانيا الغربية" else c] += 1
    for c, n in champs.items():
        add(f"كم مرة فازت {c} بكأس العالم{' (مع ألمانيا الغربية)' if c == 'ألمانيا' else ''}؟", n, "مرات" if n > 2 else "", "")

    # ---------------- اللاعبين
    arab_ids = [i for i, links in col.get("arabs", []) if links >= 20][:400]
    famous = list(dict.fromkeys(ids[:1700] + arab_ids))
    famous = [i for i in famous if i in raw]
    squads = col.get("squads", {})

    # شهرة الأندية: كم لاعب من الأشهر (أول 600) لعب فيها. هيك الأندية الكبيرة بتطلع والدوريات المغمورة لا
    elite = set(ids[:600])
    club_fame = defaultdict(int)
    for pid in famous:
        for t in {t["t"] for t in raw[pid]["teams"] if not t["nat"] and not is_youth(t)}:
            if pid in elite:
                club_fame[t] += 1
    # الأندية اللي أغلب لاعبينها من شرق آسيا (الدوري الياباني مثلاً) مش معروفة عندنا، فبنستثنيها
    far_east = ("اليابان", "كوريا", "الصين")
    club_players = defaultdict(list)
    for pid in famous:
        for t in {t["t"] for t in raw[pid]["teams"] if not t["nat"] and not is_youth(t)}:
            club_players[t].append(pid)
    def east_share(t):
        ps = club_players.get(t, [])
        if not ps:
            return 0
        n = sum(1 for pid in ps if any(any(k in x for k in far_east) for x in (raw[pid].get("sport_nat") or raw[pid].get("nat") or [])))
        return n / len(ps)
    big_club = {t for t, n in club_fame.items() if n >= 6 and east_share(t) < 0.5}
    ok_club = {t for t, n in club_fame.items() if n >= 3 and east_share(t) < 0.5}
    arab_set = set(arab_ids)
    # الأندية العربية المعروفة: لعب فيها 4 لاعبين عرب مشهورين أو أكثر
    arab_club = defaultdict(int)
    for pid in arab_ids:
        if pid in raw:
            for t in {t["t"] for t in raw[pid]["teams"] if not t["nat"] and not is_youth(t)}:
                arab_club[t] += 1
    known_arab_club = {t for t, n in arab_club.items() if n >= 4}
    rank = {pid: k for k, pid in enumerate(famous)}

    per_cands = []
    for pid in famous:
        p = raw[pid]
        name = _clean(p.get("ar"))
        if not name or not re.search(r"[\u0600-\u06FF]", name):
            continue
        clubs_all = [t for t in p["teams"] if not is_youth(t) and not t["nat"]]
        # بس لاعبين معروفين: لعب بنادي كبير، أو لاعب عربي
        if pid not in arab_set and not any(t["t"] in big_club for t in clubs_all):
            continue
        by = p.get("by")
        if by and by < 1950 and rank.get(pid, 9999) > 300:   # لاعبين قدام كثير: بس المشاهير
            continue
        spells = [t for t in p["teams"] if not is_youth(t)]
        clubs = [t for t in spells if not t["nat"] and t["ar"]]
        nts = [t for t in spells if t["nat"] and t["ar"]]
        gk = any("goalkeeper" in x for x in (p.get("pos_en") or []))
        cand = []
        if by and by >= 1940:
            cand.append((f"بأي سنة انولد {name}؟", by, "", ""))
        if p.get("h") and 160 <= p["h"] <= 205:
            cand.append((f"كم طول {name} بالسنتيمتر؟", p["h"], "سم", ""))
        dist = list(dict.fromkeys(_clean(t["ar"]) for t in sorted(clubs, key=lambda t: t["s"] or 9999)))
        if len(dist) >= 3:
            cand.append((f"مع كم نادي لعب {name} بمسيرته؟", len(dist), "أندية", "، ".join(dist[:5]) + ("…" if len(dist) > 5 else "")))
        firsts = {}
        for t in sorted(clubs, key=lambda t: t["s"] or 9999):
            firsts.setdefault(t["t"], t)
        joins = []
        for t in firsts.values():
            cname = _clean(t["ar"])
            if not t["s"] or not (t["t"] in ok_club or (pid in arab_set and t["t"] in known_arab_club)):
                continue
            joins.append((f"بأي سنة انضم {name} {_al(cname)}؟", t["s"], "", f"وضل فيه لحد {t['e']}" if t["e"] else "ولسا فيه"))
            if t["e"] and t["e"] - t["s"] >= 2:
                cand.append((f"كم سنة لعب {name} مع {cname}؟", t["e"] - t["s"], "سنين", f"من {t['s']} لـ{t['e']}"))
            if by and t["t"] in big_club and 15 <= t["s"] - by <= 38:
                cand.append((f"كم كان عمر {name} لما انضم {_al(cname)}؟", t["s"] - by, "سنة", f"سنة {t['s']}"))
        rnd.shuffle(joins)
        cand.extend(joins[:2])
        for t in clubs:
            cname = _clean(t["ar"])
            if t["t"] not in ok_club and t["t"] not in known_arab_club:
                continue   # أرقام بأندية مغمورة: صعبة وما بتهم حدا
            if t.get("goals") and 10 <= t["goals"] <= 700 and not gk:
                cand.append((f"كم هدف سجّل {name} بالدوري مع {cname}؟", t["goals"], "هدف", f"في {t['apps']} مباراة" if t.get("apps") else ""))
            if t.get("apps") and 50 <= t["apps"] <= 800:
                cand.append((f"كم مباراة لعب {name} بالدوري مع {cname}؟", t["apps"], "مباراة", f"من {t['s']}" if t["s"] else ""))
            if t.get("num") and (t["t"] in ok_club or pid in arab_set):
                cand.append((f"شو رقم قميص {name} مع {cname}؟", t["num"], "", ""))
        for t in nts:
            ntn = _nt(t["ar"])
            if t.get("apps") and 20 <= t["apps"] <= 250:
                cand.append((f"كم مباراة دولية لعب {name} مع {ntn}؟", t["apps"], "مباراة", f"وسجّل {t['goals']} هدف" if t.get("goals") else ""))
            if t.get("goals") and 10 <= t["goals"] <= 150:
                cand.append((f"كم هدف دولي سجّل {name} مع {ntn}؟", t["goals"], "هدف", ""))
        sq = squads.get(pid)
        if sq and sq.get("num"):
            cand.append((f"شو رقم قميص {name} مع {sq['club_ar']} هلأ؟", sq["num"], "", ""))
        nt_ids = {t["t"] for t in nts}
        wc = sorted({y for ev, (team, y) in wins["wc"].items() if ev in p.get("events", set()) and team in nt_ids})
        if len(wc) == 1:
            cand.append((f"بأي سنة فاز {name} بكأس العالم؟", wc[0], "", ""))
        last_end = max((t["e"] for t in clubs if t["e"]), default=None)
        open_spell = any(t["e"] is None and (t["s"] or 0) >= 2010 for t in clubs)
        if last_end and not open_spell and not p.get("dy") and by and by < NOW_YEAR - 36 and last_end - by >= 30:
            cand.append((f"بأي سنة لعب {name} آخر موسم إله كمحترف؟", last_end, "", ""))
        rnd.shuffle(cand)
        per_cands.append((rank.get(pid, 9999), cand))

    # الأشهر بياخذ أسئلة أكثر، وبنزيد لحد ما نوصل 7500 سؤال بالمجموع
    weight = lambda r: 2 if r < 300 else 1.4 if r < 900 else 1
    per_player = 0
    for base in range(4, 14):
        if sum(min(len(c), int(base * weight(r))) for r, c in per_cands) >= 7500:
            break
    cap = base
    for r, cand in per_cands:
        for c in cand[:int(cap * weight(r))]:
            before = len(qs)
            add(*c)
            per_player += len(qs) - before
    log(f"  لاعبين بالأسئلة: {len(per_cands)}، لحد {cap} سؤال لكل لاعب")

    # ---------------- الأندية: تأسيس، ملعب، دوري الأبطال
    top_clubs = sorted(big_club, key=lambda t: -club_fame[t])[:300]
    ucl = defaultdict(int)
    for team, _y in wins["ucl"]:
        ucl[team] += 1
    info = {}
    for i in range(0, len(top_clubs), 60):
        vals = " ".join("wd:" + c for c in top_clubs[i:i + 60])
        try:
            for b in sparql(f"""SELECT ?t ?inc ?cap ?va WHERE {{ VALUES ?t {{ {vals} }}
                OPTIONAL {{ ?t wdt:P571 ?inc }}
                OPTIONAL {{ ?t wdt:P115 ?ven. ?ven wdt:P1083 ?cap. OPTIONAL {{ ?ven rdfs:label ?va FILTER(LANG(?va)="ar") }} }} }}""", tries=2):
                d = info.setdefault(qid(v(b, "t")), {})
                if v(b, "inc") and "inc" not in d:
                    d["inc"] = year(v(b, "inc"))
                if v(b, "cap") and "cap" not in d:
                    try:
                        d["cap"] = int(float(v(b, "cap"))); d["venue"] = v(b, "va")
                    except ValueError:
                        pass
        except SystemExit:
            log("  ما زبط جلب معلومات الأندية لهالدفعة")
        time.sleep(1)
    for t in top_clubs:
        cname = _clean(team_names.get(t))
        if not cname or not re.search(r"[؀-ۿ]", cname):
            continue
        d = info.get(t, {})
        if d.get("inc") and 1850 <= d["inc"] <= 2015:
            add(f"بأي سنة تأسس {cname}؟", d["inc"], "", "")
        if d.get("cap") and 5000 <= d["cap"] <= 130000:
            add(f"كم متفرج بيتسع ملعب {cname}{(' (' + _clean(d['venue']) + ')') if d.get('venue') else ''}؟", d["cap"], "متفرج", "")
        if ucl.get(t):
            add(f"كم مرة فاز {cname} بدوري أبطال أوروبا (أو كأس أوروبا للأندية)؟", ucl[t], "مرات" if ucl[t] > 2 else "", "")

    OUT.write_text(json.dumps({"generated": time.strftime("%Y-%m-%d"), "questions": qs}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"football_q.json: {len(qs)} سؤال ({per_player} عن اللاعبين، {OUT.stat().st_size // 1024} KB)")
