# Simple Version – Dokumentation (Übersicht)

**Simple Version** ist eine webbasierte Archiv-Verwaltung mit Versionskontrolle
für industrielle Automation (SPS-, HMI-, Safety-Projekte, Zeichnungen usw.) mit
rollenbasierter Rechtevergabe.

- Zugriff im Browser: `http://<server-ip>:8001`
- Erstanmeldung (MUSS geändert werden): `admin` / `admin`

## Zieldokumentationen

| Dokument | Für wen | Inhalt |
|---|---|---|
| [00 Systemadministration (Server)](00_Systemadministration-Server.md) | Server-Verantwortliche, IT | Installation, systemd-Dienst, Konfiguration, Backup/Wiederherstellung, Logs, Fehler, Sicherheit |
| [01 Anwendungsadmin](01_Anwendungsadmin.md) | Administrator | Benutzer & Rollen, Ordner-Berechtigungen, Ordnerstruktur, Archive, Verwaltung |
| [02 Supervisor](02_Supervisor.md) | Bereichsverantwortliche | Eigene Bereiche verwalten, Unterordner-Vorlagen, Benutzern Ordner zuweisen |
| [03 Benutzer](03_Benutzer.md) | Fachanwender | Anmelden, Upload/Versionen, Kommentare, Bearbeitungsstatus, Download |

## Rollenmodell (kompakt)

| Rolle | Ordner sehen | Ordner verwalten | Löschen | Upload/Kommentar/Status | Benutzer & Rechte |
|---|---|---|---|---|---|
| **Admin** | alles | überall | überall | überall | unbeschränkt |
| **Supervisor** | eigene Bereiche | eigene Bereiche | eigene Bereiche | eigene Bereiche | Benutzern Ordner im eigenen Bereich zuweisen |
| **Benutzer** | zugeteilte Ordner | – | **nie** | zugeteilte Ordner | – |

Vergeben/Entziehen eines Ordners betrifft **automatisch alle Unterordner** –
serverseitig erzwungen, nicht nur im UI ausgeblendet.

## Schnellstart

1. **Installation:** `sudo ./install.sh` (siehe Doku 00)
2. **Login:** `admin` / `admin` → Passwort ändern
3. **Ordner anlegen:** Stammbereich → Eingabefeld oben links; Unterordner mit
   Vorlagen (SPS, HMI, Frequenzumformer, Safety, Zeichnung-E, Zeichnung-M)
4. **Benutzer anlegen & Bereiche zuweisen** → ⚙ Verwaltung
5. **Backup:** `sudo ./backup.sh` (konsistentes Abbild von Daten + Archiven)

## Sicherheit (Standard)

- **Login-Sperre:** 5 Fehlversuche → gesperrt für 15 Minuten (läuft automatisch ab)
- **Passwortwechsel:** beendet andere Sessions des Benutzers
  (Admin-Zurücksetzen beendet alle Sessions des betroffenen Benutzers)
- **Sessions:** 7 Tage, gleitend verlängert, `HttpOnly`/`SameSite=Lax`-Cookie;
  optional `COOKIE_SECURE=1` für HTTPS-TLS-Betrieb
- **Upload:** streaming auf Platte (RAM-unabhängig), SHA256 beim Schreiben

Hinweis: Diese Dateien unter `docs/` sind Teil des Projekts; socket-spezifische
Werte (IP, Port) an die jeweilige Installation anzupassen.