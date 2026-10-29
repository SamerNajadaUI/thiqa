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
        for b in sparql(f"""SELECT ?p ?team ?en ?ar ?start ?end ?nat WHERE {{ VALUES ?p {{ {vals} }}
            ?p p:P54 ?s. ?s ps:P54 ?team. OPTIONAL {{ ?s pq:P580 ?start }} OPTIONAL {{ ?s pq:P582 ?end }}
            BIND(EXISTS {{ ?team wdt:P31/wdt:P279* wd:Q6979593 }} AS ?nat)
            OPTIONAL {{ ?team rdfs:label ?en FILTER(LANG(?en)="en") }}
            OPTIONAL {{ ?team rdfs:label ?ar FILTER(LANG(?ar)="ar") }} }}"""):
            x = P[qid(v(b, "p"))]
            x["teams"].append({"t": qid(v(b, "team")), "en": v(b, "en"), "ar": v(b, "ar"),
                               "s": year(v(b, "start")), "e": year(v(b, "end")), "nat": v(b, "nat") == "true"})
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


# ---------------------------------------------------------------- shape

YOUTH = ("under-", "u-1", "u-2", "u1", "u2", "youth", "olympic", "b team", " ii", " b", "reserves", "academy",
         "تحت", "الأولمبي", "الرديف", "الشباب")


def is_youth(t: dict) -> bool:
    name = f" {(t.get('en') or '').lower()} {(t.get('ar') or '')}"
    return any(k in name for k in YOUTH)


def shape(p: dict, rank: int) -> dict | None:
    if not p.get("en"):
        return None
    clubs, nts = {}, {}
    for t in p["teams"]:
        if is_youth(t):
            continue
        bucket = nts if t["nat"] else clubs
        cur = bucket.get(t["t"])
        if cur is None:
            bucket[t["t"]] = {**t}
        else:  # نفس الفريق أكثر من فترة: بناخذ أول بداية وآخر نهاية للعرض
            cur["s"] = min(x for x in (cur["s"], t["s"]) if x) if (cur["s"] or t["s"]) else None
            cur["e"] = None if (cur["e"] is None or t["e"] is None) else max(cur["e"], t["e"])
    if not clubs:
        return None
    club_list = sorted(clubs.values(), key=lambda t: (t["s"] or 9999))
    latest = max((t["s"] or 0) for t in club_list)
    active = not p.get("dy") and (p.get("by") or 0) >= 1984 and any(t["e"] is None and (t["s"] or 0) >= 2019 for t in club_list) and latest >= 2019
    lv = next(l for cut, l in LEVELS if rank < cut)
    nat = p.get("sport_nat") or p.get("nat") or []
    return {
        "id": p["id"], "n": p["en"], "a": p.get("ar") or p["en"], "img": p.get("img"),
        "by": p.get("by"), "dy": p.get("dy"), "h": p.get("h"),
        "pos": p["pos"][:2], "nat": nat[:2],
        "c": [[t["ar"] or t["en"], t["s"], t["e"]] for t in club_list if (t["ar"] or t["en"])],
        "nt": [[t["ar"] or t["en"], t["s"], t["e"]] for t in sorted(nts.values(), key=lambda t: t["s"] or 9999) if (t["ar"] or t["en"])][:2],
        "lv": lv, "act": active, "r": rank,
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
            name = c["ar"] or c["en"]
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


# ---------------------------------------------------------------- main

def main() -> int:
    log("بجيب قائمة أشهر اللاعبين من Wikidata...")
    pool = fetch_pool()
    ids = [i for i, _ in pool]
    log(f"  {len(ids)} لاعب")
    raw = fetch_details(ids)
    kept = {}
    for rank, pid in enumerate(ids):
        s = shape(raw[pid], rank)
        if s:
            kept[pid] = s
    team_names = {}
    for p in raw.values():
        for t in p["teams"]:
            team_names.setdefault(t["t"], t["ar"] or t["en"] or t["t"])
    log("بجيب المدربين...")
    coaches = fetch_coaches(set(team_names))
    challenges = build_challenges(raw, kept, coaches, team_names)
    data = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "Wikidata (CC0) · الصور من Wikimedia Commons",
        "players": sorted(kept.values(), key=lambda p: p["r"]),
        "challenges": challenges,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"كتبت {len(kept)} لاعب و{len(challenges)} تحدي ({OUT.stat().st_size // 1024} KB).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
