# TimeClock Benutzerhandbuch

> Vollständige Anleitung für Endbenutzer und Administratoren

---

## Inhaltsverzeichnis

1. [Erste Schritte](#erste-schritte)
2. [Für Mitarbeiter](#für-mitarbeiter)
3. [Für Administratoren](#für-administratoren)
4. [Häufige Aufgaben](#häufige-aufgaben)
5. [Fehlerbehebung](#fehlerbehebung)

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
4. Eine freundliche Begrüßungsnachricht wird angezeigt
5. Ihr Status wird auf dem Bildschirm aktualisiert

**Was passiert:**
- Das System bestimmt automatisch, ob Sie **EIN** oder **AUS** stempeln, basierend auf Ihrer letzten Aktion
- Wenn Ihre letzte Aktion AUS war (oder Sie heute noch nicht eingestempelt haben), stempeln Sie **EIN**
- Wenn Ihre letzte Aktion EIN war, stempeln Sie **AUS**

### Anzeige der Tageszusammenfassung

Nach jeder Stempelaktion sehen Sie:
- Eine kurze Zusammenfassung mit den heute geleisteten Gesamtstunden
- Zwei Aktionsschaltflächen (für 5 Sekunden sichtbar):
  - **Heutigen Report anzeigen** - Detaillierte Aufschlüsselung der heutigen Sitzungen
  - **Heutige Sitzungen bearbeiten** - Doppelte Scans entfernen oder Fehler korrigieren

**Nach 5 Sekunden:**
- Die Aktionsschaltflächen verschwinden
- Um später auf diese Funktionen zuzugreifen, müssen Sie Ihren Badge erneut scannen zur Identifikation

### Bearbeitung Ihrer Zeiteinträge

Sie können Ihre Zeiteinträge der letzten 7 Tage bearbeiten:

1. **Innerhalb von 5 Sekunden nach dem Stempeln:** Klicken Sie auf **Heutige Sitzungen bearbeiten**
2. **Nach 5 Sekunden:** Scannen Sie den Badge, wenn dazu aufgefordert
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
4. Wählen Sie **Ein** oder **Aus**
5. Stellen Sie die Zeit ein
6. Speichern

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
6. (Optional) Klicken Sie auf **Als CSV exportieren**, um für die Lohnabrechnung zu speichern

**Berichtsfunktionen:**
- Paart automatisch Ein- und Ausstempelereignisse
- Berechnet die geleisteten Gesamtstunden
- Zeigt tägliche Durchschnitte
- Markiert offene Sitzungen (wenn Mitarbeiter vergessen hat auszustempeln)

### Datenexport

**Rohe Zeiteinträge exportieren:**
1. Navigieren Sie zu **Admin → CSV Export**
2. Klicken Sie auf **Zeiteinträge exportieren**
3. Die Datei wird auf USB-Laufwerk gespeichert (falls angeschlossen) oder im Verzeichnis `exports/`
4. Ein Bestätigungs-Popup zeigt den Dateipfad

**Datenbank-Backup exportieren:**
1. Navigieren Sie zu **Admin → DB Export**
2. Klicken Sie auf **Datenbank exportieren**
3. Ein vollständiges SQLite-Datenbank-Backup wird erstellt
4. Nützlich für Backups oder Migration zu einem anderen System

**Export-Speicherorte:**
- USB-Laufwerke werden automatisch erkannt (`/media`, `/run/media`, `/mnt`)
- Wenn keine USB gefunden wird, werden Dateien im Verzeichnis `exports/` gespeichert
- Sie können mit Umgebungsvariable überschreiben: `export TIME_CLOCK_EXPORT_PATH=/benutzerdefinierter/pfad`

---

## Häufige Aufgaben

### Entfernen doppelter Scans

**Problem:** Mitarbeiter hat versehentlich den Badge zweimal gescannt, wodurch doppelte Einträge entstanden sind.

**Lösung:**
1. Innerhalb von 5 Sekunden nach dem Stempeln: Klicken Sie auf **Heutige Sitzungen bearbeiten**
2. Oder scannen Sie Badge → **Heutige Sitzungen bearbeiten**
3. Wählen Sie das Datum aus
4. Aktivieren Sie die doppelten Einträge
5. Klicken Sie auf **Ausgewählte löschen**
6. Bestätigen Sie die Löschung

Die doppelten Einträge werden aus den Berichten entfernt, aber in der Datenbank für Audit-Zwecke aufbewahrt.

### Korrektur vergessener Ausstempelung

**Problem:** Mitarbeiter hat gestern vergessen auszustempeln.

**Lösung:**
1. Scannen Sie Badge → **Heutige Sitzungen bearbeiten**
2. Wählen Sie das gestrige Datum aus
3. Klicken Sie auf **Eintrag hinzufügen**
4. Wählen Sie **Aus**
5. Stellen Sie die Zeit ein (z.B. Ende des Arbeitstages)
6. Speichern

Das System wird dies automatisch mit dem vorhandenen Einstempel-Eintrag paaren.

### Anzeige der Mitarbeiterstunden

**Für Mitarbeiter:**
- Zeigen Sie die heutige Zusammenfassung sofort nach dem Stempeln an
- Oder scannen Sie Badge → **Heutigen Report anzeigen**

**Für Administratoren:**
- Navigieren Sie zu **Admin → WT Reports**
- Wählen Sie Mitarbeiter und Datumsbereich
- Erstellen Sie Bericht

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

### Doppelte Zeicheneingabe

**Symptome:** Beim Tippen erscheint jedes Zeichen zweimal

**Lösungen:**
- Dies wird automatisch von der Anwendung behandelt
- Wenn es weiterhin auftritt, versuchen Sie langsamer zu tippen
- Das System filtert automatisch doppelte Tastenanschläge

---

## Tipps & Best Practices

### Für Mitarbeiter

- **Einmal scannen:** Das System verhindert schnelle Scans, aber es ist am besten, einmal zu scannen und auf die Bestätigung zu warten
- **Status überprüfen:** Nach dem Scannen überprüfen Sie, dass die Begrüßungsnachricht die richtige Aktion zeigt (EIN/AUS)
- **5-Sekunden-Fenster nutzen:** Wenn Sie sofort nach dem Stempeln einen Fehler bemerken, verwenden Sie die Schnellaktions-Schaltflächen
- **Regelmäßige Überprüfungen:** Überprüfen Sie regelmäßig Ihre Zeiteinträge, um Probleme frühzeitig zu erkennen

### Für Administratoren

- **Regelmäßige Backups:** Exportieren Sie die Datenbank regelmäßig für Backup-Zwecke
- **Berichtsüberwachung:** Generieren Sie wöchentliche Berichte, um Muster oder Probleme zu erkennen
- **Badge-Verwaltung:** Behalten Sie den Überblick darüber, welche Badges welchen Mitarbeitern zugewiesen sind
- **Hardware-Test:** Testen Sie regelmäßig die RFID-Leser-Funktionalität mit der Funktion Tag identifizieren

---

## Support

Bei technischen Problemen oder Fragen:
- Überprüfen Sie den Fehlerbehebungsabschnitt oben
- Überprüfen Sie die Anwendungsprotokolle
- Kontaktieren Sie Ihren Systemadministrator

---

*Zuletzt aktualisiert: Dez 2025*

