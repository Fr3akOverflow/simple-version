# Simple Version – Dokumentation Supervisor

Dokumentation für **Supervisor:innen**. Als Supervisor verwaltest du die
Ordner **deines zugewiesenen Bereichs** und weist **Benutzern** Ordner in
deinem Bereich zu.

---

## 1. Was dir als Supervisor zusteht

Der Administrator hat dir **einen oder mehrere Ordner (= Bereiche)** zugewiesen,
z. B. „Testbereich 1". Rechte:

| Aktion | In deinem Bereich |
|---|---|
| Ordner sehen | ✓ (kompletter Unterbaum) |
| Ordner anlegen / Unterordner anlegen | ✓ |
| Ordner umbenennen | ✓ |
| Ordner löschen (inkl. Inhalt) | ✓ |
| Upload / Kommentare / Bearbeitungsstatus | ✓ |
| Benutzern (Rolle **Benutzer**) Ordner zuweisen / entziehen | ✓ (nur eigene Zuweisungen) |
| **Eigenes Passwort ändern** | ✓ (oben rechts → „Passwort ändern") |
| Benutzer oder Admins verwalten | ✗ |
| Ordner außerhalb deiner Bereiche | ✗ (nicht sichtbar) |

**Wichtig:** Die Rechte gelten **ausschließlich innerhalb deiner Bereiche**.
Was dir nicht zugewiesen ist, siehst du in der Ordnerliste nicht.

---

## 2. Anmelden

1. Anwendung öffnen: `http://<server-ip>:8001`
2. Mit Benutzername/Passwort anmelden.
3. Oben rechts siehst du deinen Namen und das Badge **„Supervisor"**.
4. **Eigenes Passwort ändern:** oben rechts auf **„Passwort ändern"** klicken –
   aktuelles Passwort eingeben, neues Passwort setzen. Gilt für alle Rollen.

---

## 3. Bereiche verwalten (Ordnerstruktur)

### 3.1 Unterordner anlegen (Vorlagen)

1. Ordner links anklicken, dann **„Unterordner"** – oder das **⊕**-Symbol
   an der Ordnerzeile.
2. **Checkboxen** anhaken: **SPS, HMI, Frequenzumformer, Safety,
   Zeichnung-E, Zeichnung-M** – alle angehakten werden angelegt.
3. Optional **einen eigenen Namen** zusätzlich.
4. **„Anlegen"** klicken.

### 3.2 Ordner umbenennen

**✎**-Symbol an der Ordnerzeile (Hover) → neuen Namen eingeben → bestätigen.

### 3.3 Ordner löschen

**🗑**-Symbol an der Ordnerzeile → Dialog bestätigen.
⚠️ **Geht mit:** alle Unterordner und Archive dieses Ordners werden
endgültig gelöscht (auch die gespeicherten Dateien). Nicht umkehrbar!

---

## 4. Benutzern Rechte geben (nur Rolle Benutzer)

1. Oben rechts **⚙ Verwaltung** öffnen.
2. Du siehst die Liste der **Benutzer** (Rolle „Benutzer").
3. In der Karte deines Benutzers:
   - **Dropdown „Ordner zuweisen"** → Ordner aus **deinem Bereich** wählen →
     **Zuweisen**.
   - **Entziehen:** **×** am Chip eines zugewiesenen Ordners.

### Automatik bei Zuweisung / Entzug

- **Zuweisen eines Ordners** → alle **Unterordner automatisch mit zugewiesen**.
- **Entziehen eines Ordners** → alle **Unterordner automatisch mit entzogen**.

### Einschränkungen (serverseitig erzwungen)

- Du kannst **nur Ordner aus deinem eigenen Bereich** zuweisen.
- Entziehen kannst du **nur Zuweisungen, die du selbst vergeben hast** –
  Zuweisungen des Admins (oder anderer Supervisoren) kannst du nicht ändern.
- Du kannst **keine Admins oder andere Supervisoren** verwalten.
- Du kannst Benutzer **nicht anlegen, löschen** oder **Rollen ändern**.

---

## 5. Pfad-Sichtbarkeit bei Unterordner-Zuweisung

Weist du einem Benutzer **nur einen Unterordner** zu (z. B. „SPS", nicht den
ganzen Bereich), sieht der Benutzer die darüberliegenden Ordner nur als **Pfad**
– als wäre es eine Browser-Navigation. Er kann dort nichts sehen und nichts
hochladen, verfügbar ist nur „SPS".

Tipp: Nur dann `zugewiesen`, wenn du den kompletten Bereich freigeben willst,
**„Testbereich 1"** zuweisen – Unterordner kommen automatisch mit.

---

## 6. Arbeit mit Archiven

- **Upload:** Ordner anklicken → **Upload** → Datei → **Kommentar (Pflicht)**
  → Hochladen. Jeder Upload erzeugt die **nächste Version** (V1, V2, …).
- **Status:** In der Archiv-Karte „✎ Bearbeiten" (**In Bearbeitung**, Kommentar
  Pflicht) bzw. „✓ Freigeben" (Kommentar optional).
- **Verlauf:** „💬 Details" – **neuester Eintrag oben**, mit **Verfasser**.
- **Download:** „⬇" in der Archiv-Karte, oder eine bestimmte Version in den
  Details.

---

## 7. Schnellübersicht „darf ich das?"

| Frage | Antwort |
|---|---|
| Sehe ich andere Bereiche als meine? | Nein |
| Darf ich im gesamten System löschen? | Nein, nur in meinem Bereich |
| Zuweisungen des Admins ändern? | Nein |
| Benutzer anlegen/löschen? | Nein |
| Upload/Pflicht-Kommentar? | Ja, in meinem Bereich |
| Unterordner-Anlagen mit Vorlagen? | Ja |