# Maico KWL – Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5?style=flat-square)](https://github.com/hacs/integration) [![PayPal](https://img.shields.io/badge/PayPal-Spenden-00457C?logo=paypal&logoColor=white&style=flat-square)](https://www.paypal.com/donate/?hosted_button_id=SLNW2MCC268SG)

Eine benutzerdefinierte [Home Assistant](https://www.home-assistant.io/) Integration zur Steuerung und Überwachung von **Maico Lüftungsanlagen** (KWL) über Modbus TCP.

Einrichtung komplett über die Oberfläche (Config Flow) – es ist **keine** YAML-Konfiguration nötig. Bei der Einrichtung wird das Modell ausgewählt; vorhandene optionale Sensoren werden automatisch erkannt.

## Unterstützte Geräte

**KWL-Zentral (Trio / WR / WS)** – gemeinsame Modbus-Plattform:
Trio zentral, Trio dezentral, WS 120 Trio, WS 160 Flat, WS 170, WS 300 Flat / RB 300 Flat, WS 320, WS 470, WR 310, WR 410 sowie die WS 75 Powerbox.

**PushPull** – PP 45 / PPB 30 (über LAN-Gateway, das Modbus TCP ↔ RTU wandelt).

> **Verifiziert** wurde die Integration an einer **WS 300 Flat** (Firmware ≥ 1.3.0). Die übrigen Modelle teilen sich dieselbe Steuerungsplattform; einzelne Firmware-/Modellabweichungen (z. B. bei der Skalierung) können auftreten. Im Zweifel die Werte mit der Maico-App vergleichen und ggf. ein [Issue](https://github.com/theoldphilip/homeassistant-maico-kwl/issues) melden.

## Funktionen

- **Lüftungssteuerung** über eine Fan-Entität
  - Schieberegler = Lüftungsstufe (Reduziert / Nennlüftung / Intensiv)
  - Voreinstellungen (Dropdown) = Betriebsart (Aus / Manuell / Auto Zeit / Auto Sensor / Eco-Zuluft / Eco-Abluft)
  - Beim Ändern der Stufe wird die Betriebsart automatisch auf „Manuell" gesetzt
- **Sensoren** für Temperaturen, Drehzahlen, Volumenströme, Luftfeuchte, CO₂, Betriebszustände
- **Automatische Feature-Erkennung** – optionale Sensoren (CO₂, externe Feuchte/VOC, Heizregister, Sole) werden nur angelegt, wenn das Gerät sie hat
- **Wärmerückgewinnung** wird live aus den Temperaturen berechnet
- **Stromverbrauch** wird aus dem Volumenstrom geschätzt (Watt + kWh fürs Energie-Dashboard)
- **Betriebsstunden** je Lüftungsstufe sowie Fehler-/Hinweis-Diagnose
- **Stoßlüftung** per Knopfdruck (zeitbegrenzte Intensivlüftung)
- **Filterwechsel-Warnung** mit einstellbarer Schwelle (Tage)
- **Sommermodus** mit automatischer Nachtkühlung (optional, per Schalter)
- Lokale Anbindung (local polling), keine Cloud

## Installation

### Über HACS (empfohlen)

1. HACS öffnen → **Integrationen**
2. Oben rechts auf die drei Punkte → **Benutzerdefinierte Repositories**
3. Repository hinzufügen: `https://github.com/theoldphilip/homeassistant-maico-kwl`
4. Kategorie: **Integration** → **Hinzufügen**
5. Anschließend „Maico KWL" suchen und installieren
6. Home Assistant neu starten

### Manuell

1. Den Ordner `custom_components/maico_kwl` in das `custom_components`-Verzeichnis der Home-Assistant-Konfiguration kopieren
2. Home Assistant neu starten

## Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen**
2. Nach „Maico KWL" suchen
3. Eingeben:
   - **Modell** – das angeschlossene Maico-Gerät aus der Liste
   - **IP-Adresse** der Lüftungsanlage (bei PushPull: IP des LAN-Gateways)
   - **Filterwechsel-Warnung (Tage)** – Standard: 7

Port (502), Unit-ID (1) und Abfrageintervall (30 s) sind voreingestellt.

> **Update von einer älteren Version (Einzelgerät):** Bestehende Installationen werden automatisch migriert und behalten **alle Entitäten, Entity-IDs, Dashboards und Automationen** unverändert. Es ist keine Neueinrichtung nötig.

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
| `maico_kwl_sommermodus_status` | Status des Sommermodus (Text) |
| `maico_kwl_leistung` | Geschätzte Leistungsaufnahme (W) |
| `maico_kwl_energie` | Geschätzter Energieverbrauch (kWh, für Energie-Dashboard) |

> **Hinweis:** Leistung und Energie sind **Schätzwerte** (keine geeichte Messung). Wie sie berechnet werden, ist im Abschnitt [Stromverbrauch (Schätzung)](#stromverbrauch-schätzung) erklärt.

### Filterwarnung

| Entität | Beschreibung |
|---|---|
| `binary_sensor.maico_kwl_filter_restlaufzeit_zuluft_alert` | Wird aktiv, wenn die Filter-Restlaufzeit die Schwelle unterschreitet |

## Sommermodus (Nachtkühlung)

Ist der Schalter `switch.maico_kwl_sommermodus` aktiv, regelt die Integration die Anlage temperaturabhängig:

- **Nachtkühlung:** Ist die Außenluft mindestens *Mindest-Differenz* °C kühler als die Raumluft **und** liegt die Raumluft über der *Zieltemperatur*, schaltet die Anlage auf Manuell + Intensiv. Der Bypass wird vom Gerät selbst geöffnet.
- **Bereit (Schutzlüftung):** In der neutralen Zone (weder kühl genug zum Kühlen noch zu warm) läuft die Anlage auf Manuell + Schutzlüftung – minimaler Luftaustausch, damit Feuchte und CO₂ nicht ansteigen, ohne aktiv zu kühlen.
- **Tagsüber bei Hitze:** Ist die Außenluft wärmer als die Raumluft (inkl. 1 °C Hysterese), wird die Anlage abgeschaltet, um keine warme Luft einzubringen.
- **Zieltemperatur erreicht:** Wurde aktiv gekühlt und die Raumluft erreicht die Zieltemperatur, wird die Anlage abgeschaltet, damit die Räume nicht auskühlen.
- **Stoßlüftung aktiv:** Wird über den Button `button.maico_kwl_stosslueftung` eine Stoßlüftung ausgelöst, pausiert der Sommermodus für die eingestellte Dauer und greift nicht ein. Danach übernimmt die normale Logik automatisch wieder.

Der aktuelle Zustand ist am Sensor `sensor.maico_kwl_sommermodus_status` ablesbar (Kühlt / Bereit / Aus / Stoßlüftung aktiv / Inaktiv). Schwellen über `number.maico_kwl_cool_min_diff` (Standard 2 °C) und `number.maico_kwl_cool_target` (Standard 22 °C) einstellbar. Ist der Schalter aus, greift keinerlei Automatik – die Anlage lässt sich vollständig manuell bedienen.

### Schutz gegen häufiges Schalten (Anti-Pendeln)

Damit die Anlage an der Schaltgrenze nicht ständig hin- und herspringt, gibt es zwei Mechanismen:

- **Hysterese** (`number.maico_kwl_cool_hysteresis`, Standard 0,5 °C): ein Totband um die Zieltemperatur. Gekühlt wird erst ab *Zieltemperatur + Hysterese*, gestoppt erst bei *Zieltemperatur − Hysterese*. Bei Ziel 21 °C und Hysterese 0,5 °C heißt das: Start ab 21,5 °C, Stopp erst bei 20,5 °C.
- **Mindest-Laufzeit** (`number.maico_kwl_min_runtime`, Standard 10 min, einstellbar 5–15 min): nach jedem Schaltvorgang wird mindestens diese Zeit gewartet, bevor erneut geschaltet wird – auch wenn die Temperatur kurz zappelt.

## Stromverbrauch (Schätzung)

Die Sensoren `maico_kwl_leistung` (W) und `maico_kwl_energie` (kWh) liefern eine **rechnerische Schätzung** des Stromverbrauchs. Das Gerät selbst meldet keine Leistung über Modbus, daher wird sie aus dem Volumenstrom abgeleitet.

### Grundlage: der SPI-Wert

Das Maico-Datenblatt der WS 300 Flat gibt einen **SPI-Wert** (spezifische Leistungsaufnahme) von **0,2 Wh/m³** nach DIN EN 13141-7 (A7) an. Dieser Wert beschreibt, wie viel elektrische Energie das Gerät pro gefördertem Kubikmeter Luft aufnimmt – also den Wirkungsgrad der Ventilatoren über alle Stufen hinweg.

### Leistung (Watt)

Aus dem SPI-Wert und dem aktuell gemessenen Volumenstrom ergibt sich die Momentanleistung:

```
Leistung [W] = Volumenstrom [m³/h] × SPI [Wh/m³]
             = Volumenstrom [m³/h] × 0,2
```

Da Zu- und Abluft getrennt gemessen werden, wird der **Mittelwert beider Volumenströme** verwendet. Liegt kein Volumenstrom an (Anlage aus), wird die **Standby-Leistung von ca. 1 W** angesetzt (ebenfalls aus dem Datenblatt).

Beispielwerte:

| Betrieb | Volumenstrom | geschätzte Leistung |
|---|---|---|
| Aus (Standby) | 0 m³/h | ~1 W |
| Schutzlüftung | ~100 m³/h | ~20 W |
| Nennlüftung | ~150 m³/h | ~30 W |
| Intensiv | ~200 m³/h | ~40 W |

Zum Vergleich: Das Datenblatt nennt 45 W beim genormten Referenz-Betriebspunkt – die Schätzung für Intensiv (40 W) liegt also in derselben Größenordnung.

### Energie (kWh)

Der Energiesensor **integriert die geschätzte Leistung über die Zeit**. Bei jeder Aktualisierung wird die seit der letzten Messung verstrichene Zeit mit der momentanen Leistung multipliziert und aufaddiert:

```
Energie [kWh] += Leistung [W] × verstrichene Zeit [h] ÷ 1000
```

Der Sensor ist als `total_increasing`-Zähler ausgelegt und damit direkt im **Home-Assistant-Energie-Dashboard** verwendbar. Der Zählerstand übersteht einen Neustart (über `RestoreEntity`); Ausfallzeiten werden nicht mitgezählt.

### Wichtige Einordnung

Dies ist eine **Schätzung, keine geeichte Messung**. Der reale Verbrauch weicht ab, weil der SPI-Wert ein genormter Mittelwert ist und der tatsächliche Bedarf u. a. von Kanaldruck, Filterzustand und Betriebspunkt abhängt. Für eine exakte Erfassung wäre eine Strommesssteckdose nötig. Für eine Größenordnung („was kostet die Lüftung ungefähr") ist die Schätzung jedoch gut geeignet.

## Erweiterte Parameter (offizielle Maico-Registerliste)

Zusätzlich zu den Basis-Funktionen sind weitere Register aus der offiziellen Maico-Parameterliste eingebunden:

### Lese-Sensoren

| Entität | Beschreibung |
|---|---|
| `maico_kwl_temp_raum` | Temperatur Raum (Gerätefühler, Register 700) |
| `maico_kwl_bh_feuchteschutz` … `_gesamt` | Betriebsstunden je Stufe + gesamt (850–859, 32-Bit) |
| `maico_kwl_fehler` | Aktueller Fehler (OK / Aktiv, Bitfeld 401/402 als Attribut) |
| `maico_kwl_hinweis` | Aktueller Hinweis (OK / Aktiv, Bitfeld 403/404 als Attribut) |

### Steuerung (schreibt direkt ins Gerät)

| Entität | Register | Beschreibung |
|---|---|---|
| `number.maico_kwl_t_raum_max` | 302 | T-Raum max. – Schwelle für die automatische Bypass-Kühlung (18–30 °C) |
| `number.maico_kwl_t_zuluft_min_kuehlen` | 301 | Minimale Zulufttemperatur beim Kühlen (8–29 °C) |
| `number.maico_kwl_dauer_lueftungsstufe` | 153 | Dauer der Stoßlüftung (5–90 min) |
| `button.maico_kwl_stosslueftung` | 551 | Stoßlüftung auslösen (Intensiv für die eingestellte Dauer) |

> **Firmware ≥ 1.3.0:** Ab dieser Firmware gibt es keine Sommer-/Winterumschaltung mehr – der Bypass wird vollautomatisch geregelt und öffnet, sobald die Raumtemperatur über **T-Raum max.** (Register 302) steigt und die Außenluft kühler ist. Dieser Wert ist damit der eigentliche Hebel für die geräteeigene Kühlung. Die früheren Register „Jahreszeit" (552) und „Solltemperatur Raum" (553, nur mit Nachheizregister wirksam) sind daher nicht eingebunden.

> ⚠️ **Hinweis zur HA-Nachtkühlung:** Der HA-**Sommermodus** regelt zusätzlich aktiv die Lüftungsstufe hoch (Intensiv), während das Gerät nur den Bypass öffnet. Beide ergänzen sich. Damit sie in dieselbe Richtung arbeiten, sollte **T-Raum max.** nicht höher als die gewünschte Kühl-Zieltemperatur stehen.

## Lovelace Custom Card

Zum Lieferumfang gehört eine grafische Lovelace-Karte (`lovelace/maico-kwl-card.js`), die die Anlage als interaktives Schema darstellt – mit animierten Luftstrom-Pfeilen, Temperaturanzeige an allen vier Anschlüssen, Wärmetauscher-Wirkungsgrad, Bypass-Status und einer konfigurierbaren Raumübersicht.

### Installation der Karte

1. Die Datei `lovelace/maico-kwl-card.js` aus dem Repo in den Ordner `config/www/` deiner Home-Assistant-Installation kopieren.

2. In HA die Ressource registrieren: **Einstellungen → Dashboards → ⋮ → Ressourcen → Hinzufügen**
   ```
   URL:  /local/maico-kwl-card.js
   Typ:  JavaScript-Modul
   ```

3. HA-Browser-Cache leeren (**Strg+Shift+R**).

### Karte einbinden

Im Dashboard eine neue Karte hinzufügen → **Manuelle Karte** → folgenden YAML-Block einfügen:

```yaml
type: custom:maico-kwl-card
name: Maico WS 300 Flat
entities:
  aussenluft:   sensor.maico_ws_300_flat_aussenluft
  zuluft:       sensor.maico_ws_300_flat_zuluft
  abluft:       sensor.maico_ws_300_flat_abluft
  fortluft:     sensor.maico_ws_300_flat_fortluft
  status:       sensor.htr_maico_ws_300_flat_sommermodus_status
  stufe:        sensor.maico_ws_300_flat_luftungsstufe
  volumenstrom: sensor.maico_ws_300_flat_volumenstrom_zuluft
  wrg:          sensor.maico_ws_300_flat_warmeruckgewinnung  # optional
  bypass:       sensor.maico_ws_300_flat_bypass_status       # optional
rooms:
  zuluft:
    - { name: Schlafzimmer,  icon: "🛏" }
    - { name: Wohnzimmer,    icon: "🛋" }
    - { name: Arbeitszimmer, icon: "💼" }
  abluft:
    - { name: Bad,           icon: "🚿" }
    - { name: Küche,         icon: "🍳" }
    - { name: HTR,           icon: "🔧" }
```

Die Entity-IDs entsprechen der Standard-Benennung dieser Integration. Bei abweichenden Namen (z.B. durch mehrere Geräte) die IDs entsprechend anpassen. Räume sind vollständig konfigurierbar – Name, Icon und Anzahl lassen sich frei wählen.

### Erklärungstext (optional)

Als aufklappbare Erklärungskarte direkt über der Karte (Markdown-Karte):

```yaml
type: markdown
content: >
  <details>
  <summary>❓ <b>Erklärung der Lüftungskarte</b> (zum Aufklappen tippen)</summary>

  Die Karte zeigt den aktuellen Zustand der Lüftungsanlage auf einen Blick.

  **Außen (links):** Frischluft tritt ein (Außenluft) und verbrauchte Luft verlässt das Gebäude (Fortluft).

  **Innen (rechts):** Aufbereitete Zuluft geht in die Wohnräume, Abluft wird aus Bädern und Küche abgesaugt.

  **Wärmetauscher (Mitte):** Überträgt die Wärme der Abluft auf die Außenluft.
  Der WRG-Wert zeigt den Wirkungsgrad – bei geöffnetem Bypass (Nachtkühlung) ist er bewusst niedrig.

  **Bypass:** Öffnet automatisch im Sommermodus, um kühle Nachtluft direkt einzuleiten.
  </details>
```

> **Hinweis:** Ein grafischer Editor für die Karten-Konfiguration (ohne YAML) ist in Entwicklung.

## Optionale Sensoren

Geräte der KWL-Zentral-Plattform können zusätzliche Sensoren besitzen (mehrere CO₂-, VOC- und externe Feuchtesensoren). Diese werden **automatisch erkannt**:

- Meldet das Gerät beim Lesen einen Modbus-Fehler für ein Register, gilt der Sensor als **nicht vorhanden** und es wird keine Entität angelegt.
- Existiert das Register, wird die Entität angelegt, ist aber **standardmäßig deaktiviert**. So bleibt das Dashboard übersichtlich. Wer einen dieser Sensoren verbaut hat, aktiviert die Entität einfach in den Geräteeinstellungen (Einstellungen → Geräte & Dienste → Gerät → die deaktivierte Entität → aktivieren).

Betroffen sind: `CO₂ Sensor 2–4`, `VOC Sensor 1–2`, `Luftfeuchte Sensor 1–4 (extern)`.

## PushPull (PP 45 / PPB 30)

Die dezentralen PushPull-Geräte nutzen eine andere Steuerungsplattform (RLS 45 K) mit eigenem, schlankem Registersatz. Angebunden werden sie über ein **LAN-Gateway**, das Modbus TCP ↔ RTU wandelt – aus Sicht von Home Assistant also normales Modbus TCP.

Bereitgestellte Entitäten:

| Entität | Beschreibung |
|---|---|
| Betriebsart | Wärmerückgewinnung / Querlüftung |
| Lüftungsstufe | Aus / Stufe 1–4 / Intensiv |
| Luftfeuchte | relative Feuchte in % |
| Filterwechsel | Restlaufzeit in Tagen |
| Betriebsstunden Gesamt | aus getrennten Stunden-/Tage-Registern berechnet |

> PushPull-Geräte haben **keinen** Bypass und keine Temperaturfühler wie die zentralen KWL – Sommermodus/Nachtkühlung gibt es hier daher nicht.

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
- Ein unterstütztes Maico-Gerät (siehe oben) mit aktiviertem Modbus TCP, erreichbar im Netzwerk (bei PushPull über ein LAN-Gateway)

## Haftungsausschluss

Dieses Projekt ist ein privates, inoffizielles Hobbyprojekt und steht in keiner Verbindung zur Maico Elektroapparate-Fabrik GmbH. Nutzung auf eigene Verantwortung. Die Register-Zuordnung wurde für eine konkrete WS 300 Flat ermittelt und kann je nach Firmware/Modell abweichen.

## Lizenz

MIT – siehe [LICENSE](LICENSE).

## Unterstützung

Dieses Projekt entsteht in der Freizeit und ist kostenlos. Wenn es dir hilft und du „Danke" sagen möchtest, freue ich mich über einen Kaffee. ☕ Völlig freiwillig – die Integration bleibt natürlich für alle frei nutzbar.

[![Mit PayPal spenden](https://img.shields.io/badge/PayPal-Spenden-00457C?logo=paypal&logoColor=white&style=for-the-badge)](https://www.paypal.com/donate/?hosted_button_id=SLNW2MCC268SG)
