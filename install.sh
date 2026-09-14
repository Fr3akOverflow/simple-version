#!/usr/bin/env bash
#
# Simple Version - Installationsskript
# -----------------------------
# Erstellt die virtuelle Umgebung, installiert alle Abhängigkeiten und
# richtet - wenn systemd und Root vorhanden sind - einen automatisch
# startenden Dienst ein (einfach kopierbar auf die Zielmaschine).
#
# Verwendung:
#   ./install.sh                  # Standard (Port 8001, 0.0.0.0)
#   PORT=8080 ./install.sh        # Anderer Port
#   SERVICE_USER=svuser ...       # Dienst unter anderem Benutzer
#
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
VENV_DIR="$PROJECT_DIR/.venv"

PORT="${PORT:-8001}"
HOST="${HOST:-0.0.0.0}"
WORKERS="${WORKERS:-1}"
SERVICE_NAME="simple-version"
SERVICE_USER="${SERVICE_USER:-root}"

# Weitere, per Environment steuerbare Optionen (werden als Environment= in die Unit geschrieben)
OPTIONAL_ENVS="COOKIE_SECURE SESSION_DAYS PBKDF2_ITERATIONS LOGIN_MAX_ATTEMPTS LOGIN_LOCK_MINUTES"

PY_MIN_MAJOR=3
PY_MIN_MINOR=10

say(){  printf '\033[1;36m[simple-version]\033[0m %s\n' "$*"; }
good(){ printf '\033[1;32m[OK]\033[0m             %s\n' "$*"; }
fail(){ printf '\033[1;31m[FEHLER]\033[0m        %s\n' "$*" >&2; exit 1; }

[ -f "$BACKEND_DIR/main.py" ] || fail "backend/main.py nicht gefunden - Skript muss im Projektordner liegen."
[ -f "$PROJECT_DIR/requirements.txt" ] || fail "requirements.txt nicht gefunden."

say "Projektordner: $PROJECT_DIR"

# ---------------------------------------------------------------- Python
command -v python3 >/dev/null 2>&1 || fail "python3 ist nicht installiert (z.B. 'apt install python3')."
PY_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MAJOR="${PY_VERSION%%.*}"
PY_MINOR="${PY_VERSION#*.}"
PY_MINOR="${PY_MINOR%%.*}"
if [ "$PY_MAJOR" -lt "$PY_MIN_MAJOR" ] || { [ "$PY_MAJOR" -eq "$PY_MIN_MAJOR" ] && [ "$PY_MINOR" -lt "$PY_MIN_MINOR" ]; }; then
  fail "Python $PY_VERSION vorhanden, benötigt wird Python ${PY_MIN_MAJOR}.${PY_MIN_MINOR}+"
fi
good "Python $PY_VERSION"

# ---------------------------------------------------------------- venv
make_venv(){
  python3 -m venv "$VENV_DIR"
}
if [ ! -x "$VENV_DIR/bin/python" ]; then
  say "Erstelle virtuelle Umgebung .venv ..."
  if ! make_venv 2>/dev/null; then
    if [ "$(id -u)" = "0" ] && command -v apt-get >/dev/null 2>&1; then
      say "python3-venv fehlt - installiere python3-venv und python3-pip ..."
      apt-get update -qq
      apt-get install -y -qq python3-venv python3-pip
      make_venv || fail "Virtuelle Umgebung konnte nicht erstellt werden."
    else
      fail "python3-venv fehlt - als Root ausführen oder 'python3-venv' installieren."
    fi
  fi
fi
good "Virtuelle Umgebung (.venv)"

# ------------------------------------------------- Abhängigkeiten
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt" -q
"$VENV_DIR/bin/python" -c "import fastapi, uvicorn, multipart, aiofiles" \
  || fail "Import-Check der Abhängigkeiten fehlgeschlagen."
good "Abhängigkeiten installiert (fastapi, uvicorn, python-multipart, aiofiles)"

# ------------------------------------------------- systemd
if command -v systemctl >/dev/null 2>&1 && [ "$(id -u)" = "0" ]; then
  if [ "$SERVICE_USER" != "root" ] && ! id "$SERVICE_USER" >/dev/null 2>&1; then
    say "Benutzer '$SERVICE_USER' existiert nicht - verwende root."
    SERVICE_USER="root"
  fi
  if [ "$SERVICE_USER" != "root" ] && [ "$(stat -c %U "$PROJECT_DIR")" != "$SERVICE_USER" ]; then
    say "Übernehme Besitzer des Projektordners für '$SERVICE_USER' (chown -R) ..."
    chown -R "$SERVICE_USER" "$PROJECT_DIR"
    good "Besitzer: $SERVICE_USER"
  fi

  SERVICE_UNIT="/etc/systemd/system/${SERVICE_NAME}.service"
  say "Richte systemd-Dienst '$SERVICE_NAME' ein (http://$HOST:$PORT, ${WORKERS} Worker) ..."
  cat > "$SERVICE_UNIT" <<EOF
[Unit]
Description=Simple Version - Archivverwaltung
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$BACKEND_DIR
ExecStart=$VENV_DIR/bin/python -m uvicorn main:app --host $HOST --port $PORT --workers $WORKERS
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
  # Optional gesetzte Konfigurationsvariablen in die Unit übernehmen
  for e in $OPTIONAL_ENVS; do
    val="${!e:-}"
    if [ -n "$val" ]; then
      printf 'Environment=%s=%s\n' "$e" "$val" >> "$SERVICE_UNIT"
      good "$e=$val (Environment)"
    fi
  done
  systemctl daemon-reload
  systemctl enable "$SERVICE_NAME" >/dev/null 2>&1 || true
  systemctl restart "$SERVICE_NAME"
  sleep 2
  if systemctl -q is-active "$SERVICE_NAME"; then
    good "Dienst läuft ($SERVICE_NAME)"
  else
    fail "Dienst startet nicht - Protokoll ansehen: systemctl status $SERVICE_NAME"
  fi
else
  say "Kein systemd/Root erkannt - manueller Start über ./run.sh (kein Autostart)."
fi

# ------------------------------------------------- Firewall
if command -v ufw >/dev/null 2>&1 && [ "$(id -u)" = "0" ]; then
  if ufw status 2>/dev/null | grep -q "Status: active"; then
    ufw allow "$PORT/tcp" >/dev/null 2>&1 || true
    good "Firewall: Port $PORT/tcp freigegeben (ufw)"
  fi
fi

# ------------------------------------------------- Zusammenfassung
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
IP="${IP:-<IP-Adresse>}"
say "------------------------------------------------------------"
say "Installation abgeschlossen."
say "  Zugriff im Netzwerk : http://${IP}:${PORT}"
say "  Lokal               : http://${HOST}:${PORT}"
say "  Admin-Login         : admin / admin   (Passwort SOFORT über 'Passwort ändern' ändern!)"
say "  Dienst verwalten    : systemctl {status|restart|stop} $SERVICE_NAME"
say "  Worker / Konfig     : WORKERS=$WORKERS · optional: COOKIE_SECURE=1 SESSION_DAYS=…"
say "  Ohne systemd        : ./run.sh"
say "------------------------------------------------------------"