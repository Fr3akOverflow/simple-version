import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "simver.db"


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER REFERENCES folders(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS archives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id INTEGER NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'frei',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(folder_id, name)
        );

        CREATE TABLE IF NOT EXISTS archive_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id INTEGER NOT NULL REFERENCES archives(id) ON DELETE CASCADE,
            version_number INTEGER NOT NULL,
            filename TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            checksum TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id INTEGER NOT NULL REFERENCES archives(id) ON DELETE CASCADE,
            version_id INTEGER REFERENCES archive_versions(id) ON DELETE SET NULL,
            action TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'supervisor', 'user')),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS folder_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            folder_id INTEGER NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
            granted_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, folder_id)
        );

        CREATE TABLE IF NOT EXISTS login_attempts (
            username TEXT PRIMARY KEY,
            attempts INTEGER NOT NULL DEFAULT 0,
            window_start TEXT NOT NULL,
            locked_until TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_archives_folder ON archives(folder_id);
        CREATE INDEX IF NOT EXISTS idx_versions_archive ON archive_versions(archive_id);
        CREATE INDEX IF NOT EXISTS idx_comments_archive ON comments(archive_id);
        CREATE INDEX IF NOT EXISTS idx_permissions_user ON folder_permissions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
    """)

    comments_cols = _columns(conn, "comments")
    if "user_id" not in comments_cols:
        conn.execute("ALTER TABLE comments ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_comments_user ON comments(user_id)")

    users_cols = _columns(conn, "users")
    if "display_name" not in users_cols:
        conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT")

    # Default-Admin anlegen, falls noch kein Benutzer existiert
    if conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"] == 0:
        from auth import hash_password
        h, s = hash_password("admin")
        conn.execute(
            "INSERT INTO users (username, password_hash, password_salt, role, display_name) VALUES (?, ?, ?, 'admin', 'Admin')",
            ("admin", h, s),
        )

    conn.commit()
    conn.close()


def folder_row(conn: sqlite3.Connection, folder_id: int):
    return conn.execute(
        "SELECT id, parent_id, name, created_at FROM folders WHERE id = ?", (folder_id,)
    ).fetchone()


def collect_folder_ids(conn: sqlite3.Connection, folder_id: int) -> list[int]:
    """Ordner selbst plus alle Unterordner (rekursiv)."""
    ids: list[int] = []
    stack = [folder_id]
    while stack:
        fid = stack.pop()
        ids.append(fid)
        children = conn.execute("SELECT id FROM folders WHERE parent_id = ?", (fid,)).fetchall()
        stack.extend(r["id"] for r in children)
    return ids


def collect_archive_ids(conn: sqlite3.Connection, folder_id: int) -> list[int]:
    """Alle Archiv-IDs im Unterbaum (inkl. des Ordners selbst)."""
    ids: list[int] = []
    stack = [folder_id]
    seen: set[int] = set()
    while stack:
        fid = stack.pop()
        if fid in seen:
            continue
        seen.add(fid)
        for a in conn.execute("SELECT id FROM archives WHERE folder_id = ?", (fid,)).fetchall():
            ids.append(a["id"])
        stack.extend(r["id"] for r in conn.execute("SELECT id FROM folders WHERE parent_id = ?", (fid,)).fetchall())
    return ids