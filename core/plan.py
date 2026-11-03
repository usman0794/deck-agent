"""Turn an analysis into an editable slide plan (list of dicts)."""
import urllib.parse
from datetime import date

from core.decide import WEIGHTS


def fmt(n):
    return f"{n:,.0f}" if abs(n) >= 100 else f"{n:,.2f}"


def _clip(bullets, limit=6, chars=140):
    return [str(b)[:chars] for b in (bullets or [])[:limit]]


def make_agent_plan(agent, org, cfg):
    """Detailed decision deck: up to 18 slides, one message each."""
    on = cfg.get("slides", {})
    ui = agent.get("user_intent", {})
    ds = agent.get("data_summary", {})
    result = agent.get("result", {})
    options = agent.get("options", [])
    best = agent.get("best", 0)
    best_opt = options[best] if options else {}
    check = agent.get("check", {})
    conf = check.get("confidence", {})
    why_not = check.get("why_not", {})
    tie = check.get("tie", False)
    evidence_strength = check.get("evidence_strength", 0)
    metric = result.get("metric") or ui.get("metric") or "metric"
    group = result.get("category") or ui.get("group") or "group"
    problem = ui.get("problem") or "Decision"
    goal = ui.get("goal") or "reduce"
    problem_type = agent.get("problem_type", {}).get("type", "improve")
    research = agent.get("research") or {}
    findings = research.get("findings", [])
    sources = research.get("sources", [])
    themes = research.get("themes", {})
    coverage = research.get("coverage", 0.0)
    status = research.get("status", "ok")
    has_research = bool(findings)
    findings_map = {f["id"]: f for f in findings}
    mode_label = "AI-assisted" if agent.get("mode") == "ai" else "Rule-based"
    constraints = ", ".join(f"{k}: {v}" for k, v in (ui.get("constraints") or {}).items() if v) or "none"

    slides = []

    def add(sid, stype, title, bullets=None, **extra):
        slide = {"id": sid, "type": stype, "title": title,
                 "bullets": _clip(bullets), "on": on.get(sid, True)}
        slide.update(extra)
        slides.append(slide)
        return slide

    add("title", "title", problem,
        [org, date.today().strftime("%d %b %Y"), f"Mode: {mode_label}"])
    add("executive_summary", "bullets", "Executive summary",
        [f"Problem: {problem}", f"Recommended: {best_opt.get('name', '')}",
         f"Expected effect: {best_opt.get('expected_effect', 'n/a')}",
         f"Confidence: {conf.get('label', 'n/a')} (winner in {conf.get('wins', 0)} of {conf.get('total', 0)} scenarios)"],
        notes=f"Reason: {agent.get('reason', '')} Evidence strength: {evidence_strength}.")
    add("problem", "bullets", "The problem as understood",
        [problem, f"Type: {problem_type}", f"Goal: {goal} {metric}", f"Group: {group}",
         f"Constraints: {constraints}", "Assumptions: estimates are directional, not exact."])
    add("data", "bullets", "What the data shows",
        [ds.get("about", ""), f"Rows: {result.get('rows', 0)}",
         f"Quality: {', '.join(ds.get('quality_notes', [])) or 'no major issues'}",
         f"Trend: {result.get('trend') or 'no date column'}"])
    add("chart", "chart", f"{metric} by {group}")

    if has_research:
        theme_lines = [f"{theme.replace('_', ' ').title()}: {len(ids)} finding(s)"
                       for theme, ids in themes.items() if ids]
        add("research", "bullets", "What outside research found",
            theme_lines + [f"Coverage: {coverage:.0%} of sub-questions"],
            notes="Verified findings only; untrusted page text was not used.")
        practice = [f"[{fid}] {findings_map[fid]['claim']}"
                    for fid in (themes.get("good_practices", []) + themes.get("benchmarks", []))[:4]]
        add("good_practices", "bullets", "Good practices and benchmarks found", practice,
            notes="Every claim carries its source number.")
    else:
        add("research", "bullets", "No external research used",
            ["Research was unavailable, partial, or disabled.",
             f"Status: {status}. The options below are based on the data only."])

    for i, o in enumerate(options):
        evidence = ", ".join(f"[{e}]" for e in o.get("evidence_ids", [])) or "none"
        add(f"solution_{i + 1}", "bullets", f"Solution {i + 1}: {o.get('name', '')}",
            [o.get("idea", ""),
             "How: " + " / ".join(o.get("how_it_works", [])),
             f"Evidence: {evidence}",
             f"Expected effect: {o.get('expected_effect', 'n/a')}",
             f"Ratings: impact {o.get('impact')}, cost {o.get('cost')}, risk {o.get('risk')}, speed {o.get('speed')}",
             f"Main risk: {o.get('main_risk', '')}"],
            notes=f"Failure condition: {o.get('failure_condition', '')}")

    add("comparison", "options", "Three solutions compared", options=options, best=best)
    add("criteria", "bullets", "How we judged",
        [f"Weights: impact {WEIGHTS['impact']}, cost {WEIGHTS['cost']}, "
         f"risk {WEIGHTS['risk']}, speed {WEIGHTS['speed']}",
         "Cost and risk are lower-is-better."])
    add("robustness", "scenarios", "Robustness",
        scenarios=check.get("sensitivity", {}).get("scenarios", []),
        notes=f"Confidence: {conf.get('label')} (winner in {conf.get('wins', 0)} of {conf.get('total', 0)} scenarios). "
              f"Evidence strength: {evidence_strength}.")
    rec_bullets = [f"Recommended: {best_opt.get('name', '')}", agent.get("reason", ""),
                   f"Confidence: {conf.get('label', 'n/a')} (winner in {conf.get('wins', 0)} of {conf.get('total', 0)} scenarios)",
                   f"Evidence strength: {evidence_strength} verified finding(s)"]
    if tie:
        rec_bullets.append("Human decision required: the top two options are tied.")
    rec_bullets += list(why_not.values())
    add("recommendation", "bullets", "Recommendation and why", rec_bullets,
        footer="Decision support. Estimates are assumptions. A person makes the final decision.",
        notes="Why not the others: " + " ".join(why_not.values()))
    steps = best_opt.get("how_it_works", [])
    add("roadmap", "bullets", "Implementation roadmap",
        [f"First 30 days: {steps[0] if steps else 'Start'}",
         f"60 days: {steps[1] if len(steps) > 1 else 'Continue'}",
         f"90 days: {steps[2] if len(steps) > 2 else 'Scale and review'}"])
    risks = [best_opt.get("main_risk", ""), best_opt.get("failure_condition", "")]
    risks += list(why_not.values())
    add("risks", "bullets", "Risks and mitigations", risks)
    add("kpis", "bullets", "KPIs to track",
        [f"Metric: {metric}", f"Target: {best_opt.get('expected_effect', 'n/a')}",
         "Review: weekly", "Review dates: 30, 60, 90 days"])
    if has_research:
        add("sources", "sources", "Sources",
            [f"[{i + 1}] {s.get('title', '')} - "
             f"{urllib.parse.urlparse(s.get('url', '')).netloc or s.get('url', '')} - "
             f"{s.get('retrieved_date', '')}"
             for i, s in enumerate(sources)],
            sources_list=sources)

    max_slides = int(cfg.get("max_slides", 18))
    return slides[:max_slides]


def make_plan(r, topic, org, cfg, ai=None, agent=None):
    """Build a slide plan. When agent has the full pipeline result, build the agent deck."""
    if agent is not None and "check" in agent:
        return make_agent_plan(agent, org, cfg)
    on = cfg.get("slides", {})
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
