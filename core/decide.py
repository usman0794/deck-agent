"""Decision agent: generate three options, score them, and recommend one."""
from core import analyze, archetypes, check, guardrails, problem, research, understand

# Weighted score. Cost and risk are lower-is-better, so they are inverted.
WEIGHTS = {"impact": 0.4, "cost": 0.25, "risk": 0.2, "speed": 0.15}
RATINGS = ("impact", "cost", "risk", "speed")


def clamp_options(options):
    """Clamp every rating to an integer between 1 and 5."""
    for o in options:
        for k in RATINGS:
            try:
                o[k] = max(1, min(5, int(o.get(k, 3))))
            except (TypeError, ValueError):
                o[k] = 3
    return options


def rule_options(result, problem, goal, metric, category):
    """Rule-based fallback: three realistic options derived from the data."""
    top = result["top"]
    low = result["low"]
    share = result["top_share"]
    if goal == "increase":
        return [
            {"name": f"Grow {low}",
             "summary": f"Focus on the lowest-performing {category} ({low}) where there is the most room to grow.",
             "est_effect": f"+{share}%", "impact": 5, "cost": 4, "risk": 3, "speed": 3},
            {"name": "Balanced rollout",
             "summary": f"Spread effort across all {category} groups.",
             "est_effect": "moderate", "impact": 3, "cost": 3, "risk": 2, "speed": 4},
            {"name": f"Quick win in {top}",
             "summary": f"Build on the strongest {category} ({top}) for fast, low-risk gains.",
             "est_effect": "small", "impact": 2, "cost": 2, "risk": 1, "speed": 5},
        ]
    return [
        {"name": f"Target {top}",
         "summary": f"Focus on the largest contributor ({top}, {share}% of {metric}).",
         "est_effect": f"-{share}%", "impact": 5, "cost": 4, "risk": 3, "speed": 3},
        {"name": "Balanced rollout",
         "summary": f"Spread effort across all {category} groups.",
         "est_effect": "moderate", "impact": 3, "cost": 3, "risk": 2, "speed": 4},
        {"name": f"Quick win in {low}",
         "summary": f"Address a smaller {category} group for fast, low-risk improvement.",
         "est_effect": "small", "impact": 2, "cost": 2, "risk": 1, "speed": 5},
    ]


def score_options(options, weights=None):
    """Add a weighted score to each option. Cost and risk are lower-is-better."""
    w = weights or WEIGHTS
    scored = []
    for o in options:
        score = (o["impact"] * w["impact"]
                 + (6 - o["cost"]) * w["cost"]
                 + (6 - o["risk"]) * w["risk"]
                 + o["speed"] * w["speed"])
        scored.append({**o, "score": round(score, 3)})
    return scored


def pick_best(scored):
    """Return the index of the highest score; ties prefer lower risk, then lower cost."""
    best = 0
    for i in range(1, len(scored)):
        a, b = scored[best], scored[i]
        if b["score"] > a["score"] + 1e-9:
            best = i
        elif abs(b["score"] - a["score"]) <= 1e-9:
            if b["risk"] < a["risk"]:
                best = i
            elif b["risk"] == a["risk"] and b["cost"] < a["cost"]:
                best = i
    return best


def make_reason(scored, best):
    """One-sentence reason naming the runner-up and the criteria where the winner leads."""
    winner = scored[best]
    runner = max((o for i, o in enumerate(scored) if i != best), key=lambda o: o["score"])
    criteria = []
    if winner["impact"] > runner["impact"]:
        criteria.append("impact")
    if winner["cost"] < runner["cost"]:
        criteria.append("lower cost")
    if winner["risk"] < runner["risk"]:
        criteria.append("lower risk")
    if winner["speed"] > runner["speed"]:
        criteria.append("speed")
    if not criteria:
        criteria.append("overall balance")
    return f"{winner['name']} leads {runner['name']} on {', '.join(criteria)}."


def run_agent(df, user_text, cfg, use_ai, overrides=None, asked=None):
    """Run stages 1-4. Returns status, questions (when needed) and the full result."""
    overrides = overrides or {}
    asked = set(asked or [])
    findings = guardrails.validate_input(df, user_text)
    profile = understand.profile_data(df)
    data_summary = understand.interpret_data(df, profile, cfg, use_ai)
    problem_type = problem.classify_problem(user_text, cfg, use_ai)
    numeric_cols = list(profile.get("numeric", {}).keys())
    categorical_cols = list(profile.get("categories", {}).keys())
    intent = understand.understand_user(user_text, list(df.columns), cfg, use_ai, df=df,
                                        numeric_columns=numeric_cols,
                                        categorical_columns=categorical_cols)
    for key in ("problem", "goal", "metric", "group", "constraints", "audience"):
        if overrides.get(key) not in (None, ""):
            intent[key] = overrides[key]
    if not intent.get("metric"):
        intent["metric"] = data_summary.get("suggested_metric")
    if not intent.get("group"):
        intent["group"] = data_summary.get("suggested_group")
    if not intent.get("problem"):
        intent["problem"] = (user_text or "Decision").strip()

    questions = []
    if not intent.get("problem"):
        questions.append({"id": "problem", "field": "problem",
                          "text": "What problem are you trying to solve?",
                          "kind": "text", "options": None, "required": True})
    if not intent.get("goal"):
        questions.append({"id": "goal", "field": "goal",
                          "text": "Do you want to increase or reduce it?",
                          "kind": "choice", "options": ["increase", "reduce"], "required": True})
    if not intent.get("metric"):
        numeric = list(profile.get("numeric", {}).keys())
        if numeric:
            questions.append({"id": "metric", "field": "metric",
                              "text": "Which column is the metric?",
                              "kind": "choice", "options": numeric, "required": True})
    questions = [q for q in questions if q["id"] not in asked]
    if questions:
        return {
            "status": "needs_input",
            "questions": questions[:3],
            "profile": profile,
            "data_summary": data_summary,
            "user_intent": intent,
            "problem_type": problem_type,
            "findings": findings,
            "mode": "rules",
        }

    direction = intent.get("goal") or "reduce"
    analysis = analyze.analyze(df, intent["metric"], intent["group"])
    options = None
    mode = "rules"
    if use_ai and research.available(cfg):
        try:
            options = research.ai_options(
                intent["problem"], direction, analysis["metric"], analysis["category"], cfg,
                constraints=intent.get("constraints"))
            mode = "ai"
        except Exception:
            options = None
    if not options:
        options = archetypes.build_options(problem_type["type"], analysis,
                                           intent["problem"], direction, analysis["category"])
    clamp_options(options)
    findings += guardrails.validate_options(options)
    scored = score_options(options)
    best = pick_best(scored)
    findings += guardrails.validate_decision(scored, best)
    reason = make_reason(scored, best)
    sens = check.sensitivity(scored)
    crit = check.critique(intent["problem"], analysis, scored, best, cfg, use_ai)
    conf = check.confidence(sens, scored, best)
    return {
        "status": "ok",
        "profile": profile,
        "data_summary": data_summary,
        "user_intent": intent,
        "problem_type": problem_type,
        "result": analysis,
        "options": scored,
        "best": best,
        "reason": reason,
        "check": {"sensitivity": sens, "critique": crit, "confidence": conf},
        "findings": findings,
        "mode": mode,
    }
