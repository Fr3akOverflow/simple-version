from fastapi import APIRouter, HTTPException, Request

from auth import require_user, folder_accessible, accessible_folder_ids
from database import get_db, collect_folder_ids
from models import PermissionGrant

router = APIRouter()


@router.get("/api/permissions")
async def list_permissions(request: Request):
    user = require_user(request)
    conn = get_db()
    if user["role"] == "admin":
        rows = conn.execute(
            "SELECT p.id, p.user_id, u.username, u.display_name, u.role AS user_role, "
            "p.folder_id, f.name AS folder_name, "
            "(SELECT username FROM users WHERE id = p.granted_by) AS granted_by_username "
            "FROM folder_permissions p "
            "JOIN users u ON u.id = p.user_id "
            "JOIN folders f ON f.id = p.folder_id "
            "ORDER BY p.created_at DESC"
        ).fetchall()
    else:
        scope = accessible_folder_ids(conn, user)
        placeholders = ",".join("?" for _ in scope)
        rows = conn.execute(
            "SELECT p.id, p.user_id, u.username, u.display_name, u.role AS user_role, "
            "p.folder_id, f.name AS folder_name, "
            "(SELECT username FROM users WHERE id = p.granted_by) AS granted_by_username "
            "FROM folder_permissions p "
            "JOIN users u ON u.id = p.user_id "
            "JOIN folders f ON f.id = p.folder_id "
            f"WHERE p.folder_id IN ({placeholders}) "
            "ORDER BY p.created_at DESC",
            tuple(scope),
        ).fetchall()
    conn.close()
    return [
        {"id": r["id"], "user_id": r["user_id"], "username": r["username"],
         "display_name": r["display_name"], "user_role": r["user_role"],
         "folder_id": r["folder_id"], "folder_name": r["folder_name"],
         "granted_by": r["granted_by_username"]}
        for r in rows
    ]


@router.post("/api/permissions")
async def grant_permission(req: PermissionGrant, request: Request):
    actor = require_user(request)
    conn = get_db()

    target = conn.execute("SELECT id, role FROM users WHERE id = ?", (req.user_id,)).fetchone()
    if target is None:
        conn.close()
        raise HTTPException(404, "Benutzer nicht gefunden")

    folder = conn.execute("SELECT id FROM folders WHERE id = ?", (req.folder_id,)).fetchone()
    if folder is None:
        conn.close()
        raise HTTPException(404, "Ordner nicht gefunden")

    if actor["role"] == "supervisor":
        if target["role"] != "user":
            conn.close()
            raise HTTPException(403, "Supervisor kann nur Benutzern Ordner zuweisen")
        if not folder_accessible(conn, actor, req.folder_id):
            conn.close()
            raise HTTPException(403, "Ordner liegt außerhalb deines Berechtigungsbereichs")
    elif actor["role"] != "admin":
        conn.close()
        raise HTTPException(403, "Keine Berechtigung zum Zuweisen")

    try:
        folder_ids = collect_folder_ids(conn, req.folder_id)
        existing = {r["folder_id"] for r in conn.execute(
            f"SELECT folder_id FROM folder_permissions WHERE user_id = ? AND folder_id IN ({','.join('?' * len(folder_ids))})",
            (req.user_id, *folder_ids),
        ).fetchall()}
        added = 0
        for fid in folder_ids:
            if fid in existing:
                continue
            conn.execute(
                "INSERT INTO folder_permissions (user_id, folder_id, granted_by) VALUES (?, ?, ?)",
                (req.user_id, fid, actor["id"]),
            )
            added += 1
        conn.commit()
    except Exception:
        conn.close()
        raise HTTPException(500, "Zuweisung fehlgeschlagen")
    conn.close()
    return {"status": "granted", "folders": added}


@router.delete("/api/permissions/{perm_id}")
async def revoke_permission(perm_id: int, request: Request):
    actor = require_user(request)
    conn = get_db()
    perm = conn.execute(
        "SELECT id, user_id, folder_id, granted_by FROM folder_permissions WHERE id = ?", (perm_id,)
    ).fetchone()
    if perm is None:
        conn.close()
        raise HTTPException(404, "Zuweisung nicht gefunden")
    if actor["role"] == "user":
        conn.close()
        raise HTTPException(403, "Keine Berechtigung")
    if actor["role"] == "supervisor":
        if perm["granted_by"] != actor["id"]:
            conn.close()
            raise HTTPException(403, "Nur eigene Zuweisungen können aufgehoben werden")
        if not folder_accessible(conn, actor, perm["folder_id"]):
            conn.close()
            raise HTTPException(403, "Ordner liegt außerhalb deines Berechtigungsbereichs")
    folder_ids = collect_folder_ids(conn, perm["folder_id"])
    cur = conn.execute(
        f"DELETE FROM folder_permissions WHERE user_id = ? AND folder_id IN ({','.join('?' * len(folder_ids))})",
        (perm["user_id"], *folder_ids),
    )
    conn.commit()
    removed = cur.rowcount
    conn.close()
    return {"status": "revoked", "removed": removed}