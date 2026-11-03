"""Offline mode (no sign-in, no UI).
python cli.py data.csv --text "we pay too much overtime and need a plan" [--topic ...] [--goal ...] [--metric ...] [--category ...] [--org "My Team"] [--template base.pptx] [--ai] [--out briefing.pptx]
Edit config.json to change slides, colours and limits."""
import argparse
import json
from pathlib import Path
from core import build, data, decide, plan

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("data")
ap.add_argument("--text", default=None, help="Describe the situation in plain words")
ap.add_argument("--topic", default=None, help="Override the problem statement")
ap.add_argument("--org")
ap.add_argument("--goal", choices=["increase", "reduce"], help="Override the goal")
ap.add_argument("--metric", help="Override the metric column")
ap.add_argument("--category", help="Override the group column")
ap.add_argument("--config", default=str(Path(__file__).with_name("config.json")))
ap.add_argument("--template")
ap.add_argument("--ai", action="store_true")
ap.add_argument("--out", default="briefing.pptx")
a = ap.parse_args()

cfg = json.loads(Path(a.config).read_text())
df = data.load(a.data, a.data)
text = a.text or a.topic or "Decision"
overrides = {}
if a.topic:
    overrides["problem"] = a.topic
if a.goal:
    overrides["goal"] = a.goal
if a.metric:
    overrides["metric"] = a.metric
if a.category:
    overrides["group"] = a.category

agent = decide.run_agent(df, text, cfg, a.ai, overrides=overrides)
p = plan.make_plan(agent["result"], agent["user_intent"]["problem"],
                   a.org or cfg["organisation"], cfg, agent=agent)
tpl = Path(a.template).read_bytes() if a.template else None
Path(a.out).write_bytes(build.build_pptx(p, df, agent["result"], cfg, tpl))

ui = agent["user_intent"]
conf = agent["check"]["confidence"]
print(f"Understood problem: {ui['problem']}")
print(f"Goal: {ui['goal']} | Metric: {ui['metric']} | Group: {ui['group']} | "
      f"Audience: {ui.get('audience', 'leadership')}")
print("Options:")
for i, o in enumerate(agent["options"], 1):
    print(f"  {i}. {o['name']} - score {o['score']:.2f} "
          f"(impact {o['impact']}, cost {o['cost']}, risk {o['risk']}, speed {o['speed']})")
best = agent["options"][agent["best"]]
print(f"Confidence: {conf['label']} (winner in {conf['wins']} of {conf['total']} scenarios)")
print(f"Recommended: {best['name']}")
print(f"Reason: {agent['reason']}")
print(f"Mode: {agent['mode']}")
print(f"Saved {a.out}")
