from fastapi import APIRouter, HTTPException, Request

from auth import require_user, require_admin, hash_password, invalidate_sessions
from database import get_db
from models import UserCreate, UserUpdate

router = APIRouter()


@router.get("/api/users")
async def list_users(request: Request):
    user = require_user(request)
    conn = get_db()
    if user["role"] == "admin":
        rows = conn.execute(
            "SELECT u.id, u.username, u.display_name, u.role FROM users u ORDER BY u.username"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT u.id, u.username, u.display_name, u.role FROM users u WHERE u.role = 'user' ORDER BY u.username"
        ).fetchall()

    perms: dict[int, list[int]] = {}
    for r in conn.execute("SELECT user_id, folder_id FROM folder_permissions").fetchall():
        perms.setdefault(r["user_id"], []).append(r["folder_id"])
    conn.close()
    return [
        {"id": r["id"], "username": r["username"], "display_name": r["display_name"],
         "role": r["role"], "permissions": perms.get(r["id"], [])}
        for r in rows
    ]


@router.post("/api/users")
async def create_user(req: UserCreate, request: Request):
    require_admin(request)
    username = req.username.strip()
    if not username:
        raise HTTPException(422, "Benutzername darf nicht leer sein")
    if not req.password:
        raise HTTPException(422, "Passwort darf nicht leer sein")
    if req.role not in ("admin", "supervisor", "user"):
        raise HTTPException(422, "Ungültige Rolle")

    conn = get_db()
    if conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
        conn.close()
        raise HTTPException(409, "Benutzername existiert bereits")
    h, s = hash_password(req.password)
    cur = conn.execute(
        "INSERT INTO users (username, password_hash, password_salt, role, display_name) VALUES (?, ?, ?, ?, ?)",
        (username, h, s, req.role, req.display_name or username),
    )
    conn.commit()
    conn.close()
    return {"id": cur.lastrowid, "username": username, "display_name": req.display_name or username, "role": req.role}


@router.patch("/api/users/{user_id}")
async def update_user(user_id: int, req: UserUpdate, request: Request):
    actor = require_admin(request)
    conn = get_db()
    target = conn.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,)).fetchone()
    if target is None:
        conn.close()
        raise HTTPException(404, "Benutzer nicht gefunden")

    if target["role"] == "admin" and target["id"] != actor["id"]:
        conn.close()
        raise HTTPException(403, "Andere Administratoren dürfen nicht geändert werden")

    if req.role is not None and req.role != target["role"]:
        if target["id"] == actor["id"] and req.role != "admin":
            conn.close()
            raise HTTPException(403, "Du kannst deine eigene Rolle nicht aufheben")
        admin_count = conn.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'admin'").fetchone()["c"]
        if target["role"] == "admin" and req.role != "admin" and admin_count <= 1:
            conn.close()
            raise HTTPException(403, "Es muss mindestens ein Admin existieren")
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (req.role, user_id))

    if req.display_name is not None:
        conn.execute("UPDATE users SET display_name = ? WHERE id = ?", (req.display_name.strip() or None, user_id))
    password_changed = False
    if req.password:
        h, s = hash_password(req.password)
        conn.execute("UPDATE users SET password_hash = ?, password_salt = ? WHERE id = ?", (h, s, user_id))
        password_changed = True
    conn.commit()
    target_id = target["id"]
    conn.close()
    # Sicherheit: bei Passwort-Neuzusetzung alle bestehenden Sessions des Benutzers beenden.
    if password_changed:
        invalidate_sessions(target_id)
    return {"status": "ok"}


@router.delete("/api/users/{user_id}")
async def delete_user(user_id: int, request: Request):
    actor = require_admin(request)
    conn = get_db()
    target = conn.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,)).fetchone()
    if target is None:
        conn.close()
        raise HTTPException(404, "Benutzer nicht gefunden")
    if target["id"] == actor["id"]:
        conn.close()
        raise HTTPException(403, "Du kannst dein eigenes Konto nicht löschen")
    if target["role"] == "admin":
        admin_count = conn.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'admin'").fetchone()["c"]
        if admin_count <= 1:
            conn.close()
            raise HTTPException(403, "Es muss mindestens ein Admin existieren")
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}