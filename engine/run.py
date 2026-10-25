#!/usr/bin/env python3
"""
قائمة الثقة اليومية — محرك التوقعات والقسائم

1. يسحب أسعار السوق (الأودز) من The Odds API لكل مباريات الـ24 ساعة الجاية
   بكرة القدم والسلة والتنس، ولكل الأسواق اللي بنقدر نصحّحها من النتيجة النهائية:
   الفائز، فرصة مزدوجة، مجموع الأهداف/النقاط (كل الخطوط)، الهانديكاب (كل الخطوط)،
   أهداف/نقاط كل فريق، والفريقين بيسجلوا.
2. لكل سوق بيشيل هامش الشركات وبياخذ الوسيط بين الشركات ليطلع الاحتمال الحقيقي.
3. بيبني 3 قسائم يومياً: آمنة، شبه آمنة، وخطيرة — كل مباراة بتدخل بقسيمة وحدة بس،
   وما بتتكرر نفس المباراة بقسيمتين (عشان النتائج ما تكون مربوطة ببعض).
4. بيرجع على الأيام الماضية وبيصحّح كل توقع وكل قسيمة من النتيجة النهائية.

الاستخدام:
    ODDS_API_KEY=xxxx python engine/run.py     # نتائج الأيام الماضية + قسائم اليوم
    python engine/run.py --demo                 # بيانات تجريبية بدون مفتاح
    python engine/run.py --results-only         # تحديث النتائج بس

مكتبات بايثون الأساسية فقط (بدون pip install).
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

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "docs" / "data"
TODAY_FILE = DATA_DIR / "today.json"
HISTORY_FILE = DATA_DIR / "history.json"
OVERRIDES_FILE = ROOT / "results_overrides.json"
CONFIG_FILE = ROOT / "config.json"

API_BASE = "https://api.the-odds-api.com/v4"
AMMAN = timezone(timedelta(hours=3))  # الأردن على UTC+3 طول السنة
ISO = "%Y-%m-%dT%H:%M:%SZ"
COUPON_KINDS = ("safe", "medium", "risky")

# الأسواق البديلة بتندمج مع الأساسية (نفس الخط = نفس التوقع)
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


# ---------------------------------------------------------------- API client

class BudgetExhausted(Exception):
    pass


class OddsApi:
    def __init__(self, key: str, reserve: float, per_run: float):
        self.key = key
        self.reserve = reserve
        self.per_run = per_run
        self.remaining: float | None = None
        self.spent = 0.0

    def can_spend(self, cost: float) -> bool:
        if self.spent + cost > self.per_run:
            return False
        if self.remaining is not None and self.remaining - cost < self.reserve:
            return False
        return True

    def get(self, path: str, cost: float = 0, **params):
        """cost = الكريدت المتوقع (0 للطلبات المجانية). بيرجع None إذا الطلب ما زبط."""
        if cost and not self.can_spend(cost):
            raise BudgetExhausted(f"وصلت حد الصرف ({self.spent:.0f} كريدت بهالتشغيل، المتبقي بالحساب {self.remaining}).")
        params["apiKey"] = self.key
        url = f"{API_BASE}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "thiqa-daily/2.0"})
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
                raise SystemExit("مفتاح ODDS_API_KEY غلط أو منتهي. تأكد منه بإعدادات GitHub Secrets.")
            if e.code == 429:
                raise BudgetExhausted("خلص رصيد الطلبات بـ The Odds API.")
            log(f"  تخطيت {path}: HTTP {e.code} {body}")
            return None
        except urllib.error.URLError as e:
            log(f"  تخطيت {path}: مشكلة اتصال ({e.reason})")
            return None


# ---------------------------------------------------------------- probabilities

def _keys(base: str, o: dict, home: str, away: str):
    """(مفتاح المجموعة، مفتاح النتيجة). المجموعة = النتائج اللي مجموعها 100% عند الشركة."""
    name, pt, desc = o.get("name"), o.get("point"), o.get("description")
    if base in ("h2h", "btts"):
        return (base,), (base, name, None, None)
    if pt is None:
        return None, None
    pt = float(pt)
    if (pt * 2) != int(pt * 2):  # خطوط الربع (2.25) نتيجتها نص ربح/نص خسارة، بنتخطاها
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
    """بيرجع قائمة (مفتاح_النتيجة، احتمال، عدد_الشركات)."""
    samples: dict[tuple, dict[tuple, list[float]]] = {}
    books: dict[tuple, set] = {}
    for b in bookmakers:
        seen = set()
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
        result.extend((ok, v / total, n_books) for ok, v in med.items())
    return result


def event_legs(ev: dict, sport_key: str, league: str, bookmakers: list, cfg: dict) -> list[dict]:
    home, away = ev["home_team"], ev["away_team"]
    group = group_of(sport_key)
    probs = market_probabilities(bookmakers, home, away, cfg["min_bookmakers"], cfg["min_bookmakers_extra_markets"])

    raw = [(market, name, pt, desc, p, n) for (market, name, pt, desc), p, n in probs]

    # فرصة مزدوجة من سوق الفائز (كرة القدم)
    h2h = {name: (p, n) for market, name, pt, desc, p, n in raw if market == "h2h"}
    if group == "soccer" and "Draw" in h2h and home in h2h and away in h2h:
        n = min(v[1] for v in h2h.values())
        raw.append(("double_chance", home, None, None, h2h[home][0] + h2h["Draw"][0], n))
        raw.append(("double_chance", away, None, None, h2h[away][0] + h2h["Draw"][0], n))
        raw.append(("double_chance", "No Draw", None, None, h2h[home][0] + h2h[away][0], n))

    max_p = 1.0 / cfg["min_leg_odds"]
    legs = []
    for market, name, pt, desc, p, n in raw:
        if p > max_p or p < 0.05:
            continue
        legs.append({
            "id": f"{ev['id']}|{market}|{name}|{pt}|{desc}",
            "event_id": ev["id"], "sport_key": sport_key, "group": group, "league": league,
            "home": home, "away": away, "commence_time": ev["commence_time"],
            "market": market, "name": name, "point": pt, "description": desc,
            "prob": round(p, 4), "books": n, "result": "pending", "score": None,
        })
    return legs


# ---------------------------------------------------------------- selection

def best_per_event(legs: list[dict], lo: float = 0.0, hi: float = 1.0, exclude: set | None = None) -> list[dict]:
    best: dict[str, dict] = {}
    for leg in legs:
        if exclude and leg["event_id"] in exclude:
            continue
        if not (lo <= leg["prob"] <= hi):
            continue
        cur = best.get(leg["event_id"])
        if cur is None or (leg["prob"], leg["books"]) > (cur["prob"], cur["books"]):
            best[leg["event_id"]] = leg
    return sorted(best.values(), key=lambda l: (-l["prob"], -l["books"], l["commence_time"]))


def build_coupons(legs: list[dict], tiers: dict) -> list[dict]:
    """
    لكل قسيمة: الاحتمال المستهدف لكل توقع = (الاحتمال الكلي المستهدف) ^ (1 / عدد التوقعات).
    من كل مباراة بناخذ التوقع الأقرب للهدف، وما بنحط مباراتين من نفس المباراة بنفس القسيمة.
    بنفضّل مباريات ما انستخدمت بقسيمة قبلها، وما بنكرر نفس نوع السوق أكثر من مرتين.
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
            score = (abs(leg["prob"] - target), -leg["books"])
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
        for leg in ranked:  # إذا ما كفّى، بنرخي شرط تنويع الأسواق
            if len(chosen) >= k:
                break
            if leg not in chosen:
                chosen.append(leg)

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


# ---------------------------------------------------------------- predict

def predict(api: OddsApi, cfg: dict, now: datetime) -> tuple[list[dict], dict]:
    sports = api.get("/sports") or []  # مجاني
    active = {s["key"]: s for s in sports if s.get("active") and not s.get("has_outrights")}
    keys = [k for k in cfg["soccer_leagues"] + cfg["basketball_leagues"] if k in active]
    tennis = sorted(k for k in active if k.startswith("tennis_")) if cfg.get("include_all_active_tennis") else []

    window = {
        "commenceTimeFrom": now.strftime(ISO),
        "commenceTimeTo": (now + timedelta(hours=cfg["window_hours"])).strftime(ISO),
    }
    regions = cfg["regions"]
    n_regions = len(regions.split(","))

    featured: list[tuple[str, dict]] = []  # (sport_key, event with bookmakers)
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
        events = api.get(f"/sports/{key}/events", **window)  # مجاني
        if not events:
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

    # أسواق إضافية (الفريقين بيسجلوا، كل خطوط الأهداف...) لأقوى المباريات
    def fav_strength(item):
        key, ev = item
        legs = event_legs(ev, key, "", ev.get("bookmakers", []), cfg)
        return max((l["prob"] for l in legs if l["market"] == "h2h"), default=0)

    deep_pool = [it for it in featured if cfg["markets"][group_of(it[0])]["extra"]]
    deep_pool.sort(key=fav_strength, reverse=True)
    deep_done = 0
    for key, ev in deep_pool:
        if deep_done >= cfg.get("extra_markets_events_per_run", 0):
            break
        mk = cfg["markets"][group_of(key)]["extra"]
        cost = len(mk.split(",")) * n_regions
        if not api.can_spend(cost):
            break
        extra = api.get(f"/sports/{key}/events/{ev['id']}/odds", cost=cost, regions=regions, markets=mk, oddsFormat="decimal")
        if extra and extra.get("bookmakers"):
            ev["bookmakers"] = ev.get("bookmakers", []) + extra["bookmakers"]
        deep_done += 1

    legs = []
    for key, ev in featured:
        legs.extend(event_legs(ev, key, active[key].get("title", key), ev.get("bookmakers", []), cfg))
    stats = {"events": len(featured), "legs": len(legs), "deep_events": deep_done,
             "markets": sorted({l["market"] for l in legs})}
    log(f"  {stats['events']} مباراة، {stats['legs']} توقع ممكن، أسواق إضافية لـ{deep_done} مباراة.")
    return legs, stats


# ---------------------------------------------------------------- grading

SCORE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*$")


def grade_leg(leg: dict, hs: float, as_: float) -> str:
    home, away = leg["home"], leg["away"]
    m, n, pt, desc = leg["market"], leg["name"], leg["point"], leg["description"]
    winner = home if hs > as_ else away if as_ > hs else "Draw"
    leg["score"] = f"{hs:g}-{as_:g}"
    if m == "h2h":
        return "hit" if winner == n else "miss"
    if m == "double_chance":
        ok = winner != "Draw" if n == "No Draw" else winner in (n, "Draw")
        return "hit" if ok else "miss"
    if m == "btts":
        both = hs > 0 and as_ > 0
        return "hit" if (n == "Yes") == both else "miss"
    if m == "totals":
        diff = (hs + as_ - pt) if n == "Over" else (pt - hs - as_)
    elif m == "team_totals":
        ts = hs if desc == home else as_
        diff = (ts - pt) if n == "Over" else (pt - ts)
    elif m == "spreads":
        mine, other = (hs, as_) if n == home else (as_, hs)
        diff = mine + pt - other
    else:
        return "void"
    return "hit" if diff > 0 else "void" if diff == 0 else "miss"


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


def check_results(api: OddsApi | None, cfg: dict, history: dict, now: datetime) -> int:
    overrides = load_json(OVERRIDES_FILE, {})
    finals: dict[str, tuple[float, float]] = {}
    for k, v in overrides.items():
        m = SCORE_RE.match(str(v))
        if m:
            finals[k] = (float(m.group(1)), float(m.group(2)))

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
                new = "void"  # ما توفرت نتيجة: تأجيل، انسحاب، أو الرياضة ما إلها نتائج بالـAPI
            else:
                continue
            if new != leg["result"]:
                leg["result"] = new
                changed += 1
        for c in day.get("coupons", []):
            c["result"] = coupon_result(c)
    log(f"  تحدثت نتائج {changed} توقع.")
    return changed


# ---------------------------------------------------------------- demo data

def _poisson_cdf(k: int, lam: float) -> float:
    return sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(k + 1))


def _poisson_sample(rng: random.Random, lam: float) -> int:
    l, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= l:
            return k
        k += 1


def _norm_cdf(x: float) -> float:
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


def _demo_markets(e) -> tuple[list, tuple[float, float]]:
    """بيرجع (أسواق بشكل الـAPI لشركة وحدة عادلة، دالة نتيجة)."""
    group, _, _, home, away, a, b = e
    mk = []
    if group == "soccer":
        lh, la = a, b
        ph = pd = 0.0
        for i in range(12):
            for j in range(12):
                p = (math.exp(-lh) * lh ** i / math.factorial(i)) * (math.exp(-la) * la ** j / math.factorial(j))
                if i > j:
                    ph += p
                elif i == j:
                    pd += p
        pa = 1 - ph - pd
        mk.append(("h2h", [(home, None, None, ph), ("Draw", None, None, pd), (away, None, None, pa)]))
        for line in (0.5, 1.5, 2.5, 3.5, 4.5):
            under = _poisson_cdf(int(line), lh + la)
            mk.append(("alternate_totals", [("Over", line, None, 1 - under), ("Under", line, None, under)]))
        btts = (1 - math.exp(-lh)) * (1 - math.exp(-la))
        mk.append(("btts", [("Yes", None, None, btts), ("No", None, None, 1 - btts)]))
        for line in (0.5, 1.5):
            u = _poisson_cdf(int(line), lh)
            mk.append(("team_totals", [("Over", line, home, 1 - u), ("Under", line, home, u)]))
        diff_ge2 = sum((math.exp(-lh) * lh ** i / math.factorial(i)) * (math.exp(-la) * la ** j / math.factorial(j))
                       for i in range(12) for j in range(12) if i - j >= 2)
        mk.append(("alternate_spreads", [(home, -1.5, None, diff_ge2), (away, 1.5, None, 1 - diff_ge2)]))
    elif group == "basketball":
        mu, tot, sd_m, sd_t = a, b, 12.0, 17.0
        ph = 1 - _norm_cdf(-mu / sd_m)
        mk.append(("h2h", [(home, None, None, ph), (away, None, None, 1 - ph)]))
        for line in (-0.5 - round(mu) + k * 4 for k in range(-2, 4)):
            p = 1 - _norm_cdf((-line - mu) / sd_m)
            mk.append(("alternate_spreads", [(home, line, None, p), (away, -line, None, 1 - p)]))
        for line in (round(tot) + 0.5 + k * 8 for k in range(-3, 3)):
            under = _norm_cdf((line - tot) / sd_t)
            mk.append(("alternate_totals", [("Over", line, None, 1 - under), ("Under", line, None, under)]))
    else:
        mk.append(("h2h", [(home, None, None, a), (away, None, None, 1 - a)]))
    return mk


def _demo_score(e, rng: random.Random) -> tuple[float, float]:
    group, _, _, _, _, a, b = e
    if group == "soccer":
        return float(_poisson_sample(rng, a)), float(_poisson_sample(rng, b))
    if group == "basketball":
        margin, tot = rng.gauss(a, 12), rng.gauss(b, 17)
        h = round((tot + margin) / 2)
        return float(h), float(round(tot) - h)
    return (2.0, rng.choice([0.0, 1.0])) if rng.random() < a else (rng.choice([0.0, 1.0]), 2.0)


def demo_day(day: datetime, rng: random.Random, cfg: dict, resolve: bool) -> dict:
    pool = rng.sample(DEMO_EVENTS, 12)
    legs, scores = [], {}
    for i, e in enumerate(pool):
        group, key, league, home, away = e[:5]
        kickoff = day.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=11 + i)
        ev_id = f"demo-{day:%Y%m%d}-{i}"
        books = []
        for bk in range(rng.randint(6, 14)):
            markets = []
            for mkey, outs in _demo_markets(e):
                margin = 1.05 + rng.uniform(-0.01, 0.02)
                markets.append({"key": mkey, "outcomes": [
                    {"name": n, "point": pt, "description": d,
                     "price": round(1 / max(0.003, min(0.997, p * margin * rng.uniform(0.985, 1.015))), 3)}
                    for n, pt, d, p in outs]})
            books.append({"key": f"book{bk}", "markets": markets})
        ev = {"id": ev_id, "home_team": home, "away_team": away,
              "commence_time": kickoff.astimezone(timezone.utc).strftime(ISO)}
        legs.extend(event_legs(ev, key, league, books, cfg))
        scores[ev_id] = _demo_score(e, random.Random(zlib.crc32(ev_id.encode())))
    out = {"date": day.strftime("%Y-%m-%d"), "top": top_list(legs, cfg["top_list_size"]),
           "coupons": build_coupons(legs, cfg["coupons"])}
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

def main() -> int:
    ap = argparse.ArgumentParser(description="قائمة الثقة اليومية")
    ap.add_argument("--demo", action="store_true", help="بيانات تجريبية بدون مفتاح API")
    ap.add_argument("--no-results", action="store_true", help="لا تحدّث نتائج الأيام الماضية")
    ap.add_argument("--results-only", action="store_true", help="حدّث النتائج بس")
    args = ap.parse_args()

    now = datetime.now(timezone.utc).replace(microsecond=0)
    cfg = load_json(CONFIG_FILE, None)
    if cfg is None:
        raise SystemExit("ما لقيت config.json")
    if args.demo:
        build_demo(now, cfg)
        return 0

    key = os.environ.get("ODDS_API_KEY", "").strip()
    if not key:
        raise SystemExit("لازم تحط مفتاح ODDS_API_KEY (من the-odds-api.com).")

    api = OddsApi(key, cfg.get("min_credits_reserve", 20), cfg.get("max_credits_per_run", 16))
    history = load_json(HISTORY_FILE, {"days": []})
    # نشيل البيانات التجريبية والصيغة القديمة أول ما يشتغل بمفتاح حقيقي
    history["days"] = [d for d in history.get("days", [])
                       if "coupons" in d and not any(str(l["id"]).startswith("demo-") for l in all_legs(d))]

    try:
        if cfg.get("check_results", True) and not args.no_results:
            log("بفحص نتائج الأيام الماضية...")
            check_results(api, cfg, history, now)
        if not args.results_only:
            log("بجهّز قسائم اليوم...")
            legs, stats = predict(api, cfg, now)
            date = now.astimezone(AMMAN).strftime("%Y-%m-%d")
            day = {"date": date, "top": top_list(legs, cfg["top_list_size"]),
                   "coupons": build_coupons(legs, cfg["coupons"])}
            history["days"] = [d for d in history["days"] if d["date"] != date]
            if day["top"]:
                history["days"].append(day)
            save_json(TODAY_FILE, {"date": date, "generated_at": now.strftime(ISO), "demo": False,
                                   "coupons": day["coupons"], "top": day["top"], "stats": stats})
    except BudgetExhausted as e:
        log(f"توقفت: {e}")
    finally:
        history["days"].sort(key=lambda d: d["date"])
        save_json(HISTORY_FILE, history)
        log(f"صرفت {api.spent:.0f} كريدت. المتبقي: {api.remaining}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
