"""Offline mode (no sign-in, no UI).
python cli.py data.csv --topic "Reduce overtime cost" --goal reduce --metric overtime_hours --category department [--org "My Team"] [--template base.pptx] [--ai] [--out briefing.pptx]
Edit config.json to change slides, colours and limits."""
import argparse
import json
from pathlib import Path
from core import analyze, build, data, decide, plan

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("data")
ap.add_argument("--topic", default="Decision")
ap.add_argument("--org")
ap.add_argument("--goal", choices=["increase", "reduce"], default="reduce")
ap.add_argument("--metric")
ap.add_argument("--category")
ap.add_argument("--config", default=str(Path(__file__).with_name("config.json")))
ap.add_argument("--template")
ap.add_argument("--ai", action="store_true")
ap.add_argument("--out", default="briefing.pptx")
a = ap.parse_args()

cfg = json.loads(Path(a.config).read_text())
df = data.load(a.data, a.data)
detected = analyze.analyze(df)
agent = decide.run_agent(df, a.topic, a.goal,
                         a.metric or detected["metric"],
                         a.category or detected["category"],
                         cfg, a.ai)
p = plan.make_plan(agent["result"], a.topic, a.org or cfg["organisation"], cfg, agent=agent)
tpl = Path(a.template).read_bytes() if a.template else None
Path(a.out).write_bytes(build.build_pptx(p, df, agent["result"], cfg, tpl))

print("Options:")
for i, o in enumerate(agent["options"], 1):
    print(f"  {i}. {o['name']} - score {o['score']:.2f} "
          f"(impact {o['impact']}, cost {o['cost']}, risk {o['risk']}, speed {o['speed']})")
best = agent["options"][agent["best"]]
print(f"Recommended: {best['name']}")
print(f"Reason: {agent['reason']}")
print(f"Mode: {agent['mode']}")
print(f"Saved {a.out}")
