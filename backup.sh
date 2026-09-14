#!/usr/bin/env bash
#
# backup.sh – konsistentes Backup der Simple-Version-Daten
#
# Nutzung:
#   sudo ./backup.sh                      -> /mnt/backups/simple-version-<Zeitstempel>
#   sudo ./backup.sh /pfad/zum/ziel       -> in ein beliebiges Zielverzeichnis
#
# Sichert: data/simver.db (konsistent via sqlite .backup) + data/archives/.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/data"
DEST="${1:-/mnt/backups/simple-version-$(date +%Y%m%d-%H%M%S)}"

if [ ! -f "$DATA_DIR/simver.db" ]; then
  echo "[FEHLER] Keine Datenbank gefunden in $DATA_DIR (wurde die Anwendung schon einmal gestartet?)." >&2
  exit 1
fi

mkdir -p "$DEST"

# Konsistentes Abbild der Datenbank (auch bei laufendem Dienst, WAL-Modus).
# 1) bevorzugt: sqlite3-Kommando; 2) sonst: Projekt-Python mit SQLite-Backup-API.
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$DATA_DIR/simver.db" ".backup '$DEST/simver.db'"
  echo "[OK] simver.db (sqlite3 .backup)"
elif [ -x "$SCRIPT_DIR/.venv/bin/python" ] || command -v python3 >/dev/null 2>&1; then
  PY="${SCRIPT_DIR}/.venv/bin/python"
  [ -x "$PY" ] || PY="$(command -v python3)"
  "$PY" - "$DATA_DIR/simver.db" "$DEST/simver.db" <<'PYEOF'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
conn = sqlite3.connect(src)
out = sqlite3.connect(dst)
conn.backup(out)
out.close()
conn.close()
PYEOF
  echo "[OK] simver.db (Python-SQLite backup API)"
else
  echo "[WARN] weder sqlite3 noch python3 gefunden - Kopiere Datenbank ungesichert (Dienst vorher stoppen empfohlen)."
  cp "$DATA_DIR/simver.db" "$DEST/simver.db"
fi

# Archiv-Dateien (eine Datei je Version) mitkopieren.
if [ -d "$DATA_DIR/archives" ]; then
  cp -a "$DATA_DIR/archives" "$DEST/archives"
  echo "[OK] archives/"
fi

echo "------------------------------------------------------------"
echo "Backup abgeschlossen: $DEST"
echo "Gesamtgröße: $(du -sh "$DEST" | cut -f1)"