"""Domain-neutral solution archetypes. Each returns an option with code-computed estimates."""
RATINGS = ("impact", "cost", "risk", "speed")


def _shares(analysis):
    groups = analysis.get("groups")
    if groups is None:
        groups = {}
    total = float(analysis.get("total") or 0) or 1.0
    return {str(k): float(v) / total for k, v in groups.items()}


def _rating(value, low, high, invert=False):
    if high == low:
        return 3
    r = 1 + 4 * (value - low) / (high - low)
    if invert:
        r = 5 - r
    return max(1, min(5, int(round(r))))


def _base(name, summary, est_effect, impact, cost, risk, speed):
    return {"name": name, "summary": summary, "est_effect": est_effect,
            "impact": max(1, min(5, int(impact))),
            "cost": max(1, min(5, int(cost))),
            "risk": max(1, min(5, int(risk))),
            "speed": max(1, min(5, int(speed)))}


def target_the_worst(analysis, problem, direction, group_col):
    shares = _shares(analysis)
    if not shares:
        return None
    target = analysis["top"] if direction == "reduce" else analysis["low"]
    share = shares.get(str(target), 0.0)
    impact = _rating(share, min(shares.values()), max(shares.values()))
    effect = f"-{share * 100:.0f}%" if direction == "reduce" else f"+{share * 100:.0f}%"
    return _base(f"Target {target}",
                 f"Focus on {target}, the largest contributor to {problem}.",
                 effect, impact, 4, 3, 3)


def copy_the_best(analysis, problem, direction, group_col):
    shares = _shares(analysis)
    if not shares:
        return None
    best = analysis["low"] if direction == "reduce" else analysis["top"]
    return _base(f"Copy {best}",
                 f"Apply what {best} does well to the other groups.",
                 "moderate", 4, 2, 2, 4)


def spread_evenly(analysis, problem, direction, group_col):
    return _base(f"Spread across {group_col}",
                 f"Distribute effort evenly across all {group_col} groups.",
                 "moderate", 3, 3, 2, 4)


def quick_win_in_one_group(analysis, problem, direction, group_col):
    shares = _shares(analysis)
    if not shares:
        return None
    small = min(shares, key=shares.get)
    return _base(f"Quick win in {small}",
                 f"Start with {small}, the smallest group, for a fast low-risk win.",
                 "small", 2, 1, 1, 5)


def pilot_then_scale(analysis, problem, direction, group_col):
    shares = _shares(analysis)
    if not shares:
        return None
    ordered = sorted(shares, key=shares.get)
    pilot = ordered[len(ordered) // 2] if ordered else None
    return _base(f"Pilot in {pilot}, then scale",
                 f"Test the approach in {pilot} first, then roll out.",
                 "moderate", 4, 3, 2, 2)


def concentrate_on_top_contributors(analysis, problem, direction, group_col):
    shares = _shares(analysis)
    if not shares:
        return None
    ordered = sorted(shares, key=shares.get, reverse=True)
    top = ordered[:2] if len(ordered) > 1 else ordered
    combined = sum(shares[g] for g in top)
    names = " and ".join(top)
    effect = f"-{combined * 100:.0f}%" if direction == "reduce" else f"+{combined * 100:.0f}%"
    return _base(f"Concentrate on {names}",
                 f"Put most effort into the top contributors ({names}), which hold {combined * 100:.0f}% of the total.",
                 effect, 5, 4, 3, 3)


ARCHETYPES = {
    "target_the_worst": target_the_worst,
    "copy_the_best": copy_the_best,
    "spread_evenly": spread_evenly,
    "quick_win_in_one_group": quick_win_in_one_group,
    "pilot_then_scale": pilot_then_scale,
    "concentrate_on_top_contributors": concentrate_on_top_contributors,
}


def select_archetypes(problem_type, analysis, direction):
    """Pick the best 3 archetypes for the problem type and data shape."""
    shares = _shares(analysis)
    n = len(shares)
    max_share = max(shares.values()) if shares else 0
    vals = list(shares.values()) if shares else [0]
    mean = sum(vals) / len(vals) if vals else 0
    var = sum((v - mean) ** 2 for v in vals) / len(vals) if vals else 0
    cv = (var ** 0.5) / mean if mean else 0
    high_spread = cv > 0.6
    low_spread = cv < 0.25
    few_groups = n <= 3
    top_heavy = max_share > 0.4

    if problem_type == "improve":
        if direction == "reduce":
            candidates = ["target_the_worst", "concentrate_on_top_contributors", "copy_the_best",
                          "quick_win_in_one_group", "spread_evenly", "pilot_then_scale"]
        else:
            candidates = ["copy_the_best", "target_the_worst", "concentrate_on_top_contributors",
                          "quick_win_in_one_group", "spread_evenly", "pilot_then_scale"]
    elif problem_type == "prioritise":
        candidates = ["concentrate_on_top_contributors", "target_the_worst", "quick_win_in_one_group",
                      "copy_the_best", "spread_evenly", "pilot_then_scale"]
    elif problem_type == "allocate":
        candidates = ["spread_evenly", "concentrate_on_top_contributors", "pilot_then_scale",
                      "quick_win_in_one_group", "target_the_worst", "copy_the_best"]
    elif problem_type == "diagnose":
        candidates = ["copy_the_best", "target_the_worst", "spread_evenly",
                      "concentrate_on_top_contributors", "quick_win_in_one_group", "pilot_then_scale"]
    else:  # choose
        candidates = ["copy_the_best", "concentrate_on_top_contributors", "quick_win_in_one_group",
                      "target_the_worst", "spread_evenly", "pilot_then_scale"]

    if few_groups:
        candidates = ["pilot_then_scale"] + [c for c in candidates if c != "pilot_then_scale"]
    elif top_heavy:
        candidates = ["concentrate_on_top_contributors"] + [c for c in candidates if c != "concentrate_on_top_contributors"]
    elif high_spread:
        candidates = ["target_the_worst", "copy_the_best"] + [c for c in candidates if c not in ("target_the_worst", "copy_the_best")]
    elif low_spread:
        candidates = ["spread_evenly"] + [c for c in candidates if c != "spread_evenly"]

    seen = []
    for c in candidates:
        if c not in seen:
            seen.append(c)
    return seen[:3]


def build_options(problem_type, analysis, problem, direction, group_col):
    """Build exactly 3 options using the selected archetypes."""
    selected = select_archetypes(problem_type, analysis, direction)
    options = []
    for name in selected:
        fn = ARCHETYPES.get(name)
        if not fn:
            continue
        opt = fn(analysis, problem, direction, group_col)
        if opt and opt["name"] not in [o["name"] for o in options]:
            options.append(opt)
    if len(options) < 3:
        for name, fn in ARCHETYPES.items():
            if len(options) >= 3:
                break
            opt = fn(analysis, problem, direction, group_col)
            if opt and opt["name"] not in [o["name"] for o in options]:
                options.append(opt)
    return options[:3]
