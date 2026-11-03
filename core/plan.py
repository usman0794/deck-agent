"""Turn an analysis into an editable slide plan (list of dicts)."""
from datetime import date


def fmt(n):
    return f"{n:,.0f}" if abs(n) >= 100 else f"{n:,.2f}"


def make_plan(r, topic, org, cfg, ai=None):
    """ai: optional {'background': [...], 'actions': [...]} from core.research."""
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
