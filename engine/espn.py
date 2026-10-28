"""
ESPN (مجاني، بدون مفتاح): نتائج مباشرة، نتائج نهائية، وشعارات الفرق.

- كرة القدم والسلة: شعار كل فريق.
- التنس: علم بلد اللاعب.
- بنستخدمه كل ساعة عشان نحدّث حالة المباريات ونصحّح التوقعات بدون ما نصرف رصيد الأودز.
أي خطأ هون ما بيوقف الموقع: بنكمّل بدون شعارات أو نتائج.
"""
from __future__ import annotations

import difflib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from football_data import normalize

BASE = "https://site.api.espn.com/apis/site/v2/sports"

LEAGUES = {
    "soccer_epl": ("soccer", "eng.1"),
    "soccer_efl_champ": ("soccer", "eng.2"),
    "soccer_spain_la_liga": ("soccer", "esp.1"),
    "soccer_italy_serie_a": ("soccer", "ita.1"),
    "soccer_germany_bundesliga": ("soccer", "ger.1"),
    "soccer_france_ligue_one": ("soccer", "fra.1"),
    "soccer_netherlands_eredivisie": ("soccer", "ned.1"),
    "soccer_portugal_primeira_liga": ("soccer", "por.1"),
    "soccer_uefa_champs_league": ("soccer", "uefa.champions"),
    "soccer_uefa_europa_league": ("soccer", "uefa.europa"),
    "soccer_saudi_arabia_pro_league": ("soccer", "ksa.1"),
    "basketball_nba": ("basketball", "nba"),
}


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def league_for(sport_key: str):
    if sport_key in LEAGUES:
        return LEAGUES[sport_key]
    if sport_key.startswith("tennis_atp"):
        return ("tennis", "atp")
    if sport_key.startswith("tennis_wta"):
        return ("tennis", "wta")
    return None


def _parse(s: str) -> datetime:
    s = s.replace("Z", "")
    fmt = "%Y-%m-%dT%H:%M:%S" if s.count(":") == 2 else "%Y-%m-%dT%H:%M"
    return datetime.strptime(s[:19] if s.count(":") == 2 else s[:16], fmt).replace(tzinfo=timezone.utc)


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


class Espn:
    def __init__(self, max_requests: int = 40):
        self.cache: dict[tuple, list] = {}
        self.used = 0
        self.max_requests = max_requests
        self.failed = False

    def _get(self, url: str):
        if self.used >= self.max_requests or self.failed:
            return None
        self.used += 1
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 thiqa-daily"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            log(f"  ESPN: ما زبط ({getattr(e, 'reason', e)})")
            if isinstance(e, urllib.error.URLError) and not isinstance(e, urllib.error.HTTPError):
                self.failed = True  # الموقع مش متاح: ما بنضل نحاول
            return None

    def games(self, sport: str, league: str, day: str) -> list[dict]:
        key = (sport, league, day)
        if key in self.cache:
            return self.cache[key]
        data = self._get(f"{BASE}/{sport}/{league}/scoreboard?dates={day}") or {}
        out = []
        for ev in data.get("events", []):
            comps = []
            if sport == "tennis":
                for g in ev.get("groupings", []):
                    if "singles" in ((g.get("grouping") or {}).get("slug") or ""):
                        comps += g.get("competitions", [])
            else:
                comps = ev.get("competitions", [])[:1]
            for c in comps:
                g = _game(sport, ev, c)
                if g:
                    out.append(g)
        self.cache[key] = out
        return out


def _game(sport: str, ev: dict, c: dict):
    st = (c.get("status") or ev.get("status") or {})
    typ = st.get("type") or {}
    sides = {}
    for p in c.get("competitors", []):
        ha = p.get("homeAway")
        if ha not in ("home", "away"):
            continue
        if sport == "tennis":
            ath = p.get("athlete") or {}
            name = ath.get("displayName") or ""
            logo = (ath.get("flag") or {}).get("href")
            sides[ha] = {"name": name, "names": [name, ath.get("shortName")], "logo": logo,
                         "sets": [_num(l.get("value")) for l in p.get("linescores", [])], "winner": p.get("winner")}
        else:
            t = p.get("team") or {}
            sides[ha] = {"name": t.get("displayName") or "", "logo": t.get("logo"),
                         "names": [t.get("displayName"), t.get("shortDisplayName"), t.get("name"), t.get("location")],
                         "score": _num(p.get("score"))}
    if "home" not in sides or "away" not in sides:
        return None
    date = c.get("date") or ev.get("date")
    if not date:
        return None
    h, a = sides["home"], sides["away"]
    if sport == "tennis":
        hs = sum(1 for x, y in zip(h["sets"], a["sets"]) if x is not None and y is not None and x > y)
        as_ = sum(1 for x, y in zip(h["sets"], a["sets"]) if x is not None and y is not None and y > x)
        if typ.get("completed") and h.get("winner") == a.get("winner"):
            return None  # ما في فائز واضح (انسحاب قبل البداية مثلاً)
        if typ.get("completed") and (hs == as_):
            hs, as_ = (1, 0) if h.get("winner") else (0, 1)
        h["score"], a["score"] = float(hs), float(as_)
    return {
        "id": str(c.get("id") or ev.get("id")),
        "date": _parse(date),
        "state": typ.get("state"),          # pre / in / post
        "completed": bool(typ.get("completed")),
        "detail": typ.get("shortDetail") or typ.get("detail") or "",
        "clock": st.get("displayClock"),
        "home": h, "away": a,
    }


def _sim(a: str, names: list) -> float:
    na = normalize(a)
    best = 0.0
    for n in names:
        nb = normalize(n)
        if not na or not nb:
            continue
        r = difflib.SequenceMatcher(None, na, nb).ratio()
        ta, tb = set(na.split()), set(nb.split())
        if ta and tb and (ta <= tb or tb <= ta):
            r = max(r, 0.9)
        best = max(best, r)
    return best


def find_game(leg: dict, games: list[dict]):
    kickoff = datetime.strptime(leg["commence_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    tol = 36 * 3600 if leg["group"] == "tennis" else 3 * 3600
    best, best_score, swapped = None, 0.0, False
    for g in games:
        if abs((g["date"] - kickoff).total_seconds()) > tol:
            continue
        for sw in (False, True):
            if sw and leg["group"] != "tennis":
                continue
            gh, ga = (g["away"], g["home"]) if sw else (g["home"], g["away"])
            sh, sa = _sim(leg["home"], gh["names"]), _sim(leg["away"], ga["names"])
            if sh >= 0.6 and sa >= 0.6 and sh + sa > best_score:
                best, best_score, swapped = g, sh + sa, sw
    return best, swapped


def days_for(kickoff: datetime) -> list[str]:
    eastern = kickoff - timedelta(hours=5)
    return sorted({kickoff.strftime("%Y%m%d"), eastern.strftime("%Y%m%d")})


def update_legs(client: Espn, legs: list[dict]) -> dict[str, tuple[float, float]]:
    """
    بيعبّي لكل توقع: الشعارات، معلومات ESPN، والحالة المباشرة.
    بيرجع النتائج النهائية: event_id -> (أهداف صاحب الأرض، أهداف الضيف) بترتيب The Odds API.
    """
    finals: dict[str, tuple[float, float]] = {}
    by_event: dict[str, list[dict]] = {}
    for l in legs:
        by_event.setdefault(l["event_id"], []).append(l)
    for eid, group in by_event.items():
        l0 = group[0]
        lg = league_for(l0["sport_key"])
        if not lg:
            continue
        sport, league = lg
        kickoff = datetime.strptime(l0["commence_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        game, swapped = None, False
        for day in days_for(kickoff):
            game, swapped = find_game(l0, client.games(sport, league, day))
            if game:
                break
        if not game:
            continue
        gh, ga = (game["away"], game["home"]) if swapped else (game["home"], game["away"])
        hs, as_ = gh.get("score"), ga.get("score")
        live = {"state": game["state"], "detail": game["detail"],
                "score": f"{hs:g}-{as_:g}" if hs is not None and as_ is not None and game["state"] != "pre" else None}
        for l in group:
            l["espn"] = {"s": sport, "l": league, "id": game["id"], "sw": swapped}
            if gh.get("logo"):
                l["home_logo"] = gh["logo"]
            if ga.get("logo"):
                l["away_logo"] = ga["logo"]
            l["live"] = live
        if game["completed"] and game["state"] == "post" and hs is not None and as_ is not None:
            finals[eid] = (hs, as_)
    return finals
