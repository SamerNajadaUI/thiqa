"""
قعدة المحللين

5 شخصيات بتحكي عن كل توقع، كل وحدة من زاويتها، وكلها بتشتغل على نفس الأرقام الحقيقية:
  1. المتعصب      2. المتشائم      3. الحالم (بيراهن على المستحيل)
  4. المتحفظ (بيخاف من الـ50/50)      5. المنطقي (أرقام وتاريخ)
بعدين 3 حكام بيقيّموا كلامهم:
  حكم الأدلة، حكم المخاطرة، حكم السوق (وين رايحة الفلوس)
وبالآخر القاضي بيطلع الحكم الصافي: مع / بحذر / ضد.
حكم القاضي بيدخل فعلاً باختيار القسائم.

الدوال هون نقية (بدون شبكة)، فبنقدر نحسبها لأي توقع محفوظ.
"""
from __future__ import annotations

WITH, CAUTION, AGAINST = 1, 0, -1
FSI, PDI = "⁨", "⁩"


def nm(x) -> str:
    return f"{FSI}{x}{PDI}"


def pc(p: float) -> str:
    return f"{p * 100:.0f}%"


def odds(p: float) -> str:
    return f"{1 / max(p, 0.001):.2f}"


def _num(x: float) -> str:
    return f"{x:g}"


def label(l: dict) -> str:
    m, n, pt, d = l["market"], l["name"], l.get("point"), l.get("description")
    unit = "نقطة" if l["group"] == "basketball" else "أهداف"
    if m == "h2h":
        return "تعادل" if n == "Draw" else f"فوز {nm(n)}"
    if m == "double_chance":
        return "ما في تعادل" if n == "No Draw" else f"{nm(n)} ما بيخسر"
    if m == "btts":
        return "الفريقين بيسجلوا" if n == "Yes" else "مش الفريقين بيسجلوا"
    if m == "totals":
        return f"{'أكثر' if n == 'Over' else 'أقل'} من {_num(pt)} {unit}"
    if m == "team_totals":
        return f"{nm(d)} {'أكثر' if n == 'Over' else 'أقل'} من {_num(pt)}"
    if m == "spreads":
        return f"{nm(n)} هانديكاب {'+' if pt > 0 else ''}{_num(pt)}"
    return m


def opposite(l: dict) -> str:
    m, n, pt, d = l["market"], l["name"], l.get("point"), l.get("description")
    other = l["away"] if n == l["home"] else l["home"]
    unit = "نقطة" if l["group"] == "basketball" else "أهداف"
    if m == "h2h":
        if l["group"] == "soccer" and n != "Draw":
            return f"{nm(other)} ما بيخسر"
        return f"فوز {nm(other)}" if n != "Draw" else "فريق يفوز"
    if m == "double_chance":
        return "تعادل" if n == "No Draw" else f"فوز {nm(other)}"
    if m == "btts":
        return "فريق على الأقل ما بيسجل" if n == "Yes" else "الفريقين بيسجلوا"
    if m == "totals":
        return f"{'أقل' if n == 'Over' else 'أكثر'} من {_num(pt)} {unit}"
    if m == "team_totals":
        return f"{nm(d)} {'أقل' if n == 'Over' else 'أكثر'} من {_num(pt)}"
    if m == "spreads":
        return f"{nm(other)} هانديكاب {'+' if -pt > 0 else ''}{_num(-pt)}"
    return "العكس"


def backed_team(l: dict):
    if l["market"] in ("h2h", "double_chance", "spreads") and l["name"] not in ("Draw", "No Draw"):
        return l["name"]
    if l["market"] == "team_totals":
        return l.get("description")
    return None


def flags(l: dict) -> set[str]:
    """إشارات من الأرقام المحفوظة (وبيكمّلها نص التحذيرات للتوقعات القديمة)."""
    f = set(l.get("flags") or [])
    pm, sp, cp, mp, mv = l.get("market_prob"), l.get("sharp_prob"), l.get("crowd_prob"), l.get("model_prob"), l.get("movement")
    vol = l.get("crowd_volume") or 0
    if sp is not None and pm is not None:
        f.add("sharp_with" if sp >= pm - 0.01 else "sharp_against")
    if cp is not None and pm is not None and vol >= 3000:
        f.add("crowd_with" if cp >= pm - 0.02 else "crowd_against")
        if cp < pm - 0.04:
            f.add("crowd_upset")
    if mp is not None and pm is not None:
        f.add("model_with" if mp >= pm - 0.03 else "model_against")
    if mv is not None and abs(mv) >= 0.01:
        f.add("money_in" if mv > 0 else "money_out")
    for w in l.get("warnings") or []:
        if "أعلى من معدله" in w:
            f.add("hot_streak")
        if "أقل من مستواه الحقيقي" in w:
            f.add("opp_bounce")
        if "بترجع لطبيعتها" in w:
            f.add("goals_regress")
    return f


def _stat_reason(l: dict):
    """أول سبب إحصائي (فيه أرقام) بعد أسباب السوق."""
    for r in (l.get("reasons") or [])[1:]:
        skip = ("شركات", "شركة", "Polymarket", "الأدق", "احتماله", "نموذجنا")
        if any(ch.isdigit() for ch in r) and not any(x in r for x in skip):
            return r
    return None


# ---------------------------------------------------------------- personas

def fan(l, f):
    p = l["prob"]
    team = backed_team(l)
    conf = min(0.99, p + 0.12)
    why = _stat_reason(l) or ((l.get("reasons") or [""])[0])
    if team:
        t = f"{nm(team)} ما في منه! {why}. يا عمي {label(l)} مضمونة، أنا بعطيها {pc(conf)}."
    else:
        t = f"هاي المباراة رح تولّع! {label(l)} أكيد. {why}."
    return {"k": "fan", "v": WITH, "c": round(conf, 3), "t": t}


def pessimist(l, f):
    p = l["prob"]
    lose = 1 - p
    n = max(2, round(1 / max(lose, 0.01)))
    ws = l.get("warnings") or []
    if ws:
        t = f"دايماً في مشكلة: {ws[0]}. وفوق هيك، احتمال إنها تخيب {pc(lose)}، يعني تقريباً مرة من كل {n}."
    else:
        t = f"ماشي، كل شي شكله تمام. بس احتمال إنها تخيب {pc(lose)}، يعني مرة من كل {n}، وأنا دايماً بطلع بهديك المرة."
    v = AGAINST if (ws and p < 0.85) or p < 0.7 else CAUTION
    return {"k": "pessimist", "v": v, "c": round(1 - p, 3), "t": t}


def dreamer(l, f):
    p = l["prob"]
    opp = opposite(l)
    extra = " وحتى جمهور Polymarket شايف في مفاجأة!" if "crowd_upset" in f else ""
    t = (f"شو بدي بـ«{label(l)}» وأودزها {odds(p)}؟ أنا رايح على «{opp}» بأودز {odds(1 - p)}. "
         f"الكورة ما إلها كبير، وكم مرة شفنا المستحيل يصير.{extra}")
    return {"k": "dreamer", "v": AGAINST, "c": round(1 - p, 3), "t": t}


def conservative(l, f):
    p = l["prob"]
    against = {"sharp_against", "crowd_against", "model_against", "money_out"} & f
    if p < 0.62:
        return {"k": "careful", "v": AGAINST, "c": round(p, 3),
                "t": f"هاي قريبة من 50/50 ({pc(p)}). أنا ما بلعب بالنار، بعيد عنها."}
    if p < 0.78 or against:
        extra = " وكمان في إشارة ضدها." if against else ""
        return {"k": "careful", "v": CAUTION, "c": round(p, 3),
                "t": f"احتمالها {pc(p)}، مش سيئة بس مش مريحة.{extra} بحطها بس بقسيمة صغيرة."}
    return {"k": "careful", "v": WITH, "c": round(p, 3),
            "t": f"{pc(p)} وكل الإشارات متفقة. هاي من النوع اللي بنام عليه وأنا مرتاح."}


def logical(l, f):
    p = l["prob"]
    sup, sig = l.get("support", 0), l.get("signals", 0)
    ratio = sup / sig if sig else 0.5
    parts = [f"بالأرقام: {sup} من {sig} إشارات معه." if sig else "ما في إلا رأي السوق لهالمباراة."]
    mp, pm = l.get("model_prob"), l.get("market_prob")
    if mp is not None:
        parts.append(f"نموذج الأهداف بيعطيه {pc(mp)} والسوق {pc(pm)}.")
    st = _stat_reason(l)
    if st:
        parts.append(st + ".")
    elif mp is None:
        parts.append(f"السوق بيعطيه {pc(pm)}" + (f"، والشركات الأدق {pc(l['sharp_prob'])}" if l.get("sharp_prob") is not None else "")
                     + (f"، والجمهور العالمي {pc(l['crowd_prob'])}" if l.get("crowd_prob") is not None else "") + ".")
    if "hot_streak" in f:
        parts.append("بس انتبهوا: الفورمة الأخيرة أعلى من مستوى الفريق الحقيقي، وهاي عادة ما بتدوم.")
    if "opp_bounce" in f:
        parts.append("والخصم نتائجه الأخيرة أقل من مستواه، وممكن يرجع.")
    if not l.get("eligible", True) or (sig >= 2 and ratio < 0.5):
        v = AGAINST
    elif ratio >= 0.6 and sig >= 2 and (mp is None or mp >= pm - 0.03) and p >= 0.7 and "hot_streak" not in f:
        v = WITH
    else:
        v = CAUTION
    return {"k": "logic", "v": v, "c": round(p, 3), "t": " ".join(parts)}


PERSONAS = (fan, pessimist, dreamer, conservative, logical)


# ---------------------------------------------------------------- judges

def _best(scores: dict) -> str:
    return max(scores, key=lambda k: scores[k])


def judge_evidence(l, f, ps):
    logic = next(x for x in ps if x["k"] == "logic")
    ws = l.get("warnings") or []
    ratio = l.get("support", 0) / l["signals"] if l.get("signals") else 0.5
    scores = {"logic": 9, "careful": 6, "pessimist": 7 if ws else 4,
              "fan": 3 if ratio >= 0.8 else 2, "dreamer": 3 if l["prob"] < 0.6 else 1}
    v = logic["v"]
    t = {WITH: "الأرقام بتدعم التوقع، وأقوى كلام كان كلام المنطقي لأنه مبني على إحصائيات مش على عواطف.",
         CAUTION: "الأدلة مختلطة: في أرقام معه وفي أرقام ضده. كلام المنطقي هو الأقرب للحقيقة.",
         AGAINST: "الأدلة ضعيفة أو ضد التوقع. المتعصب حكى بعاطفة، والأرقام ما بتسنده."}[v]
    return {"k": "evidence", "v": v, "best": _best(scores), "s": scores, "t": t}


def judge_risk(l, f, ps):
    p = l["prob"]
    ws = l.get("warnings") or []
    if p < 0.65 or len(ws) >= 2:
        v, t = AGAINST, f"المخاطرة عالية: احتمال الخيبة {pc(1 - p)}" + (f" وفي {len(ws)} تحذيرات." if ws else ".")
    elif p < 0.8 or ws:
        v, t = CAUTION, f"المخاطرة متوسطة: احتمال الخيبة {pc(1 - p)}. المتحفظ والمتشائم معهم حق يحذّروا."
    else:
        v, t = WITH, f"المخاطرة قليلة: احتمال الخيبة {pc(1 - p)} بس، وما في تحذيرات."
    scores = {"careful": 8, "pessimist": 8 if ws else 5, "logic": 7, "fan": 2, "dreamer": 3}
    return {"k": "risk", "v": v, "best": _best(scores), "s": scores, "t": t}


def judge_market(l, f, ps):
    checks = []
    if "sharp_with" in f or "sharp_against" in f:
        checks.append(("sharp_with" in f, "الشركات الأدق"))
    if "crowd_with" in f or "crowd_against" in f:
        checks.append(("crowd_with" in f, "الجمهور العالمي"))
    if "money_in" in f or "money_out" in f:
        checks.append(("money_in" in f, "حركة الأودز"))
    agree = sum(1 for ok, _ in checks if ok)
    total = len(checks)
    if not total:
        v, t = CAUTION, "ما في معلومات كافية عن وين رايحة الفلوس بهالمباراة."
    elif agree == total and l["prob"] >= 0.7:
        v, t = WITH, "الفلوس كلها بنفس الاتجاه: " + " و".join(n for _, n in checks) + " مع التوقع."
    elif agree / total < 0.5 or "money_out" in f and (l.get("movement") or 0) <= -0.03:
        v, t = AGAINST, "الفلوس مش مع التوقع: " + " و".join(n for ok, n in checks if not ok) + " ضده."
    else:
        v, t = CAUTION, f"الفلوس مقسومة: {agree} من {total} مع التوقع."
    scores = {"logic": 7, "pessimist": 5, "careful": 5,
              "fan": 4 if agree == total and total else 1, "dreamer": 6 if "crowd_upset" in f else 1}
    return {"k": "market", "v": v, "best": _best(scores), "s": scores, "t": t}


JUDGES = (judge_evidence, judge_risk, judge_market)
JUDGE_WEIGHTS = {"evidence": 0.4, "risk": 0.3, "market": 0.3}
NAMES = {"fan": "المتعصب", "pessimist": "المتشائم", "dreamer": "الحالم", "careful": "المتحفظ", "logic": "المنطقي"}


def build(l: dict) -> dict:
    f = flags(l)
    ps = [fn(l, f) for fn in PERSONAS]
    js = [fn(l, f, ps) for fn in JUDGES]
    avg = {p["k"]: sum(j["s"][p["k"]] for j in js) / len(js) for p in ps}
    persona_view = sum(avg[p["k"]] * p["v"] for p in ps) / sum(avg.values())
    value = sum(JUDGE_WEIGHTS[j["k"]] * j["v"] for j in js) + 0.15 * persona_view
    v = WITH if value >= 0.45 else AGAINST if value <= -0.3 else CAUTION
    best = max(avg, key=avg.get)
    p = l["prob"]
    if v == WITH:
        t = f"الصافي: مع. {label(l)} باحتمال {pc(p)}. أقنعني كلام {NAMES[best]}، والحكام متفقين إنه التوقع مسنود."
    elif v == CAUTION:
        worry = next((j["t"] for j in js if j["v"] < WITH), "")
        t = f"الصافي: بحذر. {label(l)} باحتمال {pc(p)}، بس مش للقسيمة الآمنة. {worry}"
    else:
        worry = next((j["t"] for j in js if j["v"] == AGAINST), "")
        t = f"الصافي: ضد. ما بنصح بـ{label(l)}. {worry}"
    return {"p": ps, "j": [{k: j[k] for k in ("k", "v", "best", "t")} for j in js],
            "q": {"v": v, "best": best, "t": t, "score": round(value, 3)}}


def attach(legs: list[dict], only_missing: bool = False) -> int:
    n = 0
    for l in legs:
        if only_missing and l.get("panel"):
            continue
        try:
            l["panel"] = build(l)
            n += 1
        except Exception:  # توقع ناقص معلومات: بدون قعدة
            pass
    return n


def verdict(l: dict) -> int:
    return (l.get("panel") or {}).get("q", {}).get("v", CAUTION)
