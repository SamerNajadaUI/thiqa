#!/usr/bin/env python3
"""
بيانات لعبة "مسيرة لاعب": لاعبين كبار، ولكل واحد الأندية اللي لعب فيها بالترتيب مع شعار كل نادي.

- اللاعبين من engine/career_names.txt (عناوين ويكيبيديا الإنجليزية).
- المسيرة من Wikidata (P54 مع سنين البداية والنهاية)، بدون المنتخبات وفرق الشباب والرديف.
- الشعار: من ESPN إذا لقينا النادي هناك، وإلا من Wikimedia Commons (P154).

الاستخدام: python engine/career.py   (بيكتب docs/games/career.json)
"""
from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = Path(__file__).resolve().parent / "career_names.txt"
OUT = ROOT / "docs" / "games" / "career.json"
PARTY = ROOT / "docs" / "games" / "party.json"
SPARQL = "https://query.wikidata.org/sparql"
WIKI = "https://en.wikipedia.org/w/api.php"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer"
UA = "AbuOdehGame/1.0 (https://github.com/SamerNajadaUI/thiqa)"
ESPN_LEAGUES = ["eng.1", "eng.2", "esp.1", "esp.2", "ita.1", "ita.2", "ger.1", "ger.2", "fra.1", "fra.2", "ned.1", "por.1",
                "sco.1", "bel.1", "tur.1", "gre.1", "rus.1", "aut.1", "sui.1", "den.1", "swe.1", "nor.1", "usa.1", "mex.1",
                "bra.1", "bra.2", "arg.1", "ksa.1", "eng.3", "eng.4", "sco.2", "por.2", "ned.2", "usa.2", "chi.1", "col.1", "uru.1", "qat.1", "uae.1", "egy.1", "jpn.1", "chn.1", "uefa.champions", "uefa.europa"]
# فرق الشباب والرديف والمنتخبات (بنشيلها من المسيرة)
NOT_SENIOR = re.compile(r"(\s(II|III|B|C)$|\b(U-?\d{2}|Under[- ]\d+|Sub[- ]\d+|Youth|Reserves?|Academy|Castilla|Atl[eè]tic|"
                        r"Jong|Primavera|Next Gen|Amateure?|Juvenil|Promesas|Olympic|national)\b|youth|reserve)", re.I)


def log(m: str) -> None:
    print(m, file=sys.stderr, flush=True)


def get_json(url: str, data: bytes | None = None, tries: int = 3, timeout: int = 60):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            log(f"  محاولة {i + 1}: {url[:80]} {e}")
            time.sleep(5 * (i + 1))
    return None


def sparql(q: str):
    d = get_json(SPARQL, urllib.parse.urlencode({"query": q, "format": "json"}).encode(), tries=4, timeout=120)
    return d["results"]["bindings"] if d else []


def v(b, k):
    return b[k]["value"] if k in b else None


def qid(u):
    return u.rsplit("/", 1)[-1]


def year(s):
    try:
        return int(s[:4]) if s and s[0] != "-" else None
    except ValueError:
        return None


def plain(x: str) -> str:
    x = unicodedata.normalize("NFKD", x or "")
    x = "".join(c for c in x if not unicodedata.combining(c)).lower()
    x = re.sub(r"[^a-z0-9 ]", " ", x)
    stop = {"fc", "cf", "afc", "sc", "ac", "as", "ss", "ssc", "sv", "fk", "sk", "ca", "cd", "ud", "rc", "rcd", "club", "de", "of", "the",
            "football", "futbol", "calcio", "f", "c", "1", "fussball", "sporting", "and", "athletic", "tsg", "vfl", "vfb", "bv", "bsc", "1899", "1900", "1909", "04", "05"}
    return " ".join(w for w in x.split() if w not in stop)


# ---------- 1) العناوين → Wikidata ----------
def resolve(titles: list[str]) -> list[str]:
    ids: list[str] = []
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        url = WIKI + "?" + urllib.parse.urlencode({"action": "query", "format": "json", "redirects": 1, "prop": "pageprops",
                                                   "ppprop": "wikibase_item|disambiguation", "titles": "|".join(chunk)})
        d = get_json(url) or {}
        q = d.get("query", {})
        back = {}
        for r in q.get("normalized", []) + q.get("redirects", []):
            back[r["to"]] = back.get(r["from"], r["from"])
        found = {}
        for p in q.get("pages", {}).values():
            pp = p.get("pageprops", {})
            if "wikibase_item" in pp and "disambiguation" not in pp:
                found[back.get(p["title"], p["title"])] = pp["wikibase_item"]
                found[p["title"]] = pp["wikibase_item"]
        for t in chunk:
            if t in found:
                ids.append(found[t])
            else:
                log(f"  ما لقيت: {t}")
        time.sleep(1)
    return list(dict.fromkeys(ids))


# ---------- 2) شعارات ESPN ----------
def espn_logos() -> dict[str, str]:
    out: dict[str, str] = {}
    for lg in ESPN_LEAGUES:
        d = get_json(f"{ESPN}/{lg}/teams", tries=2, timeout=30)
        if not d:
            continue
        try:
            teams = d["sports"][0]["leagues"][0]["teams"]
        except (KeyError, IndexError):
            continue
        for t in teams:
            t = t.get("team", t)
            tid = str(t.get("id") or "")
            if not tid:
                continue
            for nm in {t.get("displayName"), t.get("name"), t.get("shortDisplayName"), t.get("location")}:
                k = plain(nm or "")
                if len(k) >= 3:
                    out.setdefault(k, tid)
        time.sleep(0.3)
    log(f"  ESPN: {len(out)} اسم فريق")
    return out


# ---------- 3) اللاعبين والمسيرة ----------
def fetch(ids: list[str]) -> dict:
    P: dict[str, dict] = {}
    for i in range(0, len(ids), 40):
        chunk = ids[i:i + 40]
        vals = " ".join("wd:" + x for x in chunk)
        for b in sparql(f"""SELECT ?p ?en ?ar ?img ?sl WHERE {{ VALUES ?p {{ {vals} }} ?p wikibase:sitelinks ?sl.
            OPTIONAL {{ ?p rdfs:label ?en FILTER(LANG(?en)="en") }} OPTIONAL {{ ?p rdfs:label ?ar FILTER(LANG(?ar)="ar") }}
            OPTIONAL {{ ?p wdt:P18 ?img }} }}"""):
            p = P.setdefault(qid(v(b, "p")), {"teams": {}, "al": set()})
            p.update({"en": v(b, "en"), "ar": v(b, "ar"), "sl": int(v(b, "sl") or 0)})
            if v(b, "img") and "img" not in p:
                p["img"] = urllib.parse.unquote(v(b, "img").rsplit("/", 1)[-1])
        time.sleep(1)
        for b in sparql(f"""SELECT ?p ?al WHERE {{ VALUES ?p {{ {vals} }} ?p skos:altLabel ?al FILTER(LANG(?al)="en" || LANG(?al)="ar") }}"""):
            P.setdefault(qid(v(b, "p")), {"teams": {}, "al": set()})["al"].add(v(b, "al"))
        time.sleep(1)
        for b in sparql(f"""SELECT ?p ?s ?team ?en ?ar ?start ?end ?nat ?logo WHERE {{ VALUES ?p {{ {vals} }}
            ?p p:P54 ?s. ?s ps:P54 ?team. OPTIONAL {{ ?s pq:P580 ?start }} OPTIONAL {{ ?s pq:P582 ?end }}
            BIND(EXISTS {{ ?team wdt:P31/wdt:P279* wd:Q6979593 }} AS ?nat)
            OPTIONAL {{ ?team wdt:P154 ?logo }}
            OPTIONAL {{ ?team rdfs:label ?en FILTER(LANG(?en)="en") }} OPTIONAL {{ ?team rdfs:label ?ar FILTER(LANG(?ar)="ar") }} }}"""):
            p = P.setdefault(qid(v(b, "p")), {"teams": {}, "al": set()})
            s = p["teams"].setdefault(v(b, "s"), {"t": qid(v(b, "team")), "en": v(b, "en"), "ar": v(b, "ar"),
                                                  "s": year(v(b, "start")), "e": year(v(b, "end")), "nat": v(b, "nat") == "true"})
            if v(b, "logo") and "logo" not in s:
                s["logo"] = urllib.parse.unquote(v(b, "logo").rsplit("/", 1)[-1])
        log(f"  {min(i + 40, len(ids))}/{len(ids)}")
        time.sleep(1)
    return P


def espn_find(espn: dict, en: str) -> str | None:
    """الاسم كامل، أو اسم ESPN كله موجود جوّا اسم Wikidata (S.L. Benfica ← Benfica) إذا في تطابق واحد بس."""
    k = plain(en)
    if not k:
        return None
    if k in espn:
        return espn[k]
    toks = set(w for w in k.split() if len(w) > 1)
    hits = {tid for name, tid in espn.items() if len(name) >= 4 and set(name.split()) <= toks}
    if len(hits) == 1:
        return hits.pop()
    k2 = " ".join(w for w in k.split() if len(w) > 1)
    return espn.get(k2)


def career(p: dict, espn: dict, party_logos: dict) -> list:
    spells = []
    for s in p["teams"].values():
        if s["nat"] or not (s["en"] or s["ar"]):
            continue
        if NOT_SENIOR.search(s["en"] or "") or re.search(r"(شباب|رديف|تحت \d+|الثاني$| ب$| ب )", s["ar"] or ""):
            continue
        if s["s"] is None and s["e"] is None:
            continue
        spells.append(s)
    spells.sort(key=lambda s: (s["s"] if s["s"] is not None else s["e"], s["e"] if s["e"] is not None else 9999))
    out = []
    for s in spells:
        if out and out[-1]["t"] == s["t"]:   # نفس النادي مكرر (فترتين ورا بعض)
            out[-1]["e"] = s["e"] if s["e"] is not None else out[-1]["e"]
            continue
        name = s["ar"] or s["en"]
        lg = ""
        if party_logos.get(name):
            lg = "e:" + party_logos[name]
        else:
            k = espn_find(espn, s["en"] or "")
            if k:
                lg = "e:" + k
            elif s.get("logo"):
                lg = "c:" + s["logo"]
        out.append({"t": s["t"], "n": name, "en": s["en"] or "", "s": s["s"], "e": s["e"], "lg": lg})
    return out


def main() -> int:
    titles = [l.strip() for l in NAMES.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    log(f"عناوين: {len(titles)}")
    ids = resolve(titles)
    log(f"لاعبين بـWikidata: {len(ids)}")
    espn = espn_logos()
    party_logos = {}
    try:
        party_logos = json.loads(PARTY.read_text(encoding="utf-8")).get("logos", {})
    except Exception:
        pass
    P = fetch(ids)
    players, no_logo, total_clubs = [], 0, 0
    for pid in ids:
        p = P.get(pid)
        if not p or not p.get("teams"):
            continue
        c = career(p, espn, party_logos)
        if len(c) < 2:
            log(f"  أقل من ناديين: {p.get('en')} ({len(c)})")
            continue
        total_clubs += len(c)
        no_logo += sum(1 for x in c if not x["lg"])
        al = sorted({a for a in p["al"] if a and len(a) <= 40})[:12]
        players.append({"id": pid, "a": p.get("ar") or p.get("en"), "n": p.get("en") or p.get("ar"), "al": al,
                        "img": ("c:" + p["img"]) if p.get("img") else None, "sl": p.get("sl", 0),
                        "c": [[x["n"], x["s"], x["e"], x["lg"]] for x in c]})
    players.sort(key=lambda x: -x["sl"])
    OUT.write_text(json.dumps({"generated": time.strftime("%Y-%m-%d"), "players": players}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"career.json: {len(players)} لاعب، {total_clubs} نادي، بدون شعار: {no_logo}")
    return 0 if players else 1


if __name__ == "__main__":
    raise SystemExit(main())
