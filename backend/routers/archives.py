from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from auth import require_user, folder_accessible
from database import get_db, folder_row
from models import Archive, ArchiveVersion, Comment, CommentCreate, StatusChange
from storage import (
    stream_to_temp, commit_version, discard_temp, discard_version,
    version_path, remove_archive,
)

router = APIRouter()


def folder_accessible_or_403(conn, user, folder_id, msg="Kein Zugriff auf diesen Ordner"):
    if not folder_accessible(conn, user, folder_id):
        raise HTTPException(403, msg)


def _check_archive_access(conn, user: dict, archive_id: int):
    """Prüft Zugriff auf ein Archiv und liefert dessen folder_id. Wirft HTTPException bei Fehler."""
    row = conn.execute("SELECT id, folder_id FROM archives WHERE id = ?", (archive_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Archiv nicht gefunden")
    if not folder_accessible(conn, user, row["folder_id"]):
        raise HTTPException(403, "Kein Zugriff auf dieses Archiv")
    return row


def comments_query(conn, archive_id: int) -> list:
    return conn.execute(
        "SELECT c.id, c.action, c.version_id, c.text, c.created_at, u.username AS user_name, "
        "v.version_number "
        "FROM comments c "
        "LEFT JOIN users u ON u.id = c.user_id "
        "LEFT JOIN archive_versions v ON c.version_id = v.id "
        "WHERE c.archive_id = ? ORDER BY c.created_at DESC, c.id DESC",
        (archive_id,),
    ).fetchall()


def _require_comment(comment: str | None, field: str = "Kommentar"):
    if not comment or not comment.strip():
        raise HTTPException(422, f"{field} ist Pflicht")


# ---------- Archive ----------

@router.get("/api/folders/{folder_id}/archives", response_model=list[Archive])
async def list_archives(folder_id: int, request: Request):
    user = require_user(request)
    conn = get_db()
    if folder_row(conn, folder_id) is None:
        conn.close()
        raise HTTPException(404, "Ordner nicht gefunden")
    folder_accessible_or_403(conn, user, folder_id)

    rows = conn.execute("""
        SELECT a.id, a.folder_id, a.name, a.status, a.created_at,
               COUNT(v.id) as version_count
        FROM archives a
        LEFT JOIN archive_versions v ON v.archive_id = a.id
        WHERE a.folder_id = ?
        GROUP BY a.id
        ORDER BY a.name
    """, (folder_id,)).fetchall()

    # Neueste Version je Archiv in EINER Query (statt N+1).
    ids = [r["id"] for r in rows]
    latest: dict[int, dict] = {}
    if ids:
        placeholders = ",".join("?" for _ in ids)
        lv_rows = conn.execute(f"""
            SELECT archive_id, id, version_number, filename, size_bytes, checksum, created_at
            FROM (
                SELECT archive_id, id, version_number, filename, size_bytes, checksum, created_at,
                       ROW_NUMBER() OVER (PARTITION BY archive_id ORDER BY version_number DESC, id DESC) AS rn
                FROM archive_versions WHERE archive_id IN ({placeholders})
            ) WHERE rn = 1
        """, ids).fetchall()
        latest = {r["archive_id"]: dict(r) for r in lv_rows}
    conn.close()

    return [
        Archive(
            id=r["id"], folder_id=r["folder_id"], name=r["name"], status=r["status"],
            created_at=r["created_at"], version_count=r["version_count"],
            latest_version=ArchiveVersion(**latest[r["id"]]) if r["id"] in latest else None,
        )
        for r in rows
    ]


@router.post("/api/archives")
async def upload_archive(
    request: Request,
    folder_id: int = Form(...),
    comment: str = Form(...),
    file: UploadFile = File(...),
):
    user = require_user(request)
    _require_comment(comment, "Kommentar bei Upload")

    original_name = Path(file.filename or "datei.bin").name
    if not original_name:
        raise HTTPException(422, "Dateiname fehlt")
    if original_name.startswith("v") and "_" in original_name and original_name[1:].split("_", 1)[0].isdigit():
        raise HTTPException(422, "Ungültiger Dateiname")

    conn = get_db()
    if folder_row(conn, folder_id) is None:
        conn.close()
        raise HTTPException(404, "Ordner nicht gefunden")
    folder_accessible_or_403(conn, user, folder_id)

    archive = conn.execute(
        "SELECT id FROM archives WHERE folder_id = ? AND name = ?",
        (folder_id, original_name),
    ).fetchone()
    if archive is None:
        cur = conn.execute(
            "INSERT INTO archives (folder_id, name) VALUES (?, ?)",
            (folder_id, original_name),
        )
        archive_id = cur.lastrowid
        version_number = 1
    else:
        archive_id = archive["id"]
        last = conn.execute(
            "SELECT MAX(version_number) as mv FROM archive_versions WHERE archive_id = ?",
            (archive_id,),
        ).fetchone()["mv"]
        version_number = (last or 0) + 1
    conn.commit()
    conn.close()

    # Streaming in Temp-Datei (RAM-unabhängig), SHA256 + Größe beim Schreiben berechnen.
    tmp_path, checksum_hex, size = stream_to_temp(file.file)
    stored_name = None
    try:
        if size == 0:
            raise HTTPException(422, "Leere Datei")
        stored_name = commit_version(tmp_path, archive_id, version_number, original_name)

        conn = get_db()
        try:
            cur = conn.execute(
                "INSERT INTO archive_versions (archive_id, version_number, filename, size_bytes, checksum) VALUES (?, ?, ?, ?, ?)",
                (archive_id, version_number, stored_name, size, checksum_hex),
            )
            version_id = cur.lastrowid
            conn.execute(
                "INSERT INTO comments (archive_id, version_id, action, text, user_id) VALUES (?, ?, 'upload', ?, ?)",
                (archive_id, version_id, comment.strip(), user["id"]),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, version_number, filename, size_bytes, checksum, created_at FROM archive_versions WHERE id = ?",
                (version_id,),
            ).fetchone()
        finally:
            conn.close()
    except BaseException:
        if stored_name:
            discard_version(archive_id, stored_name)
        discard_temp(tmp_path)
        raise

    return {"archive_id": archive_id, "version": ArchiveVersion(**dict(row))}


@router.get("/api/archives/{archive_id}", response_model=Archive)
async def get_archive(archive_id: int, request: Request):
    user = require_user(request)
    conn = get_db()
    _check_archive_access(conn, user, archive_id)
    r = conn.execute("""
        SELECT a.id, a.folder_id, a.name, a.status, a.created_at, COUNT(v.id) as version_count
        FROM archives a LEFT JOIN archive_versions v ON v.archive_id = a.id
        WHERE a.id = ? GROUP BY a.id
    """, (archive_id,)).fetchone()
    ver = conn.execute(
        "SELECT id, version_number, filename, size_bytes, checksum, created_at FROM archive_versions "
        "WHERE archive_id = ? ORDER BY version_number DESC LIMIT 1",
        (archive_id,),
    ).fetchone()
    conn.close()
    return Archive(
        id=r["id"], folder_id=r["folder_id"], name=r["name"], status=r["status"],
        created_at=r["created_at"], version_count=r["version_count"],
        latest_version=ArchiveVersion(**dict(ver)) if ver else None,
    )


@router.get("/api/archives/{archive_id}/versions", response_model=list[ArchiveVersion])
async def list_archive_versions(archive_id: int, request: Request):
    user = require_user(request)
    conn = get_db()
    _check_archive_access(conn, user, archive_id)
    rows = conn.execute(
        "SELECT id, version_number, filename, size_bytes, checksum, created_at FROM archive_versions "
        "WHERE archive_id = ? ORDER BY version_number DESC",
        (archive_id,),
    ).fetchall()
    conn.close()
    return [ArchiveVersion(**dict(r)) for r in rows]


@router.get("/api/archives/{archive_id}/download")
@router.get("/api/archives/{archive_id}/download/{version_id}")
async def download_archive(archive_id: int, version_id: int | None = None, request: Request = None):
    user = require_user(request)
    conn = get_db()
    name_row = conn.execute("SELECT name, folder_id FROM archives WHERE id = ?", (archive_id,)).fetchone()
    if name_row is None:
        conn.close()
        raise HTTPException(404, "Archiv nicht gefunden")
    if not folder_accessible(conn, user, name_row["folder_id"]):
        conn.close()
        raise HTTPException(403, "Kein Zugriff auf dieses Archiv")
    if version_id is None:
        row = conn.execute(
            "SELECT filename FROM archive_versions WHERE archive_id = ? ORDER BY version_number DESC LIMIT 1",
            (archive_id,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT filename FROM archive_versions WHERE archive_id = ? AND id = ?",
            (archive_id, version_id),
        ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(404, "Version nicht gefunden")

    p = version_path(archive_id, row["filename"])
    if p is None:
        raise HTTPException(404, "Datei nicht gefunden")
    return FileResponse(path=str(p), filename=name_row["name"], media_type="application/octet-stream")


@router.post("/api/archives/{archive_id}/status", response_model=Archive)
async def set_status(archive_id: int, req: StatusChange, request: Request):
    user = require_user(request)
    if req.status not in ("frei", "bearbeitung"):
        raise HTTPException(422, "Ungültiger Status")

    conn = get_db()
    _check_archive_access(conn, user, archive_id)

    if req.status == "bearbeitung":
        _require_comment(req.comment, "Kommentar zum Bearbeiten")
        conn.execute(
            "INSERT INTO comments (archive_id, action, text, user_id) VALUES (?, 'status', ?, ?)",
            (archive_id, f"IN BEARBEITUNG gesetzt: {req.comment.strip()}", user["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO comments (archive_id, action, text, user_id) VALUES (?, 'status', ?, ?)",
            (archive_id, f"Bearbeitung beendet: {req.comment.strip() if req.comment and req.comment.strip() else 'Freigegeben'}", user["id"]),
        )

    conn.execute("UPDATE archives SET status = ? WHERE id = ?", (req.status, archive_id))
    conn.commit()
    conn.close()
    return await get_archive(archive_id, request)


@router.post("/api/archives/{archive_id}/comments", response_model=Comment)
async def add_comment(archive_id: int, req: CommentCreate, request: Request):
    user = require_user(request)
    _require_comment(req.text, "Kommentar")
    conn = get_db()
    _check_archive_access(conn, user, archive_id)
    cur = conn.execute(
        "INSERT INTO comments (archive_id, action, text, user_id) VALUES (?, 'kommentar', ?, ?)",
        (archive_id, req.text.strip(), user["id"]),
    )
    conn.commit()
    row = comments_query(conn, archive_id)
    conn.close()
    row = next(r for r in row if r["id"] == cur.lastrowid)
    return Comment(
        id=row["id"], action=row["action"], text=row["text"],
        version_number=row["version_number"], created_at=row["created_at"], user_name=row["user_name"],
    )


@router.get("/api/archives/{archive_id}/comments", response_model=list[Comment])
async def list_comments(archive_id: int, request: Request):
    user = require_user(request)
    conn = get_db()
    _check_archive_access(conn, user, archive_id)
    rows = comments_query(conn, archive_id)
    conn.close()
    return [
        Comment(
            id=r["id"], action=r["action"], text=r["text"],
            version_number=r["version_number"], created_at=r["created_at"], user_name=r["user_name"],
        )
        for r in rows
    ]


@router.delete("/api/archives/{archive_id}")
async def delete_archive(archive_id: int, request: Request):
    user = require_user(request)
    if user["role"] == "user":
        raise HTTPException(403, "Löschen ist für Benutzer nicht verfügbar")
    conn = get_db()
    archive = conn.execute("SELECT id, folder_id FROM archives WHERE id = ?", (archive_id,)).fetchone()
    if archive is None:
        conn.close()
        raise HTTPException(404, "Archiv nicht gefunden")
    if user["role"] == "supervisor" and not folder_accessible(conn, user, archive["folder_id"]):
        conn.close()
        raise HTTPException(403, "Kein Zugriff auf dieses Archiv")
    conn.execute("DELETE FROM archives WHERE id = ?", (archive_id,))
    conn.commit()
    conn.close()
    remove_archive(archive_id)
    return {"status": "deleted"}