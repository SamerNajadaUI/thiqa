#!/usr/bin/env python3
"""
بيجيب كيانات من Wikidata حسب engine/wd_specs.py وبيكتبها engine/wd/<key>.json.
بيشتغل بالـCI (الجلسة السحابية ما بتوصل Wikidata).
الاستعمال: python engine/wd_fetch.py [key ...]     (بدون مفاتيح = الكل)
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from wd_specs import SPECS, EXTRA  # noqa: E402

OUT = HERE / "wd"
EP = "https://query.wikidata.org/sparql"
UA = "TaalilaQuizBot/1.0 (https://github.com/SamerNajadaUI/thiqa; quiz data for an Arabic party game)"
LATIN = re.compile(r"[A-Za-z]")


def log(m):
    print(m, flush=True)


def sparql(q, tries=4):
    data = urllib.parse.urlencode({"query": q, "format": "json"}).encode()
    for t in range(tries):
        try:
            req = urllib.request.Request(EP, data=data, headers={"User-Agent": UA, "Accept": "application/sparql-results+json",
                                                                  "Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))["results"]["bindings"]
        except urllib.error.HTTPError as e:
            wait = int(e.headers.get("Retry-After") or 0) or (10 * (t + 1))
            body = e.read().decode("utf-8", "ignore")[:300]
            log(f"    HTTP {e.code} (محاولة {t + 1}) {body[:160]!r}")
            if e.code in (400,) or "TimeoutException" in body or "timeout" in body.lower():
                raise RuntimeError(f"HTTP {e.code}: {body[:200]}")
            time.sleep(min(wait, 60))
        except Exception as e:
            log(f"    خطأ (محاولة {t + 1}): {e}")
            time.sleep(10 * (t + 1))
    raise RuntimeError("فشل بعد كل المحاولات")


def val(b, k):
    return b[k]["value"] if k in b else None


def qid(u):
    return u.rsplit("/", 1)[-1] if u else None


def fname(u):
    return urllib.parse.unquote(u.rsplit("/", 1)[-1]).replace("_", " ") if u else None


def base_query(sp):
    img = f"?item wdt:{sp['img']} ?img_ ." if sp["need_img"] else f"OPTIONAL {{ ?item wdt:{sp['img']} ?img_ . }}"
    arw = "?arts schema:about ?item ; schema:isPartOf <https://ar.wikipedia.org/> ." if sp["arwiki"] else \
        "OPTIONAL { ?arts schema:about ?item ; schema:isPartOf <https://ar.wikipedia.org/> . }"
    return f"""SELECT ?item ?sl (SAMPLE(?ar_) AS ?ar) (SAMPLE(?en_) AS ?en) (SAMPLE(?img_) AS ?img) (SAMPLE(?arts) AS ?art)
       (SAMPLE(?ard_) AS ?ard) (SAMPLE(?end_) AS ?end) WHERE {{
  {sp['where']}
  ?item wikibase:sitelinks ?sl . FILTER(?sl >= {sp['min_sl']})
  ?item rdfs:label ?ar_ . FILTER(LANG(?ar_) = "ar")
  {img}
  {arw}
  OPTIONAL {{ ?item rdfs:label ?en_ . FILTER(LANG(?en_) = "en") }}
  OPTIONAL {{ ?item schema:description ?ard_ . FILTER(LANG(?ard_) = "ar") }}
  OPTIONAL {{ ?item schema:description ?end_ . FILTER(LANG(?end_) = "en") }}
}} GROUP BY ?item ?sl ORDER BY DESC(?sl) LIMIT {sp['limit']}"""


def extra_query(ids, prop, kind):
    vals = " ".join("wd:" + i for i in ids)
    if kind == "label":
        body = f"?item wdt:{prop} ?x . OPTIONAL {{ ?x rdfs:label ?xl . FILTER(LANG(?xl) = \"ar\") }} BIND(CONCAT(STRAFTER(STR(?x), \"entity/\"), \":\", COALESCE(?xl, \"\")) AS ?v)"
    elif kind == "year":
        body = f"?item wdt:{prop} ?x . BIND(STR(YEAR(?x)) AS ?v)"
    elif kind == "id":
        body = f"?item wdt:{prop} ?x . BIND(STRAFTER(STR(?x), \"entity/\") AS ?v)"
    elif kind == "count":
        body = f"?item wdt:{prop} ?x . BIND(STRAFTER(STR(?x), \"entity/\") AS ?v)"
    else:   # num / str / file
        body = f"?item wdt:{prop} ?x . BIND(STR(?x) AS ?v)"
    return f"SELECT ?item (GROUP_CONCAT(DISTINCT ?v; separator=\"|\") AS ?vs) WHERE {{ VALUES ?item {{ {vals} }} {body} }} GROUP BY ?item"


def run(sp):
    t0 = time.time()
    rows = sparql(base_query(sp))
    items, seen = [], set()
    for b in rows:
        q = qid(val(b, "item"))
        ar = (val(b, "ar") or "").strip()
        if not q or q in seen or not ar or LATIN.search(ar):
            continue
        seen.add(q)
        img = val(b, "img")
        items.append({"q": q, "ar": ar, "en": val(b, "en"), "img": fname(img) if img else None, "sl": int(val(b, "sl")),
                      "arw": bool(val(b, "art")), "ard": val(b, "ard"), "end": val(b, "end")})
    by = {it["q"]: it for it in items}
    for name in sp["extra"]:
        prop, kind = EXTRA[name]
        ids = list(by)
        for i in range(0, len(ids), 250):
            try:
                for b in sparql(extra_query(ids[i:i + 250], prop, kind)):
                    it = by.get(qid(val(b, "item")))
                    if not it:
                        continue
                    vs = [v for v in (val(b, "vs") or "").split("|") if v]
                    if kind == "count":
                        it[name] = len(vs)
                    elif kind == "file":
                        it[name] = fname(vs[0]) if vs else None
                    else:
                        it[name] = vs
            except Exception as e:
                log(f"    extra {name}: {e}")
            time.sleep(0.5)
    log(f"  {sp['key']}: {len(items)} ({len(rows)} صف) في {time.time() - t0:.0f}ث — " + "، ".join(x["ar"] for x in items[:12]))
    return items


def main():
    want = set(sys.argv[1:])
    OUT.mkdir(exist_ok=True)
    summ_p = OUT / "_summary.json"
    try:
        summary = json.loads(summ_p.read_text(encoding="utf-8"))
    except Exception:
        summary = {}
    for sp in SPECS:
        if want and sp["key"] not in want:
            continue
        try:
            items = run(sp)
            (OUT / f"{sp['key']}.json").write_text(json.dumps({"key": sp["key"], "fetched": time.strftime("%Y-%m-%d"), "count": len(items),
                                                                "items": items}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            summary[sp["key"]] = {"count": len(items), "ok": True, "top": [x["ar"] for x in items[:25]], "bottom": [x["ar"] for x in items[-15:]]}
        except Exception as e:
            log(f"  ✗ {sp['key']}: {e}")
            summary[sp["key"]] = {"count": 0, "ok": False, "err": str(e)[:300]}
        time.sleep(1.5)
    summ_p.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
