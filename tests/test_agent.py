"""Tests for the decision agent pipeline (no network, no API key)."""
import io
import json
from pathlib import Path

import pandas as pd
import pytest
from pptx import Presentation

from core import build, decide, plan, understand

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def cfg():
    return json.loads((ROOT / "config.json").read_text())


@pytest.fixture
def workers_df():
    return pd.read_csv(ROOT / "workers_sample_data.csv")


def test_run_agent_detects_intent(workers_df, cfg):
    out = decide.run_agent(workers_df, "we pay too much overtime", cfg, use_ai=False)
    assert out["mode"] == "rules"
    assert out["user_intent"]["goal"] == "reduce"
    assert out["user_intent"]["metric"] == "overtime_hours"
    assert len(out["options"]) == 3
    assert 0 <= out["best"] < 3
    assert out["reason"].strip()
    for o in out["options"]:
        for k in ("impact", "cost", "risk", "speed"):
            assert 1 <= o[k] <= 5


def test_profile_and_understand_rules(workers_df):
    profile = understand.profile_data(workers_df)
    assert profile["rows"] == len(workers_df)
    assert "overtime_hours" in profile["numeric"]
    assert "department" in profile["categories"]

    intent = understand.understand_user(
        "we pay too much overtime", list(workers_df.columns), {}, use_ai=False)
    assert intent["goal"] == "reduce"
    assert intent["metric"] == "overtime_hours"


def test_ratings_clamped():
    options = [
        {"name": "A", "summary": "", "est_effect": "", "impact": 9, "cost": 0, "risk": 6, "speed": 1},
        {"name": "B", "summary": "", "est_effect": "", "impact": -2, "cost": 99, "risk": 0, "speed": 5},
        {"name": "C", "summary": "", "est_effect": "", "impact": 3, "cost": 3, "risk": 3, "speed": 3},
    ]
    decide.clamp_options(options)
    for o in options:
        for k in ("impact", "cost", "risk", "speed"):
            assert 1 <= o[k] <= 5


def test_tie_prefers_lower_risk():
    scored = [
        {"name": "A", "impact": 3, "cost": 3, "risk": 1, "speed": 3, "score": 3.0},
        {"name": "B", "impact": 3, "cost": 3, "risk": 2, "speed": 3, "score": 3.0},
        {"name": "C", "impact": 1, "cost": 1, "risk": 5, "speed": 1, "score": 1.0},
    ]
    assert decide.pick_best(scored) == 0


def test_sensitivity_and_confidence(workers_df, cfg):
    out = decide.run_agent(workers_df, "we pay too much overtime", cfg, use_ai=False)
    sens = out["check"]["sensitivity"]
    assert sens["total"] == 6
    assert len(sens["scenarios"]) == 6
    conf = out["check"]["confidence"]
    assert conf["label"] in ("High", "Medium", "Low")
    assert 0 <= conf["wins"] <= 6


def test_pptx_has_required_slides(workers_df, cfg):
    out = decide.run_agent(workers_df, "we pay too much overtime", cfg, use_ai=False)
    p = plan.make_plan(out["result"], out["user_intent"]["problem"], "Test Org", cfg, agent=out)
    pptx_bytes = build.build_pptx(p, workers_df, out["result"], cfg)
    prs = Presentation(io.BytesIO(pptx_bytes))
    titles = [slide.shapes.title.text for slide in prs.slides if slide.shapes.title is not None]
    assert "The problem" in titles
    assert "Robustness" in titles
    assert "Recommendation and why" in titles
