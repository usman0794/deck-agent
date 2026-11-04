"""Session model and storage for the agent workflow."""
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
SESSIONS_DIR = ROOT / "sessions"
DATA_DIR = ROOT / "session_data"


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class Session:
    id: str
    status: str = "created"
    data_ref: Optional[str] = None
    profile: dict = field(default_factory=dict)
    user_text: str = ""
    intent: dict = field(default_factory=dict)
    questions_asked: list = field(default_factory=list)
    questions_answered: dict = field(default_factory=dict)
    options: list = field(default_factory=list)
    weights: dict = field(default_factory=dict)
    best: int = 0
    decision: dict = field(default_factory=dict)
    confidence: dict = field(default_factory=dict)
    findings: list = field(default_factory=list)
    deck_path: Optional[str] = None
    problem_type: dict = field(default_factory=dict)
    data_summary: dict = field(default_factory=dict)
    reason: str = ""
    check: dict = field(default_factory=dict)
    research: dict = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class SessionStore:
    def save(self, session):
        raise NotImplementedError

    def get(self, session_id):
        raise NotImplementedError

    def delete(self, session_id):
        raise NotImplementedError


class InMemoryStore(SessionStore):
    def __init__(self):
        self._sessions = {}

    def save(self, session):
        self._sessions[session.id] = session

    def get(self, session_id):
        return self._sessions.get(session_id)

    def delete(self, session_id):
        self._sessions.pop(session_id, None)


class FileStore(SessionStore):
    def __init__(self, directory=None):
        self.dir = Path(directory or SESSIONS_DIR)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id):
        return self.dir / f"{session_id}.json"

    def save(self, session):
        session.updated_at = _now()
        self._path(session.id).write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")

    def get(self, session_id):
        p = self._path(session_id)
        if not p.exists():
            return None
        return Session.from_dict(json.loads(p.read_text(encoding="utf-8")))

    def delete(self, session_id):
        p = self._path(session_id)
        if p.exists():
            p.unlink()


def get_store(kind="file"):
    if kind == "memory":
        return InMemoryStore()
    return FileStore()
