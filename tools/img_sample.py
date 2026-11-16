#!/usr/bin/env python3
"""عيّنة صور من أقسام الصور بجمع نقاط (للمراجعة البصرية): بنزّل N صورة من كل قسم صور مع الجواب.
بيشتغل بالـCI (img_sample.yml) لأن ويكيميديا محجوبة من الجلسة. الناتج: sample/<cid>/<i>.jpg + sample/index.json"""
import json, random, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PQ = ROOT / "docs" / "games" / "pq"
OUT = ROOT / "sample"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 24
only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 and sys.argv[2] else None
OUT.mkdir(exist_ok=True)
idx = json.loads((PQ / "index.json").read_text())
res = {}
UA = {"User-Agent": "thiqa-quiz-check/1.0 (https://samernajadaui.github.io/thiqa/)"}
for c in idx["cats"]:
    if c.get("k") != "img" or (only and c["id"] not in only):
        continue
    qs = json.loads((PQ / f"{c['id']}.json").read_text())["qs"]
    qs = [q for q in qs if len(q) > 3 and q[3].startswith("http")]
    # السؤال الأساسي (اسمه) أولوية، وبعدين الأنواع الثانية
    rnd = random.Random(c["id"])
    pick = rnd.sample(qs, min(N, len(qs)))
    d = OUT / c["id"]
    d.mkdir(exist_ok=True)
    items = []
    for i, q in enumerate(pick):
        url = q[3].replace("width=640", "width=220")
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
            (d / f"{i}.jpg").write_bytes(data)
            items.append({"f": f"{c['id']}/{i}.jpg", "q": q[1], "a": q[2][0], "lv": q[0], "url": q[3]})
        except Exception as e:
            items.append({"f": None, "q": q[1], "a": q[2][0], "err": str(e)[:80], "url": q[3]})
        time.sleep(0.15)
    res[c["id"]] = {"name": c["name"], "items": items}
    print(c["id"], sum(1 for x in items if x["f"]), "/", len(items), flush=True)
(OUT / "index.json").write_text(json.dumps(res, ensure_ascii=False, indent=0))
