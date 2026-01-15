# TimeClock Benutzerhandbuch

> Vollständige Anleitung für Endbenutzer und Administratoren

**Übersetzungen:** [English](USER_GUIDE.md) | [Italiano (Italian)](USER_GUIDE_IT.md)

---

## Inhaltsverzeichnis

1. [Erste Schritte](#erste-schritte)
2. [Für Mitarbeiter](#für-mitarbeiter)
3. [Für Administratoren](#für-administratoren)
4. [Fehlerbehebung](#fehlerbehebung)

---

## Erste Schritte

### Erster Start

Wenn Sie TimeClock zum ersten Mal starten, werden Sie aufgefordert, einen **Administrator** zu registrieren. Dies ist obligatorisch und kann nicht übersprungen werden.

**Schritte:**
1. Geben Sie den vollständigen Namen des Administrators ein
2. Scannen Sie einen RFID-Badge (oder geben Sie die Tag-ID manuell ein)
3. Das Admin-Kontrollkästchen wird automatisch aktiviert und gesperrt
4. Klicken Sie auf **Speichern**, um die Registrierung abzuschließen

Nach der Registrierung kann der Administrator-Badge verwendet werden, um auf alle Verwaltungsfunktionen zuzugreifen.

---

## Für Mitarbeiter

### Ein- und Ausstempeln

**So stempeln Sie ein oder aus:**
1. Stellen Sie sich vor das TimeClock-Terminal
2. Halten Sie Ihren RFID-Badge in die Nähe des Lesers
3. Warten Sie auf das grüne LED-Blinken (bestätigt erfolgreichen Scan)
4. Eine freundliche Begrüßungsnachricht wird angezeigt (verschwindet nach 8 Sekunden)
5. Ihr Status wird auf dem Bildschirm aktualisiert

**Was passiert:**
- Das System bestimmt automatisch, ob Sie **EIN** oder **AUS** stempeln, basierend auf Ihrer letzten Aktion
- Wenn Ihre letzte Aktion AUS war (oder Sie heute noch nicht eingestempelt haben), stempeln Sie **EIN**
- Wenn Ihre letzte Aktion EIN war, stempeln Sie **AUS**

### Anzeige der Tageszusammenfassung

Nach jeder Stempelaktion sehen Sie:
- Eine freundliche Begrüßungsnachricht
- Eine Statusmeldung, die Ihre Stempelaktion anzeigt (z.B. "Eingestempelt - Ihr Name")
- Zwei Aktionsschaltflächen:
  - **Heutige Sitzungen anzeigen** - Detaillierte Aufschlüsselung der heutigen Sitzungen
  - **Heutige Sitzungen bearbeiten** - Doppelte Scans entfernen oder Fehler korrigieren

**Hinweis:** Die Aktionsschaltflächen bleiben jederzeit sichtbar. Wenn Sie sie nach der anfänglichen Gnadenfrist (2 Minuten) anklicken, müssen Sie Ihren Badge erneut scannen zur Identifikation.

### Bearbeitung Ihrer Zeiteinträge

Sie können Ihre Zeiteinträge der letzten 7 Tage bearbeiten:

1. **Innerhalb von 2 Minuten nach dem Stempeln:** Klicken Sie auf **Heutige Sitzungen bearbeiten** (kein Badge-Scan erforderlich)
2. **Nach 2 Minuten:** Klicken Sie auf **Heutige Sitzungen bearbeiten** und scannen Sie den Badge, wenn dazu aufgefordert
3. Wählen Sie das Datum aus, das Sie bearbeiten möchten (nur letzte 7 Tage)
4. Zeigen Sie alle Einträge für diesen Tag an
5. Wählen Sie Einträge zum Löschen aus (entfernt doppelte Scans)
6. Oder fügen Sie manuelle Einträge hinzu, wenn Sie vergessen haben, ein- oder auszustempeln

**Wichtig:** Gelöschte Einträge werden nicht dauerhaft entfernt—sie werden für Audit-Zwecke als inaktiv markiert.

### Manueller Eintrag

Wenn Sie vergessen haben, ein- oder auszustempeln:

1. Greifen Sie auf den Eintrags-Editor zu (siehe oben)
2. Klicken Sie auf **Eintrag hinzufügen**
3. Wählen Sie das Datum aus (nur letzte 7 Tage)
4. Stellen Sie die Zeit ein
5. Speichern

**Hinweis:** Das System bestimmt automatisch, ob der Eintrag EIN oder AUS sein soll, basierend auf Ihren bestehenden Einträgen für diesen Tag.

### Entfernen doppelter Scans

**Problem:** Sie haben versehentlich den Badge zweimal gescannt, wodurch doppelte Einträge entstanden sind.

**Lösung:**
1. Klicken Sie auf **Heutige Sitzungen bearbeiten** (innerhalb von 2 Minuten nach dem Stempeln, kein Badge-Scan erforderlich)
2. Oder scannen Sie Badge → **Heutige Sitzungen bearbeiten** (wenn mehr als 2 Minuten vergangen sind)
3. Wählen Sie das Datum aus
4. Aktivieren Sie die doppelten Einträge
5. Klicken Sie auf **Ausgewählte löschen**
6. Bestätigen Sie die Löschung

### Korrektur vergessener Ausstempelung

**Problem:** Sie haben gestern vergessen auszustempeln.

**Lösung:**
1. Scannen Sie Badge → **Heutige Sitzungen bearbeiten**
2. Wählen Sie das gestrige Datum aus
3. Klicken Sie auf **Eintrag hinzufügen**
4. Stellen Sie die Zeit ein (z.B. Ende des Arbeitstages)
5. Speichern

Das System wird dies automatisch mit dem vorhandenen Einstempel-Eintrag paaren.

### Tipps für Mitarbeiter

- **Einmal scannen:** Das System verhindert schnelle Scans, aber es ist am besten, einmal zu scannen und auf die Bestätigung zu warten
- **Status überprüfen:** Nach dem Scannen überprüfen Sie, dass die Begrüßungsnachricht die richtige Aktion zeigt (EIN/AUS)
- **Aktionsschaltflächen nutzen:** Wenn Sie nach dem Stempeln einen Fehler bemerken, verwenden Sie die Aktionsschaltflächen, um Ihre Sitzungen schnell zu bearbeiten
- **Regelmäßige Überprüfungen:** Überprüfen Sie regelmäßig Ihre Zeiteinträge, um Probleme frühzeitig zu erkennen

---

## Für Administratoren

### Zugriff auf Admin-Panel

Scannen Sie Ihren Administrator-Badge jederzeit, um auf das Admin-Panel zuzugreifen. Der Bildschirm wechselt automatisch in den Admin-Modus.

### Registrierung neuer Mitarbeiter

1. Navigieren Sie zu **Admin → Benutzer erfassen**
2. Geben Sie den vollständigen Namen des Mitarbeiters ein
3. Scannen Sie ihren RFID-Badge (oder geben Sie die Tag-ID manuell ein)
4. Lassen Sie das Admin-Kontrollkästchen **deaktiviert** (es sei denn, Sie erstellen einen weiteren Admin)
5. Klicken Sie auf **Speichern**

**Hinweis:** Jeder Badge kann nur einem Mitarbeiter zugewiesen werden. Wenn Sie versuchen, einen bereits verwendeten Badge zu registrieren, sehen Sie eine Fehlermeldung.

### Identifizierung von Badges

Um zu überprüfen, welchem Mitarbeiter ein Badge gehört:

1. Navigieren Sie zu **Admin → Tag identifizieren**
2. Scannen Sie den Badge
3. Zeigen Sie die angezeigten Informationen an:
   - Mitarbeitername
   - Tag-ID
   - Rolle (Administrator oder Mitarbeiter)
   - Registrierungsstatus

### Generierung von Arbeitszeitberichten

1. Navigieren Sie zu **Admin → WT Reports**
2. Wählen Sie einen Mitarbeiter aus der Dropdown-Liste
3. (Optional) Legen Sie einen Datumsbereich fest:
   - Klicken Sie auf **Daten auswählen**
   - Wählen Sie Start- und Enddatum
   - Klicken Sie auf **Bestätigen**
4. Klicken Sie auf **Bericht erstellen**
5. Überprüfen Sie den Bericht, der zeigt:
   - Tägliche Aufschlüsselung der Sitzungen
   - Ein- und Ausstempelzeiten
   - Dauer pro Sitzung
   - Tägliche Summen
   - Periodenzusammenfassung (Gesamtstunden, Durchschnitt pro Tag)
6. Export-Optionen:
   - **Als Excel exportieren** - Strukturierte Tabelle mit Stunden pro Tag pro Monat
   - **Als CSV exportieren** - Semikolon-getrenntes Format für Lohnsysteme
   - **Als PDF exportieren** - Formatierter Bericht zum Drucken

**Berichtsfunktionen:**
- Paart automatisch Ein- und Ausstempelereignisse
- Berechnet die geleisteten Gesamtstunden aus tatsächlichen Stempel-Einträgen
- Zeigt tägliche Durchschnitte
- Markiert offene Sitzungen (wenn Mitarbeiter vergessen hat auszustempeln)
- Export-Formate zeigen Stunden pro Tag, organisiert nach Monaten

**Export-Format:**
Die exportierten Dateien zeigen Arbeitsstunden pro Tag in einem einfachen, klaren Format:
- Mitarbeitername und Datumsbereich oben
- Jeder Monat separat aufgelistet
- Tagesnummern (1-31) oben
- Geleistete Stunden pro Tag im H:MM-Format darunter
- Monatssummen in der rechten Spalte

### Datenexport

**Rohe Zeiteinträge exportieren (CSV):**
1. Navigieren Sie zu **Admin → CSV Export**
2. Klicken Sie auf **Zeiteinträge exportieren**
3. Die Datei wird auf USB-Laufwerk gespeichert (falls angeschlossen) oder im Verzeichnis `exports/`
4. Ein Bestätigungs-Popup zeigt den Dateipfad
5. Enthält rohe Ein-/Ausstempel-Einträge mit Zeitstempeln

**Arbeitsstunden-Berichte exportieren:**
1. Navigieren Sie zu **Admin → WT Reports**
2. Wählen Sie Mitarbeiter und Datumsbereich
3. Erstellen Sie Bericht
4. Wählen Sie Export-Format:
   - **Excel** - Für Tabellenkalkulationsanwendungen (`.xlsx`)
   - **CSV** - Für Import in Lohnsysteme (`.csv`, Semikolon-getrennt)
   - **PDF** - Zum Drucken und Dokumentation (`.pdf`)
5. Dateien werden gespeichert im Format: `Arbeitszeit_[Mitarbeitername]_[Startdatum]_[Enddatum].[ext]`

**Datenbank-Backup exportieren:**
1. Navigieren Sie zu **Admin → DB Export**
2. Klicken Sie auf **Datenbank exportieren**
3. Ein vollständiges SQLite-Datenbank-Backup wird erstellt
4. Nützlich für Backups oder Migration zu einem anderen System

**Export-Speicherorte:**
- USB-Laufwerke werden automatisch erkannt (`/media`, `/run/media`, `/mnt`)
- Wenn keine USB gefunden wird, werden Dateien im Verzeichnis `exports/` gespeichert
- Sie können mit Umgebungsvariable überschreiben: `export TIME_CLOCK_EXPORT_PATH=/benutzerdefinierter/pfad`

### Tipps für Administratoren

- **Regelmäßige Backups:** Exportieren Sie die Datenbank regelmäßig für Backup-Zwecke
- **Berichtsüberwachung:** Generieren Sie wöchentliche Berichte, um Muster oder Probleme zu erkennen
- **Badge-Verwaltung:** Behalten Sie den Überblick darüber, welche Badges welchen Mitarbeitern zugewiesen sind
- **Hardware-Test:** Testen Sie regelmäßig die RFID-Leser-Funktionalität mit der Funktion Tag identifizieren

---

## Fehlerbehebung

### Badge wird nicht erkannt

**Symptome:** Rotes LED-Blinken, "Unbekannter Tag"-Nachricht

**Lösungen:**
- Stellen Sie sicher, dass der Badge nahe am Leser gehalten wird (innerhalb von 2-3 cm)
- Versuchen Sie erneut zu scannen (warten Sie 1-2 Sekunden zwischen den Scans)
- Überprüfen Sie, ob der Badge registriert ist: Admin → Tag identifizieren
- Kontaktieren Sie den Administrator, um den Badge zu registrieren

### Kein Zugriff auf Admin-Funktionen

**Symptome:** Admin-Badge wechselt nicht zum Admin-Bildschirm

**Lösungen:**
- Überprüfen Sie, ob der Badge als Administrator registriert ist
- Überprüfen Sie die Badge-Zuweisung: Admin → Tag identifizieren
- Stellen Sie sicher, dass Sie den richtigen Badge scannen
- Versuchen Sie, die Anwendung neu zu starten

### Export funktioniert nicht

**Symptome:** Export-Schaltfläche erstellt keine Datei oder Datei nicht gefunden

**Lösungen:**
- Überprüfen Sie, ob das USB-Laufwerk ordnungsgemäß eingebunden ist
- Überprüfen Sie, ob das USB Schreibrechte hat
- Überprüfen Sie, ob das Verzeichnis `exports/` existiert und beschreibbar ist
- Überprüfen Sie die Anwendungsprotokolle auf Fehlermeldungen
- Versuchen Sie, einen benutzerdefinierten Export-Pfad festzulegen: `export TIME_CLOCK_EXPORT_PATH=/tmp`

### Bildschirm wird leer (Bildschirmschoner)

**Symptome:** Bildschirm zeigt Matrix-ähnliche Animation nach Inaktivität

**Lösungen:**
- Dies ist normales Verhalten (aktiviert sich nach 60 Sekunden Inaktivität)
- Berühren Sie den Bildschirm oder scannen Sie einen Badge, um ihn zu wecken
- Der Bildschirm kehrt zum vorherigen Bildschirm zurück

### Schaltflächen reagieren nicht

**Symptome:** Schaltfläche erscheint gedrückt, löst aber keine Aktion aus

**Lösungen:**
- Stellen Sie sicher, dass Sie den Tipp vollständig ausführen (drücken und loslassen)
- Warten Sie einen Moment zwischen den Tipps (schnelle Doppeltipps werden unterdrückt)
- Bei Touchscreen: Stellen Sie sicher, dass der Finger vollständig abhebt, bevor Sie erneut tippen

---

*Zuletzt aktualisiert: Jan 2026*
