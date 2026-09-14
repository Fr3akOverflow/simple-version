import hashlib
import os
import shutil
import tempfile
from pathlib import Path

STORAGE_DIR = Path(__file__).parent.parent / "data" / "archives"
CHUNK_SIZE = 1024 * 1024


def _tmp_dir() -> Path:
    """Temporäres Verzeichnis im selben Dateisystem wie STORAGE_DIR (für atomaren Move)."""
    d = STORAGE_DIR / ".upload_tmp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_name(filename: str) -> str:
    return Path(filename).name


def stream_to_temp(fileobj) -> tuple[str, str, int]:
    """Streamt eine Upload-Datei in eine Temp-Datei und berechnet dabei SHA256 + Größe.

    Liefert (tmp_path, sha256_hex, size_bytes). Bei Fehler wird die Temp-Datei entfernt.
    """
    fd, tmp_path = tempfile.mkstemp(dir=str(_tmp_dir()))
    h = hashlib.sha256()
    size = 0
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := fileobj.read(CHUNK_SIZE):
                out.write(chunk)
                h.update(chunk)
                size += len(chunk)
    except BaseException:
        discard_temp(tmp_path)
        raise
    return tmp_path, h.hexdigest(), size


def commit_version(tmp_path: str, archive_id: int, version_number: int, original_name: str) -> str:
    """Verschiebt die Temp-Datei atomar an ihren endgültigen Speicherort. Liefert den Namen."""
    archive_dir = STORAGE_DIR / str(archive_id)
    archive_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"v{version_number}_{_safe_name(original_name)}"
    os.replace(tmp_path, archive_dir / stored_name)
    return stored_name


def discard_temp(tmp_path: str):
    try:
        os.unlink(tmp_path)
    except OSError:
        pass


def discard_version(archive_id: int, stored_name: str):
    try:
        (STORAGE_DIR / str(archive_id) / stored_name).unlink()
    except OSError:
        pass


def version_path(archive_id: int, stored_name: str) -> Path | None:
    p = STORAGE_DIR / str(archive_id) / stored_name
    return p if p.is_file() else None


def remove_archive(archive_id: int):
    shutil.rmtree(STORAGE_DIR / str(archive_id), ignore_errors=True)