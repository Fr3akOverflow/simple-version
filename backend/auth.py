import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta

from fastapi import HTTPException, Request

from config import (
    SESSION_COOKIE,
    SESSION_DAYS,
    PBKDF2_ITERATIONS,
    LOGIN_MAX_ATTEMPTS,
    LOGIN_LOCK_MINUTES,
)
from database import get_db

_TS = "%Y-%m-%d %H:%M:%S"
# Sliding Expiration: Session verlängern, wenn weniger als dieser Rest übrig ist.
EXTEND_BEFORE = timedelta(days=1)


def _now() -> str:
    return datetime.utcnow().strftime(_TS)


def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    ).hex()
    return h, salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    h = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    ).hex()
    return hmac.compare_digest(h, password_hash)


def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    expires = (datetime.utcnow() + timedelta(days=SESSION_DAYS)).strftime(_TS)
    conn = get_db()
    conn.execute(
        "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
        (user_id, token, expires),
    )
    conn.commit()
    conn.close()
    return token


def get_session_user(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    conn = get_db()
    row = conn.execute(
        "SELECT u.id, u.username, u.role, s.expires_at FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.token = ? AND s.expires_at > datetime('now')",
        (token,),
    ).fetchone()
    if row is None:
        conn.close()
        return None
    user = dict(row)
    # Sliding Expiration: Restzeit < 1 Tag -> Session um den vollen Zeitraum verlängern.
    try:
        expires = datetime.strptime(row["expires_at"], _TS)
        if expires - datetime.utcnow() < EXTEND_BEFORE:
            new_exp = (datetime.utcnow() + timedelta(days=SESSION_DAYS)).strftime(_TS)
            conn.execute("UPDATE sessions SET expires_at = ? WHERE token = ?", (new_exp, token))
            conn.commit()
    except (ValueError, TypeError):
        pass
    conn.close()
    return user


def invalidate_sessions(user_id: int, keep_token: str | None = None):
    """Löscht alle Sessions eines Benutzers (optional mit Ausnahme des eigenen Tokens)."""
    conn = get_db()
    if keep_token:
        conn.execute("DELETE FROM sessions WHERE user_id = ? AND token != ?", (user_id, keep_token))
    else:
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# ---------- Login-Schutz (Brute-Force) ----------

def login_locked(username: str) -> bool:
    """True, wenn der Benutzername aktuell gesperrt ist (Sperre läuft automatisch ab)."""
    conn = get_db()
    row = conn.execute(
        "SELECT locked_until FROM login_attempts WHERE username = ?", (username,)
    ).fetchone()
    if row is None:
        conn.close()
        return False
    locked_until = row["locked_until"]
    if locked_until:
        if locked_until > _now():
            conn.close()
            return True
        conn.execute("DELETE FROM login_attempts WHERE username = ?", (username,))
        conn.commit()
    conn.close()
    return False


def record_failed_login(username: str):
    conn = get_db()
    now = _now()
    row = conn.execute(
        "SELECT attempts, window_start, locked_until FROM login_attempts WHERE username = ?",
        (username,),
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO login_attempts (username, attempts, window_start) VALUES (?, 1, ?)",
            (username, now),
        )
    elif row["locked_until"] and row["locked_until"] > now:
        pass  # bereits gesperrt
    else:
        attempts = row["attempts"]
        ws = row["window_start"]
        fresh = False
        try:
            fresh = (datetime.utcnow() - datetime.strptime(ws, _TS)) <= timedelta(minutes=LOGIN_LOCK_MINUTES)
        except (ValueError, TypeError):
            fresh = True
        attempts = attempts + 1 if fresh else 1
        window_start = ws if fresh else now
        locked_until = None
        if attempts >= LOGIN_MAX_ATTEMPTS:
            locked_until = (datetime.utcnow() + timedelta(minutes=LOGIN_LOCK_MINUTES)).strftime(_TS)
            attempts = LOGIN_MAX_ATTEMPTS
        conn.execute(
            "UPDATE login_attempts SET attempts = ?, window_start = ?, locked_until = ? WHERE username = ?",
            (attempts, window_start, locked_until, username),
        )
    conn.commit()
    conn.close()


def clear_failed_logins(username: str):
    conn = get_db()
    conn.execute("DELETE FROM login_attempts WHERE username = ?", (username,))
    conn.commit()
    conn.close()


def require_user(request: Request):
    user = get_session_user(request)
    if user is None:
        raise HTTPException(401, "Nicht angemeldet")
    return user


def require_admin(request: Request):
    user = require_user(request)
    if user["role"] != "admin":
        raise HTTPException(403, "Nur für Administratoren")
    return user


def login(username: str, password: str) -> sqlite3.Row | None:
    conn = get_db()
    user = conn.execute(
        "SELECT id, username, password_hash, password_salt, role FROM users WHERE username = ?",
        (username.strip(),),
    ).fetchone()
    conn.close()
    if user is None:
        return None
    if not verify_password(password, user["password_hash"], user["password_salt"]):
        return None
    return user


def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        conn = get_db()
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()


def folder_accessible(conn: sqlite3.Connection, user: dict, folder_id: int) -> bool:
    """Prüft, ob der Benutzer Zugriff auf diesen Ordner (und damit den Unterbaum) hat."""
    if user["role"] == "admin":
        return True
    folder = conn.execute("SELECT id, parent_id FROM folders WHERE id = ?", (folder_id,)).fetchone()
    if folder is None:
        return False
    granted = {
        r["folder_id"]
        for r in conn.execute(
            "SELECT folder_id FROM folder_permissions WHERE user_id = ?", (user["id"],)
        ).fetchall()
    }
    if folder_id in granted:
        return True
    parent = folder["parent_id"]
    guard = 0
    while parent is not None and guard < 100:
        if parent in granted:
            return True
        parent = conn.execute(
            "SELECT parent_id FROM folders WHERE id = ?", (parent,)
        ).fetchone()
        parent = None if parent is None else parent["parent_id"]
        guard += 1
    return False


def accessible_folder_ids(conn: sqlite3.Connection, user: dict) -> set[int]:
    """Alle Ordner-IDs im Zugriffsbereich (zugeteilte Ordner + deren Unterbaum)."""
    if user["role"] == "admin":
        return {r["id"] for r in conn.execute("SELECT id FROM folders").fetchall()}
    granted = [r["folder_id"] for r in conn.execute(
        "SELECT folder_id FROM folder_permissions WHERE user_id = ?", (user["id"],)
    ).fetchall()]
    accessible = set()
    stack = list(granted)
    checked = set()
    while stack:
        fid = stack.pop()
        if fid in checked:
            continue
        checked.add(fid)
        accessible.add(fid)
        children = conn.execute("SELECT id FROM folders WHERE parent_id = ?", (fid,)).fetchall()
        stack.extend(r["id"] for r in children)
    return accessible


def tree_visible_ids(conn: sqlite3.Connection, user: dict) -> set[int]:
    """Sichtbare Ordner im Baum: Zugriffsbereich plus die Pfad-Vorfahren (nur Pfad, nicht deren Inhalt)."""
    visible = accessible_folder_ids(conn, user)
    if user["role"] == "admin":
        return visible

    extra = set()
    for fid in list(visible):
        parent = conn.execute("SELECT parent_id FROM folders WHERE id = ?", (fid,)).fetchone()
        parent = None if parent is None else parent["parent_id"]
        while parent is not None and parent not in visible:
            extra.add(parent)
            row = conn.execute("SELECT parent_id FROM folders WHERE id = ?", (parent,)).fetchone()
            parent = None if row is None else row["parent_id"]
    return visible | extra


def folder_can_manage(user: dict) -> bool:
    return user["role"] in ("admin", "supervisor")


def can_delete(user: dict) -> bool:
    return user["role"] in ("admin", "supervisor")