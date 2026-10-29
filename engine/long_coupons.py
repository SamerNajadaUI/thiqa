"""
قسيمة الأسبوع (أودز ≈ 200) وقسيمة الشهر (أودز ≈ 1000)

- كل وحدة إلها فترة: 7 أيام أو 30 يوم من يوم بنائها. لما تخلص الفترة بتنبني وحدة جديدة.
- بتنبني بنفس تشغيل الصبح، بس بنافذة أودز أوسع، فما بتصرف رصيد زيادة.
- التوقعات من أقوى الإشارات، توقع واحد من كل مباراة، ومن رياضات بنقدر نجيب نتيجتها تلقائياً.
- الاحتمال الحقيقي ≈ 1 ÷ الأودز، وبنعرضه زي ما هو.
"""
from __future__ import annotations

import math
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import espn
import panel

ISO = "%Y-%m-%dT%H:%M:%SZ"
KINDS = ("weekly", "monthly")


def _t(s: str) -> datetime:
    return datetime.strptime(s, ISO).replace(tzinfo=timezone.utc)


def needs_build(long: dict, kind: str, now: datetime) -> bool:
    cur = long.get(kind)
    return not cur or _t(cur["end"]) <= now


def fetch_hours_needed(long: dict, cfg: dict, now: datetime) -> int:
    hours = 0
    for kind in KINDS:
        if needs_build(long, kind, now):
            hours = max(hours, cfg["long_coupons"][kind]["days"] * 24)
    return hours


def _score(leg: dict, target: float):
    ratio = leg["support"] / leg["signals"] if leg.get("signals") else 0.5
    return (-round(ratio, 2), abs(leg["prob"] - target), -leg["books"])


def build(legs: list[dict], kind: str, t: dict, now: datetime, exclude: set[str]) -> dict:
    end = now + timedelta(days=t["days"])
    per_event: dict[str, dict] = {}
    for l in legs:
        k = _t(l["commence_time"])
        if not (now < k <= end) or l["event_id"] in exclude:
            continue
        if not espn.league_for(l["sport_key"]):  # لازم نقدر نصحّحها تلقائياً
            continue
        if not l.get("eligible", True) or not (t["min_leg"] <= l["prob"] <= t["max_leg"]):
            continue
        if panel.verdict(l) < t.get("min_verdict", 0):
            continue
        if l.get("signals") and l["support"] / l["signals"] < t.get("min_support_ratio", 0.5):
            continue
        cur = per_event.get(l["event_id"])
        if cur is None or _score(l, t["leg_target"]) < _score(cur, t["leg_target"]):
            per_event[l["event_id"]] = l
    pool = sorted(per_event.values(), key=lambda l: _score(l, t["leg_target"]))

    target = t["target_odds"]
    chosen, odds = [], 1.0
    while pool and odds < target and len(chosen) < t["max_legs"]:
        need = target / odds
        if need <= 1 / t["min_leg"]:
            # آخر توقع: بنختار اللي بيقرّبنا من الأودز المطلوبة أكثر
            leg = min(pool, key=lambda l: (abs(math.log((1 / l["prob"]) / need)), _score(l, t["leg_target"])))
        else:
            leg = pool[0]
        pool.remove(leg)
        chosen.append(deepcopy(leg))
        odds *= 1 / leg["prob"]

    chosen.sort(key=lambda l: l["commence_time"])
    prob = 1.0
    for l in chosen:
        prob *= l["prob"]
    return {
        "kind": kind, "start": now.strftime(ISO), "end": end.strftime(ISO),
        "target_odds": target, "legs": chosen,
        "prob": round(prob, 6) if chosen else None,
        "fair_odds": round(1 / prob, 1) if chosen else None,
        "reached": odds >= target * 0.9,
        "result": "pending" if chosen else "none",
    }


def coupon_result(c: dict) -> str:
    if not c["legs"]:
        return "none"
    rs = [l["result"] for l in c["legs"]]
    if "miss" in rs:
        return "lost"
    if "pending" in rs:
        return "pending"
    return "won" if any(r == "hit" for r in rs) else "void"


def refresh(long: dict, legs: list[dict], cfg: dict, now: datetime, log) -> None:
    """بيبني القسائم اللي فترتها خلصت، وبيأرشف القديمة."""
    used: set[str] = set()
    for kind in KINDS:
        if not needs_build(long, kind, now):
            used.update(l["event_id"] for l in long[kind]["legs"])
    for kind in KINDS:
        if not needs_build(long, kind, now):
            continue
        old = long.get(kind)
        if old and old.get("legs"):
            old["result"] = coupon_result(old)
            long.setdefault("past", []).append(old)
            long["past"] = long["past"][-24:]
        c = build(legs, kind, cfg["long_coupons"][kind], now, used)
        used.update(l["event_id"] for l in c["legs"])
        long[kind] = c
        log(f"  قسيمة {'الأسبوع' if kind == 'weekly' else 'الشهر'}: {len(c['legs'])} مباراة، أودز {c['fair_odds']}")


def open_days(long: dict) -> list[dict]:
    """القسائم الحالية والقديمة اللي لسا فيها نتائج، بشكل "يوم" عشان التصحيح."""
    cs = [long[k] for k in KINDS if long.get(k)] + [c for c in long.get("past", []) if c.get("result") == "pending"]
    return [{"date": "long", "long": True, "top": [], "coupons": cs}] if cs else []
