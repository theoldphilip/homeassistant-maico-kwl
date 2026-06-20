# Maico WS 300 Flat – Home Assistant Integration

Eine benutzerdefinierte [Home Assistant](https://www.home-assistant.io/) Integration zur Steuerung und Überwachung einer **Maico WS 300 Flat** Lüftungsanlage (KWL) über Modbus TCP.

Einrichtung komplett über die Oberfläche (Config Flow) – es ist **keine** YAML-Konfiguration nötig.

## Funktionen

- **Lüftungssteuerung** über eine Fan-Entität
  - Schieberegler = Lüftungsstufe (Reduziert / Nennlüftung / Intensiv)
  - Voreinstellungen (Dropdown) = Betriebsart (Aus / Manuell / Auto Zeit / Auto Sensor / Eco-Zuluft / Eco-Abluft)
  - Beim Ändern der Stufe wird die Betriebsart automatisch auf „Manuell" gesetzt
- **Sensoren** für Temperaturen, Drehzahlen, Volumenströme, Luftfeuchte, CO₂, Betriebszustände
- **Wärmerückgewinnung** wird live aus den Temperaturen berechnet
- **Filterwechsel-Warnung** mit einstellbarer Schwelle (Tage)
- **Sommermodus** mit automatischer Nachtkühlung (optional, per Schalter)
- Lokale Anbindung (local polling), keine Cloud

## Installation

### Über HACS (empfohlen)

1. HACS öffnen → **Integrationen**
2. Oben rechts auf die drei Punkte → **Benutzerdefinierte Repositories**
3. Repository hinzufügen: `https://github.com/theoldphilip/homeassistant-maico-kwl`
4. Kategorie: **Integration** → **Hinzufügen**
5. Anschließend „Maico WS 300 Flat" suchen und installieren
6. Home Assistant neu starten

### Manuell

1. Den Ordner `custom_components/maico_kwl` in das `custom_components`-Verzeichnis der Home-Assistant-Konfiguration kopieren
2. Home Assistant neu starten

## Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen**
2. Nach „Maico WS 300 Flat" suchen
3. Eingeben:
   - **IP-Adresse** der Lüftungsanlage
   - **Filterwechsel-Warnung (Tage)** – Standard: 7

Port (502), Unit-ID (1) und Abfrageintervall (30 s) sind voreingestellt.

## Entitäten

### Steuerung

| Entität | Typ | Beschreibung |
|---|---|---|
| `fan.maico_kwl_lueftung` | Fan | Lüftungsstufe (Prozent) + Betriebsart (Voreinstellung) |
| `switch.maico_kwl_sommermodus` | Switch | Automatische Nachtkühlung an/aus |
| `number.maico_kwl_cool_min_diff` | Number | Kühlung: Mindest-Temperaturdifferenz (°C) |
| `number.maico_kwl_cool_target` | Number | Kühlung: Zieltemperatur (°C) |

### Sensoren

| Entität (unique_id) | Beschreibung |
|---|---|
| `maico_kwl_temp_aussenluft` | Temperatur Frischluft (von draußen) |
| `maico_kwl_temp_zuluft` | Temperatur Zuluft (in die Räume) |
| `maico_kwl_temp_abluft` | Temperatur Raumluft (aus den Räumen) |
| `maico_kwl_temp_fortluft` | Temperatur Abluft (nach draußen) |
| `maico_kwl_drehzahl_zuluft` | Drehzahl Zuluft |
| `maico_kwl_drehzahl_abluft` | Drehzahl Raumluft |
| `maico_kwl_volumenstrom_zuluft` | Volumenstrom Zuluft |
| `maico_kwl_volumenstrom_abluft` | Volumenstrom Raumluft |
| `maico_kwl_humidity_abluft` | Luftfeuchte Raumluft |
| `maico_kwl_co2_abluft` | CO₂ Raumluft |
| `maico_kwl_betriebsart` | Betriebsart (Text) |
| `maico_kwl_lueftungsstufe` | Lüftungsstufe (Text) |
| `maico_kwl_schalter_zuluft` | Schalter Zuluftventilator |
| `maico_kwl_schalter_abluft` | Schalter Abluftventilator |
| `maico_kwl_schalter_bypass` | Bypass-Status |
| `maico_kwl_filter_restlaufzeit_zuluft` | Filterwechsel (Restlaufzeit in Tagen) |
| `maico_kwl_wrg_efficiency` | Wärmerückgewinnung (%) |

### Filterwarnung

| Entität | Beschreibung |
|---|---|
| `binary_sensor.maico_kwl_filter_restlaufzeit_zuluft_alert` | Wird aktiv, wenn die Filter-Restlaufzeit die Schwelle unterschreitet |

## Sommermodus (Nachtkühlung)

Ist der Schalter `switch.maico_kwl_sommermodus` aktiv, regelt die Integration die Anlage temperaturabhängig:

- **Nachtkühlung:** Ist die Außenluft mindestens *Mindest-Differenz* °C kühler als die Raumluft **und** liegt die Raumluft über der *Zieltemperatur*, schaltet die Anlage auf Manuell + Intensiv. Der Bypass wird vom Gerät selbst geöffnet.
- **Tagsüber bei Hitze:** Ist die Außenluft wärmer als die Raumluft, wird die Anlage abgeschaltet, um keine warme Luft einzubringen.
- **Zieltemperatur erreicht:** Die Anlage wird abgeschaltet, damit die Räume nicht auskühlen.

Schwellen über `number.maico_kwl_cool_min_diff` (Standard 2 °C) und `number.maico_kwl_cool_target` (Standard 22 °C) einstellbar. Ist der Schalter aus, greift keinerlei Automatik – die Anlage lässt sich vollständig manuell bedienen.

## Modbus-Register

Die Integration verwendet folgende Holding-Register (Unit-ID 1):

| Funktion | Lesen | Schreiben |
|---|---|---|
| Betriebsart | 550 | 550 |
| Lüftungsstufe | 650 | 554 |
| Drehzahl Zu-/Abluft | 651 / 652 | – |
| Volumenstrom Zu-/Abluft | 653 / 654 | – |
| Filter-Restlaufzeit | 655 | – |
| Temperaturen (Frisch/Zu/Raum/Ab) | 703–706 | – |
| Luftfeuchte Raumluft | 750 | – |
| CO₂ Raumluft | 755 | – |
| Schalter Zu-/Abluft/Bypass | 800–802 | – |

Temperaturen werden als `int16` mit Faktor 0,1 gelesen.

> **Hinweis:** Die Lüftungsstufe wird aus Register 650 gelesen, aber nach Register 554 geschrieben (Werte 1–4). Ein Schreiben auf 650 lehnt das Gerät ab.

## Voraussetzungen

- Home Assistant 2024.1.0 oder neuer
- Maico WS 300 Flat mit aktiviertem Modbus TCP, erreichbar im Netzwerk

## Haftungsausschluss

Dieses Projekt ist ein privates, inoffizielles Hobbyprojekt und steht in keiner Verbindung zur Maico Elektroapparate-Fabrik GmbH. Nutzung auf eigene Verantwortung. Die Register-Zuordnung wurde für eine konkrete WS 300 Flat ermittelt und kann je nach Firmware/Modell abweichen.

## Lizenz

MIT – siehe [LICENSE](LICENSE).
