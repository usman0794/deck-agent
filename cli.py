"""Offline mode (no sign-in, no UI). Calls the service layer.

python cli.py data.csv --text "we pay too much overtime and need a plan" \
    [--answers '{"metric":"overtime_hours"}'] [--topic ...] [--goal ...] \
    [--metric ...] [--category ...] [--use-ai] [--out briefing.pptx]
"""
import argparse
import importlib.util
import json
from pathlib import Path

from core import research_web
from service import workflow

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("data")
ap.add_argument("--text", default=None, help="Describe the situation in plain words")
ap.add_argument("--answers", default=None, help="JSON file or inline JSON with answers to clarifying questions")
ap.add_argument("--topic", default=None, help="Override the problem statement")
ap.add_argument("--org", default=None, help="Organisation name (not stored in the session)")
ap.add_argument("--goal", choices=["increase", "reduce"], help="Override the goal")
ap.add_argument("--metric", help="Override the metric column")
ap.add_argument("--category", help="Override the group column")
ap.add_argument("--use-ai", action="store_true")
ap.add_argument("--research", action="store_true", default=None,
                help="Run external research (default: on when a search provider is available)")
ap.add_argument("--no-research", action="store_false", dest="research",
                help="Skip external research")
ap.add_argument("--out", default="briefing.pptx")
a = ap.parse_args()


def _research_available():
    try:
        cfg = json.loads(Path(__file__).with_name("config.json").read_text())
        provider = research_web.get_search_provider(cfg)
        if isinstance(provider, research_web.DDGSProvider):
            return importlib.util.find_spec("ddgs") is not None
        return True
    except Exception:
        return False

session = workflow.create_session()
sid = session["id"]
workflow.upload_data(sid, Path(a.data).read_bytes(), a.data)

result = workflow.submit_problem(sid, a.text or a.topic or "Decision")
if result["status"] == "needs_input":
    answers = {}
    if a.answers:
        raw = a.answers.strip()
        answers = json.loads(raw) if raw.startswith("{") else json.loads(Path(a.answers).read_text())
    result = workflow.answer_questions(sid, answers)
if result["status"] == "needs_input":
    print("Needs input:")
    for q in result.get("questions", []):
        print(f"  {q['id']}: {q['text']} options={q.get('options')}")
    raise SystemExit(1)

edits = {}
if a.topic:
    edits["problem"] = a.topic
if a.goal:
    edits["goal"] = a.goal
if a.metric:
    edits["metric"] = a.metric
if a.category:
    edits["group"] = a.category
if edits:
    result = workflow.confirm_understanding(sid, edits)

if a.research is None:
    if _research_available():
        a.research = True
    else:
        a.research = False
if a.research:
    r = workflow.run_research(sid)
    if r.get("status") == "blocked":
        print(f"Research skipped: {r.get('message', '')}")
    else:
        print(f"Research: status={r.get('status')} coverage={r.get('coverage', 0):.0%} "
              f"findings={len(r.get('findings', []))} sources={len(r.get('sources', []))}")
        if r.get("message"):
            print(f"Research message: {r.get('message')}")

result = workflow.generate_options(sid, use_ai=a.use_ai)
if result["status"] != "options_ready":
    print("Failed:", result)
    raise SystemExit(1)

decision = workflow.get_decision(sid)
deck = workflow.build_deck(sid)
Path(a.out).write_bytes(deck["bytes"])

ui = decision["user_intent"]
ptype = decision["problem_type"]
conf = decision["confidence"]
print(f"Understood problem: {ui.get('problem')}")
print(f"Problem type: {ptype.get('type')} (confidence {ptype.get('confidence')}, {ptype.get('reason')})")
print(f"Goal: {ui.get('goal')} | Metric: {ui.get('metric')} | Group: {ui.get('group')}")
print("Options:")
for i, o in enumerate(decision["options"], 1):
    print(f"  {i}. {o['name']} - score {o['score']:.2f} "
          f"(impact {o['impact']}, cost {o['cost']}, risk {o['risk']}, speed {o['speed']})")
print(f"Confidence: {conf.get('label')} (winner in {conf.get('wins')} of {conf.get('total')} scenarios)")
best = decision["options"][decision["best"]]
print(f"Recommended: {best['name']}")
print(f"Reason: {decision['reason']}")
print(f"Findings: {decision.get('findings', [])}")
print(f"Saved {a.out}")
