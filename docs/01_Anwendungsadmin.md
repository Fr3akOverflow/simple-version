# Simple Version – Dokumentation Anwendungsadmin

Dokumentation für den/die **Anwendungs-Administrator:in**. Hier geht es um die
tägliche Verwaltung der Anwendung im Web-Browser: Benutzerkonten, Rollen,
Berechtigungen auf Ordner, Ordnerstruktur und Archiv-Inhalte.

---

## 1. Anmelden & Abmelden

1. Anwendung im Browser öffnen: `http://<server-ip>:8001`
2. Mit **Benutzername** und **Passwort** anmelden.
3. Oben rechts wird der angemeldete Benutzer mit seinem **Rollen-Badge** angezeigt.
4. **Abmelden** über den Button „Abmelden" oben rechts.

> Standard-Konto nach der Erstinstallation: `admin` / `admin` –
> **das Passwort sofort über den Button „Passwort ändern" oben rechts
> ändern** (funktioniert für jede Rolle – auch für dein eigenes Konto).

---

## 2. Rollen im Überblick

| Rolle | Ordner sehen | Ordner anlegen/umbenennen | Löschen | Upload/Kommentar/Status | Benutzer & Rechte verwalten |
|---|---|---|---|---|---|
| **Admin** | alles | überall | überall | überall | ja, unbeschränkt |
| **Supervisor** | nur eigene Bereiche | nur im eigenen Bereich | nur im eigenen Bereich | im eigenen Bereich | Benutzern Ordner im eigenen Bereich zuweisen |
| **Benutzer** | nur zugeteilte Ordner | nein | **nie** | in zugeteilten Ordnern | nein |

Alle Rechte werden **serverseitig** erzwungen – nicht nur das UI ausgeblendet.

---

## 3. Die Verwaltung (⚙)

Oben rechts auf **⚙ Verwaltung** klicken. Als Admin siehst du:

- **Benutzer anlegen** (Formular ganz oben)
- pro Benutzer eine Karte mit:
  - Rollen-Auswahl (zuständig)
  - „Passwort"-Button (Passwort zurücksetzen)
  - „Löschen"-Button
  - **Zugewiesene Ordner** (Chips, mit × entziehen)
  - „Zuweisen"-Auswahl (Ordner auswählen → zuweisen)

### 3.1 Benutzer anlegen

| Feld | Bedeutung |
|---|---|
| Benutzername | eindeutiger Login-Name (Pflicht) |
| Anzeigename | Anzeige in der Kopfzeile (optional) |
| Passwort | Initial-Passwort (Pflicht) |
| Rolle | **Supervisor**, **Benutzer** oder **Admin** |

Danach **+** klicken. Der Benutzer kann sich sofort anmelden.

### 3.2 Rolle ändern / Passwort zurücksetzen

- Rolle: in der Benutzerkarte das Auswahlfeld ändern → gilt sofort.
- Passwort: auf **Passwort** klicken, neues Passwort im Dialog eingeben.

> **Dein eigenes Passwort** änderst du nicht hier, sondern über den Button
> **„Passwort ändern" oben rechts im Kopfbereich** (gilt für alle Rollen,
> das aktuelle Passwort wird zur Sicherheit abgefragt).

> **Andere Admin-Konten** kannst du **nicht ändern** (weder Rolle noch Name).
> **Löschen** darfst du sie jedoch – solange mindestens ein Admin übrig bleibt
> („Es muss mindestens ein Admin existieren"). Dein **eigenes** Konto kannst du
> weder ändern (keine Selbst-Herabstufung) noch löschen.

### 3.3 Benutzer löschen

**Löschen** in der Benutzerkarte → bestätigen. Alle Ordner-Zuweisungen dieses
Benutzers entfallen automatisch. Sein Konto (auch Verlauf-Einträge „von
Benutzer Y") bleibt in der Anzeige erhalten, aber sperr- und vererbungslos.

> Du kannst dein **eigenes** Konto nicht löschen.

---

## 4. Berechtigungen auf Ordner (Bereiche)

### 4.1 Zuweisen

1. In einer Benutzerkarte im Dropdown **„Ordner zuweisen"** einen Ordner wählen.
2. **„Zuweisen"** klicken.

**Automatische Unterordner:** Wird **ein Ordner zugewiesen, werden automatisch
alle seine Unterordner mit zugewiesen** – explizit als eigene Einträge angelegt.

Beispiel: „Testbereich 1" zugewiesen → „Testbereich 1" **und** „SPS"
(darunter) gelten als zugeteilt.

Der Benutzer sieht danach exakt diesen Bereich (plus evtl. weitere Zuweisungen).

### 4.2 Entziehen

Auf das **×** am Chip eines zugewiesenen Ordners klicken → bestätigen.

**Automatischer Unterordner-Entzug:** Es werden **alle zugehörigen
Unterordner mit entzogen** (für denselben Benutzer). Der Benutzer verliert
damit sofort den Zugriff, auch auf darin liegende Archive.

> Tipp: Wird nur ein Unterordner (z. B. „SPS") entzogen, bleibt der
> übergeordnete Bereich (z. B. „Testbereich 1") weiterhin zugeteilt.
> Wird der übergeordnete Bereich entzogen, entfällt der komplette Unterbaum.

### 4.3 Sichtbarkeit nur über den Pfad

Hat ein Benutzer nur einen **Unterordner** zugeteilt (nicht dessen
übergeordnete Ebene), erscheinen die Zwischen-Ordner als reiner **Pfad**:
Sie sind sichtbar, aber der Benutzer kann dort weder Inhalte sehen noch
hochladen – direkt verfügbar ist ausschließlich der zugeteilte Bereich.

---

## 5. Ordner-Verwaltung

### 5.1 Ordner im Stammbereich anlegen

Links oben im Eingabefeld **„Neuer Ordner im Stammbereich..."** Namen eingeben
und **+** klicken.

### 5.2 Unterordner anlegen (Vorlagen)

1. Ordner links **anklicken**, dann **„Unterordner"** oben rechts – oder das
   **⊕**-Symbol des Ordnerzeilen-Ziels.
2. Es erscheint eine Auswahl mit **Checkboxen**:

   **SPS · HMI · Frequenzumformer · Safety · Zeichnung-E · Zeichnung-M**

3. Eine oder mehrere Kategorien anhaken – **alle angehakten** werden angelegt.
4. Optional ein **eigener Name** zusätzlich.
5. **„Anlegen"** klicken.

Bereits vorhandene Namen werden als Fehler gemeldet, die übrigen trotzdem angelegt.

### 5.3 Umbenennen

Richtung:  **✎**-Symbol an der Ordnerzeile (sichtbar bei Hover) → neuen Namen
eingeben.

### 5.4 Ordner löschen (inkl. Inhalt)

**🗑**-Symbol an der Ordnerzeile oder **„Ordner löschen"** oben rechts → Dialog
bestätigen. **WARNUNG:** Der Ordner wird mitsamt **allen Unterordnern und
Archiven endgültig gelöscht** (auch die gespeicherten Dateien auf dem Server).

---

## 6. Archive

- **Hochladen:** Ordner anklicken → **Upload** → Datei wählen → **Kommentar
  (Pflicht!)** → „Hochladen". Jeder Upload erzeugt automatisch die **nächste
  Version** (V1 → V2 → …). Äquivalente Namen gelten als neue Version.
- **Bearbeitungsstatus:** In der Archiv-Karte „✎ Bearbeiten" (setzt **In
  Bearbeitung**, Kommentar Pflicht) bzw. „✓ Freigeben" (Kommentar optional).
- **Kommentare & Verlauf:** „💬 Details" zeigt Versionen und Verlauf –
  **neuester Eintrag zuerst**, mit **Verfasser** (Benutzername).
- **Download:** „⬇ Download" (aktuellste Version) oder per Version in den Details.

Als Admin siehst du alle Archive aller Bereiche.

---

## 7. Wichtige Hinweise

- **Kennwörter geheim halten** – Administratoren können auf alle Daten zugreifen.
- **Verantwortung Löschen:** einmal gelöschte Archive sind unwiederbringlich weg.
- **Rollenhierarchie einhalten:** der Admin vergibt Supervisoren ganze
  Bereiche; Supervisoren verwalten Benutzer **innerhalb** ihrer Bereiche.
- **Zwang-Kommentare** sind bewusst Pflicht (Upload + In-Bearbeitung) – das
  sichert die Nachvollziehbarkeit des Verlaufs.