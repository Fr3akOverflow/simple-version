from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

import auth as authmod
from auth import (
    login, logout, create_session, get_session_user,
    require_user, hash_password, verify_password,
    login_locked, record_failed_login, clear_failed_logins,
    invalidate_sessions,
)
from config import SESSION_COOKIE, COOKIE_SECURE, COOKIE_PATH, COOKIE_SAMESITE, SESSION_DAYS
from database import get_db
from models import LoginRequest, PasswordChange

router = APIRouter()


@router.post("/api/login")
async def api_login(req: LoginRequest):
    username = req.username.strip()
    if login_locked(username):
        raise HTTPException(423, "Zu viele Fehlversuche - vorübergehend gesperrt")
    user = login(username, req.password)
    if user is None:
        record_failed_login(username)
        raise HTTPException(401, "Benutzername oder Passwort falsch")
    clear_failed_logins(username)
    token = create_session(user["id"])
    resp = JSONResponse({"status": "ok", "user": {"id": user["id"], "username": user["username"], "role": user["role"]}})
    resp.set_cookie(
        SESSION_COOKIE, token,
        httponly=True, samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE,
        path=COOKIE_PATH, max_age=SESSION_DAYS * 86400,
    )
    return resp


@router.post("/api/logout")
async def api_logout(request: Request):
    logout(request)
    resp = JSONResponse({"status": "ok"})
    resp.delete_cookie(SESSION_COOKIE, path=COOKIE_PATH)
    return resp


@router.get("/api/me")
async def api_me(request: Request):
    user = get_session_user(request)
    if user is None:
        raise HTTPException(401, "Nicht angemeldet")
    conn = get_db()
    row = conn.execute(
        "SELECT id, username, display_name, role FROM users WHERE id = ?", (user["id"],)
    ).fetchone()
    conn.close()
    return {
        "id": row["id"], "username": row["username"], "display_name": row["display_name"],
        "role": row["role"],
        "can_manage": row["role"] in ("admin", "supervisor"),
        "can_delete": row["role"] in ("admin", "supervisor"),
    }


@router.patch("/api/me/password")
async def change_own_password(req: PasswordChange, request: Request):
    user = require_user(request)
    conn = get_db()
    row = conn.execute(
        "SELECT id, password_hash, password_salt FROM users WHERE id = ?", (user["id"],)
    ).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(404, "Benutzer nicht gefunden")
    if not verify_password(req.current_password, row["password_hash"], row["password_salt"]):
        conn.close()
        raise HTTPException(400, "Aktuelles Passwort ist falsch")
    h, s = hash_password(req.new_password)
    conn.execute("UPDATE users SET password_hash = ?, password_salt = ? WHERE id = ?", (h, s, user["id"]))
    conn.commit()
    conn.close()
    # Sicherheit: alle anderen Sessions dieses Benutzers invalidieren (aktueller Token bleibt erhalten).
    invalidate_sessions(user["id"], keep_token=request.cookies.get(SESSION_COOKIE))
    return {"status": "ok"}