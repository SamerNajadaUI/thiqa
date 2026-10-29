#!/usr/bin/env python3
"""
بيانات لعبة "تحدي الأصحاب" (docs/games/party.json)

- اللاعبين الحاليين: كل تشكيلة كل نادي بـ8 دوريات (الخمس الكبرى + التركي + الأمريكي + السعودي).
  التشكيلة الحالية من ESPN (مين بيلعب بالنادي هلأ، ورقم القميص والمركز)، والتفاصيل من Wikidata
  (الاسم بالعربي، المنتخب، المسيرة، كأس العالم ودوري الأبطال، الزملاء).
- المعتزلين: أشهر المعتزلين، ومعهم المعتزلين العرب.
- لكل لاعب: زملاء مشهورين لعب معهم (بالنادي أو المنتخب) ومدربين مشهورين دربوه، للتلميح الأخير.

بيتشغّل من engine/players.py (بيستعمل نفس البيانات اللي جابها من Wikidata).
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "games" / "party.json"

# (ESPN، صفحة ويكيبيديا الإنجليزية، الاسم بالعربي)
LEAGUES = [
    ("eng.1", "Premier League", "الدوري الإنجليزي"),
    ("esp.1", "La Liga", "الدوري الإسباني"),
    ("ita.1", "Serie A", "الدوري الإيطالي"),
    ("ger.1", "Bundesliga", "الدوري الألماني"),
    ("fra.1", "Ligue 1", "الدوري الفرنسي"),
    ("tur.1", "Süper Lig", "الدوري التركي"),
    ("usa.1", "Major League Soccer", "الدوري الأمريكي"),
    ("ksa.1", "Saudi Pro League", "الدوري السعودي"),
]
ARAB_LEAGUE = "Q7172"
STOP = {"fc", "cf", "afc", "sc", "ac", "as", "ss", "ssc", "us", "sv", "vfb", "vfl", "tsg", "fsv", "club", "de", "cd",
        "ud", "rcd", "ca", "rc", "sd", "sfc", "fk", "sk", "jk", "bk", "calcio", "football", "futbol", "the", "and",
        "spor", "kulubu", "ogc", "losc", "sl"}
COUNTRY_FIX = {  # أسماء ESPN اللي مش دول بالمعنى الرسمي
    "England": "إنجلترا", "Scotland": "إسكتلندا", "Wales": "ويلز", "Northern Ireland": "أيرلندا الشمالية",
    "USA": "الولايات المتحدة", "United States": "الولايات المتحدة", "Korea Republic": "كوريا الجنوبية",
    "South Korea": "كوريا الجنوبية", "Ivory Coast": "ساحل العاج", "Côte d'Ivoire": "ساحل العاج",
    "Türkiye": "تركيا", "Turkey": "تركيا", "DR Congo": "الكونغو الديمقراطية", "Congo DR": "الكونغو الديمقراطية",
    "Czechia": "التشيك", "Czech Republic": "التشيك", "Bosnia-Herzegovina": "البوسنة والهرسك",
    "Bosnia and Herzegovina": "البوسنة والهرسك", "Curacao": "كوراساو", "Curaçao": "كوراساو",
    "Cape Verde": "الرأس الأخضر", "Cape Verde Islands": "الرأس الأخضر", "Kosovo": "كوسوفو",
}
POS_AR = {"gk": "حارس مرمى", "df": "مدافع", "mf": "لاعب وسط", "fw": "مهاجم"}


try:
    from unidecode import unidecode
except ImportError:  # محلياً بدونها
    def unidecode(x):
        return x


def norm_tokens(name: str) -> list[str]:
    x = unidecode(unicodedata.normalize("NFKD", name or ""))
    x = "".join(c for c in x if not unicodedata.combining(c)).lower()
    x = x.replace("ø", "o").replace("ß", "ss").replace("ı", "i").replace("ł", "l").replace("đ", "d")
    return [t for t in re.split(r"[^a-z]+", x) if t]


def club_tokens(name: str) -> set[str]:
    return {t for t in norm_tokens(name) if t not in STOP and len(t) > 1}


def pos_cat(labels: list[str] | None) -> str | None:
    x = " ".join(labels or []).lower()
    if "goalkeeper" in x:
        return "gk"
    if "midfield" in x:
        return "mf"
    if "defen" in x or "back" in x or "sweeper" in x:
        return "df"
    if "forward" in x or "wing" in x or "striker" in x or "attack" in x:
        return "fw"
    return None


def espn_pos(a: dict) -> str | None:
    p = a.get("position") or {}
    name = (p.get("name") or p.get("displayName") or "").lower()
    ab = (p.get("abbreviation") or "").upper()
    if "goal" in name or ab in ("G", "GK"):
        return "gk"
    if "defen" in name or ab in ("D", "CD", "LB", "RB", "CB"):
        return "df"
    if "mid" in name or ab in ("M", "CM", "DM", "AM"):
        return "mf"
    if "forward" in name or "attack" in name or ab in ("F", "FW", "ST", "LW", "RW"):
        return "fw"
    return None


def name_match(espn_names: list[str], wd_name: str) -> int:
    """درجة التطابق بين اسم ESPN واسم Wikidata (0 = ما في)."""
    w = norm_tokens(wd_name)
    if not w:
        return 0
    best = 0
    for en in espn_names:
        e = norm_tokens(en)
        if not e:
            continue
        if e == w:
            return 3
        if set(w) <= set(e) or set(e) <= set(w):
            best = max(best, 2)
        elif e[-1] == w[-1] and e[0][0] == w[0][0]:
            best = max(best, 1)
    return best


# ---------------------------------------------------------------- collect

def collect(sparql, qid, v, year, get_json, log, espn_base: str) -> dict:
    """بيرجع: squads {wd_id: info}، espn_only [info]، arabs [(id, links)]، countries {en: ar}."""
    # الدوريات من صفحات ويكيبيديا الإنجليزية
    titles = " ".join(json.dumps(t) + "@en" for _, t, _ in LEAGUES)
    lg_q = {}
    for b in sparql(f"""SELECT ?l ?t WHERE {{ VALUES ?t {{ {titles} }}
        ?a schema:about ?l; schema:isPartOf <https://en.wikipedia.org/>; schema:name ?t }}"""):
        lg_q[v(b, "t")] = qid(v(b, "l"))
    log(f"  دوريات Wikidata: {len(lg_q)}/{len(LEAGUES)}")

    # أندية كل دوري، دوري دوري، وبعدين أسماءها البديلة
    clubs = defaultdict(dict)  # league qid -> club qid -> {en, ar, toks}
    for lq in lg_q.values():
        try:
            rows = sparql(f"""SELECT DISTINCT ?club ?en ?ar WHERE {{ ?club wdt:P118 wd:{lq}.
                FILTER NOT EXISTS {{ ?club wdt:P31 wd:Q5 }}
                OPTIONAL {{ ?club rdfs:label ?en FILTER(LANG(?en)="en") }}
                OPTIONAL {{ ?club rdfs:label ?ar FILTER(LANG(?ar)="ar") }} }}""", tries=3)
        except SystemExit:
            log(f"  ما زبط جلب أندية {lq}")
            continue
        for b in rows:
            c = clubs[lq].setdefault(qid(v(b, "club")), {"en": v(b, "en"), "ar": v(b, "ar"), "names": set()})
            if v(b, "en"):
                c["names"].add(v(b, "en"))
        time.sleep(1)
    every = {cq: c for cs in clubs.values() for cq, c in cs.items()}
    ids_ = sorted(every)
    for i in range(0, len(ids_), 150):
        vals = " ".join("wd:" + c for c in ids_[i:i + 150])
        try:
            for b in sparql(f"""SELECT ?club ?al WHERE {{ VALUES ?club {{ {vals} }}
                ?club skos:altLabel ?al FILTER(LANG(?al)="en") }}""", tries=2):
                every[qid(v(b, "club"))]["names"].add(v(b, "al"))
        except SystemExit:
            log("  ما زبط جلب الأسماء البديلة")
        time.sleep(1)
    for c in every.values():
        c["toks"] = [club_tokens(n) for n in c["names"] if n]
    log(f"  أندية Wikidata: {len(every)}")
    time.sleep(1)

    countries = dict(COUNTRY_FIX)
    try:
        for b in sparql("""SELECT ?en ?ar WHERE { ?c wdt:P31 wd:Q6256.
            ?c rdfs:label ?en FILTER(LANG(?en)="en") ?c rdfs:label ?ar FILTER(LANG(?ar)="ar") }""", tries=3):
            countries.setdefault(v(b, "en"), v(b, "ar"))
    except SystemExit:
        log("  ما زبط جلب أسماء الدول")
    time.sleep(1)

    # تشكيلات ESPN ومطابقة كل فريق بنادي من Wikidata
    teams = []  # {lg_ar, espn_name, club, roster}
    for slug, title, lg_ar in LEAGUES:
        try:
            ts = get_json(f"{espn_base}/{slug}/teams")["sports"][0]["leagues"][0]["teams"]
        except Exception as e:
            log(f"  ESPN {slug}: {e}")
            continue
        cands = clubs.get(lg_q.get(title), {})
        for t in ts:
            t = t["team"]
            names = [t.get("displayName"), t.get("shortDisplayName"), t.get("name"), t.get("location")]
            et = [club_tokens(n) for n in names if n]
            best, score = None, 0.0
            for cq, c in cands.items():
                for ct in c["toks"]:
                    for e in et:
                        if ct and e:
                            j = len(ct & e) / len(ct | e)
                            if j > score:
                                best, score = cq, j
            try:
                roster = get_json(f"{espn_base}/{slug}/teams/{t['id']}/roster").get("athletes", [])
            except Exception:
                roster = []
            club = best if score >= 0.5 else None
            teams.append({"lg": lg_ar, "espn": t.get("displayName"), "club": club,
                          "club_ar": (cands[club]["ar"] if club else None) or t.get("displayName"), "roster": roster})
            if not club:
                log(f"  ما لقيت نادي Wikidata لـ {t.get('displayName')} ({slug})")
            time.sleep(0.2)
    log(f"  ESPN: {len(teams)} فريق، {sum(len(t['roster']) for t in teams)} لاعب")

    # لاعبين Wikidata المسجلين بهالأندية حالياً (أو لحد السنة الماضية)
    club_ids = sorted({t["club"] for t in teams if t["club"]})
    wd_by_club = defaultdict(list)
    for i in range(0, len(club_ids), 8):
        vals = " ".join("wd:" + c for c in club_ids[i:i + 8])
        try:
            rows = sparql(f"""SELECT ?p ?club ?en WHERE {{ VALUES ?club {{ {vals} }}
            ?p p:P54 ?s. ?s ps:P54 ?club. OPTIONAL {{ ?s pq:P582 ?end }}
            FILTER(!BOUND(?end) || YEAR(?end) >= YEAR(NOW()) - 1)
            ?p wdt:P106 wd:Q937857. ?p rdfs:label ?en FILTER(LANG(?en)="en") }}""")
        except SystemExit:
            log("  ما زبط استعلام لاعبين أندية")
            rows = []
        for b in rows:
            wd_by_club[qid(v(b, "club"))].append((qid(v(b, "p")), v(b, "en")))
        time.sleep(1)

    for k in wd_by_club:
        wd_by_club[k] = list(dict.fromkeys(wd_by_club[k]))  # كل لاعب مرة وحدة (حتى لو إله أكثر من فترة)
    by_last = defaultdict(set)
    for lst in wd_by_club.values():
        for pid, en in lst:
            toks = norm_tokens(en)
            if toks:
                by_last[toks[-1]].add((pid, en))
    squads, espn_only = {}, []
    for t in teams:
        cands = wd_by_club.get(t["club"], [])
        for a in t["roster"]:
            names = [n for n in (a.get("displayName"), a.get("fullName")) if n]
            if not names:
                continue
            scored = sorted(((name_match(names, en), pid) for pid, en in cands), reverse=True)
            jersey = a.get("jersey")
            cit = a.get("citizenship") or a.get("citizenshipCountry") or a.get("flag") or ""
            if isinstance(cit, dict):
                cit = cit.get("name") or cit.get("displayName") or cit.get("alt") or ""
            info = {"lg": t["lg"], "club_ar": t["club_ar"], "club": t["club"], "pc": espn_pos(a),
                    "num": int(jersey) if str(jersey or "").isdigit() else None,
                    "nat_ar": countries.get(cit), "en": names[0], "full": names[-1], "espn": str(a.get("id") or ""),
                    "age": a.get("age")}
            if scored and scored[0][0] >= 1 and (len(scored) == 1 or scored[0][0] > scored[1][0]):
                squads[scored[0][1]] = info
                continue
            # يمكن Wikidata مسجّله بنادي ثاني بنفس الدوريات (انتقال جديد أو إعارة)
            last = norm_tokens(names[0])[-1:] or [""]
            wide = sorted(((name_match(names, en), pid) for pid, en in by_last.get(last[0], ())), reverse=True)
            if wide and wide[0][0] >= 2 and (len(wide) == 1 or wide[0][0] > wide[1][0]) and wide[0][1] not in squads:
                squads[wide[0][1]] = info
            else:
                espn_only.append(info)
    # اللي ما انطابقوا: بندوّر عليهم بالاسم مباشرة بـ Wikidata (الاسم أو الاسم البديل)، ونتأكد من العمر
    rest = []
    for i in range(0, len(espn_only), 80):
        chunk = espn_only[i:i + 80]
        names = {n for e in chunk for n in (e["en"], e.get("full")) if n}
        vals = " ".join(json.dumps(n) + "@en" for n in names)
        found = defaultdict(set)
        try:
            for b in sparql(f"""SELECT ?p ?name ?b WHERE {{ VALUES ?name {{ {vals} }}
                {{ ?p rdfs:label ?name }} UNION {{ ?p skos:altLabel ?name }}
                ?p wdt:P106 wd:Q937857. OPTIONAL {{ ?p wdt:P569 ?b }} }}""", tries=2):
                found[v(b, "name")].add((qid(v(b, "p")), year(v(b, "b"))))
        except SystemExit:
            rest.extend(chunk)
            continue
        for e in chunk:
            cands = found.get(e["en"], set()) | found.get(e.get("full") or "", set())
            if isinstance(e.get("age"), int) and len(cands) > 1:
                by = time.gmtime().tm_year - e["age"]
                cands = {c for c in cands if c[1] and abs(c[1] - by) <= 1}
            pids = {c[0] for c in cands}
            if len(pids) == 1 and next(iter(pids)) not in squads:
                squads[next(iter(pids))] = e
            else:
                rest.append(e)
        time.sleep(1)
    espn_only = rest
    log(f"  التشكيلات: {len(squads)} لاعب مطابق مع Wikidata، {len(espn_only)} من ESPN بس")

    # اللاعبين العرب المعروفين (عشان المعتزلين العرب): دولة دولة عشان الاستعلام ما يثقل
    arabs = {}
    try:
        arab_c = [qid(v(b, "c")) for b in sparql(f"SELECT ?c WHERE {{ ?c wdt:P463 wd:{ARAB_LEAGUE} }}")]
    except SystemExit:
        arab_c = []
    for c in arab_c:
        for prop in ("P1532", "P27"):
            try:
                rows = sparql(f"""SELECT ?p ?l WHERE {{ ?p wdt:{prop} wd:{c}; wdt:P106 wd:Q937857;
                    wikibase:sitelinks ?l. FILTER(?l >= 8) }}""", tries=2)
            except SystemExit:
                log(f"  العرب: ما زبط {c} {prop}")
                continue
            for b in rows:
                arabs[qid(v(b, "p"))] = int(v(b, "l"))
            time.sleep(1)
    arabs = sorted(arabs.items(), key=lambda x: -x[1])[:1500]
    log(f"  لاعبين عرب: {len(arabs)}")
    return {"squads": squads, "espn_only": espn_only, "arabs": arabs, "countries": countries}


# ---------------------------------------------------------------- build

def clean_nt(name: str | None) -> str | None:
    if not name:
        return None
    x = re.sub(r"\s*(الوطني\s*)?لكرة القدم.*$", "", name)
    x = re.sub(r"\s+للرجال$", "", x).strip()
    return x if x.startswith("منتخب") else "منتخب " + x


def build(raw: dict, ids: list[str], col: dict, wins: dict, coaches: dict, team_names: dict,
          shape, is_youth, NOW_YEAR: int, log) -> None:
    squads = col["squads"]
    links = {pid: raw[pid].get("links", 0) for pid in ids}

    # الفترات لكل فريق (للزملاء والمدربين)
    by_team = defaultdict(list)
    spells = {}
    for pid in ids:
        sp = [(t["t"], t["s"], t["e"] or NOW_YEAR, t["nat"]) for t in raw[pid]["teams"] if t["s"] and not is_youth(t)]
        spells[pid] = sp
        for t, s, e, nat in sp:
            by_team[t].append((pid, s, e))

    def ov(a1, a2, b1, b2):
        return max(a1, b1) < min(a2, b2) or (max(a1, b1) == min(a2, b2) and (a1 == a2 or b1 == b2))

    def name_of(pid):
        p = raw[pid]
        return re.sub(r"\s*\([^)]*\)\s*$", "", p.get("ar") or p.get("en") or "").strip()

    out = []
    for pid in ids:
        base = shape(raw[pid], 0, wins)
        if not base:
            continue
        sq = squads.get(pid)
        cur = bool(sq)
        if not cur and base["act"]:
            continue  # لاعب حالي برا الدوريات الثمانية: ما بندخله
        cur_team = sq["club"] if sq else None
        # زملاء مشهورين: للاعب الحالي من برا ناديه الحالي (لأنه الخيارات من ناديه)،
        # وللمعتزل من الأندية مش المنتخب (لأنه الخيارات من منتخبه)
        mates = {}
        for t, s, e, nat in spells[pid]:
            if (cur and t == cur_team) or (not cur and nat):
                continue
            for other, os_, oe in by_team[t]:
                if other != pid and ov(s, e, os_, oe) and links.get(other, 0) >= 15:
                    where = clean_nt(team_names.get(t)) if nat else team_names.get(t)
                    if other not in mates or links[other] > mates[other][2]:
                        mates[other] = (name_of(other), where, links[other], nat)
        tm = [[n, w, 1 if nat else 0] for n, w, _, nat in sorted(mates.values(), key=lambda m: -m[2])[:4] if n and w]
        co = []
        for cid, c in coaches.items():
            for (t, s, e) in c["spells"]:
                if cur and t == cur_team:
                    continue
                if any(t == t2 and s and ov(s, e, s2, e2) for t2, s2, e2, _ in spells[pid]):
                    nm = re.sub(r"\s*\([^)]*\)\s*$", "", c["ar"] or c["en"] or "")
                    if nm and team_names.get(t):
                        co.append([nm, team_names[t]])
                    break
        clubs = base["c"]
        last = max(clubs, key=lambda c: (c[2] or c[1] or 0)) if clubs else None
        nt = clean_nt(base["nt"][0][0]) if base["nt"] else None
        nat = (base["nat"] or [None])[0] or (sq or {}).get("nat_ar")
        out.append({
            "id": pid, "a": base["a"], "n": base["n"], "img": base["img"]
            or (f"https://a.espncdn.com/i/headshots/soccer/players/full/{sq['espn']}.png" if sq and sq["espn"] else None),
            "pc": (sq or {}).get("pc") or pos_cat(raw[pid].get("pos_en")) or "mf",
            "cur": cur, "lg": sq["lg"] if sq else None, "hc": sq["club_ar"] if sq else None,
            "rc": last[0] if (last and not cur) else None, "num": (sq or {}).get("num"),
            "nt": nt, "nat": nat, "by": base["by"], "wc": base["wc"], "ucl": base["ucl"],
            "tm": tm, "co": co[:3], "r": links[pid],
        })

    # لاعبين ESPN اللي ما لقيناهم بـ Wikidata: بالاسم الإنجليزي، والزملاء من ناديهم الحالي
    famous_at = defaultdict(list)
    for p in out:
        if p["cur"]:
            famous_at[p["hc"]].append(p)
    for i, e in enumerate(col["espn_only"]):
        mates = sorted(famous_at.get(e["club_ar"], []), key=lambda p: -p["r"])[:1]
        out.append({
            "id": "e" + (e["espn"] or str(i)), "a": e["en"], "n": e["en"],
            "img": f"https://a.espncdn.com/i/headshots/soccer/players/full/{e['espn']}.png" if e["espn"] else None,
            "pc": e["pc"] or "mf", "cur": True, "lg": e["lg"], "hc": e["club_ar"], "rc": None, "num": e["num"],
            "nt": clean_nt(e["nat_ar"]) if e["nat_ar"] else None, "nat": e["nat_ar"],
            "by": (NOW_YEAR - e["age"]) if isinstance(e.get("age"), int) else None,
            "wc": [], "ucl": [], "tm": [], "co": [], "r": 0, "x": 1,
        })
    out.sort(key=lambda p: -p["r"])
    data = {"generated": time.strftime("%Y-%m-%d"), "leagues": [l for _, _, l in LEAGUES], "players": out}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    cur = [p for p in out if p["cur"]]
    log(f"party.json: {len(cur)} لاعب حالي، {len(out) - len(cur)} معتزل، "
        f"{sum(1 for p in out if p['tm'] or p['co'])} عندهم زميل/مدرب ({OUT.stat().st_size // 1024} KB)")
    for lg in data["leagues"]:
        clubs = {p["hc"] for p in cur if p["lg"] == lg}
        log(f"  {lg}: {len(clubs)} نادي، {sum(1 for p in cur if p['lg'] == lg)} لاعب")
