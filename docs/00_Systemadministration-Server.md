# Simple Version – Dokumentation Systemadministration (Server)

Dokumentation für den/die Systemadministrator:in. Hier geht es um Installation,
Dienst- und Autostart-Verwaltung, Konfiguration, Backup/Wiederherstellung,
Logs und Fehlersuche.

---

## 1. Überblick

**Simple Version** ist eine webbasierte Archiv-Verwaltung mit Versionskontrolle
für industrielle Automation (SPS-, HMI-, Safety-Projekte, Zeichnungen usw.).

| Komponente | Technologie |
|---|---|
| Backend | Python 3.10+, FastAPI, Uvicorn (optional mehrere Worker) |
| Datenbank | SQLite (`data/simver.db`, Datei-basiert) |
| Dateiablage | `data/archives/` (eine Datei je Version) |
| Frontend | Einzeldatei `frontend/index.html` (kein Build / kein Node nötig) |
| Authentifizierung | Session-Cookie (7 Tage, gleitende Verlängerung), PBKDF2-Passwort-Hash, Login-Sperre bei Fehlversuchen |
| Abhängigkeiten | `fastapi`, `uvicorn`, `python-multipart`, `aiofiles` |

Das System kennt drei Rollen: **Admin**, **Supervisor** und **Benutzer**.

---

## 2. Verzeichnisstruktur

```
simple-version/
├── backend/            # Server-Code
│   ├── main.py         # App-Instanz, Middleware, /api/stats, Frontend-Auslieferung
│   ├── config.py       # zentrale Konfiguration (Sessions, Cookie, Login-Sperre)
│   ├── auth.py         # Passwort-Hash, Sessions, Login-Sperre, Berechtigungen
│   ├── database.py     # SQLite-Zugriff + Schema-Initialisierung
│   ├── storage.py      # Streaming-Upload (SHA256 beim Schreiben), Dateiablage
│   ├── models.py       # Pydantic-Modelle
│   └── routers/        # API-Router
│       ├── session.py      # /api/login, /api/logout, /api/me, Passwort ändern
│       ├── users.py        # Benutzer-Verwaltung
│       ├── permissions.py  # Ordner-Zuweisungen
│       ├── folders.py      # Ordnerstruktur
│       └── archives.py     # Upload/Download/Versionen/Kommentare/Status
├── frontend/           # index.html (UI)
├── data/               # Laufzeitdaten – MUSS gesichert werden!
│   ├── simver.db       # SQLite-Datenbank (Ordner, Archive, Benutzer, Rechte, Verlauf)
│   └── archives/       # Versionierte Dateien: <archive_id>/v<N>_<dateiname>
├── requirements.txt    # Python-Abhängigkeiten
├── install.sh          # Installationsskript (venv + Abhängigkeiten + systemd)
├── run.sh              # Manueller Start (ohne systemd)
├── backup.sh           # Konsistentes Backup von data/ (sqlite .backup + archives)
└── .venv/              # Virtuelle Python-Umgebung (wird von install.sh erzeugt)
```

> **Wichtig:** `data/` enthält sämtliche Daten. Für ein Backup reicht es,
> `data/` zu sichern.

---

## 3. Systemanforderungen

- Linux (getestet auf Debian/Ubuntu-Derivaten)
- `python3` ≥ **3.10**
- ca. 200 MB freier Speicherplatz
- Ein frei wählbarer TCP-Port (Standard: **8001**)
- Für den automatischen Start als Dienst: `systemd` + `root`

Auf anderen Plattformen (Windows/macOS) funktioniert die Anwendung ebenfalls –
dann ohne systemd-Autostart (`./run.sh`).

---

## 4. Installation

### 4.1 Projekt auf den Server kopieren

```bash
# vom Entwicklungsrechner aus
scp -r simple-version root@<server-ip>:/opt/
```

Für den produktiven Einsatz empfiehlt sich ein Ort wie `/opt/simple-version`.
Rechte prüfen:

```bash
cd /opt/simple-version
chmod +x install.sh run.sh
```

### 4.2 Installer ausführen (als root)

```bash
sudo ./install.sh
```

Der Installer führt aus:

1. **Python-Check** (≥ 3.10)
2. **Virtuelle Umgebung** `.venv` – fehlt `python3-venv`, wird es automatisch
   via `apt` nachinstalliert
3. **Abhängigkeiten** aus `requirements.txt` + Import-Check
4. **systemd-Dienst** `simple-version.service` anlegen + starten + Autostart
5. **Firewall** (ufw): Port automatisch freigeben, falls die Firewall aktiv ist

Ausgabe (Beispiel):

```
[OK]             Python 3.11
[OK]             Virtuelle Umgebung (.venv)
[OK]             Abhängigkeiten installiert
[OK]             Dienst läuft (simple-version)
  Zugriff im Netzwerk : http://<SERVER-IP>:8001
  Admin-Login         : admin / admin   (Passwort in der Verwaltung ändern!)
```

### 4.3 Konfiguration über Umgebungsvariablen

Der Installer respektiert die Variablen **zum Installationszeitpunkt**:

```bash
PORT=8080 ./install.sh              # anderer Port (Standard 8001)
HOST=0.0.0.0 ./install.sh           # Bind-Adresse (Standard 0.0.0.0)
SERVICE_USER=svuser ./install.sh    # Dienst-Benutzer (Standard root, übernimmt Projektbesitz)
WORKERS=2 ./install.sh              # Anzahl Uvicorn-Worker (Standard 1)
COOKIE_SECURE=1 ./install.sh        # Session-Cookie nur über HTTPS (wenn TLS vorgeschaltet)
SESSION_DAYS=14 ./install.sh        # Session-Gültigkeit in Tagen (Standard 7, gleitend verlängert)
LOGIN_MAX_ATTEMPTS=5 ./install.sh   # Fehlversuche bis Login-Sperre (Standard 5)
LOGIN_LOCK_MINUTES=15 ./install.sh  # Sperrdauer in Minuten (Standard 15)
```

Die optionalen Optionen (`COOKIE_SECURE`, `SESSION_DAYS`, `PBKDF2_ITERATIONS`,
`LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCK_MINUTES`) werden als `Environment=` in die
systemd-Unit geschrieben, falls sie beim Aufruf gesetzt sind.

Ein späterer Wechsel von Port/Bind-Adresse erfordert eine Anpassung der
Systemd-Unit:

```bash
sudo systemctl edit simple-version.service   # dann:
# [Service]
# ExecStart=/opt/simple-version/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8081 --workers 1
sudo systemctl daemon-reload
sudo systemctl restart simple-version
```

> **Hinweis:** Änderungen an `PORT`/`HOST`/`WORKERS` sind nur im systemd-Befehl
> **`ExecStart`** wirksam – sie werden nicht als `Environment=` gesetzt.
> Bei mehreren Workern wird die SQLite-Datenbank im WAL-Modus gemeinsam genutzt
> (Login-Sperre und Sessions sind datenbankgestützt und daher Workern unabhängig).

---

## 5. Dienst- und Autostart-Verwaltung

```bash
systemctl status  simple-version      # Status anzeigen
systemctl restart simple-version      # Neustart
systemctl stop    simple-version      # Stoppen
systemctl start   simple-version      # Starten
systemctl enable  simple-version      # Autostart einschalten (Standard: an)
systemctl disable simple-version      # Autostart ausschalten
```

Nach einer Änderung am Projekt (z. B. Frontend-Dateien austauschen) ist ein
Neustart meist nicht nötig – `index.html` wird bei jedem Request von der Platte
gelesen. Nach einer Code-Änderung am Backend:

```bash
sudo systemctl restart simple-version
```

---

## 6. Logs und Fehlersuche

### Dienst-Logs

```bash
journalctl -u simple-version -f            # live mitverfolgen
journalctl -u simple-version --since today # heutige Ausgabe
journalctl -u simple-version -n 100        # letzte 100 Zeilen
```

### Häufige Fehler

| Symptom | Ursache / Lösung |
|---|---|
| Port bereits belegt | `ss -ltnp | grep 8001` – andere Instanz stoppen oder `PORT` wechseln |
| `python3-venv fehlt` | Installer installiert es automatisch; sonst `apt install python3-venv` |
| Zugriff von anderen PCs nicht möglich | Firewall: `ufw allow 8001/tcp`; Bind-Adresse `0.0.0.0` prüfen |
| Dienst startet nicht | `journalctl -u simple-version -n 50` ansehen; `python3 -m compileall backend` testen |
| Vergessenes Admin-Passwort | siehe Abschnitt 8 (Notfall-Zugriff) |

---

## 7. Backup und Wiederherstellung

### Was gesichert werden muss

Nur der Ordner **`data/`**:

- `data/simver.db` – Datenbank (Ordner, Archive, Benutzer, Rollen, Rechte, Verlauf)
- `data/archives/` – alle versionierten Dateien

Alles andere (Code, Frontend, `.venv`) ist reproduzierbar.

### Sauberes Backup (empfohlen, ohne Dienstunterbrechung)

SQLite läuft im WAL-Modus – für ein konsistentes Abbild die Datenbank per
SQLite-Kommando sichern und den Dateibaum mitkopieren. Das Paket enthält dafür
das fertige Skript **`backup.sh`**:

```bash
cd /opt/simple-version
sudo ./backup.sh                                         # -> /mnt/backups/simple-version-<Zeitstempel>
sudo ./backup.sh /pfad/zum/ziel                          # beliebiges Ziel
# Cron-Eintrag (täglich 02:10):
#   10 2 * * * /opt/simple-version/backup.sh /mnt/backups/latest 2>&1 >/dev/null
```

Manuell entspricht das dem Skript-Inhalt:

```bash
APP=/opt/simple-version
DEST=/mnt/backups/simple-version-$(date +%Y%m%d-%H%M%S)
mkdir -p "$DEST"
sqlite3 "$APP/data/simver.db" ".backup '$DEST/simver.db'"
cp -a "$APP/data/archives" "$DEST/archives"
```

> Alternativ kann der Dienst kurz gestoppt werden:
> `systemctl stop simple-version && cp -a data /mnt/backups/... && systemctl start simple-version`

### Wiederherstellung

```bash
sudo systemctl stop simple-version
# ABLAGE ZWISCHENLAGERN, falls es das alte Datenbetriebsvolumen sein soll:
# mv data data.bak
#   ODER (empfohlen) nur die archivierte Dateien + DB zurückkopieren:
[ -d data ] && rm -rf data/archives
mkdir -p data
cp -a <backup>/archives data/archives
cp <backup>/simver.db data/simver.db
sudo systemctl start simple-version
```

Stimmt die Anzahl der `data/archives/<id>`-Verzeichnisse nicht zur Datenbank,
werden fehlende Dateien beim Download als „nicht gefunden" gemeldet – die Datenbank
selbst bleibt intakt.

---

## 8. Sicherheit & Notfall

- **Standard-Anmeldung nach Erstinstallation sofort ändern:**
  `admin / admin` – über **oben rechts → „Passwort ändern"** (Button ist für
  **jede Rolle** verfügbar: Admin, Supervisor und Benutzer können so ihr
  eigenes Passwort jederzeit selbst ändern; das aktuelle Passwort wird dabei
  zur Bestätigung abgefragt).
- Passwörter werden gehasht (PBKDF2-SHA256, 200.000 Iterationen) gespeichert –
  Klartext liegt nirgends vor.
- **Login-Sperre:** nach `LOGIN_MAX_ATTEMPTS` (Standard 5) Fehlversuchen
  innerhalb von `LOGIN_LOCK_MINUTES` (Standard 15) Minuten wird der
  Benutzername für diese Dauer gesperrt (`HTTP 423`). Das betrifft **auch
  korrekte Passwörter** in der Sperrzeit. Die Sperre ist datenbankgestützt und
  läuft automatisch ab (keine manuelle Freigabe nötig).
- **Sessions:** sind 7 Tage gültig (Cookie, `Path=/`, `HttpOnly`,
  `SameSite=Lax`) und werden **gleitend verlängert** (Restzeit < 1 Tag →
  Verlängerung um vollen Zeitraum). Die App sendet `Cache-Control: no-store`.
  Mit `COOKIE_SECURE=1` wird das Cookie zusätzlich nur über HTTPS gesendet
  (nur bei vorgeschaltetem TLS aktivieren!).
- **Passwortwechsel invalidiert Sessions:** Ändert ein Benutzer sein Passwort
  („Passwort ändern"), werden **alle anderen** Sessions dieses Benutzers
  beendet. Setzt ein Admin das Passwort eines Benutzers zurück, werden **alle**
  Sessions dieses Benutzers beendet (dieser muss sich neu anmelden).
- Download-Dateien werden gestreamt; beim Upload wird die Datei **streaming**
  (nicht im RAM gepuffert) auf Platte geschrieben, SHA256-Prüfsumme und Größe
  werden dabei direkt berechnet.
- **Notfall: verlorenes Admin-Passwort zurücksetzen** (direkt auf dem Server):

```bash
cd /opt/simple-version/backend
/opt/simple-version/.venv/bin/python -c "
from auth import hash_password
from database import get_db
h, s = hash_password('neuPasswort123')
c = get_db()
c.execute(\"UPDATE users SET password_hash=?, password_salt=? WHERE username='admin'\", (h, s))
c.commit()
c.close()
print('Passwort für admin zurückgesetzt')"
```

Danach mit `admin` / `neuPasswort123` anmelden.

> Es gilt: **Löschen ist nur für Admin/Supervisor freigeschaltet.**
> Benutzer können Upload/Kommentare/Bearbeitungsstatus, aber nichts löschen.

---

## 9. Aktualisierung (Update)

1. Alte Daten sichern (Abschnitt 7).
2. Neue Projektversion über die alte kopieren (außer `data/`):
   ```bash
   rsync -a --delete --exclude data --exclude .venv neu/ /opt/simple-version/
   ```
3. Erneut installieren (Aktualisiert Abhängigkeiten, behält Daten):
   ```bash
   cd /opt/simple-version && sudo ./install.sh
   ```
4. Datenbank-Migrationen laufen automatisch beim Start (`init_db`).

---

## 10. Deinstallation

```bash
sudo systemctl disable --now simple-version
rm /etc/systemd/system/simple-version.service
sudo systemctl daemon-reload
sudo rm -rf /opt/simple-version          # VORSICHT: löscht auch alle Daten!
```

---

## 11. Kurzreferenz

| Bereich | Befehl |
|---|---|
| Installation | `sudo ./install.sh` |
| Manueller Start | `./run.sh` (Port: `PORT=8080 ./run.sh`) |
| Status | `systemctl status simple-version` |
| Neustart | `systemctl restart simple-version` |
| Logs | `journalctl -u simple-version -f` |
| Backup | `data/` – Kopie von `data/simver.db` + `data/archives/` |
| Erster Login | `http://<server-ip>:8001` – `admin / admin` |