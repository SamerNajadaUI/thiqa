#!/usr/bin/env python3
"""
قاعدة بيانات لعبة "احزر اللاعب" من Wikidata (مجانية ومفتوحة)

- أشهر ~1600 لاعب كرة قدم (الشهرة = عدد لغات ويكيبيديا اللي إلهم صفحة فيها).
- لكل لاعب: الاسم بالعربي والإنجليزي، الصورة، المركز، الجنسية، الطول، سنة الميلاد،
  الأندية بالسنين، والمنتخبات.
- المستوى من الشهرة: سهل، متوسط، صعب، مستحيل.
- تحديات: لعبوا مع ميسي ورونالدو، زملاء نجم، نفس المدرب بفريقين، لعبوا بالناديين.

الاستخدام: python engine/players.py   (بيكتب docs/games/players.json)
"""
from __future__ import annotations

import itertools
import json
import re
import random
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "games" / "players.json"
SPARQL = "https://query.wikidata.org/sparql"
UA = "AbuOdehGame/1.0 (https://github.com/SamerNajadaUI/thiqa)"
TOP = 1600
LEVELS = [(200, 1), (500, 2), (1000, 3), (TOP, 4)]  # المرتبة حسب الشهرة -> المستوى
NOW_YEAR = datetime.now(timezone.utc).year

MESSI, RONALDO = "Q615", "Q11571"
COACHES = {  # بنجيب الـ Q من Wikidata بالاسم
    "Pep Guardiola", "José Mourinho", "Carlo Ancelotti", "Jürgen Klopp", "Zinedine Zidane",
    "Diego Simeone", "Antonio Conte", "Luis Enrique", "Thomas Tuchel", "Arsène Wenger",
    "Alex Ferguson", "Mauricio Pochettino", "Unai Emery", "Rafael Benítez", "Massimiliano Allegri",
    "Louis van Gaal", "Fabio Capello", "Marcello Lippi", "Vicente del Bosque", "Hansi Flick",
    "Xabi Alonso", "Mikel Arteta", "Roberto Mancini", "Luciano Spalletti", "Frank Rijkaard",
}


def log(m: str) -> None:
    print(m, file=sys.stderr, flush=True)


def sparql(q: str, tries: int = 4):
    data = urllib.parse.urlencode({"query": q, "format": "json"}).encode()
    for i in range(tries):
        req = urllib.request.Request(SPARQL, data=data, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))["results"]["bindings"]
        except Exception as e:  # Wikidata أحياناً بيضغط: بنستنى ونرجع نحاول
            log(f"  محاولة {i + 1}: {e}")
            time.sleep(10 * (i + 1))
    raise SystemExit("Wikidata ما رد.")


def qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def v(b: dict, k: str):
    return b[k]["value"] if k in b else None


def num(s):
    try:
        x = float(s)
        return int(x) if x == int(x) else None
    except (TypeError, ValueError):
        return None


def year(s):
    try:
        return int(s[:4]) if s and s[0] != "-" else None
    except ValueError:
        return None


# ---------------------------------------------------------------- fetch

def fetch_pool() -> list[tuple[str, int]]:
    rows = sparql("""SELECT ?p ?links WHERE {
      ?p wdt:P106 wd:Q937857; wdt:P413 ?pos; wikibase:sitelinks ?links; wdt:P569 ?b.
      FILTER(?links >= 30 && YEAR(?b) >= 1935) } GROUP BY ?p ?links""")
    pool = sorted({(qid(v(b, "p")), int(v(b, "links"))) for b in rows}, key=lambda x: -x[1])
    return pool[:TOP]


def batches(xs, n=120):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def fetch_details(ids: list[str]) -> dict:
    P: dict[str, dict] = {i: {"id": i, "pos": [], "nat": [], "teams": []} for i in ids}
    for chunk in batches(ids):
        vals = " ".join("wd:" + i for i in chunk)
        for b in sparql(f"""SELECT ?p ?en ?ar ?b ?d ?img ?h ?hu WHERE {{ VALUES ?p {{ {vals} }}
            OPTIONAL {{ ?p rdfs:label ?en FILTER(LANG(?en)="en") }}
            OPTIONAL {{ ?p rdfs:label ?ar FILTER(LANG(?ar)="ar") }}
            OPTIONAL {{ ?p wdt:P569 ?b }} OPTIONAL {{ ?p wdt:P570 ?d }} OPTIONAL {{ ?p wdt:P18 ?img }}
            OPTIONAL {{ ?p p:P2048/psv:P2048 [ wikibase:quantityAmount ?h; wikibase:quantityUnit ?hu ] }} }}"""):
            x = P[qid(v(b, "p"))]
            x.setdefault("en", v(b, "en"))
            x.setdefault("ar", v(b, "ar"))
            x.setdefault("by", year(v(b, "b")))
            x.setdefault("dy", year(v(b, "d")))
            if v(b, "img") and not x.get("img"):
                x["img"] = v(b, "img").replace("http://", "https://") + "?width=360"
            if v(b, "h") and not x.get("h"):
                h, unit = float(v(b, "h")), qid(v(b, "hu") or "")
                cm = h if unit == "Q174728" else h * 100 if unit == "Q11573" else None
                if cm and 150 <= cm <= 215:
                    x["h"] = round(cm)
        time.sleep(1)
        for b in sparql(f"""SELECT ?p ?prop ?x ?en ?ar WHERE {{ VALUES ?p {{ {vals} }}
            VALUES ?prop {{ wdt:P413 wdt:P1532 wdt:P27 }} ?p ?prop ?x.
            OPTIONAL {{ ?x rdfs:label ?en FILTER(LANG(?en)="en") }}
            OPTIONAL {{ ?x rdfs:label ?ar FILTER(LANG(?ar)="ar") }} }}"""):
            x = P[qid(v(b, "p"))]
            label = v(b, "ar") or v(b, "en")
            if not label:
                continue
            key = {"P413": "pos", "P1532": "sport_nat", "P27": "nat"}[qid(v(b, "prop"))]
            x.setdefault(key, [])
            if label not in x[key]:
                x[key].append(label)
        time.sleep(1)
        seen = {}
        for b in sparql(f"""SELECT ?p ?s ?team ?en ?ar ?start ?end ?nat ?num ?apps ?goals WHERE {{ VALUES ?p {{ {vals} }}
            ?p p:P54 ?s. ?s ps:P54 ?team. OPTIONAL {{ ?s pq:P580 ?start }} OPTIONAL {{ ?s pq:P582 ?end }}
            OPTIONAL {{ ?s pq:P1618 ?num }} OPTIONAL {{ ?s pq:P1350 ?apps }} OPTIONAL {{ ?s pq:P1351 ?goals }}
            BIND(EXISTS {{ ?team wdt:P31/wdt:P279* wd:Q6979593 }} AS ?nat)
            OPTIONAL {{ ?team rdfs:label ?en FILTER(LANG(?en)="en") }}
            OPTIONAL {{ ?team rdfs:label ?ar FILTER(LANG(?ar)="ar") }} }}"""):
            sid = v(b, "s")
            t = seen.get(sid)
            if t is None:
                t = seen[sid] = {"t": qid(v(b, "team")), "en": v(b, "en"), "ar": v(b, "ar"),
                                 "s": year(v(b, "start")), "e": year(v(b, "end")), "nat": v(b, "nat") == "true"}
                P[qid(v(b, "p"))]["teams"].append(t)
            for k in ("num", "apps", "goals"):
                if v(b, k) and k not in t:
                    t[k] = num(v(b, k))
        time.sleep(1)
        # الجوايز (مع كم مرة) والبطولات اللي شارك فيها
        for b in sparql(f"""SELECT ?p ?st ?aw ?en ?t WHERE {{ VALUES ?p {{ {vals} }}
            ?p p:P166 ?st. ?st ps:P166 ?aw. OPTIONAL {{ ?st pq:P585 ?t }}
            OPTIONAL {{ ?aw rdfs:label ?en FILTER(LANG(?en)="en") }} }}"""):
            x = P[qid(v(b, "p"))]
            x.setdefault("awards", {}).setdefault(v(b, "en") or "", set()).add(year(v(b, "t")) or v(b, "st"))
        time.sleep(1)
        for b in sparql(f"""SELECT ?p ?ev WHERE {{ VALUES ?p {{ {vals} }} ?p wdt:P1344 ?ev }}"""):
            P[qid(v(b, "p"))].setdefault("events", set()).add(qid(v(b, "ev")))
        log(f"  {min(len(ids), ids.index(chunk[-1]) + 1)}/{len(ids)} لاعب")
        time.sleep(1)
    return P


def fetch_coaches(teams_known: set[str]) -> dict:
    names = " ".join(json.dumps(n) + "@en" for n in sorted(COACHES))
    rows = sparql(f"""SELECT ?c ?en ?ar ?team ?start ?end WHERE {{ VALUES ?name {{ {names} }}
        ?c rdfs:label ?name; wdt:P106 ?o. ?team p:P286 ?s. ?s ps:P286 ?c; pq:P580 ?start.
        OPTIONAL {{ ?s pq:P582 ?end }}
        OPTIONAL {{ ?c rdfs:label ?en FILTER(LANG(?en)="en") }} OPTIONAL {{ ?c rdfs:label ?ar FILTER(LANG(?ar)="ar") }} }}""")
    out: dict[str, dict] = {}
    for b in rows:
        t = qid(v(b, "team"))
        if t not in teams_known:  # بس فرق حقيقية لعب فيها لاعبين من القاعدة
            continue
        c = out.setdefault(qid(v(b, "c")), {"en": v(b, "en"), "ar": v(b, "ar"), "spells": set()})
        c["spells"].add((t, year(v(b, "start")), year(v(b, "end")) or NOW_YEAR))
    return out


WORLD_CUP, UCL = "Q19317", "Q18756"


def season_year(label: str, end) -> int | None:
    """سنة النهائي: من تاريخ النهاية، أو من الاسم (2017–18 → 2018)."""
    if end:
        return end
    m = re.search(r"(\d{4})(?:\s*[–-]\s*(\d{2,4}))?", label or "")
    if not m:
        return None
    return int(m.group(1)) + 1 if m.group(2) else int(m.group(1))


def fetch_winners() -> dict:
    """{'wc': {حدث: (منتخب، سنة)}, 'ucl': [(نادي، سنة)]}"""
    out = {"wc": {}, "ucl": []}
    rows = sparql(f"""SELECT ?ev ?comp ?w ?end ?en WHERE {{ VALUES ?comp {{ wd:{WORLD_CUP} wd:{UCL} }}
        {{ ?ev wdt:P3450 ?comp }} UNION {{ ?ev wdt:P31 ?comp }}
        ?ev wdt:P1346 ?w. OPTIONAL {{ ?ev wdt:P582 ?end }}
        OPTIONAL {{ ?ev rdfs:label ?en FILTER(LANG(?en)="en") }} }}""")
    for b in rows:
        y = season_year(v(b, "en"), year(v(b, "end")))
        if not y or y < 1950:
            continue
        if qid(v(b, "comp")) == WORLD_CUP:
            out["wc"][qid(v(b, "ev"))] = (qid(v(b, "w")), y)
        else:
            out["ucl"].append((qid(v(b, "w")), y))
    out["ucl"] = sorted(set(out["ucl"]))
    log(f"  كأس العالم: {len(out['wc'])} نسخة، دوري الأبطال: {len(out['ucl'])} بطل")
    return out


# ---------------------------------------------------------------- shape

YOUTH_RE = re.compile(
    r"(under[- ]?\d{2}|\bu-?\d{2}\b|youth|olympic|reserves?|academy|primavera|juniors?|"
    r"\bb team\b|\s(b|c|ii|iii)$|atl[eè]tic$|castilla|^jong\s|amateur|\bu\d{2}s?\b)",
    re.IGNORECASE,
)


def is_youth(t: dict) -> bool:
    return bool(YOUTH_RE.search((t.get("en") or "").strip()))


def clean(label):
    return re.sub(r"\s*\([^)]*\)\s*$", "", label).strip() if label else label


def merge_nt(teams) -> list:
    """المنتخب بسطر واحد: من أول سنة لآخر سنة."""
    out: dict[str, list] = {}
    for t in teams:
        name = clean(t["ar"] or t["en"])
        if not name:
            continue
        cur = out.get(name)
        if cur is None:
            out[name] = [name, t["s"], t["e"]]
        else:
            cur[1] = min(x for x in (cur[1], t["s"]) if x) if (cur[1] or t["s"]) else None
            cur[2] = None if (cur[2] is None or t["e"] is None) else max(cur[2], t["e"])
    return sorted(out.values(), key=lambda x: x[1] or 9999)


AWARDS = [  # (جزء من الاسم الإنجليزي، الاسم بالعربي) بالترتيب حسب الأهمية
    ("ballon d'or", "الكرة الذهبية"),
    ("fifa world player of the year", "جائزة أفضل لاعب بالعالم من فيفا"),
    ("the best fifa men's player", "جائزة ذا بيست لأفضل لاعب بالعالم"),
    ("world cup golden ball", "الكرة الذهبية لأفضل لاعب بكأس العالم"),
    ("world cup golden boot", "الحذاء الذهبي لهداف كأس العالم"),
    ("european golden shoe", "الحذاء الذهبي لهداف أوروبا"),
    ("uefa men's player of the year", "جائزة أفضل لاعب بأوروبا"),
    ("uefa best player in europe", "جائزة أفضل لاعب بأوروبا"),
    ("yashin", "جائزة ياشين لأفضل حارس"),
    ("gerd müller trophy", "جائزة غيرد مولر لأفضل هداف"),
    ("golden boy", "جائزة الفتى الذهبي"),
    ("kopa trophy", "جائزة كوبا لأفضل لاعب شاب"),
    ("african footballer of the year", "جائزة أفضل لاعب بأفريقيا"),
    ("asian footballer of the year", "جائزة أفضل لاعب بآسيا"),
    ("south american footballer of the year", "جائزة أفضل لاعب بأمريكا الجنوبية"),
    ("premier league player of the season", "جائزة أفضل لاعب بالدوري الإنجليزي"),
]


def bi(x: str) -> str:
    """بـ + الاسم: "بالكرة" مش "بـالكرة"."""
    return ("ب" if re.match(r"[\u0600-\u06FF]", x or "") else "بـ") + x


def times(n: int) -> str:
    return "مرة وحدة" if n == 1 else "مرتين" if n == 2 else f"{n} مرات" if n <= 10 else f"{n} مرة"


def facts(p: dict, clubs: list, nts: list, name) -> list[str]:
    """معلومة تاريخية عن اللاعب: جايزة كبيرة، أو رقم أهداف، أو مباريات دولية."""
    out = []
    aw = {k.lower(): v for k, v in (p.get("awards") or {}).items()}
    for key, ar in AWARDS:
        hits = set().union(*[v for k, v in aw.items() if key in k]) if any(key in k for k in aw) else set()
        if hits:
            out.append(f"فاز {bi(ar)}" + (" أكثر من مرة" if len(hits) > 1 else ""))
            break
    scorers = [t for t in clubs if t.get("goals") and t.get("apps")]
    if scorers:
        t = max(scorers, key=lambda t: t["goals"])
        if t["goals"] >= 25:
            out.append(f"سجّل {t['goals']} هدف في {t['apps']} مباراة مع {name(t)}")
    nt = max((t for t in nts if t.get("apps")), key=lambda t: t["apps"], default=None)
    if nt and nt["apps"] >= 20:
        g = nt.get("goals")
        out.append(f"لعب {nt['apps']} مباراة دولية" + (f" وسجّل {g} هدف" if g else ""))
    if not out:
        dated = [t for t in clubs if t["s"]]
        if dated:
            t = max(dated, key=lambda t: (t["e"] or NOW_YEAR) - t["s"])
            yrs = (t["e"] or NOW_YEAR) - t["s"]
            if yrs >= 3:
                out.append(f"قضى {yrs} سنين مع {name(t)}")
    return out[:3]


def shape(p: dict, rank: int, wins: dict | None = None) -> dict | None:
    if not p.get("en"):
        return None
    clubs, nts = {}, {}
    for t in p["teams"]:
        if is_youth(t):
            continue
        bucket = nts if t["nat"] else clubs
        bucket.setdefault((t["t"], t["s"], t["e"]), t)  # كل فترة لحالها (مثلاً رونالدو بمانشستر مرتين)
    if not clubs:
        return None
    club_list = sorted(clubs.values(), key=lambda t: (t["s"] or 9999, t["e"] or 9999))
    latest = max((t["s"] or 0) for t in club_list)
    active = not p.get("dy") and (p.get("by") or 0) >= 1984 and any(t["e"] is None and (t["s"] or 0) >= 2019 for t in club_list) and latest >= 2019
    lv = next(l for cut, l in LEVELS if rank < cut)
    nat = p.get("sport_nat") or p.get("nat") or []
    name = lambda t: clean(t["ar"] or t["en"])
    # نادي التلميح: الحالي للاعب الحالي، وللمعتزل النادي اللي قضى فيه أطول فترة
    cur = [t for t in club_list if t["e"] is None and t["s"]]
    dated = [t for t in club_list if t["s"]]
    if active and cur:
        hc = max(cur, key=lambda t: t["s"])
    elif dated:
        hc = max(dated, key=lambda t: ((t["e"] or NOW_YEAR) - t["s"], t["s"]))
    else:
        hc = club_list[-1]
    # رقم القميص: مع نادي التلميح إذا موجود، وإلا آخر رقم معروف
    numbered = [t for t in club_list if t.get("num")]
    sn = hc if hc.get("num") else (max(numbered, key=lambda t: t["s"] or 0) if numbered else None)
    if not sn:
        sn = next((t for t in nts.values() if t.get("num")), None)
    wins = wins or {"wc": {}, "ucl": []}
    nt_ids = {t["t"] for t in nts.values()}
    wc = sorted({y for ev, (team, y) in wins["wc"].items() if ev in p.get("events", set()) and team in nt_ids})
    ucl = sorted({y for team, y in wins["ucl"] for t in club_list
                  if t["t"] == team and t["s"] and t["s"] <= y - 1 and (t["e"] is None or t["e"] >= y)})
    return {
        "id": p["id"], "n": clean(p["en"]), "a": clean(p.get("ar")) or clean(p["en"]), "img": p.get("img"),
        "by": p.get("by"), "dy": p.get("dy"), "h": p.get("h"),
        "pos": p["pos"][:2], "nat": nat[:2],
        "c": [[clean(t["ar"] or t["en"]), t["s"], t["e"]] for t in club_list if (t["ar"] or t["en"])],
        "nt": merge_nt(nts.values())[:2],
        "lv": lv, "act": active, "r": rank,
        "hc": name(hc), "_hc": hc["t"],
        "sn": [sn["num"], name(sn)] if sn else None,
        "wc": wc, "ucl": ucl,
        "fx": facts(p, club_list, list(nts.values()), name),
    }


# ---------------------------------------------------------------- connections

def spells(p: dict) -> list[tuple[str, int, int]]:
    out = []
    for t in p["teams"]:
        if t["s"] and not is_youth(t):
            out.append((t["t"], t["s"], t["e"] or NOW_YEAR))
    return out


def overlap(a, b) -> bool:
    s, e = max(a[1], b[1]), min(a[2], b[2])
    return s < e or (s == e and (a[1] == a[2] or b[1] == b[2]))


def teammates(raw: dict, who: str) -> set[str]:
    mine = spells(raw[who])
    out = set()
    for pid, p in raw.items():
        if pid == who:
            continue
        for sp in spells(p):
            if any(sp[0] == m[0] and overlap(sp, m) for m in mine):
                out.add(pid)
                break
    return out


def build_challenges(raw: dict, kept: dict, coaches: dict, team_names: dict) -> list[dict]:
    ch = []
    ok = lambda ids: sorted((i for i in ids if i in kept), key=lambda i: kept[i]["r"])

    if MESSI in raw and RONALDO in raw:
        both = ok(teammates(raw, MESSI) & teammates(raw, RONALDO))
        if both:
            ch.append({"k": "mr", "t": "لعبوا مع ميسي ورونالدو", "q": "سمّي لاعبين لعبوا مع ميسي ومع رونالدو (بالنادي أو المنتخب)", "ans": both})

    stars = sorted((i for i in kept if kept[i]["lv"] == 1), key=lambda i: kept[i]["r"])[:40]
    for s in stars:
        mates = ok(teammates(raw, s))
        if len(mates) >= 8:
            ch.append({"k": "mates", "t": f"زملاء {kept[s]['a']}", "q": f"سمّي لاعبين لعبوا بنفس الفريق مع {kept[s]['a']}", "star": s, "ans": mates})

    for cid, c in coaches.items():
        by_player = defaultdict(set)
        for pid, p in raw.items():
            if pid not in kept:
                continue
            for sp in spells(p):
                for (t, s, e) in c["spells"]:
                    if sp[0] == t and s and overlap(sp, (t, s, e)):
                        by_player[pid].add(t)
        two = ok(pid for pid, ts in by_player.items() if len(ts) >= 2)
        if len(two) >= 3:
            name = clean(c["ar"] or c["en"])
            ch.append({"k": "coach", "t": f"تحت قيادة {name} بفريقين", "q": f"سمّي لاعبين دربهم {name} بفريقين مختلفين أو أكثر", "ans": two})

    club_players = defaultdict(set)
    for pid in kept:
        for t in raw[pid]["teams"]:
            if not t["nat"] and not is_youth(t):
                club_players[t["t"]].add(pid)
    big = sorted(club_players, key=lambda t: -len(club_players[t]))[:40]
    pairs = []
    for a, b in itertools.combinations(big, 2):
        common = club_players[a] & club_players[b]
        if len(common) >= 6:
            pairs.append((len(common), a, b, common))
    pairs.sort(reverse=True)
    for _, a, b, common in pairs[:40]:
        ch.append({"k": "clubs", "t": f"لعبوا بـ{team_names[a]} و{team_names[b]}", "q": f"سمّي لاعبين لعبوا بـ{team_names[a]} وبـ{team_names[b]}", "ans": ok(common)})
    return ch


def fetch_leagues(team_ids: list[str]) -> dict:
    """الدوري تبع كل نادي (P118). بنفضّل الدوري الأعلى بالبلد إذا في أكثر من واحد."""
    out: dict[str, list] = {}
    for chunk in batches(team_ids, 200):
        vals = " ".join("wd:" + i for i in chunk)
        for b in sparql(f"""SELECT ?t ?l ?en ?ar ?links WHERE {{ VALUES ?t {{ {vals} }}
            ?t wdt:P118 ?l. ?l wikibase:sitelinks ?links.
            OPTIONAL {{ ?l rdfs:label ?en FILTER(LANG(?en)="en") }}
            OPTIONAL {{ ?l rdfs:label ?ar FILTER(LANG(?ar)="ar") }} }}"""):
            name = clean(v(b, "ar") or v(b, "en"))
            if name:
                out.setdefault(qid(v(b, "t")), []).append((int(v(b, "links")), name, v(b, "en") or ""))
        time.sleep(1)
    return {t: max(xs)[1:] for t, xs in out.items()}


BIG5 = {"Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1",
        "الدوري الإنجليزي الممتاز", "الدوري الإسباني", "الدوري الإيطالي", "الدوري الألماني", "الدوري الفرنسي الدرجة الأولى"}


# ---------------------------------------------------------------- main

def main() -> int:
    log("بجيب قائمة أشهر اللاعبين من Wikidata...")
    pool = fetch_pool()
    ids = [i for i, _ in pool]
    log(f"  {len(ids)} لاعب")
    raw = fetch_details(ids)
    log("بجيب أبطال كأس العالم ودوري الأبطال...")
    wins = fetch_winners()
    kept = {}
    for rank, pid in enumerate(ids):
        s = shape(raw[pid], rank, wins)
        if s:
            kept[pid] = s
    team_names = {}
    for p in raw.values():
        for t in p["teams"]:
            team_names.setdefault(t["t"], clean(t["ar"] or t["en"]) or t["t"])
    log("بجيب المدربين...")
    coaches = fetch_coaches(set(team_names))
    challenges = build_challenges(raw, kept, coaches, team_names)
    club_count = defaultdict(int)
    for pid in kept:
        for t in {t["t"] for t in raw[pid]["teams"] if not t["nat"] and not is_youth(t)}:
            club_count[t] += 1
    common = [t for t, n in club_count.items() if n >= 2]
    log(f"بجيب دوري {len(common)} نادي...")
    leagues = fetch_leagues(sorted(set(common) | {p["_hc"] for p in kept.values()}))
    clubs = {team_names[t]: [leagues.get(t, ("دوريات ثانية",))[0], club_count[t]] for t in common}
    for p in kept.values():
        lg = leagues.get(p.pop("_hc"))
        p["lg"] = lg[0] if lg else None
        p["b5"] = bool(lg and (lg[0] in BIG5 or lg[1] in BIG5))
    for who in ("Q615", "Q11571", "Q483915", "Q166154", "Q1835"):
        if who in kept:
            k = kept[who]
            log(f"  فحص {k['n']}: نادي={k['hc']} دوري={k['lg']} كبرى={k['b5']} رقم={k['sn']} كأس عالم={k['wc']} أبطال={k['ucl']} معلومة={k['fx'][:1]}")
    data = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "Wikidata (CC0) · الصور من Wikimedia Commons",
        "players": sorted(kept.values(), key=lambda p: p["r"]),
        "challenges": challenges,
        "clubs": clubs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"كتبت {len(kept)} لاعب و{len(challenges)} تحدي ({OUT.stat().st_size // 1024} KB).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
