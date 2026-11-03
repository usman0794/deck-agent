"""Session workflow: create, upload, submit, answer, confirm, options, ratings, decision, deck, audit."""
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

import pandas as pd

from core import analyze, build, check, decide, guardrails, plan, research, research_web, understand
from service.session import Session, get_store

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "session_data"
CFG = json.loads((ROOT / "config.json").read_text())
STORE = get_store(os.getenv("SESSION_STORE", "file"))


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _get(session_id):
    session = STORE.get(session_id)
    if not session:
        raise ValueError(json.dumps({"code": "NOT_FOUND", "message": "Session not found", "findings": []}))
    return session


def _error(code, message, findings=None):
    return {"status": "blocked", "code": code, "message": message, "findings": findings or []}


def _load_df(session):
    path = ROOT / session.data_ref
    ext = path.suffix.lower()
    if ext in (".csv", ".txt"):
        return pd.read_csv(path)
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path)
    if ext == ".json":
        return pd.read_json(path)
    raise ValueError("Unsupported data file")


def create_session():
    session = Session(id=uuid.uuid4().hex)
    session.status = "created"
    STORE.save(session)
    return session.to_dict()


def upload_data(session_id, file_bytes, filename):
    session = _get(session_id)
    digest = hashlib.sha256(file_bytes).hexdigest()[:16]
    ext = Path(filename).suffix.lower() or ".csv"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data_path = DATA_DIR / f"{digest}{ext}"
    if not data_path.exists():
        data_path.write_bytes(file_bytes)
    session.data_ref = str(data_path.relative_to(ROOT))
    df = _load_df(session)
    session.profile = understand.profile_data(df)
    session.status = "data_loaded"
    session.updated_at = _now()
    STORE.save(session)
    return session.to_dict()


def scrape_data(session_id, url, selector="table tr"):
    """Scrape a web table/list and store it as the session data."""
    from core import scraper
    df = scraper.scrape(url, selector)
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    return upload_data(session_id, csv_bytes, "scraped.csv")


def submit_problem(session_id, text):
    session = _get(session_id)
    if not session.data_ref:
        return _error("NO_DATA", "Upload data first")
    session.user_text = text
    df = _load_df(session)
    out = decide.run_agent(df, text, CFG, research.available(CFG), asked=set(session.questions_asked))
    session.profile = out.get("profile", session.profile)
    session.intent = out.get("user_intent", {})
    session.problem_type = out.get("problem_type", {})
    session.data_summary = out.get("data_summary", {})
    session.findings = out.get("findings", [])
    if out["status"] == "needs_input":
        session.status = "needs_input"
        for q in out.get("questions", []):
            if q["id"] not in session.questions_asked:
                session.questions_asked.append(q["id"])
        session.updated_at = _now()
        STORE.save(session)
        return {"status": "needs_input", "questions": out.get("questions", []),
                "user_intent": session.intent, "findings": session.findings,
                "session": session.to_dict()}
    session.status = "understood"
    session.updated_at = _now()
    STORE.save(session)
    return {"status": "understood", "user_intent": session.intent,
            "problem_type": session.problem_type, "findings": session.findings,
            "session": session.to_dict()}


def answer_questions(session_id, answers):
    session = _get(session_id)
    if session.status not in ("needs_input", "understood"):
        return _error("NOT_WAITING", "Session is not waiting for answers")
    for qid, value in (answers or {}).items():
        session.questions_answered[qid] = value
        if qid not in session.questions_asked:
            session.questions_asked.append(qid)
        if qid in ("problem", "goal", "metric", "group"):
            session.intent[qid] = value
    df = _load_df(session)
    out = decide.run_agent(df, session.user_text, CFG, research.available(CFG),
                           overrides=session.questions_answered, asked=set(session.questions_asked))
    session.profile = out.get("profile", session.profile)
    session.intent = out.get("user_intent", session.intent)
    session.problem_type = out.get("problem_type", session.problem_type)
    session.data_summary = out.get("data_summary", session.data_summary)
    session.findings = out.get("findings", [])
    if out["status"] == "needs_input":
        session.status = "needs_input"
        for q in out.get("questions", []):
            if q["id"] not in session.questions_asked:
                session.questions_asked.append(q["id"])
        session.updated_at = _now()
        STORE.save(session)
        return {"status": "needs_input", "questions": out.get("questions", []),
                "user_intent": session.intent, "findings": session.findings,
                "session": session.to_dict()}
    session.status = "understood"
    session.updated_at = _now()
    STORE.save(session)
    return {"status": "understood", "user_intent": session.intent,
            "problem_type": session.problem_type, "findings": session.findings,
            "session": session.to_dict()}


def confirm_understanding(session_id, edits):
    session = _get(session_id)
    if session.status not in ("understood", "needs_input"):
        return _error("NOTHING_TO_CONFIRM", "Nothing to confirm yet")
    session.intent.update(edits or {})
    df = _load_df(session)
    out = decide.run_agent(df, session.user_text, CFG, research.available(CFG),
                           overrides=session.intent, asked=set(session.questions_asked))
    session.profile = out.get("profile", session.profile)
    session.intent = out.get("user_intent", session.intent)
    session.problem_type = out.get("problem_type", session.problem_type)
    session.data_summary = out.get("data_summary", session.data_summary)
    session.findings = out.get("findings", [])
    if out["status"] == "needs_input":
        session.status = "needs_input"
        for q in out.get("questions", []):
            if q["id"] not in session.questions_asked:
                session.questions_asked.append(q["id"])
        session.updated_at = _now()
        STORE.save(session)
        return {"status": "needs_input", "questions": out.get("questions", []),
                "user_intent": session.intent, "findings": session.findings,
                "session": session.to_dict()}
    session.status = "understood"
    session.updated_at = _now()
    STORE.save(session)
    return {"status": "understood", "user_intent": session.intent,
            "problem_type": session.problem_type, "findings": session.findings,
            "session": session.to_dict()}


def run_research(session_id):
    session = _get(session_id)
    if session.status not in ("understood", "needs_input"):
        return _error("NOT_READY", "Confirm understanding first")
    if not session.data_ref:
        return _error("NO_DATA", "Upload data first")
    df = _load_df(session)
    group_col = session.intent.get("group")
    group_values = None
    if group_col in df.columns:
        group_values = [str(v) for v in df[group_col].dropna().unique().tolist()[:50]]
    result = research_web.research(
        session.intent.get("problem", "Decision"),
        session.problem_type.get("type", "improve"),
        list(df.columns), CFG,
        use_ai=research.available(CFG),
        group_values=group_values,
    )
    session.research = result
    session.status = "researched"
    session.updated_at = _now()
    STORE.save(session)
    return {"status": result.get("status", "ok"), "themes": result.get("themes", {}),
            "findings": result.get("findings", []), "coverage": result.get("coverage", 0.0),
            "sources": result.get("sources", []), "message": result.get("message", ""),
            "kept": result.get("kept", 0), "dropped": result.get("dropped", 0),
            "model_calls": result.get("model_calls", 0),
            "session": session.to_dict()}


def generate_options(session_id, use_ai=False):
    session = _get(session_id)
    if session.status not in ("understood", "needs_input", "researched"):
        return _error("NOT_READY", "Confirm understanding first")
    df = _load_df(session)
    out = decide.run_agent(df, session.user_text, CFG, use_ai,
                           overrides=session.intent, asked=set(session.questions_asked),
                           research_result=session.research or None)
    session.profile = out.get("profile", session.profile)
    session.intent = out.get("user_intent", session.intent)
    session.problem_type = out.get("problem_type", session.problem_type)
    session.data_summary = out.get("data_summary", session.data_summary)
    session.options = out.get("options", [])
    session.reason = out.get("reason", "")
    session.check = out.get("check", {})
    session.confidence = session.check.get("confidence", {})
    session.best = out.get("best", 0)
    session.findings = out.get("findings", [])
    if out["status"] == "needs_input":
        session.status = "needs_input"
        for q in out.get("questions", []):
            if q["id"] not in session.questions_asked:
                session.questions_asked.append(q["id"])
        session.updated_at = _now()
        STORE.save(session)
        return {"status": "needs_input", "questions": out.get("questions", []),
                "findings": session.findings, "session": session.to_dict()}
    session.status = "options_ready"
    session.updated_at = _now()
    STORE.save(session)
    return {"status": "options_ready", "options": session.options,
            "confidence": session.confidence, "findings": session.findings,
            "session": session.to_dict()}


def update_ratings(session_id, option_ratings, weights=None):
    session = _get(session_id)
    if session.status not in ("options_ready", "decided", "deck_ready"):
        return _error("NO_OPTIONS", "No options to update")
    options = session.options
    for i, option in enumerate(options):
        ratings = option_ratings.get(str(i)) or option_ratings.get(i) or {}
        for key in ("impact", "cost", "risk", "speed"):
            if key in ratings:
                try:
                    option[key] = max(1, min(5, int(ratings[key])))
                except (TypeError, ValueError):
                    pass
    if weights:
        session.weights = weights
    scored = decide.score_options(options, weights or session.weights or decide.WEIGHTS)
    session.options = scored
    session.best = decide.pick_best(scored)
    session.reason = decide.make_reason(scored, session.best)
    sens = check.sensitivity(scored)
    conf = check.confidence(sens, scored, session.best)
    session.confidence = conf
    session.check = {"sensitivity": sens, "critique": session.check.get("critique", {}),
                     "confidence": conf}
    session.status = "options_ready"
    session.updated_at = _now()
    STORE.save(session)
    return {"status": "options_ready", "options": session.options,
            "best": session.best, "confidence": session.confidence,
            "findings": session.findings, "session": session.to_dict()}


def get_decision(session_id):
    session = _get(session_id)
    if session.status not in ("options_ready", "decided", "deck_ready"):
        return _error("NO_DECISION", "No decision yet")
    session.decision = {
        "problem_type": session.problem_type,
        "user_intent": session.intent,
        "options": session.options,
        "best": session.best,
        "reason": session.reason,
        "confidence": session.confidence,
        "findings": session.findings,
    }
    session.status = "decided"
    session.updated_at = _now()
    STORE.save(session)
    return {"status": "decided", **session.decision, "session": session.to_dict()}


def build_deck(session_id, template_bytes=None):
    session = _get(session_id)
    if session.status not in ("options_ready", "decided"):
        return _error("NO_DECISION", "No decision to build")
    df = _load_df(session)
    result = analyze.analyze(df, session.intent.get("metric"), session.intent.get("group"))
    agent = {
        "user_intent": session.intent,
        "data_summary": session.data_summary,
        "result": result,
        "options": session.options,
        "best": session.best,
        "reason": session.reason,
        "check": session.check,
        "problem_type": session.problem_type,
        "research": session.research or {},
    }
    slides = plan.make_plan(result, session.intent.get("problem", "Decision"),
                            CFG.get("organisation", "Organisation"), CFG, agent=agent)
    pptx_bytes = build.build_pptx(slides, df, result, CFG, template_bytes)
    deck_path = ROOT / "sessions" / f"{session.id}.pptx"
    deck_path.write_bytes(pptx_bytes)
    session.deck_path = str(deck_path.relative_to(ROOT))
    session.status = "deck_ready"
    session.updated_at = _now()
    STORE.save(session)
    return {"status": "deck_ready", "deck_path": session.deck_path,
            "findings": session.findings, "bytes": pptx_bytes, "session": session.to_dict()}


def get_audit(session_id):
    session = _get(session_id)
    findings = guardrails.audit({
        "df": _load_df(session) if session.data_ref else None,
        "user_text": session.user_text,
        "options": session.options,
        "best": session.best,
        "plan": None,
    })
    audit = {
        "queries": (session.research or {}).get("queries", []),
        "source_urls": [s.get("url") for s in (session.research or {}).get("sources", [])],
        "kept": (session.research or {}).get("kept", 0),
        "dropped": (session.research or {}).get("dropped", 0),
        "model_calls": (session.research or {}).get("model_calls", 0),
    }
    return {"status": session.status, "findings": findings, "audit": audit,
            "session": session.to_dict()}


def get_sources(session_id):
    session = _get(session_id)
    return {"status": session.status,
            "sources": (session.research or {}).get("sources", []),
            "session": session.to_dict()}
