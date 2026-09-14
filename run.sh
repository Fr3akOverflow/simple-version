#!/usr/bin/env bash
#
# Simple Version - manueller Start (ohne systemd)
# Vorher mindestens einmal ./install.sh ausführen (legt .venv an).
#
#   ./run.sh                  # Port 8001, 0.0.0.0, 1 Worker
#   PORT=8080 ./run.sh
#   WORKERS=2 COOKIE_SECURE=1 ./run.sh
#
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
VENV_DIR="$PROJECT_DIR/.venv"
PORT="${PORT:-8001}"
HOST="${HOST:-0.0.0.0}"
WORKERS="${WORKERS:-1}"

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[FEHLER] Virtuelle Umgebung fehlt - bitte zuerst ./install.sh ausführen." >&2
  exit 1
fi

# Bereits laufende Instanz auf dem gleichen Port beenden, bevor gestartet wird.
if command -v pgrep >/dev/null 2>&1; then
  if pgrep -f "[m]ain:app --host $HOST --port $PORT" >/dev/null 2>&1; then
    echo "[WARN] Es läuft bereits eine Instanz auf $HOST:$PORT."
    echo "       Zum Beenden: pgrep -f 'uvicorn main:app' auswerten und Prozess stoppen."
  fi
fi

echo "Starte Simple Version auf http://${HOST}:${PORT}  (${WORKERS} Worker, Strg+C zum Beenden)"
cd "$BACKEND_DIR"
exec "$VENV_DIR/bin/python" -m uvicorn main:app --host "$HOST" --port "$PORT" --workers "$WORKERS"