from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from database import init_db

from routers.session import router as session_router
from routers.users import router as users_router
from routers.permissions import router as permissions_router
from routers.folders import router as folders_router
from routers.archives import router as archives_router

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Simple Version", lifespan=lifespan)


@app.middleware("http")
async def no_cache(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=(FRONTEND_DIR / "index.html").read_text())


app.include_router(session_router)
app.include_router(users_router)
app.include_router(permissions_router)
app.include_router(folders_router)
app.include_router(archives_router)


@app.get("/api/stats")
async def get_stats(request: Request):
    from auth import require_user, tree_visible_ids, accessible_folder_ids
    from database import get_db

    user = require_user(request)
    conn = get_db()
    visible = tree_visible_ids(conn, user)
    accessible = accessible_folder_ids(conn, user)
    if not accessible:
        conn.close()
        return {"folders": 0, "archives": 0, "versions": 0, "editing": 0}

    placeholders = ",".join("?" for _ in accessible)
    folders = len(visible)
    archives = conn.execute(
        f"SELECT COUNT(*) AS c FROM archives WHERE folder_id IN ({placeholders})",
        tuple(accessible),
    ).fetchone()["c"]
    versions = conn.execute(
        f"SELECT COUNT(*) AS c FROM archive_versions v "
        f"JOIN archives a ON a.id = v.archive_id WHERE a.folder_id IN ({placeholders})",
        tuple(accessible),
    ).fetchone()["c"]
    editing = conn.execute(
        f"SELECT COUNT(*) AS c FROM archives WHERE status = 'bearbeitung' "
        f"AND folder_id IN ({placeholders})",
        tuple(accessible),
    ).fetchone()["c"]
    conn.close()
    return {"folders": folders, "archives": archives, "versions": versions, "editing": editing}