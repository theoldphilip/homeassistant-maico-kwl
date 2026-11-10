# Changelog

Alle nennenswerten Änderungen an dieser Integration. Format angelehnt an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
Bestehende Installationen werden bei jedem Update automatisch migriert – Entitäten und Entity-IDs bleiben stabil.

## [1.8.0] – 2026-11-11

### Neu
- **Karte automatisch bereitstellen:** Die Integration liefert die Lovelace-Karte selbst aus und lädt sie ins Dashboard. Kopieren nach `www` und manuelle Ressource entfallen. Aktiv bei neuen Installationen; bestehende Installationen schalten die Option unter „Konfigurieren“ ein. Eine bereits manuell eingebundene Karte wird nicht angetastet.
- **Options-Dialog:** IP-Adresse, Abfrageintervall, Filterschwelle und Kartenoption lassen sich nachträglich ändern (mit Verbindungstest bei neuer IP, Schutz vor doppelter IP). Die Integration lädt sich danach automatisch neu.
- **Diagnose-Download** (Gerät → Diagnose herunterladen): Version, Modell, erkannte Register, Rohwerte, Sommermodus-Zustand. Die IP-Adresse wird geschwärzt.
- **Englische Übersetzung** der Einrichtung und des Options-Dialogs.

### Geändert
- Die Kartendatei liegt jetzt in `custom_components/maico_kwl/www/` (früher `lovelace/`). Bestehende manuelle Installationen unter `/local/maico-kwl-card.js` laufen unverändert weiter.
- Karte v1.3.1: eine doppelte Registrierung (manuell und automatisch) wird abgefangen.
- Abhängigkeiten: `http` und `frontend`. Mindestversion Home Assistant **2024.12.0** (für den Options-Dialog).

## [1.7.9] – 2026-11-10

### Neu
- **Filterwechsel quittieren (R157/158/159):** drei Buttons „Filter gewechselt“ für Gerätefilter, Außenluft- und Raumluftfilter (Kategorie Diagnose). Sie entstehen nur für Register, die das Gerät beantwortet (automatische Feature-Erkennung). Je Filter ein eigener Button, damit nur quittiert wird, was wirklich getauscht wurde.
- Beim Start steht im Log (Info-Ebene), welche optionalen Register erkannt wurden.

### Geändert
- **Fehler- und Hinweis-Sensor** sind jetzt der Kategorie „Diagnose“ zugeordnet und erscheinen nicht mehr unter den normalen Sensoren.

### Dokumentation
- README: Hinweis, dass die genannten Entity-IDs Beispiele sind und die tatsächliche ID vom Gerätenamen abhängt; Filterwechsel-Buttons dokumentiert.

## [1.7.8] – 2026-11-10

### Behoben
- **Button „Fehler quittieren“ (R405) wird wieder angelegt.** Mit aktuellen Home-Assistant-Versionen wurde er nicht erstellt (`entity_category must be a valid EntityCategory instance, got diagnostic`). Er erscheint jetzt korrekt in der Kategorie „Diagnose“.

## [1.7.7] – 2026-08-09

### Neu
- **Raumtemperaturauswahl (R109)** als Select-Entity `select.maico_kwl_raumtempauswahl` (Komfort-BDE / Extern R701 / Intern / Bus R707). Bestimmt, welchen Wert das Gerät gegen T-Raum max. (R302) für die Bypass-Kühlung vergleicht.
- **T-Raum Bus (R707)** als Number-Entity `number.maico_kwl_t_raum_bus` (−30–120 °C, Schritt 0,5 °C) für extern berechnete Raumtemperaturen. Nur wirksam bei Auswahl „Bus (R707)“.
- Mindest-Schreibzyklus von 10 Minuten für R707 wird erzwungen (Fehlermeldung mit Restzeit). Der Wert wird lokal gemerkt und nach einem Neustart wiederhergestellt, da R707 write-only ist.

### Intern
- Neue Plattform `select` (insgesamt 7 Plattformen).

## [1.7.6] – 2026-08-09

### Neu
- **Volumenstrom-Sollwerte je Stufe (R154/155/156):** `number.maico_kwl_volumenstrom_reduziert`, `…_nennlueftung`, `…_intensiv` (80–300 m³/h, Schritt 5).
- **Fehler quittieren (R405):** Button `button.maico_kwl_fehler_reset` (Kategorie Diagnose).
- **Filterüberwachung Δp (R900):** `number.maico_kwl_filter_delta_p` (10–200 %, Schritt 5).

## [1.7.4] – 2026-08-01

### Neu
- **Sensor „Temperatur Raum Ext.“ (R701)**, optional mit automatischer Feature-Erkennung, standardmäßig deaktiviert.

### Hinweis
- R707 ist write-only und daher kein Sensor (siehe 1.7.7).

## [1.7.3] – 2026-06-29

### Neu
- **Lovelace Custom Card** (`maico-kwl-card.js`): animierte Luftstrom-Pfeile, farbcodierte Temperaturen, WRG-Wirkungsgrad, Lüftungsstufe, Bypass-Status, Luftfeuchte, Dark/Light-Mode, konfigurierbare Raumübersicht und vollständiger GUI-Editor.

### Behoben
- Sommermodus: Pendeln bei Grenztemperaturen und irreführende Status-Anzeige (siehe 1.7.2).

## [1.7.2] – 2026-06-28

### Behoben
- **Pendeln im Sommermodus:** Die Weiterkühlen-Bedingung nutzt jetzt eine um die Hysterese relaxierte Differenz-Schwelle.
- **Status-Anzeige während der Mindest-Laufzeit** zeigt den tatsächlichen Gerätezustand („Kühlt – wartet X min“).

## [1.7.1] – 2026-06-25

### Behoben
- Setup-Fehler `_evaluate_summer_mode` aus 1.7.0 (Einrückungsfehler, Integration startete nicht).

## [1.7.0] – 2026-06-25 (Pre-Release)

### Neu
- **PushPull-Unterstützung (PP 45 / PPB 30)** über LAN-Gateway (Modbus TCP ↔ RTU): Betriebsart, Lüftungsstufe, Luftfeuchte, Filterwechsel, Betriebsstunden. Noch nicht an echter Hardware verifiziert.
- **Optionale Sensoren mit automatischer Erkennung:** CO₂ 2–4, VOC 1–2, externe Luftfeuchte 1–4 (vorhanden, aber standardmäßig deaktiviert).

### Verbessert
- Skalierung der Temperatur-Sollwerte kommt aus einer einzigen Quelle (Geräteprofil).

## [1.6.0] – 2026-06-25

### Neu
- **Multi-Modell-Unterstützung:** Modellauswahl bei der Einrichtung (Trio, WR, WS, WS 75 Powerbox, PushPull).
- **Automatische Feature-Erkennung** optionaler Sensoren.
- **Profil-Architektur** für Register, Skalierungen und Features.

### Migration
- Bestehende Installationen werden automatisch migriert, Entity-IDs bleiben unverändert.

## [1.5.0] – 2026-06-24

### Neu
- **Anti-Pendeln für den Sommermodus:** Hysterese (`number.maico_kwl_cool_hysteresis`, Standard 0,5 °C) und Mindest-Laufzeit (`number.maico_kwl_min_runtime`, 5–15 min, Standard 10).

## [1.4.3] – 2026-06-23

### Behoben
- Skalierung von „T-Zuluft min. (Kühlen)“ (R301): wird direkt gespeichert, nicht ×10.

## [1.4.2] – 2026-06-23

### Neu
- Betriebsstunden je Stufe, Fehler-/Hinweis-Diagnose, Temperatur Raum, Stoßlüftung per Button mit einstellbarer Dauer, T-Raum max. und T-Zuluft min. als Sollwerte.
- Der Sommermodus pausiert während einer laufenden Stoßlüftung.

## [1.3.0] – 2026-06-22

### Neu
- **Stromverbrauch-Schätzung:** `maico_kwl_leistung` (W) und `maico_kwl_energie` (kWh, Energie-Dashboard) aus Volumenstrom × SPI-Wert.

## [1.2.0] – 2026-06-22

### Neu
- Maico-Logo und Icon (brand-Ordner).

## [1.1.0] – 2026-06-21

### Geändert
- Zustand „Bereit“ nutzt Schutzlüftung statt die letzte Kühlstufe stehen zu lassen.

### Neu
- Status-Sensor für den Sommermodus.

## [1.0.0] – 2026-06-20

- Erste Version: Steuerung (Lüftungsstufe + Betriebsart), Sensoren, Filterwarnung, Wärmerückgewinnung und Sommermodus mit Nachtkühlung.

[1.8.0]: https://github.com/theoldphilip/homeassistant-maico-kwl/compare/v1.7.9...v1.8.0
[1.7.9]: https://github.com/theoldphilip/homeassistant-maico-kwl/compare/v1.7.8...v1.7.9
[1.7.8]: https://github.com/theoldphilip/homeassistant-maico-kwl/compare/v1.7.7...v1.7.8
[1.7.7]: https://github.com/theoldphilip/homeassistant-maico-kwl/compare/v.1.7.6...v1.7.7
