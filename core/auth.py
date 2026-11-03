"""Sign-in only authentication.

Two user sources are supported:
- access.json: simple editable file with plain passwords and roles.
- users.json: PBKDF2-hashed users created by manage_users.py.

No sign-up in the app.
"""
import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

USERS_FILE = Path(os.getenv("USERS_FILE", Path(__file__).resolve().parent.parent / "users.json"))
ACCESS_FILE = Path(os.getenv("ACCESS_FILE", Path(__file__).resolve().parent.parent / "access.json"))
SECRET_FILE = Path(os.getenv("AUTH_SECRET_FILE", Path(__file__).resolve().parent.parent / ".auth_secret"))
ITER = 200_000
TOKEN_TTL = int(os.getenv("SESSION_DAYS", "7")) * 24 * 3600  # stay signed in for 7 days


def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITER).hex()


def _load():
    return json.loads(USERS_FILE.read_text()) if USERS_FILE.exists() else {}


def _load_access():
    """Read access.json.

    Accepted shapes:
      {"users": {"name": "password"}}
      {"users": {"name": {"password": "password", "role": "admin"}}}
    """
    if not ACCESS_FILE.exists():
        return {}
    try:
        data = json.loads(ACCESS_FILE.read_text())
    except Exception:
        return {}
    raw = data.get("users", data) if isinstance(data, dict) else {}
    out = {}
    for name, val in raw.items():
        if isinstance(val, str):
            out[name.strip().lower()] = {"password": val, "role": "admin"}
        elif isinstance(val, dict):
            out[name.strip().lower()] = {
                "password": str(val.get("password", "")),
                "role": str(val.get("role", "admin")).strip().lower() or "admin",
            }
    return out


def _secret():
    """APP_SECRET from the environment, or a generated local key file."""
    key = os.getenv("APP_SECRET")
    if key:
        return key.encode()
    if SECRET_FILE.exists():
        return SECRET_FILE.read_bytes()
    key = os.urandom(32)
    SECRET_FILE.write_bytes(key)
    try:
        os.chmod(SECRET_FILE, 0o600)
    except OSError:
        pass
    return key


def _sign(payload):
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


def make_token(username, ttl=None):
    """Signed, expiring token stored in the browser cookie."""
    expires = int(time.time()) + (TOKEN_TTL if ttl is None else ttl)
    payload = f"{username}|{expires}"
    return base64.urlsafe_b64encode(f"{payload}|{_sign(payload)}".encode()).decode()


def verify_token(token):
    """Return the username for a valid, unexpired token, else None."""
    try:
        username, expires, signature = base64.urlsafe_b64decode(token.encode()).decode().rsplit("|", 2)
        if not hmac.compare_digest(signature, _sign(f"{username}|{expires}")):
            return None
        if int(expires) < time.time():
            return None
        return username if (username in _load() or username in _load_access()) else None
    except Exception:
        return None


def authenticate(username, password):
    """Return (ok, role). Checks access.json first, then hashed users.json."""
    name = username.strip().lower()
    access = _load_access()
    if name in access:
        ok = hmac.compare_digest(access[name]["password"], password)
        return ok, (access[name]["role"] if ok else None)
    u = _load().get(name)
    if not u:
        _hash(password, "00" * 16)  # keep timing similar
        return False, None
    ok = hmac.compare_digest(_hash(password, u["salt"]), u["hash"])
    return ok, ("admin" if ok else None)


def role_for(username):
    return _load_access().get(username.strip().lower(), {}).get("role", "admin")


def add_user(username, password):
    users = _load()
    salt = os.urandom(16).hex()
    users[username.strip().lower()] = {"salt": salt, "hash": _hash(password, salt)}
    USERS_FILE.write_text(json.dumps(users, indent=2))


def remove_user(username):
    users = _load()
    users.pop(username.strip().lower(), None)
    USERS_FILE.write_text(json.dumps(users, indent=2))


def list_users():
    return sorted(set(_load()) | set(_load_access()))


def verify(username, password):
    return authenticate(username, password)[0]
