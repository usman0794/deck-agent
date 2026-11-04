"""Tests for the UI-independent agent architecture (no network, no key)."""
import io
import json
import re
from pathlib import Path

import pandas as pd
import pytest
from pptx import Presentation

from core import build, decide, guardrails, plan, research
from service import workflow
from service.session import FileStore, InMemoryStore

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(__file__).resolve().parent / "data"
BANNED = ["overtime", "worker", "employee", "hospital", "patient", "bus",
          "route", "department", "salary", "Legal", "Support"]

CASES = [
    ("retail.csv", "we want higher sales", "improve"),
    ("retail.csv", "which store should we fix first", "prioritise"),
    ("retail.csv", "where should the new budget go", "allocate"),
    ("retail.csv", "why are returns so high", "diagnose"),
    ("retail.csv", "which store is best", "choose"),
    ("school.csv", "we want higher scores", "improve"),
    ("school.csv", "which class should we fix first", "prioritise"),
    ("school.csv", "where should the new budget go", "allocate"),
    ("school.csv", "why are absences so high", "diagnose"),
    ("school.csv", "which class is best", "choose"),
    ("delivery.csv", "we want fewer late deliveries", "improve"),
    ("delivery.csv", "which depot should we fix first", "prioritise"),
    ("delivery.csv", "where should the new budget go", "allocate"),
    ("delivery.csv", "why are late deliveries so high", "diagnose"),
    ("delivery.csv", "which depot is best", "choose"),
    ("clinic.csv", "we want shorter waits", "improve"),
    ("clinic.csv", "which ward should we fix first", "prioritise"),
    ("clinic.csv", "where should the new budget go", "allocate"),
    ("clinic.csv", "why are waits so high", "diagnose"),
    ("clinic.csv", "which ward is best", "choose"),
]


def _no_ai(monkeypatch):
    monkeypatch.setattr(research, "available", lambda cfg=None: False)
    monkeypatch.setattr(workflow, "STORE", InMemoryStore())


def _cfg():
    return json.loads((ROOT / "config.json").read_text())


def _answer(out):
    answers = {}
    for q in out.get("questions", []):
        if q["id"] == "problem":
            answers["problem"] = "Improve the metric"
        elif q["id"] == "goal":
            answers["goal"] = "reduce"
        elif q["id"] == "metric":
            answers["metric"] = q["options"][0] if q.get("options") else None
    return answers


def test_banned_words():
    pattern = re.compile(r"\b(" + "|".join(BANNED) + r")\b")
    for base in (ROOT / "core", ROOT / "service"):
        for path in base.rglob("*.py"):
            assert not pattern.search(path.read_text(encoding="utf-8")), f"Banned word in {path}"


@pytest.mark.parametrize("dataset,text,ptype", CASES)
def test_problem_types(dataset, text, ptype, monkeypatch):
    _no_ai(monkeypatch)
    df = pd.read_csv(DATA / dataset)
    out = decide.run_agent(df, text, _cfg(), use_ai=False)
    if out["status"] == "needs_input":
        out = decide.run_agent(df, text, _cfg(), use_ai=False, overrides=_answer(out))
    assert out["status"] == "ok"
    assert out["problem_type"]["type"] == ptype
    assert len(out["options"]) == 3
    names = [o["name"] for o in out["options"]]
    assert len(set(names)) == 3
    for o in out["options"]:
        for k in ("impact", "cost", "risk", "speed"):
            assert 1 <= o[k] <= 5
    group_col = out["result"]["category"]
    groups = {str(v) for v in df[group_col].unique()}
    for o in out["options"]:
        assert any(g in o["name"] for g in groups) or group_col in o["name"], \
            f"{o['name']} references no group from {groups}"


def test_vague_text_questions(monkeypatch):
    _no_ai(monkeypatch)
    df = pd.read_csv(DATA / "retail.csv")
    out = decide.run_agent(df, "help me", _cfg(), use_ai=False)
    assert out["status"] == "needs_input"
    assert 0 < len(out["questions"]) <= 3
    qids = {q["id"] for q in out["questions"]}
    answers = _answer(out)
    out2 = decide.run_agent(df, "help me", _cfg(), use_ai=False, overrides=answers)
    assert out2["status"] == "ok"
    out3 = decide.run_agent(df, "help me", _cfg(), use_ai=False, overrides=answers, asked=qids)
    assert out3["status"] == "ok"


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


def test_sensitivity_and_confidence(monkeypatch):
    _no_ai(monkeypatch)
    df = pd.read_csv(DATA / "retail.csv")
    out = decide.run_agent(df, "we want higher sales", _cfg(), use_ai=False)
    sens = out["check"]["sensitivity"]
    assert sens["total"] == 6
    assert len(sens["scenarios"]) == 6
    conf = out["check"]["confidence"]
    assert conf["label"] in ("High", "Medium", "Low")
    assert 0 <= conf["wins"] <= 6


def test_pptx_has_required_slides(monkeypatch):
    _no_ai(monkeypatch)
    df = pd.read_csv(DATA / "retail.csv")
    out = decide.run_agent(df, "we want higher sales", _cfg(), use_ai=False)
    p = plan.make_plan(out["result"], out["user_intent"]["problem"], "Test Org", _cfg(), agent=out)
    pptx_bytes = build.build_pptx(p, df, out["result"], _cfg())
    prs = Presentation(io.BytesIO(pptx_bytes))
    titles = [s.shapes.title.text for s in prs.slides if s.shapes.title is not None]
    assert "The problem as understood" in titles
    assert "Robustness" in titles
    assert "Recommendation and why" in titles


def test_service_flow(monkeypatch):
    _no_ai(monkeypatch)
    sid = workflow.create_session()["id"]
    workflow.upload_data(sid, (DATA / "retail.csv").read_bytes(), "retail.csv")
    result = workflow.submit_problem(sid, "we want higher sales")
    if result["status"] == "needs_input":
        result = workflow.answer_questions(sid, _answer(result))
    assert result["status"] == "understood"
    result = workflow.generate_options(sid, use_ai=False)
    assert result["status"] == "options_ready"
    decision = workflow.get_decision(sid)
    assert decision["status"] == "decided"
    deck = workflow.build_deck(sid)
    assert deck["status"] == "deck_ready"
    prs = Presentation(io.BytesIO(deck["bytes"]))
    assert len(prs.slides) > 0


def test_api_flow(monkeypatch):
    _no_ai(monkeypatch)
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    sid = client.post("/sessions").json()["id"]
    with open(DATA / "retail.csv", "rb") as f:
        r = client.post(f"/sessions/{sid}/data", files={"file": ("retail.csv", f, "text/csv")})
    assert r.status_code == 200
    r = client.post(f"/sessions/{sid}/problem", json={"text": "we want higher sales"})
    assert r.status_code == 200
    if r.json()["status"] == "needs_input":
        answers = _answer(r.json())
        r = client.post(f"/sessions/{sid}/answers", json={"answers": answers})
        assert r.status_code == 200
    r = client.post(f"/sessions/{sid}/options", json={"use_ai": False})
    assert r.status_code == 200
    assert r.json()["status"] == "options_ready"
    r = client.get(f"/sessions/{sid}/decision")
    assert r.status_code == 200
    assert r.json()["status"] == "decided"
    r = client.post(f"/sessions/{sid}/deck")
    assert r.status_code == 200
    assert r.json()["status"] == "deck_ready"
    r = client.get(f"/sessions/{sid}/deck.pptx")
    assert r.status_code == 200
    assert Presentation(io.BytesIO(r.content))


def test_ratings_update_changes_winner(monkeypatch):
    _no_ai(monkeypatch)
    sid = workflow.create_session()["id"]
    workflow.upload_data(sid, (DATA / "retail.csv").read_bytes(), "retail.csv")
    result = workflow.submit_problem(sid, "we want higher sales")
    if result["status"] == "needs_input":
        result = workflow.answer_questions(sid, _answer(result))
    workflow.generate_options(sid, use_ai=False)
    before = workflow.get_decision(sid)
    ratings = {str(i): {"impact": 1, "cost": 5, "risk": 5, "speed": 1} for i in range(3)}
    ratings["0"] = {"impact": 5, "cost": 1, "risk": 1, "speed": 5}
    result = workflow.update_ratings(sid, ratings)
    assert result["status"] == "options_ready"
    assert result["best"] == 0
    assert result["confidence"]["label"] in ("High", "Medium", "Low")


def test_file_store_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(research, "available", lambda cfg=None: False)
    workflow.STORE = FileStore(tmp_path)
    sid = workflow.create_session()["id"]
    workflow.upload_data(sid, (DATA / "retail.csv").read_bytes(), "retail.csv")
    workflow.STORE = FileStore(tmp_path)  # new instance reads from disk
    result = workflow.submit_problem(sid, "we want higher sales")
    assert result["status"] in ("understood", "needs_input")


def test_guardrails():
    assert guardrails.validate_input(None, "x")[0]["code"] == "EMPTY_DATA"
    assert guardrails.validate_options([])[0]["code"] == "NO_OPTIONS"
    good = [{"name": f"O{i}", "summary": "", "est_effect": "",
             "impact": 3, "cost": 3, "risk": 3, "speed": 3} for i in range(3)]
    assert guardrails.validate_options(good) == []
    assert guardrails.validate_decision(good, 0) == []
    assert guardrails.validate_output([{"title": "T"}]) == []
