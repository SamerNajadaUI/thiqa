"""
مصدر إحصائيات كرة القدم: football-data.org (مجاني، الموسم الحالي)

- طلب واحد لكل دوري بيجيب كل مباريات الموسم بنتائجها.
- منها بنحسب كل شي: الفورمة، الأرض وبرّا، الترتيب، الراحة، المواجهات.
- الحد المجاني: 10 طلبات بالدقيقة، فبنستنى 6.5 ثانية بين كل طلب.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from analysis import Match

API = "https://api.football-data.org/v4"

# مفاتيح The Odds API -> رموز football-data.org (الخطة المجانية)
COMPETITIONS = {
    "soccer_epl": "PL",
    "soccer_efl_champ": "ELC",
    "soccer_spain_la_liga": "PD",
    "soccer_italy_serie_a": "SA",
    "soccer_germany_bundesliga": "BL1",
    "soccer_france_ligue_one": "FL1",
    "soccer_netherlands_eredivisie": "DED",
    "soccer_portugal_primeira_liga": "PPL",
    "soccer_brazil_campeonato": "BSA",
    "soccer_uefa_champs_league": "CL",
}
DOMESTIC = {"PL", "ELC", "PD", "SA", "BL1", "FL1", "DED", "PPL", "BSA"}


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


class FootballData:
    def __init__(self, token: str, max_requests: int = 24):
        self.token = token
        self.max_requests = max_requests
        self.used = 0
        self._last = 0.0

    def get(self, path: str, **params):
        if self.used >= self.max_requests:
            return None
        wait = 6.5 - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        url = f"{API}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
        req = urllib.request.Request(url, headers={"X-Auth-Token": self.token, "User-Agent": "thiqa-daily/3.0"})
        for attempt in range(2):
            self._last = time.time()
            self.used += 1
            try:
                with urllib.request.urlopen(req, timeout=40) as r:
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt == 0:
                    log("  football-data: وصلنا حد الدقيقة، بستنى دقيقة...")
                    time.sleep(62)
                    continue
                if e.code in (400, 403, 404):
                    log(f"  football-data: {path} مش متاح بالخطة ({e.code})")
                    return None
                log(f"  football-data: {path} HTTP {e.code}")
                return None
            except urllib.error.URLError as e:
                log(f"  football-data: مشكلة اتصال ({e.reason})")
                return None
        return None


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def season_matches(fd: FootballData, code: str, season: int | None = None) -> tuple[list[Match], list[dict]]:
    """(مباريات موحّدة، بيانات الفرق للمطابقة)"""
    data = fd.get(f"/competitions/{code}/matches", **({"season": season} if season else {}))
    if not data:
        return [], []
    out, teams = [], {}
    for m in data.get("matches", []):
        ht, at = m.get("homeTeam") or {}, m.get("awayTeam") or {}
        if not ht.get("id") or not at.get("id"):
            continue
        date = _parse_date(m["utcDate"])
        start = (m.get("season") or {}).get("startDate")
        yr = int(start[:4]) if start else (date.year if date.month >= 7 else date.year - 1)
        ft = (m.get("score") or {}).get("fullTime") or {}
        done = m.get("status") == "FINISHED" and ft.get("home") is not None
        out.append(Match(date=date, comp=code, season=yr, home_id=str(ht["id"]), away_id=str(at["id"]),
                         home=ht.get("name") or "", away=at.get("name") or "",
                         hg=ft.get("home") if done else None, ag=ft.get("away") if done else None))
        for t in (ht, at):
            teams[str(t["id"])] = {"id": str(t["id"]), "names": [t.get("name"), t.get("shortName"), t.get("tla")]}
    return out, list(teams.values())


# ---------------------------------------------------------------- name matching

STOP = {"fc", "cf", "afc", "sc", "ac", "as", "ss", "ssc", "club", "de", "the", "calcio", "rc", "cd", "ud", "sd",
        "sv", "vfb", "vfl", "tsg", "fsv", "bv", "bsc", "fk", "hsc", "ogc", "us", "cfc", "sad", "1", "04", "05",
        "1899", "1909", "1846", "1913", "1907", "1900", "and"}
ALIAS = {
    "man city": "manchester city", "man utd": "manchester united", "man united": "manchester united",
    "spurs": "tottenham hotspur", "tottenham": "tottenham hotspur", "wolves": "wolverhampton wanderers",
    "psg": "paris saint germain", "paris sg": "paris saint germain", "inter": "internazionale",
    "inter milan": "internazionale", "milan": "milan", "ac milan": "milan",
    "bayern munich": "bayern munchen", "bayern": "bayern munchen", "atletico madrid": "atletico madrid",
    "athletic bilbao": "athletic club", "sporting lisbon": "sporting cp", "sporting": "sporting cp",
    "nottingham forest": "nottingham forest", "brighton and hove albion": "brighton hove albion",
    "leverkusen": "bayer leverkusen", "dortmund": "borussia dortmund", "gladbach": "borussia monchengladbach",
    "napoli": "napoli", "roma": "roma", "lazio": "lazio", "juventus": "juventus",
}


def normalize(name: str | None) -> str:
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("&", " and ").replace("-", " ").replace(".", " ").replace("'", "")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = " ".join(w for w in s.split() if w not in STOP)
    return ALIAS.get(s, s)


def similarity(odds_name: str, team: dict) -> float:
    a = normalize(odds_name)
    best = 0.0
    for cand in team["names"]:
        b = normalize(cand)
        if not a or not b:
            continue
        r = difflib.SequenceMatcher(None, a, b).ratio()
        ta, tb = set(a.split()), set(b.split())
        if ta and tb and (ta <= tb or tb <= ta):
            r = max(r, 0.9)
        best = max(best, r)
    return best


def match_fixture(home: str, away: str, kickoff: datetime, matches: list[Match], teams: dict) -> Match | None:
    best, best_score = None, 0.0
    for m in matches:
        if abs((m.date - kickoff).total_seconds()) > 3 * 3600:
            continue
        sh = similarity(home, teams[m.home_id]) if m.home_id in teams else 0
        sa = similarity(away, teams[m.away_id]) if m.away_id in teams else 0
        if sh >= 0.55 and sa >= 0.55 and sh + sa > best_score:
            best, best_score = m, sh + sa
    return best


# ---------------------------------------------------------------- loading

def load_competitions(fd: FootballData, codes: set[str], previous_season: bool = True):
    """بيرجع (كل المباريات، dict الفرق، الموسم الحالي لكل دوري)."""
    all_matches: list[Match] = []
    teams: dict[str, dict] = {}
    current: dict[str, int] = {}
    for code in sorted(codes):
        ms, ts = season_matches(fd, code)
        if not ms:
            continue
        current[code] = max(m.season for m in ms)
        all_matches += ms
        for t in ts:
            teams.setdefault(t["id"], t)
        log(f"  football-data {code}: {sum(m.finished for m in ms)} مباراة منتهية")
    if previous_season:
        for code in sorted(current):
            if code == "CL":
                continue
            ms, ts = season_matches(fd, code, current[code] - 1)
            all_matches += ms
            for t in ts:
                teams.setdefault(t["id"], t)
    return all_matches, teams, current
