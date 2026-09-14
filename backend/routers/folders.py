from fastapi import APIRouter, HTTPException, Request

from auth import require_user, tree_visible_ids, folder_accessible
from database import get_db, folder_row, collect_archive_ids
from models import Folder, FolderCreate, FolderRename
from storage import remove_archive

router = APIRouter()


def build_tree(rows: list, visible: set[int] | None = None) -> list[Folder]:
    if visible is not None:
        rows = [r for r in rows if r["id"] in visible]

    by_parent: dict[int | None, list] = {}
    for r in rows:
        by_parent.setdefault(r["parent_id"], []).append(dict(r))

    def build(pid):
        nodes = []
        for r in sorted(by_parent.get(pid, []), key=lambda x: x["name"].lower()):
            node = Folder(id=r["id"], name=r["name"], parent_id=r["parent_id"], created_at=r["created_at"])
            node.children = build(r["id"])
            nodes.append(node)
        return nodes

    return build(None)


@router.get("/api/folders", response_model=list[Folder])
async def list_folders(request: Request):
    user = require_user(request)
    conn = get_db()
    rows = conn.execute("SELECT id, parent_id, name, created_at FROM folders").fetchall()
    visible = tree_visible_ids(conn, user)
    conn.close()
    return build_tree(rows, visible)


@router.post("/api/folders", response_model=Folder)
async def create_folder(req: FolderCreate, request: Request):
    user = require_user(request)
    name = req.name.strip()
    if not name:
        raise HTTPException(422, "Ordnername darf nicht leer sein")

    conn = get_db()
    if req.parent_id is not None:
        parent = folder_row(conn, req.parent_id)
        if parent is None:
            conn.close()
            raise HTTPException(404, "Übergeordneter Ordner nicht gefunden")
    else:
        req.parent_id = None

    if user["role"] == "user":
        conn.close()
        raise HTTPException(403, "Keine Berechtigung zum Anlegen von Ordnern")
    if user["role"] == "supervisor" and req.parent_id is not None:
        if not folder_accessible(conn, user, req.parent_id):
            conn.close()
            raise HTTPException(403, "Ordner liegt außerhalb deines Berechtigungsbereichs")

    dup = conn.execute(
        "SELECT id FROM folders WHERE name = ? AND parent_id IS ?",
        (name, req.parent_id),
    ).fetchone()
    if dup:
        conn.close()
        raise HTTPException(409, "Ordner existiert bereits")

    cur = conn.execute(
        "INSERT INTO folders (name, parent_id) VALUES (?, ?)",
        (name, req.parent_id),
    )
    conn.commit()
    row = conn.execute("SELECT id, parent_id, name, created_at FROM folders WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return Folder(**dict(row))


@router.patch("/api/folders/{folder_id}", response_model=Folder)
async def rename_folder(folder_id: int, req: FolderRename, request: Request):
    user = require_user(request)
    if user["role"] == "user":
        raise HTTPException(403, "Keine Berechtigung zum Umbenennen")
    name = req.name.strip()
    if not name:
        raise HTTPException(422, "Ordnername darf nicht leer sein")

    conn = get_db()
    folder = folder_row(conn, folder_id)
    if folder is None:
        conn.close()
        raise HTTPException(404, "Ordner nicht gefunden")
    if user["role"] == "supervisor" and not folder_accessible(conn, user, folder_id):
        conn.close()
        raise HTTPException(403, "Ordner liegt außerhalb deines Berechtigungsbereichs")

    dup = conn.execute(
        "SELECT id FROM folders WHERE name = ? AND parent_id = ? AND id != ?",
        (name, folder["parent_id"], folder_id),
    ).fetchone()
    if dup:
        conn.close()
        raise HTTPException(409, "Ordner existiert bereits")

    conn.execute("UPDATE folders SET name = ? WHERE id = ?", (name, folder_id))
    conn.commit()
    row = conn.execute("SELECT id, parent_id, name, created_at FROM folders WHERE id = ?", (folder_id,)).fetchone()
    conn.close()
    return Folder(**dict(row))


@router.delete("/api/folders/{folder_id}")
async def delete_folder(folder_id: int, request: Request):
    user = require_user(request)
    if user["role"] == "user":
        raise HTTPException(403, "Löschen ist für Benutzer nicht verfügbar")
    conn = get_db()
    folder = conn.execute("SELECT id FROM folders WHERE id = ?", (folder_id,)).fetchone()
    if folder is None:
        conn.close()
        raise HTTPException(404, "Ordner nicht gefunden")
    if user["role"] == "supervisor" and not folder_accessible(conn, user, folder_id):
        conn.close()
        raise HTTPException(403, "Ordner liegt außerhalb deines Berechtigungsbereichs")

    archive_ids = collect_archive_ids(conn, folder_id)
    conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
    conn.commit()
    conn.close()

    for aid in archive_ids:
        remove_archive(aid)
    return {"status": "deleted"}