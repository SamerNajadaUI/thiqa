"""
طبقة التحليل

- خصائص كل فريق من مبارياته الحقيقية بالموسم: الأرض/برّا، آخر 5، الراحة، الترتيب، المواجهات.
- نموذج أهداف (Poisson مع تصحيح Dixon-Coles) بيحسب احتمال كل سوق.
- دمج النموذج مع رأي السوق والشركات الأدق.
- إشارات داعمة/معاكسة، وأسباب وتحذيرات بالعربي بأرقام حقيقية.

ما في أي شبكة هون: كل شي دوال على بيانات جاهزة، عشان نقدر نختبرها.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

FSI, PDI = "⁨", "⁩"  # عزل أسماء الفرق الإنجليزية جوّا النص العربي


def nm(name: str) -> str:
    return f"{FSI}{name}{PDI}"


def p100(p: float) -> str:
    return f"{p * 100:.0f}%"


def f1(x: float) -> str:
    return f"{x:.1f}"


# ---------------------------------------------------------------- match records

@dataclass
class Match:
    date: datetime
    comp: str
    season: int
    home_id: str
    away_id: str
    home: str
    away: str
    hg: int | None = None
    ag: int | None = None

    @property
    def finished(self) -> bool:
        return self.hg is not None and self.ag is not None


@dataclass
class TeamForm:
    team_id: str
    name: str
    played_home: int = 0
    played_away: int = 0
    gf_home: float = 0.0
    ga_home: float = 0.0
    gf_away: float = 0.0
    ga_away: float = 0.0
    w_home: int = 0
    d_home: int = 0
    l_home: int = 0
    w_away: int = 0
    d_away: int = 0
    l_away: int = 0
    fts_home: int = 0   # ما سجل
    fts_away: int = 0
    cs_home: int = 0    # شباك نظيفة
    cs_away: int = 0
    last5: list = field(default_factory=list)  # [(result W/D/L, gf, ga)]
    rest_days: float | None = None
    venue_totals: dict = field(default_factory=dict)  # "home"/"away" -> [مجموع الأهداف]
    venue_margins: dict = field(default_factory=dict)  # "home"/"away" -> [فارق الأهداف لصالح الفريق]
    venue_scored: dict = field(default_factory=dict)   # "home"/"away" -> [أهداف الفريق]

    @property
    def n5(self) -> int:
        return len(self.last5)

    @property
    def last5_gf(self) -> float:
        return sum(x[1] for x in self.last5) / self.n5 if self.n5 else 0.0

    @property
    def last5_ga(self) -> float:
        return sum(x[2] for x in self.last5) / self.n5 if self.n5 else 0.0

    @property
    def last5_points(self) -> int:
        return sum(3 if r == "W" else 1 if r == "D" else 0 for r, _, _ in self.last5)

    def last5_counts(self) -> tuple[int, int, int]:
        rs = [r for r, _, _ in self.last5]
        return rs.count("W"), rs.count("D"), rs.count("L")


def team_form(team_id: str, name: str, matches: list[Match], kickoff: datetime, season: int) -> TeamForm:
    tf = TeamForm(team_id, name)
    mine = sorted((m for m in matches if m.finished and m.date < kickoff and team_id in (m.home_id, m.away_id)),
                  key=lambda m: m.date)
    cur = [m for m in mine if m.season == season]
    for venue in ("home", "away"):
        tf.venue_totals[venue], tf.venue_margins[venue], tf.venue_scored[venue] = [], [], []
    gfh = gah = gfa = gaa = 0
    for m in cur:
        at_home = m.home_id == team_id
        gf, ga = (m.hg, m.ag) if at_home else (m.ag, m.hg)
        v = "home" if at_home else "away"
        tf.venue_totals[v].append(gf + ga)
        tf.venue_margins[v].append(gf - ga)
        tf.venue_scored[v].append(gf)
        res = "W" if gf > ga else "D" if gf == ga else "L"
        if at_home:
            tf.played_home += 1; gfh += gf; gah += ga
            tf.w_home += res == "W"; tf.d_home += res == "D"; tf.l_home += res == "L"
            tf.fts_home += gf == 0; tf.cs_home += ga == 0
        else:
            tf.played_away += 1; gfa += gf; gaa += ga
            tf.w_away += res == "W"; tf.d_away += res == "D"; tf.l_away += res == "L"
            tf.fts_away += gf == 0; tf.cs_away += ga == 0
    if tf.played_home:
        tf.gf_home, tf.ga_home = gfh / tf.played_home, gah / tf.played_home
    if tf.played_away:
        tf.gf_away, tf.ga_away = gfa / tf.played_away, gaa / tf.played_away
    for m in mine[-5:]:
        at_home = m.home_id == team_id
        gf, ga = (m.hg, m.ag) if at_home else (m.ag, m.hg)
        tf.last5.append(("W" if gf > ga else "D" if gf == ga else "L", gf, ga))
    if mine:
        tf.rest_days = (kickoff - mine[-1].date).total_seconds() / 86400
    return tf


def league_table(matches: list[Match], comp: str, season: int, kickoff: datetime) -> dict[str, tuple[int, int, int]]:
    """team_id -> (المركز، النقاط، عدد المباريات) محسوب من نتائج الدوري."""
    pts: dict[str, list[int]] = {}
    for m in matches:
        if m.comp != comp or m.season != season or not m.finished or m.date >= kickoff:
            continue
        for tid, gf, ga in ((m.home_id, m.hg, m.ag), (m.away_id, m.ag, m.hg)):
            row = pts.setdefault(tid, [0, 0, 0, 0])  # points, gd, gf, played
            row[0] += 3 if gf > ga else 1 if gf == ga else 0
            row[1] += gf - ga
            row[2] += gf
            row[3] += 1
    order = sorted(pts.items(), key=lambda kv: (-kv[1][0], -kv[1][1], -kv[1][2]))
    return {tid: (i + 1, row[0], row[3]) for i, (tid, row) in enumerate(order)}


def league_averages(matches: list[Match], comp: str, season: int, kickoff: datetime) -> tuple[float, float, int]:
    ms = [m for m in matches if m.comp == comp and m.season == season and m.finished and m.date < kickoff]
    n = len(ms)
    if not n:
        return 1.50, 1.20, 0
    lh = sum(m.hg for m in ms) / n
    la = sum(m.ag for m in ms) / n
    k = 30  # بنقرّب للمتوسط العام إذا الموسم لسا بأوله
    return (lh * n + 1.50 * k) / (n + k), (la * n + 1.20 * k) / (n + k), n


def head_to_head(matches: list[Match], a: str, b: str, kickoff: datetime, limit: int = 6) -> list[Match]:
    hs = [m for m in matches if m.finished and m.date < kickoff and {m.home_id, m.away_id} == {a, b}]
    return sorted(hs, key=lambda m: m.date)[-limit:]


# ---------------------------------------------------------------- goal model

def _pois(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _shrunk_ratio(avg: float, n: int, base: float, k: float = 5.0) -> float:
    if base <= 0:
        return 1.0
    return ((avg / base) * n + k) / (n + k)


@dataclass
class MatchContext:
    home: TeamForm
    away: TeamForm
    lh_league: float
    la_league: float
    league_n: int
    table: dict
    h2h: list
    lam_h: float = 0.0
    lam_a: float = 0.0
    grid: list = field(default_factory=list)
    notes: list = field(default_factory=list)  # تعديلات النموذج (تعب، فورمة)

    @property
    def sample(self) -> int:
        return min(self.home.played_home + self.home.played_away, self.away.played_home + self.away.played_away)


def build_model(ctx: MatchContext, rho: float = -0.08) -> MatchContext:
    h, a = ctx.home, ctx.away
    Lh, La = ctx.lh_league, ctx.la_league
    lam_h = Lh * _shrunk_ratio(h.gf_home, h.played_home, Lh) * _shrunk_ratio(a.ga_away, a.played_away, Lh)
    lam_a = La * _shrunk_ratio(a.gf_away, a.played_away, La) * _shrunk_ratio(h.ga_home, h.played_home, La)

    base = (Lh + La) / 2
    if h.n5 >= 3 and a.n5 >= 3:
        lam_h *= (_shrunk_ratio(h.last5_gf, h.n5, base) * _shrunk_ratio(a.last5_ga, a.n5, base)) ** 0.25
        lam_a *= (_shrunk_ratio(a.last5_gf, a.n5, base) * _shrunk_ratio(h.last5_ga, h.n5, base)) ** 0.25

    hr, ar = h.rest_days, a.rest_days
    if hr is not None and ar is not None:
        if hr <= 3.2 and ar >= 5:
            lam_h *= 0.96; lam_a *= 1.04
            ctx.notes.append(("tired", "home"))
        elif ar <= 3.2 and hr >= 5:
            lam_a *= 0.96; lam_h *= 1.04
            ctx.notes.append(("tired", "away"))

    ctx.lam_h = min(4.5, max(0.15, lam_h))
    ctx.lam_a = min(4.5, max(0.15, lam_a))

    g = [[_pois(i, ctx.lam_h) * _pois(j, ctx.lam_a) for j in range(11)] for i in range(11)]
    lh_, la_ = ctx.lam_h, ctx.lam_a
    g[0][0] *= max(0.0, 1 - lh_ * la_ * rho)
    g[0][1] *= max(0.0, 1 + lh_ * rho)
    g[1][0] *= max(0.0, 1 + la_ * rho)
    g[1][1] *= max(0.0, 1 - rho)
    total = sum(map(sum, g))
    ctx.grid = [[x / total for x in row] for row in g]
    return ctx


def _outcome(leg: dict, hs: int, as_: int):
    """1 أصاب، 0 خاب، None ملغى — نفس منطق التصحيح."""
    home, away = leg["home"], leg["away"]
    m, n, pt, desc = leg["market"], leg["name"], leg["point"], leg["description"]
    winner = home if hs > as_ else away if as_ > hs else "Draw"
    if m == "h2h":
        return int(winner == n)
    if m == "double_chance":
        return int(winner != "Draw") if n == "No Draw" else int(winner in (n, "Draw"))
    if m == "btts":
        return int((n == "Yes") == (hs > 0 and as_ > 0))
    if m == "totals":
        diff = (hs + as_ - pt) if n == "Over" else (pt - hs - as_)
    elif m == "team_totals":
        ts = hs if desc == home else as_
        diff = (ts - pt) if n == "Over" else (pt - ts)
    elif m == "spreads":
        mine, other = (hs, as_) if n == home else (as_, hs)
        diff = mine + pt - other
    else:
        return None
    return None if diff == 0 else int(diff > 0)


def model_probability(leg: dict, ctx: MatchContext) -> float | None:
    hit = push = 0.0
    for i, row in enumerate(ctx.grid):
        for j, p in enumerate(row):
            o = _outcome(leg, i, j)
            if o is None:
                push += p
            else:
                hit += p * o
    if push >= 0.999:
        return None
    return hit / (1 - push)


def _logit(p: float) -> float:
    p = min(0.995, max(0.005, p))
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def blend(market: float, model: float | None, weight: float) -> float:
    if model is None or weight <= 0:
        return market
    return _sigmoid((1 - weight) * _logit(market) + weight * _logit(model))


# ---------------------------------------------------------------- reasons

def _rate_text(k: int, n: int) -> str:
    return f"{k} من {n}"


def _team_side(leg: dict, ctx: MatchContext):
    """(فريقنا، الخصم، هل فريقنا صاحب الأرض)"""
    team = leg["name"] if leg["market"] in ("h2h", "double_chance", "spreads") else leg["description"]
    if team == leg["home"]:
        return ctx.home, ctx.away, True
    if team == leg["away"]:
        return ctx.away, ctx.home, False
    return None, None, None


def analyze(leg: dict, ctx: MatchContext | None, cfg: dict) -> dict:
    """بيعبّي leg بـ prob النهائي و model_prob و support و signals و reasons و warnings و eligible."""
    a = cfg.get("analysis", {})
    reasons: list[str] = []
    warns: list[str] = []
    sup = tot = 0

    pm = leg["market_prob"]
    sp = leg.get("sharp_prob")
    base = 0.5 * pm + 0.5 * sp if sp is not None else pm
    nb = leg["books"]
    reasons.append(f"{nb} {'شركات' if 3 <= nb <= 10 else 'شركة'} أودز بتعطيه بالمتوسط {p100(pm)} بعد ما شلنا هامشها")

    if sp is not None:
        tot += 1
        if sp >= pm - 0.01:
            sup += 1
            reasons.append(f"الشركات الأدق بالعالم ({nm("Pinnacle")} و{nm("Betfair")}) بتعطيه {p100(sp)}")
        else:
            warns.append(f"الشركات الأدق بالعالم أقل تفاؤلاً: بتعطيه {p100(sp)}")

    mv = leg.get("movement")
    if mv is not None and abs(mv) >= 0.01:
        tot += 1
        if mv > 0:
            sup += 1
            reasons.append(f"احتماله ارتفع {mv * 100:.1f} نقطة خلال آخر 24 ساعة، يعني في فلوس كبيرة دخلت عليه")
        else:
            warns.append(f"احتماله نزل {-mv * 100:.1f} نقطة خلال آخر 24 ساعة، والسوق بيتحرك ضده")

    model_p = None
    if ctx is not None:
        model_p = model_probability(leg, ctx)
    leg["model_prob"] = round(model_p, 4) if model_p is not None else None

    if model_p is not None:
        tot += 1
        xg = f"متوقع {f1(ctx.lam_h)} أهداف لـ{nm(leg['home'])} و{f1(ctx.lam_a)} لـ{nm(leg['away'])}"
        if model_p >= base - 0.03:
            sup += 1
            reasons.append(f"نموذجنا الإحصائي بيعطيه {p100(model_p)} ({xg})")
        else:
            warns.append(f"نموذجنا الإحصائي أقل تفاؤلاً: {p100(model_p)} ({xg})")
        s, w, t, u = _stat_reasons(leg, ctx)
        reasons += s
        warns += w
        tot += t
        sup += u
        if ctx.sample < 6:
            warns.append("الموسم لسا بأوله، فالإحصائيات مبنية على عدد قليل من المباريات")

    weight = a.get("model_weight", 0.25)
    if ctx is not None:
        weight *= min(1.0, ctx.sample / 8)
    final = blend(base, model_p, weight)

    eligible = True
    if model_p is not None and model_p < base - a.get("max_model_gap", 0.08):
        eligible = False
    if mv is not None and mv <= -a.get("max_market_drop", 0.03):
        eligible = False
    if tot >= 3 and sup / tot < a.get("min_support_ratio", 0.5):
        eligible = False

    leg.update({
        "prob": round(final, 4),
        "support": sup, "signals": tot,
        "reasons": reasons[: a.get("max_reasons", 7)],
        "warnings": warns[:3],
        "eligible": eligible,
    })
    return leg


def _stat_reasons(leg: dict, ctx: MatchContext):
    """أسباب من الإحصائيات حسب نوع السوق. بيرجع (أسباب، تحذيرات، عدد الإشارات، الداعمة)."""
    R, W = [], []
    tot = sup = 0
    h, a = ctx.home, ctx.away
    m, n, pt = leg["market"], leg["name"], leg["point"]

    def signal(ok: bool, good: str, bad: str | None = None):
        nonlocal tot, sup
        tot += 1
        if ok:
            sup += 1
            R.append(good)
        elif bad:
            W.append(bad)

    if m in ("h2h", "double_chance", "spreads") and n != "No Draw" and n != "Draw":
        me, opp, at_home = _team_side(leg, ctx)
        if me is None:
            return R, W, 0, 0
        w5, d5, l5 = me.last5_counts()
        ow5, od5, ol5 = opp.last5_counts()
        if me.n5 >= 3 and opp.n5 >= 3:
            signal(me.last5_points >= opp.last5_points,
                   f"فورمة {nm(me.name)} بآخر 5: {w5} فوز و{d5} تعادل و{l5} خسارة، مقابل {ow5} فوز لـ{nm(opp.name)}",
                   f"فورمة {nm(opp.name)} بآخر 5 أحسن ({ow5} فوز مقابل {w5})")
        if at_home and me.played_home >= 3:
            lose_rate = me.l_home / me.played_home
            signal(lose_rate <= 0.25,
                   f"{nm(me.name)} على أرضه هالموسم: فاز {_rate_text(me.w_home, me.played_home)} وخسر {me.l_home} بس",
                   f"{nm(me.name)} خسر {_rate_text(me.l_home, me.played_home)} على أرضه هالموسم")
        if not at_home and me.played_away >= 3:
            signal(me.l_away / me.played_away <= 0.34,
                   f"{nm(me.name)} برّا أرضه هالموسم: فاز {_rate_text(me.w_away, me.played_away)} وخسر {me.l_away}",
                   f"{nm(me.name)} خسر {_rate_text(me.l_away, me.played_away)} برّا أرضه")
        if opp.played_home + opp.played_away >= 3:
            ow, ol = (opp.w_away, opp.l_away) if at_home else (opp.w_home, opp.l_home)
            op = opp.played_away if at_home else opp.played_home
            if op >= 3:
                where = "برّا أرضه" if at_home else "على أرضه"
                signal(ow / op <= 0.34,
                       f"{nm(opp.name)} {where}: فاز {_rate_text(ow, op)} بس",
                       f"{nm(opp.name)} قوي {where}: فاز {_rate_text(ow, op)}")
        r1, r2 = ctx.table.get(me.team_id), ctx.table.get(opp.team_id)
        if r1 and r2 and r1[2] >= 3:
            signal(r1[0] < r2[0],
                   f"{nm(me.name)} بالمركز {r1[0]} ({r1[1]} نقطة)، و{nm(opp.name)} بالمركز {r2[0]} ({r2[1]} نقطة)",
                   f"{nm(opp.name)} أعلى بالترتيب (المركز {r2[0]} مقابل {r1[0]})")
        if len(ctx.h2h) >= 3:
            w = sum(1 for x in ctx.h2h if (x.home_id == me.team_id and x.hg > x.ag) or (x.away_id == me.team_id and x.ag > x.hg))
            d = sum(1 for x in ctx.h2h if x.hg == x.ag)
            l = len(ctx.h2h) - w - d
            ok = (l == 0 or (w >= 2 * l)) if m != "double_chance" else l <= len(ctx.h2h) / 3
            signal(ok, f"بآخر {len(ctx.h2h)} مواجهات بينهم: {nm(me.name)} فاز {w} وتعادل {d} وخسر {l}",
                   f"المواجهات المباشرة مش لصالحه: خسر {l} من آخر {len(ctx.h2h)}")
        if m == "spreads" and pt is not None and pt < 0:
            margins = me.venue_margins["home" if at_home else "away"]
            if len(margins) >= 3:
                need = -pt
                k = sum(1 for x in margins if x > need)
                signal(k / len(margins) >= 0.5,
                       f"{nm(me.name)} فاز بفارق أكثر من {need:g} بـ{_rate_text(k, len(margins))} مباريات {'على أرضه' if at_home else 'برّا'}",
                       f"{nm(me.name)} فاز بفارق كبير بـ{_rate_text(k, len(margins))} بس")

    elif m == "double_chance" and n == "No Draw":
        dh = h.d_home + h.d_away
        da = a.d_home + a.d_away
        ph = h.played_home + h.played_away
        pa = a.played_home + a.played_away
        if ph >= 4 and pa >= 4:
            rate = (dh + da) / (ph + pa)
            signal(rate <= 0.25, f"التعادل قليل عند الفريقين: {dh + da} تعادلات من {ph + pa} مباراة",
                   f"الفريقين بيتعادلوا كثير: {dh + da} من {ph + pa}")

    elif m == "totals" and pt is not None:
        over = n == "Over"
        hv, av = h.venue_totals["home"], a.venue_totals["away"]
        if h.played_home >= 3:
            R.append(f"{nm(h.name)} على أرضه: بيسجل {f1(h.gf_home)} وبيستقبل {f1(h.ga_home)} بالمباراة")
        if a.played_away >= 3:
            R.append(f"{nm(a.name)} برّا أرضه: بيسجل {f1(a.gf_away)} وبيستقبل {f1(a.ga_away)} بالمباراة")
        both = hv + av
        if len(both) >= 6:
            k = sum(1 for x in both if (x > pt if over else x < pt))
            word = "أكثر" if over else "أقل"
            signal(k / len(both) >= leg["market_prob"] - 0.1,
                   f"بـ{_rate_text(k, len(both))} مباريات إلهم (صاحب الأرض على أرضه والضيف برّا) صار {word} من {pt:g} أهداف",
                   f"بـ{_rate_text(k, len(both))} مباريات بس إلهم صار {word} من {pt:g} أهداف")
        if len(ctx.h2h) >= 3:
            avg = sum(x.hg + x.ag for x in ctx.h2h) / len(ctx.h2h)
            signal(avg > pt if over else avg < pt,
                   f"معدل الأهداف بآخر {len(ctx.h2h)} مواجهات بينهم: {f1(avg)}",
                   f"معدل الأهداف بمواجهاتهم {f1(avg)}، وهاد ضد التوقع")

    elif m == "btts":
        yes = n == "Yes"
        if h.played_home >= 3 and a.played_away >= 3:
            hs = h.played_home - h.fts_home
            as_ = a.played_away - a.fts_away
            R.append(f"{nm(h.name)} سجّل بـ{_rate_text(hs, h.played_home)} مباريات على أرضه، و{nm(a.name)} سجّل بـ{_rate_text(as_, a.played_away)} برّا")
            both_rate = (hs / h.played_home) * (as_ / a.played_away)
            signal(both_rate >= 0.5 if yes else both_rate < 0.5,
                   f"نسبة إنه الاثنين يسجلوا حسب أرقامهم: {p100(both_rate)}",
                   f"أرقامهم بتعطي إنه الاثنين يسجلوا {p100(both_rate)} بس")
            cs = h.cs_home + a.cs_away
            if not yes and cs:
                R.append(f"شباك نظيفة: {nm(h.name)} {h.cs_home} على أرضه، و{nm(a.name)} {a.cs_away} برّا")

    elif m == "team_totals" and pt is not None:
        me, opp, at_home = _team_side(leg, ctx)
        if me is None:
            return R, W, 0, 0
        scored = me.venue_scored["home" if at_home else "away"]
        if len(scored) >= 3:
            over = n == "Over"
            k = sum(1 for x in scored if (x > pt if over else x < pt))
            where = "على أرضه" if at_home else "برّا"
            signal(k / len(scored) >= leg["market_prob"] - 0.1,
                   f"{nm(me.name)} سجّل {'أكثر' if over else 'أقل'} من {pt:g} بـ{_rate_text(k, len(scored))} مباريات {where}",
                   f"{nm(me.name)} سجّل {'أكثر' if over else 'أقل'} من {pt:g} بـ{_rate_text(k, len(scored))} بس")
        conceded = opp.ga_away if at_home else opp.ga_home
        op = opp.played_away if at_home else opp.played_home
        if op >= 3:
            R.append(f"{nm(opp.name)} بيستقبل {f1(conceded)} أهداف بالمباراة {'برّا' if at_home else 'على أرضه'}")

    for kind, side in ctx.notes:
        if kind == "tired":
            tired, fresh = (h, a) if side == "home" else (a, h)
            me, _, _ = _team_side(leg, ctx) if m in ("h2h", "double_chance", "spreads", "team_totals") else (None, None, None)
            text = f"{nm(tired.name)} لعب قبل {tired.rest_days:.0f} أيام بس، و{nm(fresh.name)} مرتاح {fresh.rest_days:.0f} أيام"
            if me is not None:
                (R if me.team_id == fresh.team_id else W).append(text)
            else:
                R.append(text)
    return R, W, tot, sup
