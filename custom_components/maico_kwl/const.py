"""Constants for Maico KWL integration."""

DOMAIN = "maico_kwl"
DEVICE_MODEL = "Maico WS 300 Flat"

# Modbus Configuration
DEFAULT_MODBUS_PORT = 502
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_SLAVE_ID = 1

# Maico WS 300 Flat - Modbus Register Mapping
MODBUS_REGISTERS = {
    # Betriebsmodi und Steuerung
    "betriebsart": 550,           # Betriebsart (0-5) — read/write
    "lueftungsstufe": 650,        # Lüftungsstufe (0-4) — READ ONLY
    "lueftungsstufe_write": 554,  # Lüftungsstufe schreiben (2=Red, 3=Nenn, 4=Intensiv)
    
    # Drehzahlen
    "drehzahl_zuluft": 651,       # Drehzahl Zuluft [U/min]
    "drehzahl_abluft": 652,       # Drehzahl Abluft [U/min]
    
    # Volumenströme
    "volumenstrom_zuluft": 653,   # Volumenstrom Zuluft [m³/h]
    "volumenstrom_abluft": 654,   # Volumenstrom Abluft [m³/h]
    
    # Filter Restlaufzeiten (in Tagen)
    "filter_restlaufzeit_zuluft": 655,    # Restlaufzeit Filter Zuluft [Tage]
    "filter_restlaufzeit_aussenluft": 656, # Restlaufzeit Filter Außenluft [Tage]
    "filter_restlaufzeit_abluft": 657,    # Restlaufzeit Filter Abluft [Tage]
    
    # Temperaturen (int16, scale 0.1)
    "temp_aussenluft": 703,       # Temperatur Außenluft [°C]
    "temp_zuluft": 704,           # Temperatur Zuluft [°C]
    "temp_abluft": 705,           # Temperatur Abluft [°C]
    "temp_fortluft": 706,         # Temperatur Fortluft [°C]
    
    # Sensoren
    "humidity_abluft": 750,       # Relative Feuchte Abluft [%]
    "co2_abluft": 755,            # CO2 Abluft [ppm]
    
    # Schaltzustände (0=aus, 1=an)
    "schalter_zuluft": 800,       # Schalter Zuluftventilator
    "schalter_abluft": 801,       # Schalter Abluftventilator
    "schalter_bypass": 802,       # Schalter Bypass

    # --- Erweiterte Register (offizielle Maico-Parameterliste) ---
    # Schreibbare Steuerung
    "stosslueftung": 551,         # 1 = Stoßlüftung auslösen  [W]
    "dauer_lueftungsstufe": 153,  # Dauer der Stoßlüftung [min] (5..90)  [W]
    "t_raum_max": 302,            # T-Raum max. [°C] (18..30, int16 ×10)  [W]
    "t_zuluft_min_kuehlen": 301,  # T-Zuluft min. kühlen [°C] (8..29, int16 ×10)  [W]
    # Lese-Sensoren
    "temp_raum": 700,             # Temperatur Raum [°C] (int16 ×10)  [R]
    "fehler_1": 401,              # Aktueller Fehler (Bitfeld)  [R]
    "fehler_2": 402,              # Aktueller Fehler (Bitfeld)  [R]
    "hinweis_1": 403,             # Aktueller Hinweis (Bitfeld)  [R]
    "hinweis_2": 404,             # Aktueller Hinweis (Bitfeld)  [R]
    # Betriebsstunden — je 2 Register (High-Word + Low-Word) = 32 Bit
    "bh_feuchteschutz": 850,      # +851
    "bh_reduziert": 852,          # +853
    "bh_nenn": 854,               # +855
    "bh_intensiv": 856,           # +857
    "bh_gesamt": 858,             # +859
}

# Betriebsart Mapping (6 Modi)
BETRIEBSART_MAPPING = {
    0: "Aus",
    1: "Manuell",
    2: "Auto Zeit",
    3: "Auto Sensor",
    4: "Eco-Zuluft",
    5: "Eco-Abluft",
}

# Lüftungsstufe Mapping (5 Stufen mit deutschen Namen)
LUEFTUNGSSTUFE_MAPPING = {
    0: "Abgeschaltet",
    1: "Schutzlüftung",
    2: "Reduziert",
    3: "Nennlüftung",
    4: "Intensiv",
}

# Bypass Status
BYPASS_STATUS_MAPPING = {
    0: "Geschlossen",
    1: "Offen",
}

# Schalter Status
SCHALTER_STATUS_MAPPING = {
    0: "Aus",
    1: "An",
}

# Filter warning threshold in days
FILTER_WARNING_DAYS = 7  # Alert when filter has 7 days left

# --- Sommermodus (Nachtkühlung) ---
# Defaults for the configurable numbers
DEFAULT_COOL_MIN_DIFF = 2.0    # °C: Außen muss mind. so viel kühler sein als innen
DEFAULT_COOL_TARGET = 22.0     # °C: bis zu dieser Innentemperatur wird gekühlt
DEFAULT_COOL_HYSTERESIS = 0.5  # °C: Totband um die Zieltemperatur (gegen Pendeln)
DEFAULT_MIN_RUNTIME = 10       # min: Mindest-Haltezeit nach einem Schaltvorgang
# Hysterese: tagsüber erst "aus", wenn außen mind. so viel wärmer ist als innen
SUMMER_DAY_HYSTERESIS = 1.0    # °C
# Stage written to register 554 when night-cooling (4 = Intensiv)
SUMMER_COOL_STUFE = 4
# Stage written when in neutral "Bereit" zone (1 = Schutzlüftung, minimal)
SUMMER_IDLE_STUFE = 1

# --- Stromverbrauch (Schätzung laut Hersteller-Datenblatt) ---
# SPI-Wert nach DIN EN 13141-7 (A7): 0,2 Wh/m³.
# Leistung (W) = Volumenstrom (m³/h) * SPI.
SPI_WH_PER_M3 = 0.2
# Standby-Leistung laut Datenblatt (< 1 W)
STANDBY_POWER_W = 1.0

# Entity naming
ATTR_BETRIEBSART = "betriebsart"
ATTR_LUEFTUNGSSTUFE = "lueftungsstufe"
ATTR_FILTER_RESTLAUFZEIT = "filter_restlaufzeit_tage"
ATTR_WAERMERUECKGEWINNUNG = "waermerueckgewinnung"
