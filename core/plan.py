"""Turn an analysis into an editable slide plan (list of dicts)."""
from datetime import date


def fmt(n):
    return f"{n:,.0f}" if abs(n) >= 100 else f"{n:,.2f}"


def make_decision_plan(r, problem, org, cfg, agent):
    """Decision deck: Title, Problem, Situation, Chart, Options, Recommendation, Next steps."""
    on = cfg["slides"]
    m, c = r["metric"], r["category"]
    options = agent["options"]
    best = agent["best"]
    best_opt = options[best]
    goal = agent.get("goal", "reduce")
    situation = [
        f"Problem: {problem}",
        f"Goal: {goal} {m}",
        f"{r['rows']} records analysed; total {m}: {fmt(r['total'])}",
        f"Highest {c}: {r['top']} ({r['top_share']}% of total)",
        f"Lowest {c}: {r['low']}",
    ]
    next_steps = [
        f"Approve {best_opt['name']} and confirm budget.",
        f"Assign {c} owners and a 30-day checkpoint.",
        f"Track {m} weekly and report progress.",
    ]
    return [
        {"id": "title", "type": "title", "title": problem,
         "bullets": [org, date.today().strftime("%d %b %Y")], "on": True},
        {"id": "problem", "type": "bullets", "title": "Problem",
         "bullets": [problem, f"Goal: {goal} {m}", f"Compare {m} by {c}"],
         "on": on.get("problem", True)},
        {"id": "situation", "type": "bullets", "title": "Situation",
         "bullets": situation, "on": on.get("situation", True)},
        {"id": "chart", "type": "chart", "title": f"{m} by {c}", "bullets": [],
         "on": on.get("chart", True)},
        {"id": "options", "type": "options", "title": "Options compared", "bullets": [],
         "options": options, "best": best, "on": on.get("options", True)},
        {"id": "recommendation", "type": "bullets", "title": "Recommendation",
         "bullets": [f"Recommended: {best_opt['name']}", agent["reason"],
                     f"Expected effect: {best_opt.get('est_effect', 'n/a')}"],
         "on": on.get("recommendation", True)},
        {"id": "next_steps", "type": "bullets", "title": "Next steps",
         "bullets": next_steps, "on": on.get("next_steps", True)},
    ]


def make_plan(r, topic, org, cfg, ai=None, agent=None):
    """Build a slide plan. When agent is provided, build the decision deck."""
    if agent is not None:
        return make_decision_plan(r, topic, org, cfg, agent)
    on = cfg["slides"]
    m, c = r["metric"], r["category"]
    summary = [
        f"Topic: {topic}",
        f"{r['rows']} records analysed; total {m}: {fmt(r['total'])}",
        f"Highest {c}: {r['top']} ({r['top_share']}% of total)",
        f"Lowest {c}: {r['low']}",
    ]
    if ai and ai.get("background"):
        summary += [f"Context (AI draft): {b}" for b in ai["background"][:3]]
    actions = (ai or {}).get("actions") or [
        f"Prioritise {r['top']} ({r['top_share']}% of {m})",
        f"Review lowest performer: {r['low']}",
        f"Confirm budget and timeline for: {topic}",
        "Report progress in 30 days",
    ]
    return [
        {"id": "title", "type": "title", "title": topic, "bullets": [org, date.today().strftime("%d %b %Y")], "on": True},
        {"id": "summary", "type": "bullets", "title": "Summary", "bullets": summary, "on": on.get("summary", True)},
        {"id": "figures", "type": "bullets", "title": "Key figures",
         "bullets": [f"Records: {r['rows']}", f"Total {m}: {fmt(r['total'])}", f"Top {c}: {r['top']}"],
         "on": on.get("key_figures", True)},
        {"id": "chart", "type": "chart", "title": f"{m} by {c}", "bullets": [], "on": on.get("chart", True)},
        {"id": "table", "type": "table", "title": "Data", "bullets": [], "on": on.get("table", False)},
        {"id": "actions", "type": "bullets", "title": "Recommended actions", "bullets": actions, "on": on.get("actions", True)},
    ]
