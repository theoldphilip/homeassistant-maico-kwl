"""Device platform profiles for Maico ventilation units.

A *profile* bundles everything specific to a Maico control platform: the
Modbus register map (with scaling and flags), the models it covers, and which
optional features it may expose (presence auto-detected at runtime).

Platforms:
  * "kwl_zentral" – central KWL platform (Welt A+B): Trio, WR 310/410,
       WS 120/160/170/300/320/470, RB 300 Flat, WS 75. Shared register core;
       model differences handled by runtime feature auto-detection.
  * "pushpull"    – PP 45 / PPB 30 (RLS 45 K, Welt C). Reserved/partial;
       wired up fully in a later stage.

MIGRATION SAFETY:
The kwl_zentral register map is the original WS 300 Flat map. The entity
unique_id prefix stays "maico_kwl" for migrated installs, so existing
entity_ids (dashboards, automations, energy dashboard) keep working.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Register definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RegisterDef:
    """A single Modbus register.

    scale:    factor from raw to displayed value (1.0 = as-is, 0.1 = raw ×10).
    optional: feature-detected (Option A: Modbus error -> entity absent;
              persistent 0 -> entity created but disabled by default).
    writable: register can be written.
    width:    number of registers (2 = 32-bit High/Low word).
    """

    address: int
    scale: float = 1.0
    optional: bool = False
    writable: bool = False
    width: int = 1


# Platform identifiers
PLATFORM_KWL_ZENTRAL = "kwl_zentral"
PLATFORM_PUSHPULL = "pushpull"


# ---------------------------------------------------------------------------
# Platform "KWL-Zentral" (Welt A + B) — verified on WS 300 Flat
# ---------------------------------------------------------------------------
# Scaling note (verified firmware): humidity (750), CO2 (755) and
# T-Zuluft min. (301) are delivered DIRECTLY (scale 1.0). Temperatures
# (700, 703-706) and T-Raum max. (302) are ×10 (scale 0.1).

KWL_ZENTRAL_REGISTERS: dict[str, RegisterDef] = {
    # core control
    "betriebsart": RegisterDef(550, writable=True),
    "lueftungsstufe": RegisterDef(650),
    "lueftungsstufe_write": RegisterDef(554, writable=True),
    # fans
    "drehzahl_zuluft": RegisterDef(651),
    "drehzahl_abluft": RegisterDef(652),
    "volumenstrom_zuluft": RegisterDef(653),
    "volumenstrom_abluft": RegisterDef(654),
    # filters
    "filter_restlaufzeit_zuluft": RegisterDef(655),
    "filter_restlaufzeit_aussenluft": RegisterDef(656),
    "filter_restlaufzeit_abluft": RegisterDef(657),
    # temperatures (×10)
    "temp_aussenluft": RegisterDef(703, scale=0.1),
    "temp_zuluft": RegisterDef(704, scale=0.1),
    "temp_abluft": RegisterDef(705, scale=0.1),
    "temp_fortluft": RegisterDef(706, scale=0.1),
    "temp_raum": RegisterDef(700, scale=0.1),
    # sensors at the unit
    "humidity_abluft": RegisterDef(750, scale=1.0),
    "co2_abluft": RegisterDef(755, scale=1.0, optional=True),
    # switch states
    "schalter_zuluft": RegisterDef(800),
    "schalter_abluft": RegisterDef(801),
    "schalter_bypass": RegisterDef(802),
    # writable extras
    "stosslueftung": RegisterDef(551, writable=True),
    "dauer_lueftungsstufe": RegisterDef(153, writable=True),
    "t_raum_max": RegisterDef(302, scale=0.1, writable=True, optional=True),
    "t_zuluft_min_kuehlen": RegisterDef(301, scale=1.0, writable=True),
    # diagnostics (bitfields)
    "fehler_1": RegisterDef(401),
    "fehler_2": RegisterDef(402),
    "hinweis_1": RegisterDef(403),
    "hinweis_2": RegisterDef(404),
    # operating hours (32-bit High/Low)
    "bh_feuchteschutz": RegisterDef(850, width=2),
    "bh_reduziert": RegisterDef(852, width=2),
    "bh_nenn": RegisterDef(854, width=2),
    "bh_intensiv": RegisterDef(856, width=2),
    "bh_gesamt": RegisterDef(858, width=2),
    # optional external sensors (feature-detected)
    "rf_sensor_1": RegisterDef(751, optional=True),
    "rf_sensor_2": RegisterDef(752, optional=True),
    "rf_sensor_3": RegisterDef(753, optional=True),
    "rf_sensor_4": RegisterDef(754, optional=True),
    "co2_sensor_2": RegisterDef(756, optional=True),
    "co2_sensor_3": RegisterDef(757, optional=True),
    "co2_sensor_4": RegisterDef(758, optional=True),
    "voc_sensor_1": RegisterDef(759, optional=True),
    "voc_sensor_2": RegisterDef(760, optional=True),
    # optional actuators (feature-detected)
    "ptc_heizregister": RegisterDef(803, optional=True),
    "relais_nachheizung": RegisterDef(805, optional=True),
    "sole_umwaelzpumpe": RegisterDef(806, optional=True),
}

# Firmware-dependent scalings exposed as config options (default = verified).
KWL_ZENTRAL_SCALING_OPTIONS = {
    "humidity_abluft": 1.0,
    "co2_abluft": 1.0,
    "t_zuluft_min_kuehlen": 1.0,
}

KWL_ZENTRAL_MODELS = [
    "Trio zentral", "Trio dezentral", "WS 120 Trio", "WS 160 Flat", "WS 170",
    "WS 300 Flat", "RB 300 Flat", "WS 320", "WS 470", "WR 310", "WR 410",
    "WS 75 Powerbox",
]


# ---------------------------------------------------------------------------
# Platform "PushPull" (Welt C) — PP 45 / PPB 30, via LAN gateway (TCP)
# ---------------------------------------------------------------------------
# Different register numbers. Operating hours = separate hours(0-23)+days.
# Humidity (301) direct in %. Wired up fully in a later stage.

PUSHPULL_REGISTERS: dict[str, RegisterDef] = {
    "betriebsart": RegisterDef(200, writable=True),     # 0=WRG, 1=Quer
    "lueftungsstufe": RegisterDef(201, writable=True),  # 0..5
    "sensorbetrieb_wrg": RegisterDef(202, writable=True),
    "sensorbetrieb_quer": RegisterDef(203, writable=True),
    "filter_restlaufzeit": RegisterDef(300),
    "humidity_fmr": RegisterDef(301),
    "error_code": RegisterDef(302),
    "bh_aus_h": RegisterDef(400), "bh_aus_d": RegisterDef(401),
    "bh_fl_h": RegisterDef(402), "bh_fl_d": RegisterDef(403),
    "bh_rl1_h": RegisterDef(404), "bh_rl1_d": RegisterDef(405),
    "bh_rl2_h": RegisterDef(406), "bh_rl2_d": RegisterDef(407),
    "bh_nl_h": RegisterDef(408), "bh_nl_d": RegisterDef(409),
    "bh_il_h": RegisterDef(410), "bh_il_d": RegisterDef(411),
    "bh_gesamt_h": RegisterDef(412), "bh_gesamt_d": RegisterDef(413),
}

PUSHPULL_MODELS = ["PushPull PP 45", "PushPull PPB 30"]


# ---------------------------------------------------------------------------
# Profile registry
# ---------------------------------------------------------------------------

PROFILES: dict[str, dict] = {
    PLATFORM_KWL_ZENTRAL: {
        "key": PLATFORM_KWL_ZENTRAL,
        "name": "KWL Zentral (Trio / WR / WS)",
        "registers": KWL_ZENTRAL_REGISTERS,
        "scaling_options": KWL_ZENTRAL_SCALING_OPTIONS,
        "models": KWL_ZENTRAL_MODELS,
        "unique_prefix": "maico_kwl",
        "verified": True,
    },
    PLATFORM_PUSHPULL: {
        "key": PLATFORM_PUSHPULL,
        "name": "PushPull (PP 45 / PPB 30)",
        "registers": PUSHPULL_REGISTERS,
        "scaling_options": {},
        "models": PUSHPULL_MODELS,
        "unique_prefix": "maico_pushpull",
        "verified": False,
    },
}

# Migration defaults: existing installs (no profile stored) are WS 300 Flat.
DEFAULT_PROFILE_KEY = PLATFORM_KWL_ZENTRAL
DEFAULT_MODEL = "WS 300 Flat"


def get_profile(profile_key: str | None) -> dict:
    """Return the profile dict for a key, falling back to the default."""
    if profile_key and profile_key in PROFILES:
        return PROFILES[profile_key]
    return PROFILES[DEFAULT_PROFILE_KEY]


def model_to_profile_key(model: str | None) -> str:
    """Map a model name to its profile key."""
    if model:
        for key, prof in PROFILES.items():
            if model in prof["models"]:
                return key
    return DEFAULT_PROFILE_KEY


def all_models() -> list[str]:
    """Flat list of all selectable models across profiles."""
    models: list[str] = []
    for prof in PROFILES.values():
        models.extend(prof["models"])
    return models


def build_unique_id(legacy_ids: bool, entry_id: str, key: str) -> str:
    """Build an entity unique_id.

    legacy installs (migrated from the single-device version) keep the
    original ``maico_kwl_<key>`` form so their entity_ids never change.
    New installs get ``maico_kwl_<entry_id>_<key>`` so multiple devices on
    one Home Assistant don't collide.
    """
    if legacy_ids:
        return f"maico_kwl_{key}"
    return f"maico_kwl_{entry_id}_{key}"
