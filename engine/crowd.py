"""
رأي الجمهور العالمي: Polymarket (مجاني، بدون مفتاح)

Polymarket سوق توقعات فيه ناس من كل العالم بيحطوا فلوس حقيقية على نتيجة المباراة.
السعر = نسبة المراهنين اللي شايفين النتيجة رح تصير، موزونة بفلوسهم.
بنستخدمه كرأي ثاني مستقل عن شركات الأودز، مع حجم التداول عشان نعرف قديش الرأي قوي.
"""
from __future__ import annotations

import difflib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

from football_data import normalize

API = "https://gamma-api.polymarket.com/events"
GAME_TAG = 100639

SERIES = {
    "soccer_epl": 10188,
    "soccer_spain_la_liga": 10193,
    "soccer_italy_serie_a": 10203,
    "soccer_germany_bundesliga": 10194,
    "soccer_france_ligue_one": 10195,
    "soccer_uefa_champs_league": 10204,
    "soccer_uefa_europa_league": 10209,
    "soccer_saudi_arabia_pro_league": 10361,
    "basketball_nba": 10345,
}


def series_for(sport_key: str):
    if sport_key in SERIES:
        return SERIES[sport_key]
    if sport_key.startswith("tennis_atp"):
        return 10365
    if sport_key.startswith("tennis_wta"):
        return 10366
    return None


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 abu-odeh"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        log(f"  Polymarket: ما زبط ({getattr(e, 'reason', e)})")
        return None


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _parse_list(s):
    if isinstance(s, list):
        return s
    try:
        return json.loads(s or "[]")
    except json.JSONDecodeError:
        return []


def _time(s: str | None):
    if not s:
        return None
    s = s.replace(" ", "T").replace("+00:00", "Z").replace("+00", "Z")
    try:
        return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_event(e: dict):
    """بيرجع {start, sides: {name: prob}, draw, volume} أو None."""
    ms = [m for m in e.get("markets", []) if (m.get("sportsMarketType") or "moneyline") == "moneyline"]
    if not ms:
        return None
    start = _time(ms[0].get("gameStartTime") or e.get("startTime"))
    if not start:
        return None
    sides, draw, vol = {}, None, 0.0
    if len(ms) == 1:  # سلة وتنس: سوق واحد فيه الفريقين
        m = ms[0]
        outs, prices = _parse_list(m.get("outcomes")), [_f(p) for p in _parse_list(m.get("outcomePrices"))]
        if len(outs) != 2 or None in prices:
            return None
        sides = {outs[0]: prices[0], outs[1]: prices[1]}
        vol = _f(m.get("volume")) or 0.0
    else:  # كرة قدم: سوق نعم/لا لكل نتيجة
        for m in ms:
            prices = [_f(p) for p in _parse_list(m.get("outcomePrices"))]
            if not prices or prices[0] is None:
                continue
            title = m.get("groupItemTitle") or ""
            vol += _f(m.get("volume")) or 0.0
            if title.lower().startswith("draw"):
                draw = prices[0]
            else:
                sides[title] = prices[0]
        if len(sides) != 2:
            return None
    total = sum(sides.values()) + (draw or 0)
    if total <= 0.5 or any(p in (0.0, 1.0) for p in sides.values()):
        return None  # سوق منتهي أو فاضي
    return {"start": start, "sides": {k: v / total for k, v in sides.items()},
            "draw": (draw / total) if draw is not None else None, "volume": vol}


class Crowd:
    def __init__(self):
        self.cache: dict[int, list] = {}

    def events(self, series: int) -> list[dict]:
        if series not in self.cache:
            data = _get(f"{API}?series_id={series}&closed=false&limit=200&tag_id={GAME_TAG}") or []
            self.cache[series] = [x for x in (parse_event(e) for e in data) if x]
        return self.cache[series]


def _sim(a: str, b: str) -> float:
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    r = difflib.SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    if ta and tb and (ta <= tb or tb <= ta):
        r = max(r, 0.9)
    return r


def lookup(c: Crowd, sport_key: str, home: str, away: str, kickoff: datetime):
    """بيرجع {home, draw, away, volume} بأسماء The Odds API، أو None."""
    sid = series_for(sport_key)
    if not sid:
        return None
    best, best_s = None, 0.0
    for e in c.events(sid):
        if abs((e["start"] - kickoff).total_seconds()) > 3 * 3600:
            continue
        names = list(e["sides"])
        for a, b in ((names[0], names[1]), (names[1], names[0])):
            s1, s2 = _sim(home, a), _sim(away, b)
            if s1 >= 0.6 and s2 >= 0.6 and s1 + s2 > best_s:
                best, best_s = (e, a, b), s1 + s2
    if not best:
        return None
    e, a, b = best
    return {"home": e["sides"][a], "away": e["sides"][b], "draw": e["draw"], "volume": e["volume"]}


def leg_probability(leg: dict, cr: dict):
    """احتمال الجمهور لتوقع من نوع الفائز أو فرصة مزدوجة."""
    h, a, d = cr["home"], cr["away"], cr["draw"] or 0.0
    m, n = leg["market"], leg["name"]
    if m == "h2h":
        if n == leg["home"]:
            return h
        if n == leg["away"]:
            return a
        if n == "Draw":
            return cr["draw"]
    if m == "double_chance" and cr["draw"] is not None:
        if n == leg["home"]:
            return h + d
        if n == leg["away"]:
            return a + d
        if n == "No Draw":
            return h + a
    return None


def attach(legs: list[dict], c: Crowd, log_fn=log) -> int:
    found = 0
    seen: dict[str, dict | None] = {}
    for l in legs:
        if l["event_id"] not in seen:
            kickoff = datetime.strptime(l["commence_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            try:
                seen[l["event_id"]] = lookup(c, l["sport_key"], l["home"], l["away"], kickoff)
            except Exception as e:  # مصدر إضافي: أي مشكلة ما بتوقف التحليل
                log_fn(f"  Polymarket: {e}")
                seen[l["event_id"]] = None
            found += seen[l["event_id"]] is not None
        cr = seen[l["event_id"]]
        if cr:
            p = leg_probability(l, cr)
            if p is not None:
                l["crowd_prob"] = round(p, 4)
                l["crowd_volume"] = round(cr["volume"])
    return found
