"""FastAPI wrapper over the agent service."""
import json
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from core import auth
from service import workflow

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text())

app = FastAPI(title="Briefing Deck Agent API", version="1.0")

_cors = CFG.get("cors", {})
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors.get("allow_origins", ["*"]),
    allow_credentials=_cors.get("allow_credentials", True),
    allow_methods=_cors.get("allow_methods", ["*"]),
    allow_headers=_cors.get("allow_headers", ["*"]),
)


def get_current_user(authorization: Optional[str] = Header(None)):
    """Pluggable bearer-token auth. Verifies with the existing auth module when a token is sent."""
    required = bool(CFG.get("auth_required", False))
    if not authorization or not authorization.startswith("Bearer "):
        if required:
            raise HTTPException(status_code=401, detail={
                "code": "UNAUTHORIZED", "message": "Missing bearer token", "findings": []})
        return "anonymous"
    token = authorization.split(" ", 1)[1]
    user = auth.verify_token(token)
    if not user:
        if required:
            raise HTTPException(status_code=401, detail={
                "code": "UNAUTHORIZED", "message": "Invalid token", "findings": []})
        return "anonymous"
    return user


class ProblemRequest(BaseModel):
    text: str


class AnswersRequest(BaseModel):
    answers: dict


class ConfirmRequest(BaseModel):
    edits: dict = {}


class OptionsRequest(BaseModel):
    use_ai: bool = False


class RatingsRequest(BaseModel):
    option_ratings: dict
    weights: Optional[dict] = None


class LoginRequest(BaseModel):
    username: str
    password: str


def _error(code, message, findings=None, status_code=400):
    return JSONResponse(status_code=status_code,
                        content={"code": code, "message": message, "findings": findings or []})


@app.exception_handler(ValueError)
async def _value_error_handler(request, exc):
    try:
        detail = json.loads(str(exc))
    except Exception:
        detail = {"code": "ERROR", "message": str(exc), "findings": []}
    status = 404 if detail.get("code") == "NOT_FOUND" else 400
    return _error(detail.get("code", "ERROR"), detail.get("message", "Error"),
                  detail.get("findings"), status)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login")
def login(req: LoginRequest):
    ok, role = auth.authenticate(req.username, req.password)
    if not ok:
        raise HTTPException(status_code=401, detail={
            "code": "INVALID_CREDENTIALS",
            "message": "Invalid username or password", "findings": []})
    return {"token": auth.make_token(req.username.strip().lower()),
            "user": req.username.strip().lower(), "role": role}


@app.post("/sessions")
def create_session(_user=Depends(get_current_user)):
    return workflow.create_session()


@app.post("/sessions/{session_id}/data")
def upload_data(session_id: str, file: UploadFile = File(...), _user=Depends(get_current_user)):
    return workflow.upload_data(session_id, file.file.read(), file.filename)


@app.post("/sessions/{session_id}/scrape")
def scrape_data(session_id: str, url: str = Form(...), selector: str = Form("table tr"),
                _user=Depends(get_current_user)):
    return workflow.scrape_data(session_id, url, selector)


@app.post("/sessions/{session_id}/problem")
def submit_problem(session_id: str, req: ProblemRequest, _user=Depends(get_current_user)):
    return workflow.submit_problem(session_id, req.text)


@app.post("/sessions/{session_id}/answers")
def answer_questions(session_id: str, req: AnswersRequest, _user=Depends(get_current_user)):
    return workflow.answer_questions(session_id, req.answers)


@app.post("/sessions/{session_id}/confirm")
def confirm_understanding(session_id: str, req: ConfirmRequest, _user=Depends(get_current_user)):
    return workflow.confirm_understanding(session_id, req.edits)


@app.post("/sessions/{session_id}/options")
def generate_options(session_id: str, req: OptionsRequest, _user=Depends(get_current_user)):
    return workflow.generate_options(session_id, req.use_ai)


@app.post("/sessions/{session_id}/research")
def run_research(session_id: str, _user=Depends(get_current_user)):
    return workflow.run_research(session_id)


@app.get("/sessions/{session_id}/sources")
def get_sources(session_id: str, _user=Depends(get_current_user)):
    return workflow.get_sources(session_id)


@app.patch("/sessions/{session_id}/ratings")
def update_ratings(session_id: str, req: RatingsRequest, _user=Depends(get_current_user)):
    return workflow.update_ratings(session_id, req.option_ratings, req.weights)


@app.get("/sessions/{session_id}/decision")
def get_decision(session_id: str, _user=Depends(get_current_user)):
    return workflow.get_decision(session_id)


@app.post("/sessions/{session_id}/deck")
def build_deck(session_id: str, template: Optional[UploadFile] = File(None),
               _user=Depends(get_current_user)):
    template_bytes = template.file.read() if template else None
    result = workflow.build_deck(session_id, template_bytes)
    result.pop("bytes", None)  # binary is served by GET /deck.pptx
    return result


@app.get("/sessions/{session_id}/deck.pptx")
def get_deck(session_id: str, _user=Depends(get_current_user)):
    session = workflow._get(session_id)
    if not session.deck_path:
        return _error("NO_DECK", "No deck built", [], 404)
    path = ROOT / session.deck_path
    return Response(content=path.read_bytes(),
                    media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")


@app.get("/sessions/{session_id}/audit")
def get_audit(session_id: str, _user=Depends(get_current_user)):
    return workflow.get_audit(session_id)
