"""Offline mode (no sign-in, no UI).
python cli.py data.csv --topic "Expand bus fleet" --org "My Team" [--template base.pptx] [--ai] [--out briefing.pptx]
Edit config.json to change slides, colours and limits."""
import argparse
import json
from pathlib import Path
from core import analyze, build, data, plan, research

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("data")
ap.add_argument("--topic", default="Briefing")
ap.add_argument("--org")
ap.add_argument("--config", default=str(Path(__file__).with_name("config.json")))
ap.add_argument("--template")
ap.add_argument("--ai", action="store_true")
ap.add_argument("--out", default="briefing.pptx")
a = ap.parse_args()

cfg = json.loads(Path(a.config).read_text())
df = data.load(a.data, a.data)
r = analyze.analyze(df)
p = plan.make_plan(r, a.topic, a.org or cfg["organisation"], cfg)
if a.ai:
    lines = p[1]["bullets"]
    p = plan.make_plan(r, a.topic, a.org or cfg["organisation"], cfg, research.research(a.topic, lines, cfg))
tpl = Path(a.template).read_bytes() if a.template else None
Path(a.out).write_bytes(build.build_pptx(p, df, r, cfg, tpl))
print(f"Saved {a.out}")
