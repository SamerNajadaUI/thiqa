#!/usr/bin/env python3
"""
قائمة الثقة اليومية — المحرك

1. السوق: يسحب الأودز من The Odds API لكل مباريات الـ48 ساعة الجاية (قدم، سلة، تنس)
   ولكل الأسواق اللي بنقدر نصحّحها: الفائز، فرصة مزدوجة، المجموع، الهانديكاب،
   مجموع فريق، الفريقين بيسجلوا. بيشيل هامش الشركات وبياخذ الوسيط.
2. الشركات الأدق (Pinnacle وBetfair): احتمالها لحالها كإشارة.
3. حركة السوق: بيقارن مع لقطة الأمس (لهيك بنسحب 48 ساعة).
4. كرة القدم: إحصائيات الموسم الحقيقية من football-data.org، ونموذج أهداف
   (Poisson + Dixon-Coles)، وبيدمجه مع السوق.
5. لكل توقع: أسباب وتحذيرات بالعربي، وعدد الإشارات الداعمة.
6. 3 قسائم: آمنة، شبه آمنة، خطيرة. التوقعات اللي الإشارات ضدها بتنشال.
7. بيصحّح الأيام الماضية من النتيجة النهائية.

الاستخدام:
    ODDS_API_KEY=xxx FOOTBALL_DATA_KEY=yyy python engine/run.py
    python engine/run.py --demo
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
import zlib
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis as an  # noqa: E402
import football_data as fdata  # noqa: E402
import espn  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "docs" / "data"
TODAY_FILE = DATA_DIR / "today.json"
HISTORY_FILE = DATA_DIR / "history.json"
SNAPSHOT_FILE = DATA_DIR / "snapshot.json"
OVERRIDES_FILE = ROOT / "results_overrides.json"
CONFIG_FILE = ROOT / "config.json"

API_BASE = "https://api.the-odds-api.com/v4"
AMMAN = timezone(timedelta(hours=3))
ISO = "%Y-%m-%dT%H:%M:%SZ"
COUPON_KINDS = ("safe", "medium", "risky")
SHARP_BOOKS = {"pinnacle", "betfair_ex_eu", "betfair_ex_uk", "matchbook", "smarkets"}

MARKET_BASE = {
    "h2h": "h2h", "btts": "btts",
    "totals": "totals", "alternate_totals": "totals",
    "spreads": "spreads", "alternate_spreads": "spreads",
    "team_totals": "team_totals", "alternate_team_totals": "team_totals",
}


# ---------------------------------------------------------------- utilities

def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        log(f"تحذير: الملف {path.name} فيه خطأ ({e})، رح أتجاهله.")
        return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def parse_time(s: str) -> datetime:
    return datetime.strptime(s, ISO).replace(tzinfo=timezone.utc)


def group_of(sport_key: str) -> str:
    for g in ("soccer", "basketball", "tennis"):
        if sport_key.startswith(g + "_"):
            return g
    return "other"


def product(xs) -> float:
    out = 1.0
    for x in xs:
        out *= x
    return out


# ---------------------------------------------------------------- Odds API

class BudgetExhausted(Exception):
    pass


class OddsApi:
    def __init__(self, key: str, reserve: float, per_run: float):
        self.key, self.reserve, self.per_run = key, reserve, per_run
        self.remaining: float | None = None
        self.spent = 0.0

    def can_spend(self, cost: float) -> bool:
        if self.spent + cost > self.per_run:
            return False
        return self.remaining is None or self.remaining - cost >= self.reserve

    def get(self, path: str, cost: float = 0, **params):
        if cost and not self.can_spend(cost):
            raise BudgetExhausted(f"وصلت حد الصرف ({self.spent:.0f} كريدت، المتبقي {self.remaining}).")
        params["apiKey"] = self.key
        url = f"{API_BASE}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "thiqa-daily/3.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                rem, last = r.headers.get("x-requests-remaining"), r.headers.get("x-requests-last")
                if rem is not None:
                    self.remaining = float(rem)
                if last is not None:
                    self.spent += float(last)
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code == 401:
                raise SystemExit("مفتاح ODDS_API_KEY غلط أو منتهي.")
            if e.code == 429:
                raise BudgetExhausted("خلص رصيد The Odds API.")
            log(f"  تخطيت {path}: HTTP {e.code} {body}")
            return None
        except urllib.error.URLError as e:
            log(f"  تخطيت {path}: مشكلة اتصال ({e.reason})")
            return None


# ---------------------------------------------------------------- market probabilities

def _keys(base: str, o: dict, home: str, away: str):
    name, pt, desc = o.get("name"), o.get("point"), o.get("description")
    if base in ("h2h", "btts"):
        return (base,), (base, name, None, None)
    if pt is None:
        return None, None
    pt = float(pt)
    if (pt * 2) != int(pt * 2):  # خطوط الربع بنتخطاها
        return None, None
    if base == "totals":
        return (base, pt), (base, name, pt, None)
    if base == "team_totals":
        if desc not in (home, away):
            return None, None
        return (base, desc, pt), (base, name, pt, desc)
    if base == "spreads":
        if name == home:
            hp = pt
        elif name == away:
            hp = -pt
        else:
            return None, None
        return (base, hp), (base, name, pt, None)
    return None, None


def market_probabilities(bookmakers: list, home: str, away: str, min_books: int, min_books_extra: int):
    """قائمة (مفتاح_النتيجة، احتمال_الإجماع، عدد_الشركات، احتمال_الشركات_الأدق أو None)."""
    samples: dict[tuple, dict[tuple, list[float]]] = {}
    sharp: dict[tuple, dict[tuple, list[float]]] = {}
    books: dict[tuple, set] = {}
    for b in bookmakers:
        seen = set()
        is_sharp = b.get("key") in SHARP_BOOKS
        for m in b.get("markets", []):
            base = MARKET_BASE.get(m.get("key"))
            if not base:
                continue
            groups: dict[tuple, dict[tuple, float]] = {}
            for o in m.get("outcomes", []):
                price = o.get("price") or 0
                if price <= 1:
                    continue
                gk, ok = _keys(base, o, home, away)
                if gk is not None:
                    groups.setdefault(gk, {})[ok] = 1.0 / price
            for gk, outs in groups.items():
                if len(outs) < 2 or gk in seen:
                    continue
                seen.add(gk)
                total = sum(outs.values())
                for ok, q in outs.items():
                    samples.setdefault(gk, {}).setdefault(ok, []).append(q / total)
                    if is_sharp:
                        sharp.setdefault(gk, {}).setdefault(ok, []).append(q / total)
                books.setdefault(gk, set()).add(b.get("key"))

    result = []
    for gk, outs in samples.items():
        need = min_books if gk[0] == "h2h" else min_books_extra
        n_books = len(books.get(gk, ()))
        if n_books < need:
            continue
        med = {ok: statistics.median(v) for ok, v in outs.items() if len(v) >= need}
        if len(med) < 2:
            continue
        total = sum(med.values())
        sh = sharp.get(gk, {})
        sh_tot = sum(statistics.median(sh[ok]) for ok in med if ok in sh) if all(ok in sh for ok in med) else 0
        for ok, v in med.items():
            sp = statistics.median(sh[ok]) / sh_tot if sh_tot else None
            result.append((ok, v / total, n_books, sp))
    return result


def event_legs(ev: dict, sport_key: str, league: str, bookmakers: list, cfg: dict) -> list[dict]:
    home, away = ev["home_team"], ev["away_team"]
    group = group_of(sport_key)
    probs = market_probabilities(bookmakers, home, away, cfg["min_bookmakers"], cfg["min_bookmakers_extra_markets"])
    raw = [(m, n, pt, d, p, k, sp) for (m, n, pt, d), p, k, sp in probs]

    h2h = {n: (p, k, sp) for m, n, pt, d, p, k, sp in raw if m == "h2h"}
    if group == "soccer" and {"Draw", home, away} <= set(h2h):
        k = min(v[1] for v in h2h.values())
        sharp_ok = all(v[2] is not None for v in h2h.values())

        def dc(a, b):
            return (h2h[a][0] + h2h[b][0], (h2h[a][2] + h2h[b][2]) if sharp_ok else None)
        for name, (x, y) in ((home, (home, "Draw")), (away, (away, "Draw")), ("No Draw", (home, away))):
            p, sp = dc(x, y)
            raw.append(("double_chance", name, None, None, p, k, sp))

    max_p = 1.0 / cfg["min_leg_odds"]
    legs = []
    for m, n, pt, d, p, k, sp in raw:
        if p > max_p + 0.02 or p < 0.05:
            continue
        legs.append({
            "id": f"{ev['id']}|{m}|{n}|{pt}|{d}",
            "event_id": ev["id"], "sport_key": sport_key, "group": group, "league": league,
            "home": home, "away": away, "commence_time": ev["commence_time"],
            "market": m, "name": n, "point": pt, "description": d,
            "market_prob": round(p, 4), "sharp_prob": round(sp, 4) if sp is not None else None,
            "prob": round(p, 4), "books": k, "result": "pending", "score": None,
        })
    return legs


# ---------------------------------------------------------------- selection

def eligible(legs: list[dict], cfg: dict, now: datetime) -> list[dict]:
    max_p = 1.0 / cfg["min_leg_odds"]
    cutoff = now + timedelta(hours=cfg["window_hours"])
    return [l for l in legs if l.get("eligible", True) and l["prob"] <= max_p and parse_time(l["commence_time"]) <= cutoff]


def best_per_event(legs: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for leg in legs:
        cur = best.get(leg["event_id"])
        key = (leg["prob"], leg.get("support", 0), leg["books"])
        if cur is None or key > (cur["prob"], cur.get("support", 0), cur["books"]):
            best[leg["event_id"]] = leg
    return sorted(best.values(), key=lambda l: (-l["prob"], -l.get("support", 0), l["commence_time"]))


def build_coupons(legs: list[dict], tiers: dict) -> list[dict]:
    """
    الاحتمال المستهدف لكل توقع = (الاحتمال الكلي المستهدف) ^ (1 / عدد التوقعات).
    من كل مباراة بناخذ التوقع الأقرب للهدف، ومع التساوي اللي إشاراته الداعمة أكثر.
    توقع واحد من كل مباراة بالقسيمة، وبنفضّل مباريات ما انستخدمت، وما بنكرر نفس السوق أكثر من مرتين.
    """
    used: set[str] = set()
    coupons = []
    for kind in COUPON_KINDS:
        t = tiers[kind]
        k = t["legs"]
        target = 1.0 if kind == "safe" else t["target_total"] ** (1 / k)
        per_event: dict[str, tuple] = {}
        for leg in legs:
            if not (t["min_leg"] <= leg["prob"] <= t["max_leg"]):
                continue
            ratio = leg.get("support", 0) / leg["signals"] if leg.get("signals") else 0.5
            score = (abs(leg["prob"] - target) - 0.02 * ratio, -leg["books"])
            cur = per_event.get(leg["event_id"])
            if cur is None or score < cur[0]:
                per_event[leg["event_id"]] = (score, leg)
        ranked = [l for _, l in sorted(per_event.values(), key=lambda x: (x[1]["event_id"] in used, x[0]))]

        chosen, per_market = [], {}
        for leg in ranked:
            if len(chosen) >= k:
                break
            if per_market.get(leg["market"], 0) >= t.get("max_same_market", 2):
                continue
            chosen.append(leg)
            per_market[leg["market"]] = per_market.get(leg["market"], 0) + 1
        for leg in ranked:
            if len(chosen) >= k:
                break
            if leg not in chosen:
                chosen.append(leg)

        if kind == "safe":  # الآمنة: إذا الاحتمال الكلي نزل كثير، بنقصّر القسيمة بدل ما نحط توقع ضعيف
            chosen.sort(key=lambda l: -l["prob"])
            while len(chosen) > t["min_legs"] and product(l["prob"] for l in chosen) < t["target_total"]:
                chosen.pop()
        if len(chosen) < t["min_legs"]:
            coupons.append({"kind": kind, "legs": [], "prob": None, "fair_odds": None, "result": "none"})
            continue
        chosen = sorted((deepcopy(l) for l in chosen), key=lambda l: l["commence_time"])
        used.update(l["event_id"] for l in chosen)
        coupons.append({
            "kind": kind, "legs": chosen,
            "prob": round(product(l["prob"] for l in chosen), 4),
            "fair_odds": round(product(1 / l["prob"] for l in chosen), 2),
            "result": "pending",
        })
    return coupons


def top_list(legs: list[dict], n: int) -> list[dict]:
    top = [deepcopy(l) for l in best_per_event(legs)[:n]]
    for i, l in enumerate(top, 1):
        l["rank"] = i
    return top


# ---------------------------------------------------------------- movement snapshot

def apply_movement(legs: list[dict], snapshot: dict) -> None:
    prev = snapshot.get("probs", {})
    for l in legs:
        if l["id"] in prev:
            l["movement"] = round(l["market_prob"] - prev[l["id"]], 4)


def make_snapshot(legs: list[dict], now: datetime) -> dict:
    return {"taken_at": now.strftime(ISO),
            "probs": {l["id"]: l["market_prob"] for l in legs if l["market_prob"] >= 0.35}}


# ---------------------------------------------------------------- football analysis

def soccer_contexts(legs: list[dict], matches: list, teams: dict, current: dict) -> dict[str, an.MatchContext]:
    out: dict[str, an.MatchContext] = {}
    events = {}
    for l in legs:
        if l["group"] == "soccer":
            events.setdefault(l["event_id"], l)
    for eid, l in events.items():
        code = fdata.COMPETITIONS.get(l["sport_key"])
        if not code or code not in current:
            continue
        kickoff = parse_time(l["commence_time"])
        comp_matches = [m for m in matches if m.comp == code and m.season == current[code]]
        fx = fdata.match_fixture(l["home"], l["away"], kickoff, comp_matches, teams)
        if not fx:
            continue
        season = current[code]
        dom = code if code in fdata.DOMESTIC else None
        if dom:
            lh, la, n = an.league_averages(matches, dom, season, kickoff)
            table = an.league_table(matches, dom, season, kickoff)
        else:
            lh, la, n, table = 1.50, 1.20, 0, {}
        ctx = an.MatchContext(
            home=an.team_form(fx.home_id, l["home"], matches, kickoff, season),
            away=an.team_form(fx.away_id, l["away"], matches, kickoff, season),
            lh_league=lh, la_league=la, league_n=n, table=table,
            h2h=an.head_to_head(matches, fx.home_id, fx.away_id, kickoff),
        )
        if ctx.sample >= 2:
            out[eid] = an.build_model(ctx)
    return out


def run_analysis(legs: list[dict], contexts: dict, cfg: dict) -> None:
    for l in legs:
        an.analyze(l, contexts.get(l["event_id"]), cfg)


# ---------------------------------------------------------------- predict

def predict(api: OddsApi, cfg: dict, now: datetime) -> tuple[list[dict], dict]:
    sports = api.get("/sports") or []
    active = {s["key"]: s for s in sports if s.get("active") and not s.get("has_outrights")}
    keys = [k for k in cfg["soccer_leagues"] + cfg["basketball_leagues"] if k in active]
    tennis = sorted(k for k in active if k.startswith("tennis_")) if cfg.get("include_all_active_tennis") else []
    window = {"commenceTimeFrom": now.strftime(ISO),
              "commenceTimeTo": (now + timedelta(hours=cfg.get("fetch_hours", 48))).strftime(ISO)}
    regions = cfg["regions"]
    n_regions = len(regions.split(","))

    featured: list[tuple[str, dict]] = []
    paid_tennis = 0
    for key in keys + tennis:
        group = group_of(key)
        if group == "tennis" and paid_tennis >= cfg.get("max_tennis_tournaments", 3):
            continue
        mk = cfg["markets"][group]["featured"]
        cost = len(mk.split(",")) * n_regions
        if not api.can_spend(cost):
            log(f"  وقفت قبل {key}: حد الصرف.")
            break
        if not api.get(f"/sports/{key}/events", **window):
            continue
        odds = api.get(f"/sports/{key}/odds", cost=cost, regions=regions, markets=mk, oddsFormat="decimal", **window)
        if group == "tennis":
            paid_tennis += 1
        n = 0
        for ev in odds or []:
            if parse_time(ev["commence_time"]) > now:
                featured.append((key, ev))
                n += 1
        log(f"  {key}: {n} مباراة")

    cutoff = now + timedelta(hours=cfg["window_hours"])

    def strength(item):
        key, ev = item
        ls = event_legs(ev, key, "", ev.get("bookmakers", []), cfg)
        return max((l["market_prob"] for l in ls if l["market"] == "h2h"), default=0)

    deep = [it for it in featured if cfg["markets"][group_of(it[0])]["extra"] and parse_time(it[1]["commence_time"]) <= cutoff]
    deep.sort(key=strength, reverse=True)
    done = 0
    for key, ev in deep:
        if done >= cfg.get("extra_markets_events_per_run", 0):
            break
        mk = cfg["markets"][group_of(key)]["extra"]
        cost = len(mk.split(",")) * n_regions
        if not api.can_spend(cost):
            break
        extra = api.get(f"/sports/{key}/events/{ev['id']}/odds", cost=cost, regions=regions, markets=mk, oddsFormat="decimal")
        if extra and extra.get("bookmakers"):
            ev["bookmakers"] = ev.get("bookmakers", []) + extra["bookmakers"]
        done += 1

    legs = []
    for key, ev in featured:
        legs.extend(event_legs(ev, key, active[key].get("title", key), ev.get("bookmakers", []), cfg))
    stats = {"events": len(featured), "legs": len(legs), "deep_events": done,
             "markets": sorted({l["market"] for l in legs})}
    log(f"  {stats['events']} مباراة، {stats['legs']} توقع ممكن، أسواق إضافية لـ{done} مباراة.")
    return legs, stats


# ---------------------------------------------------------------- grading

SCORE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*$")


def grade_leg(leg: dict, hs: float, as_: float) -> str:
    o = an._outcome(leg, hs, as_)
    leg["score"] = f"{hs:g}-{as_:g}"
    return "void" if o is None else ("hit" if o else "miss")


def coupon_result(c: dict) -> str:
    if not c["legs"]:
        return "none"
    rs = [l["result"] for l in c["legs"]]
    if "miss" in rs:
        return "lost"
    if "pending" in rs:
        return "pending"
    if all(r == "void" for r in rs):
        return "void"
    return "won"


def all_legs(day: dict):
    yield from day.get("top", [])
    for c in day.get("coupons", []):
        yield from c["legs"]


def check_results(api: OddsApi | None, cfg: dict, history: dict, now: datetime, client: "espn.Espn | None" = None) -> int:
    overrides = load_json(OVERRIDES_FILE, {})
    finals: dict[str, tuple[float, float]] = {}
    for k, v in overrides.items():
        m = SCORE_RE.match(str(v))
        if m:
            finals[k] = (float(m.group(1)), float(m.group(2)))

    # ESPN أول (مجاني): نتائج مباشرة ونهائية وشعارات لكل التوقعات اللي لسا ما انحسمت
    if client is not None:
        recent = [d for d in history.get("days", []) if d["date"] >= (now.astimezone(AMMAN) - timedelta(days=3)).strftime("%Y-%m-%d")]
        open_legs = [l for d in recent for l in all_legs(d) if l["result"] == "pending"]
        if open_legs:
            try:
                for eid, sc in espn.update_legs(client, open_legs).items():
                    finals.setdefault(eid, sc)
            except Exception as e:  # ESPN مش رسمي: أي مشكلة ما بتوقف التحديث
                log(f"  ESPN: {e}")

    due: dict[str, set[str]] = {}
    for day in history.get("days", []):
        for leg in all_legs(day):
            if leg["result"] == "pending" and leg["event_id"] not in finals:
                if parse_time(leg["commence_time"]) + timedelta(hours=3) < now:
                    due.setdefault(leg["sport_key"], set()).add(leg["event_id"])

    if api:
        for key in due:
            if not api.can_spend(2):
                log("  وقفت فحص النتائج: حد الصرف.")
                break
            for g in api.get(f"/sports/{key}/scores", cost=2, daysFrom=cfg["results_days_from"]) or []:
                if not g.get("completed") or not g.get("scores"):
                    continue
                try:
                    sc = {s["name"]: float(s["score"]) for s in g["scores"]}
                    finals[g["id"]] = (sc[g["home_team"]], sc[g["away_team"]])
                except (KeyError, TypeError, ValueError):
                    pass

    changed = 0
    for day in history.get("days", []):
        for leg in all_legs(day):
            if leg["id"] in overrides and overrides[leg["id"]] in ("hit", "miss", "void"):
                new = overrides[leg["id"]]
            elif leg["result"] != "pending":
                continue
            elif leg["event_id"] in finals:
                new = grade_leg(leg, *finals[leg["event_id"]])
            elif parse_time(leg["commence_time"]) + timedelta(days=cfg["give_up_after_days"]) < now:
                new = "void"
            else:
                continue
            if new != leg["result"]:
                leg["result"] = new
                changed += 1
        for c in day.get("coupons", []):
            c["result"] = coupon_result(c)
    log(f"  تحدثت نتائج {changed} توقع.")
    return changed


# ---------------------------------------------------------------- demo

def _pois_cdf(k: int, lam: float) -> float:
    return sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(k + 1))


def _pois_sample(rng: random.Random, lam: float) -> int:
    l, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= l:
            return k
        k += 1


def _ncdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


DEMO_EVENTS = [
    ("soccer", "soccer_epl", "EPL", "Manchester City", "Burnley", 2.6, 0.7),
    ("soccer", "soccer_spain_la_liga", "La Liga", "Real Madrid", "Getafe", 2.3, 0.7),
    ("soccer", "soccer_germany_bundesliga", "Bundesliga", "Bayern Munich", "Heidenheim", 3.0, 0.9),
    ("soccer", "soccer_france_ligue_one", "Ligue 1", "Paris Saint Germain", "Le Havre", 2.4, 0.7),
    ("soccer", "soccer_saudi_arabia_pro_league", "Saudi Pro League", "Al Hilal", "Al Okhdood", 2.5, 0.8),
    ("soccer", "soccer_italy_serie_a", "Serie A", "Inter Milan", "Pisa", 2.1, 0.7),
    ("soccer", "soccer_epl", "EPL", "Arsenal", "Wolverhampton", 2.0, 0.8),
    ("soccer", "soccer_spain_la_liga", "La Liga", "Barcelona", "Alaves", 2.4, 0.9),
    ("soccer", "soccer_italy_serie_a", "Serie A", "Napoli", "Lecce", 1.7, 0.8),
    ("basketball", "basketball_nba", "NBA", "Oklahoma City Thunder", "Washington Wizards", 13.0, 228),
    ("basketball", "basketball_nba", "NBA", "Boston Celtics", "Brooklyn Nets", 9.5, 221),
    ("basketball", "basketball_nba", "NBA", "Denver Nuggets", "Utah Jazz", 8.0, 232),
    ("basketball", "basketball_euroleague", "Euroleague", "Real Madrid Baloncesto", "ASVEL", 9.0, 160),
    ("tennis", "tennis_atp_paris", "ATP Paris", "Jannik Sinner", "Qualifier A", 0.93, 0),
    ("tennis", "tennis_atp_paris", "ATP Paris", "Carlos Alcaraz", "Qualifier B", 0.90, 0),
    ("tennis", "tennis_wta_finals", "WTA Finals", "Aryna Sabalenka", "Qualifier C", 0.80, 0),
]


def _demo_markets(e) -> list:
    group, _, _, home, away, a, b = e
    mk = []
    if group == "soccer":
        lh, la = a, b
        grid = [[(math.exp(-lh) * lh ** i / math.factorial(i)) * (math.exp(-la) * la ** j / math.factorial(j))
                 for j in range(12)] for i in range(12)]
        ph = sum(grid[i][j] for i in range(12) for j in range(12) if i > j)
        pd = sum(grid[i][i] for i in range(12))
        mk.append(("h2h", [(home, None, None, ph), ("Draw", None, None, pd), (away, None, None, 1 - ph - pd)]))
        for line in (0.5, 1.5, 2.5, 3.5, 4.5):
            u = _pois_cdf(int(line), lh + la)
            mk.append(("alternate_totals", [("Over", line, None, 1 - u), ("Under", line, None, u)]))
        bt = (1 - math.exp(-lh)) * (1 - math.exp(-la))
        mk.append(("btts", [("Yes", None, None, bt), ("No", None, None, 1 - bt)]))
        for line in (0.5, 1.5):
            u = _pois_cdf(int(line), lh)
            mk.append(("team_totals", [("Over", line, home, 1 - u), ("Under", line, home, u)]))
        d2 = sum(grid[i][j] for i in range(12) for j in range(12) if i - j >= 2)
        mk.append(("alternate_spreads", [(home, -1.5, None, d2), (away, 1.5, None, 1 - d2)]))
    elif group == "basketball":
        mu, tot = a, b
        ph = 1 - _ncdf(-mu / 12)
        mk.append(("h2h", [(home, None, None, ph), (away, None, None, 1 - ph)]))
        for line in (-0.5 - round(mu) + k * 4 for k in range(-2, 4)):
            p = 1 - _ncdf((-line - mu) / 12)
            mk.append(("alternate_spreads", [(home, line, None, p), (away, -line, None, 1 - p)]))
        for line in (round(tot) + 0.5 + k * 8 for k in range(-3, 3)):
            u = _ncdf((line - tot) / 17)
            mk.append(("alternate_totals", [("Over", line, None, 1 - u), ("Under", line, None, u)]))
    else:
        mk.append(("h2h", [(home, None, None, a), (away, None, None, 1 - a)]))
    return mk


def _demo_score(e, rng: random.Random) -> tuple[float, float]:
    group, _, _, _, _, a, b = e
    if group == "soccer":
        return float(_pois_sample(rng, a)), float(_pois_sample(rng, b))
    if group == "basketball":
        margin, tot = rng.gauss(a, 12), rng.gauss(b, 17)
        h = round((tot + margin) / 2)
        return float(h), float(round(tot) - h)
    return (2.0, rng.choice([0.0, 1.0])) if rng.random() < a else (rng.choice([0.0, 1.0]), 2.0)


def _demo_history(e, kickoff: datetime, rng: random.Random):
    """موسم مصغّر للفريقين من نفس قوتهم، عشان التحليل يشتغل على بيانات بشكل الحقيقية."""
    _, key, _, home, away, lh, la = e
    code = fdata.COMPETITIONS.get(key, "DEMO")
    season = kickoff.year if kickoff.month >= 7 else kickoff.year - 1
    ms = []
    strength = {home: (lh * 0.75, 0.8), away: (la * 1.15, 1.8)}
    for team, (att, dfn) in strength.items():
        for i in range(10):
            d = kickoff - timedelta(days=4 + 7 * i + rng.uniform(0, 2))
            opp = f"Opp{i}"
            if i % 2 == 0:
                hg, ag = _pois_sample(rng, att * 1.15), _pois_sample(rng, dfn * 0.9)
                ms.append(an.Match(d, code, season, team, opp, team, opp, hg, ag))
            else:
                hg, ag = _pois_sample(rng, dfn * 1.1), _pois_sample(rng, att * 0.9)
                ms.append(an.Match(d, code, season, opp, team, opp, team, hg, ag))
    for i in range(4):
        d = kickoff - timedelta(days=120 + 90 * i)
        if i % 2:
            ms.append(an.Match(d, code, season - 1, away, home, away, home, _pois_sample(rng, la), _pois_sample(rng, lh)))
        else:
            ms.append(an.Match(d, code, season - 1, home, away, home, away, _pois_sample(rng, lh), _pois_sample(rng, la)))
    return ms, code, season


def demo_day(day: datetime, rng: random.Random, cfg: dict, resolve: bool) -> dict:
    pool = rng.sample(DEMO_EVENTS, 12)
    legs, scores, contexts = [], {}, {}
    for i, e in enumerate(pool):
        group, key, league, home, away = e[:5]
        kickoff = day.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=11 + i)
        ev_id = f"demo-{day:%Y%m%d}-{i}"
        books = []
        names = ["pinnacle", "betfair_ex_eu"] + [f"book{k}" for k in range(rng.randint(6, 12))]
        for bk in names:
            sharp = bk in SHARP_BOOKS
            markets = []
            for mkey, outs in _demo_markets(e):
                margin = (1.025 if sharp else 1.05) + rng.uniform(-0.01, 0.02)
                noise = 0.006 if sharp else 0.015
                markets.append({"key": mkey, "outcomes": [
                    {"name": n, "point": pt, "description": d,
                     "price": round(1 / max(0.003, min(0.997, p * margin * rng.uniform(1 - noise, 1 + noise))), 3)}
                    for n, pt, d, p in outs]})
            books.append({"key": bk, "markets": markets})
        ev = {"id": ev_id, "home_team": home, "away_team": away,
              "commence_time": kickoff.astimezone(timezone.utc).strftime(ISO)}
        ev_legs = event_legs(ev, key, league, books, cfg)
        for l in ev_legs:
            if rng.random() < 0.7:
                l["movement"] = round(rng.gauss(0.004, 0.014), 4)
        legs.extend(ev_legs)
        if group == "soccer" and key != "soccer_saudi_arabia_pro_league":
            ms, code, season = _demo_history(e, kickoff, rng)
            ctx = an.MatchContext(
                home=an.team_form(home, home, ms, kickoff, season),
                away=an.team_form(away, away, ms, kickoff, season),
                lh_league=1.5, la_league=1.2, league_n=100,
                table={home: (rng.randint(1, 4), rng.randint(18, 26), 10), away: (rng.randint(14, 20), rng.randint(4, 10), 10)},
                h2h=an.head_to_head(ms, home, away, kickoff),
            )
            contexts[ev_id] = an.build_model(ctx)
        scores[ev_id] = _demo_score(e, random.Random(zlib.crc32(ev_id.encode())))
    run_analysis(legs, contexts, cfg)
    pick_from = [l for l in legs if l.get("eligible", True) and l["prob"] <= 1 / cfg["min_leg_odds"]]
    out = {"date": day.strftime("%Y-%m-%d"), "top": top_list(pick_from, cfg["top_list_size"]),
           "coupons": build_coupons(pick_from, cfg["coupons"])}
    if resolve:
        for leg in all_legs(out):
            leg["result"] = grade_leg(leg, *scores[leg["event_id"]])
        for c in out["coupons"]:
            c["result"] = coupon_result(c)
    return out


def build_demo(now: datetime, cfg: dict) -> None:
    rng = random.Random(20261025)
    local = now.astimezone(AMMAN)
    days = [demo_day(local - timedelta(days=d), rng, cfg, resolve=True) for d in range(21, 0, -1)]
    today = demo_day(local, rng, cfg, resolve=False)
    days.append(today)
    save_json(HISTORY_FILE, {"days": days})
    save_json(TODAY_FILE, {"date": today["date"], "generated_at": now.strftime(ISO), "demo": True,
                           "coupons": today["coupons"], "top": today["top"], "stats": None})
    log(f"كتبت بيانات تجريبية: {len(days)} يوم.")


# ---------------------------------------------------------------- main

def hourly(cfg: dict, now: datetime) -> int:
    """كل ساعة: نتائج مباشرة ونهائية من ESPN، بدون ما نلمس القسائم أو نصرف رصيد."""
    today = load_json(TODAY_FILE, {})
    if not today or today.get("demo"):
        log("الموقع لسا على البيانات التجريبية: ما في إشي نحدّثه.")
        return 0
    history = load_json(HISTORY_FILE, {"days": []})
    client = espn.Espn()
    check_results(None, cfg, history, now, client)
    day = next((d for d in history["days"] if d["date"] == today.get("date")), None)
    if day:
        today["coupons"], today["top"] = day["coupons"], day["top"]
    today["updated_at"] = now.strftime(ISO)
    save_json(HISTORY_FILE, history)
    save_json(TODAY_FILE, today)
    log(f"تحديث الساعة: {client.used} طلب ESPN.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="قائمة الثقة اليومية")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--no-results", action="store_true")
    ap.add_argument("--results-only", action="store_true")
    ap.add_argument("--hourly", action="store_true", help="تحديث النتائج المباشرة والنهائية بس (بدون رصيد أودز)")
    args = ap.parse_args()

    now = datetime.now(timezone.utc).replace(microsecond=0)
    cfg = load_json(CONFIG_FILE, None)
    if cfg is None:
        raise SystemExit("ما لقيت config.json")
    if args.demo:
        build_demo(now, cfg)
        return 0

    if args.hourly:
        return hourly(cfg, now)

    key = os.environ.get("ODDS_API_KEY", "").strip()
    if not key:
        log("ما في مفتاح ODDS_API_KEY لسا، فالموقع رح يضل على البيانات التجريبية.")
        return 0
    fd_key = os.environ.get("FOOTBALL_DATA_KEY", "").strip()

    api = OddsApi(key, cfg.get("min_credits_reserve", 20), cfg.get("max_credits_per_run", 16))
    history = load_json(HISTORY_FILE, {"days": []})
    history["days"] = [d for d in history.get("days", [])
                       if "coupons" in d and not any(str(l["id"]).startswith("demo-") for l in all_legs(d))]

    try:
        if cfg.get("check_results", True) and not args.no_results:
            log("بفحص نتائج الأيام الماضية...")
            check_results(api, cfg, history, now, espn.Espn())
        if not args.results_only:
            log("بجيب الأودز...")
            legs, stats = predict(api, cfg, now)
            apply_movement(legs, load_json(SNAPSHOT_FILE, {}))
            save_json(SNAPSHOT_FILE, make_snapshot(legs, now))

            contexts = {}
            if fd_key:
                log("بجيب إحصائيات كرة القدم...")
                window_legs = [l for l in legs if parse_time(l["commence_time"]) <= now + timedelta(hours=cfg["window_hours"])]
                codes = {fdata.COMPETITIONS[l["sport_key"]] for l in window_legs if l["sport_key"] in fdata.COMPETITIONS}
                fd = fdata.FootballData(fd_key, cfg.get("football_data_max_requests", 24))
                matches, teams, current = fdata.load_competitions(fd, codes, cfg.get("h2h_previous_season", True))
                contexts = soccer_contexts(window_legs, matches, teams, current)
                log(f"  حللت {len(contexts)} مباراة كرة قدم بالإحصائيات ({fd.used} طلب).")
            else:
                log("  ما في FOOTBALL_DATA_KEY: التحليل رح يعتمد على السوق بس.")
            run_analysis(legs, contexts, cfg)
            stats["analyzed"] = len(contexts)

            pick_from = eligible(legs, cfg, now)
            date = now.astimezone(AMMAN).strftime("%Y-%m-%d")
            day = {"date": date, "top": top_list(pick_from, cfg["top_list_size"]),
                   "coupons": build_coupons(pick_from, cfg["coupons"])}
            try:
                espn.update_legs(espn.Espn(), list(all_legs(day)))  # شعارات الفرق
            except Exception as e:
                log(f"  ESPN: {e}")
            history["days"] = [d for d in history["days"] if d["date"] != date]
            if day["top"]:
                history["days"].append(day)
            save_json(TODAY_FILE, {"date": date, "generated_at": now.strftime(ISO), "updated_at": now.strftime(ISO),
                                   "demo": False, "coupons": day["coupons"], "top": day["top"], "stats": stats})
    except BudgetExhausted as e:
        log(f"توقفت: {e}")
    finally:
        history["days"].sort(key=lambda d: d["date"])
        save_json(HISTORY_FILE, history)
        log(f"صرفت {api.spent:.0f} كريدت. المتبقي: {api.remaining}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
