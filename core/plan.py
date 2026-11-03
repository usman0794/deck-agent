"""Turn an analysis into an editable slide plan (list of dicts)."""
from datetime import date

from core.decide import WEIGHTS


def fmt(n):
    return f"{n:,.0f}" if abs(n) >= 100 else f"{n:,.2f}"


def make_agent_plan(agent, org, cfg):
    """Full agent deck: problem, data, solutions, criteria, scores, robustness, recommendation, risks, next steps."""
    on = cfg["slides"]
    ui = agent["user_intent"]
    ds = agent["data_summary"]
    result = agent["result"]
    options = agent["options"]
    best = agent["best"]
    best_opt = options[best]
    conf = agent["check"]["confidence"]
    metric = ui["metric"]
    group = ui["group"]
    problem = ui["problem"]
    goal = ui["goal"]
    constraints = ", ".join(f"{k}: {v}" for k, v in (ui.get("constraints") or {}).items() if v) or "none"
    slides = [
        {"id": "title", "type": "title", "title": problem,
         "bullets": [org, date.today().strftime("%d %b %Y")], "on": True},
        {"id": "problem", "type": "bullets", "title": "The problem",
         "bullets": [problem, f"Goal: {goal} {metric}", f"Group: {group}",
                     f"Audience: {ui.get('audience', 'leadership')}", f"Constraints: {constraints}"],
         "on": on.get("problem", True)},
        {"id": "data", "type": "bullets", "title": "What the data shows",
         "bullets": [ds.get("about", ""), f"Rows: {result['rows']}",
                     f"Quality: {', '.join(ds.get('quality_notes', [])) or 'no major issues'}"],
         "on": on.get("data", True)},
        {"id": "chart", "type": "chart", "title": f"{metric} by {group}", "bullets": [],
         "on": on.get("chart", True)},
        {"id": "solutions", "type": "bullets", "title": "Three solutions",
         "bullets": [f"{i + 1}. {o['name']} - {o['summary']}" for i, o in enumerate(options)],
         "on": on.get("solutions", True)},
        {"id": "criteria", "type": "bullets", "title": "How we judged",
         "bullets": [f"Weights: impact {WEIGHTS['impact']}, cost {WEIGHTS['cost']}, "
                     f"risk {WEIGHTS['risk']}, speed {WEIGHTS['speed']}",
                     "Cost and risk are lower-is-better."],
         "on": on.get("criteria", True)},
        {"id": "scores", "type": "options", "title": "Scores", "bullets": [],
         "options": options, "best": best, "on": on.get("scores", True)},
        {"id": "robustness", "type": "scenarios", "title": "Robustness", "bullets": [],
         "scenarios": agent["check"]["sensitivity"]["scenarios"], "on": on.get("robustness", True)},
        {"id": "recommendation", "type": "bullets", "title": "Recommendation and why",
         "bullets": [f"Recommended: {best_opt['name']}", agent["reason"],
                     f"Confidence: {conf['label']} (winner in {conf['wins']} of {conf['total']} scenarios)"]
                    + ([f"Alternative if low confidence: {conf['alternative']}"] if conf.get("alternative") else []),
         "on": on.get("recommendation", True)},
        {"id": "risks", "type": "bullets", "title": "Risks and assumptions",
         "bullets": agent["check"]["critique"]["concerns"] or ["No major concerns identified."],
         "on": on.get("risks", True)},
        {"id": "next_steps", "type": "bullets", "title": "Next steps",
         "bullets": [f"Approve {best_opt['name']} and confirm budget.",
                     f"Assign {group} owners and a 30-day checkpoint.",
                     f"Track {metric} weekly and report progress."],
         "on": on.get("next_steps", True)},
    ]
    if on.get("key_figures"):
        slides.append({"id": "figures", "type": "bullets", "title": "Key figures",
                       "bullets": [f"Records: {result['rows']}", f"Total {metric}: {fmt(result['total'])}",
                                   f"Top {group}: {result['top']}"], "on": True})
    if on.get("table"):
        slides.append({"id": "table", "type": "table", "title": "Data", "bullets": [], "on": True})
    return slides


def make_plan(r, topic, org, cfg, ai=None, agent=None):
    """Build a slide plan. When agent has the full pipeline result, build the agent deck."""
    if agent is not None and "check" in agent:
        return make_agent_plan(agent, org, cfg)
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
