"""Data coordinator for Maico KWL."""
import logging
from datetime import timedelta, datetime, timezone
from typing import Any, Dict

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    MODBUS_REGISTERS,
    DEFAULT_SLAVE_ID,
    DEFAULT_COOL_MIN_DIFF,
    DEFAULT_COOL_TARGET,
    DEFAULT_COOL_HYSTERESIS,
    DEFAULT_MIN_RUNTIME,
    SUMMER_DAY_HYSTERESIS,
    SUMMER_COOL_STUFE,
    SUMMER_IDLE_STUFE,
)

_LOGGER = logging.getLogger(__name__)


# Detect pymodbus API: 3.10+ uses "device_id", older uses "slave"
try:
    import inspect
    _READ_PARAMS = inspect.signature(
        AsyncModbusTcpClient.read_holding_registers
    ).parameters
    _SLAVE_KWARG = "device_id" if "device_id" in _READ_PARAMS else "slave"
except Exception:  # pragma: no cover
    _SLAVE_KWARG = "slave"


class MaicoKWLCoordinator(DataUpdateCoordinator):
    """Coordinator for fetching Maico KWL data."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, unit_id: int, scan_interval: int, profile_key: str = None):
        """Initialize the coordinator."""
        self.host = host
        self.port = port
        self.unit_id = unit_id
        # Load the device profile (register map etc.). Falls back to the
        # default (kwl_zentral / WS 300 Flat) for legacy entries.
        from .profiles import get_profile
        self.profile = get_profile(profile_key)
        self.registers = self.profile["registers"]
        # Optional per-install scaling overrides (firmware-dependent regs).
        self._scaling_overrides: dict = {}
        # Features detected absent at runtime (Modbus error on probe).
        self._absent_features: set = set()
        # timeout=5 prevents the event loop from hanging on a stalled connect.
        # pymodbus handles automatic reconnects internally after the first connect.
        self.client = AsyncModbusTcpClient(host=host, port=port, timeout=5)

        # --- Sommermodus state (loaded/persisted by the platforms) ---
        self.summer_mode: bool = False
        self.cool_min_diff: float = DEFAULT_COOL_MIN_DIFF
        self.cool_target: float = DEFAULT_COOL_TARGET
        self.cool_hysteresis: float = DEFAULT_COOL_HYSTERESIS
        self.min_runtime: int = DEFAULT_MIN_RUNTIME
        # Remembers what the automation last commanded, so we don't spam the
        # device with identical writes on every poll.
        self._summer_last_action: str | None = None
        # Timestamp of the last actual switch, for the minimum-runtime guard.
        self._last_switch_ts: datetime | None = None
        # Timestamp until which a manually triggered Stoßlüftung is active.
        # While set and in the future, the summer logic stands down.
        self._boost_until: datetime | None = None
        # Human-readable status for the status sensor / notifications.
        self.summer_status: str = "Inaktiv"

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def async_connect(self) -> bool:
        """Establish the initial connection. Returns True on success."""
        try:
            await self.client.connect()
            connected = self.client.connected
            if connected:
                await self._probe_optional_features()
            return connected
        except Exception as err:
            _LOGGER.error(f"Initial connection to {self.host} failed: {err}")
            return False

    async def _probe_optional_features(self) -> None:
        """Detect which optional registers the device actually has (Option A).

        A Modbus error on read means the register does not belong to this
        device class -> the feature is absent and its entity is not created.
        A readable register (even value 0) is considered present; the entity
        platforms decide whether to disable a persistently-zero entity.
        """
        self._absent_features = set()
        for key, regdef in self.registers.items():
            if not regdef.optional:
                continue
            try:
                res = await self._read_registers(regdef.address, regdef.width)
                if res.isError():
                    self._absent_features.add(key)
            except Exception:
                # Treat a hard exception like an absent feature (safer).
                self._absent_features.add(key)
        if self._absent_features:
            _LOGGER.debug("Absent optional features: %s", sorted(self._absent_features))

    def feature_present(self, key: str) -> bool:
        """True if an optional feature/register is present on this device."""
        return key not in self._absent_features

    # Optional external sensors that become their own sensor entities when
    # the device exposes them (CO2 1-4, VOC, external humidity).
    OPTIONAL_SENSOR_KEYS = (
        "co2_abluft", "co2_sensor_2", "co2_sensor_3", "co2_sensor_4",
        "voc_sensor_1", "voc_sensor_2",
        "rf_sensor_1", "rf_sensor_2", "rf_sensor_3", "rf_sensor_4",
    )

    def _optional_sensor_keys(self):
        """Optional sensor register-keys that exist in the active profile."""
        return [k for k in self.OPTIONAL_SENSOR_KEYS if k in self.registers]

    async def _read_registers(self, address: int, count: int):
        """Read holding registers (pymodbus API-compatible)."""
        kwargs = {"address": address, "count": count, _SLAVE_KWARG: self.unit_id}
        return await self.client.read_holding_registers(**kwargs)

    def _addr(self, key: str) -> int:
        """Resolve a register key to its Modbus address."""
        return self.registers[key].address

    def _scale(self, key: str) -> float:
        """Resolve the scale factor for a register key.

        A per-install override (from config options) wins over the profile
        default, so firmware-dependent registers can be corrected without
        code changes.
        """
        if key in self._scaling_overrides:
            return self._scaling_overrides[key]
        return self.registers[key].scale

    def _width(self, key: str) -> int:
        """Number of Modbus registers this key spans (2 = 32-bit)."""
        return self.registers[key].width

    async def _write_register(self, address: int, value: int):
        """Write a single holding register (pymodbus API-compatible)."""
        kwargs = {"address": address, "value": value, _SLAVE_KWARG: self.unit_id}
        return await self.client.write_register(**kwargs)

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Modbus device (dispatch by platform)."""
        # Do NOT manually call connect() here on every poll — pymodbus reconnects
        # automatically. Manually reconnecting collides with that and can spin
        # the event loop. If not connected, report a failed update cleanly.
        if not self.client.connected:
            raise UpdateFailed("Modbus client not connected")

        from .profiles import PLATFORM_PUSHPULL
        if self.profile.get("key") == PLATFORM_PUSHPULL:
            return await self._update_pushpull()
        return await self._update_kwl_zentral()

    async def _update_kwl_zentral(self) -> Dict[str, Any]:
        """Fetch data for the central KWL platform (Welt A/B)."""
        try:
            data = {}
            
            # Betriebsart
            result = await self._read_registers(self._addr("betriebsart"), 1)
            if not result.isError():
                data["betriebsart"] = result.registers[0]
            
            # Lüftungsstufe + Drehzahlen + Volumenströme (650-654)
            result = await self._read_registers(self._addr("lueftungsstufe"), 5)
            if not result.isError():
                data["lueftungsstufe"] = result.registers[0]
                data["drehzahl_zuluft"] = result.registers[1]
                data["drehzahl_abluft"] = result.registers[2]
                data["volumenstrom_zuluft"] = result.registers[3]
                data["volumenstrom_abluft"] = result.registers[4]
            
            # Filter Restlaufzeiten (655-657)
            result = await self._read_registers(self._addr("filter_restlaufzeit_zuluft"), 3)
            if not result.isError():
                data["filter_restlaufzeit_zuluft"] = result.registers[0]
                data["filter_restlaufzeit_aussenluft"] = result.registers[1]
                data["filter_restlaufzeit_abluft"] = result.registers[2]
            
            # Temperaturen (703-706) - int16, Skalierung aus Profil
            result = await self._read_registers(self._addr("temp_aussenluft"), 4)
            if not result.isError():
                data["temp_aussenluft"] = self._int16_to_float(result.registers[0], self._scale("temp_aussenluft"))
                data["temp_zuluft"] = self._int16_to_float(result.registers[1], self._scale("temp_zuluft"))
                data["temp_abluft"] = self._int16_to_float(result.registers[2], self._scale("temp_abluft"))
                data["temp_fortluft"] = self._int16_to_float(result.registers[3], self._scale("temp_fortluft"))
            
            # Humidity (750) + CO2 (755) - Skalierung aus Profil/Override
            result = await self._read_registers(self._addr("humidity_abluft"), 1)
            if not result.isError():
                data["humidity_abluft"] = result.registers[0] * self._scale("humidity_abluft")
            
            result = await self._read_registers(self._addr("co2_abluft"), 1)
            if not result.isError():
                data["co2_abluft"] = result.registers[0] * self._scale("co2_abluft")
            
            # Schaltzustände (800-802)
            result = await self._read_registers(self._addr("schalter_zuluft"), 3)
            if not result.isError():
                data["schalter_zuluft"] = bool(result.registers[0])
                data["schalter_abluft"] = bool(result.registers[1])
                data["schalter_bypass"] = bool(result.registers[2])

            # --- Erweiterte Register ---
            # Temperatur Raum (700)
            result = await self._read_registers(self._addr("temp_raum"), 1)
            if not result.isError():
                data["temp_raum"] = self._int16_to_float(result.registers[0], self._scale("temp_raum"))

            # Konfig-Sollwerte (schreibbar, hier nur lesen für Anzeige)
            res = await self._read_registers(self._addr("t_raum_max"), 1)
            if not res.isError():
                data["t_raum_max"] = self._int16_to_float(res.registers[0], self._scale("t_raum_max"))
            res = await self._read_registers(self._addr("t_zuluft_min_kuehlen"), 1)
            if not res.isError():
                data["t_zuluft_min_kuehlen"] = self._int16_to_float(res.registers[0], self._scale("t_zuluft_min_kuehlen"))

            # Stoßlüftung (551), Dauer (153)
            for key in ("stosslueftung", "dauer_lueftungsstufe"):
                res = await self._read_registers(self._addr(key), 1)
                if not res.isError():
                    data[key] = res.registers[0]

            # Fehler/Hinweise (401-404, Bitfelder)
            for key in ("fehler_1", "fehler_2", "hinweis_1", "hinweis_2"):
                res = await self._read_registers(self._addr(key), 1)
                if not res.isError():
                    data[key] = res.registers[0]

            # Betriebsstunden: je 2 Register = 32 Bit (High-Word/Low-Word)
            for key in ("bh_feuchteschutz", "bh_reduziert", "bh_nenn",
                        "bh_intensiv", "bh_gesamt"):
                res = await self._read_registers(self._addr(key), self._width(key))
                if not res.isError() and len(res.registers) >= 2:
                    high, low = res.registers[0], res.registers[1]
                    data[key] = (high << 16) | low

            # Optionale Sensoren (nur die, die als vorhanden erkannt wurden)
            for key in self._optional_sensor_keys():
                if not self.feature_present(key):
                    continue
                res = await self._read_registers(self._addr(key), self._width(key))
                if not res.isError():
                    data[key] = res.registers[0] * self._scale(key)

            # --- Sommermodus / Nachtkühlung ---
            await self._evaluate_summer_mode(data)

            return data
            
        except ModbusException as err:
            raise UpdateFailed(f"Modbus error: {err}")
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}")

    async def _update_pushpull(self) -> Dict[str, Any]:
        """Fetch data for the PushPull platform (Welt C).

        Slim register set: Betriebsart (200), Lüftungsstufe (201), filter
        runtime (300), humidity (301, direct %), error code (302), and
        operating hours split into separate hours(0-23)+days registers.
        """
        try:
            data = {}

            # Betriebsart (200): 0=WRG, 1=Quer  /  Lüftungsstufe (201): 0..5
            for key in ("betriebsart", "lueftungsstufe",
                        "sensorbetrieb_wrg", "sensorbetrieb_quer"):
                res = await self._read_registers(self._addr(key), 1)
                if not res.isError():
                    data[key] = res.registers[0]

            # Filter-Restlaufzeit (300), Feuchte (301, direkt %), Fehlercode (302)
            for key in ("filter_restlaufzeit", "humidity_fmr", "error_code"):
                res = await self._read_registers(self._addr(key), 1)
                if not res.isError():
                    data[key] = res.registers[0] * self._scale(key)

            # Betriebsstunden: je Zustand getrennte Stunden(0-23)+Tage-Register
            # -> Gesamtstunden = Tage*24 + Stunden
            bh_pairs = {
                "bh_aus": ("bh_aus_h", "bh_aus_d"),
                "bh_fl": ("bh_fl_h", "bh_fl_d"),
                "bh_rl1": ("bh_rl1_h", "bh_rl1_d"),
                "bh_rl2": ("bh_rl2_h", "bh_rl2_d"),
                "bh_nl": ("bh_nl_h", "bh_nl_d"),
                "bh_il": ("bh_il_h", "bh_il_d"),
                "bh_gesamt": ("bh_gesamt_h", "bh_gesamt_d"),
            }
            for out_key, (h_key, d_key) in bh_pairs.items():
                rh = await self._read_registers(self._addr(h_key), 1)
                rd = await self._read_registers(self._addr(d_key), 1)
                if not rh.isError() and not rd.isError():
                    data[out_key] = rd.registers[0] * 24 + rh.registers[0]

            return data

        except ModbusException as err:
            raise UpdateFailed(f"Modbus error: {err}")
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}")

    async def _evaluate_summer_mode(self, data: Dict[str, Any]) -> None:
        """Apply night-cooling logic when summer mode is enabled.

        Rules (only when self.summer_mode is True):
          * Night-cool: outdoor at least `cool_min_diff` °C cooler than indoor
            AND indoor above `cool_target`  -> Manuell + Intensiv.
          * Daytime heat: outdoor at least SUMMER_DAY_HYSTERESIS °C warmer
            than indoor  -> switch the unit Off (Betriebsart 0).
          * Otherwise: leave the unit alone (idle), but if we were actively
            cooling and the target is reached, stop (Off).

        To avoid writing the same command on every poll, the last action is
        remembered and only changes are written.
        """
        if not self.summer_mode:
            # If the user just turned summer mode off, forget the last action
            # so the next enable will act fresh.
            self._summer_last_action = None
            self.summer_status = "Inaktiv"
            return

        # If a manual Stoßlüftung is currently running, stand down so we
        # don't cut it short. Resume normal logic once it has elapsed.
        if self._boost_until is not None:
            if datetime.now(timezone.utc) < self._boost_until:
                self.summer_status = "Stoßlüftung aktiv (Sommermodus pausiert)"
                # Forget last action so we re-evaluate cleanly afterwards.
                self._summer_last_action = None
                return
            else:
                self._boost_until = None  # expired

        t_aul = data.get("temp_aussenluft")  # outdoor
        t_ab = data.get("temp_abluft")       # indoor (extract air)
        if not isinstance(t_aul, (int, float)) or not isinstance(t_ab, (int, float)):
            self.summer_status = "Keine Temperaturdaten"
            return  # no valid temps this cycle

        indoor = t_ab
        outdoor = t_aul

        # --- Entscheidung mit Hysterese (Totband um die Zieltemperatur) ---
        # Einschalten erst oberhalb von target + hyst, Ausschalten erst
        # unterhalb von target - hyst. Dazwischen wird der Zustand gehalten.
        hyst = self.cool_hysteresis
        cool_on_temp = self.cool_target + hyst   # z.B. 21,5 °C
        cool_off_temp = self.cool_target - hyst  # z.B. 20,5 °C
        was_cooling = self._summer_last_action == "cool"

        action: str  # one of: "cool", "off", "idle"

        # Tagsüber: außen deutlich wärmer als innen -> aus (eigene Hysterese).
        if outdoor >= indoor + SUMMER_DAY_HYSTERESIS:
            action = "off"
        # Kühlbedingung: außen kühl genug UND innen über dem oberen Schaltpunkt.
        elif outdoor <= indoor - self.cool_min_diff and indoor > cool_on_temp:
            action = "cool"
        # Bereits am Kühlen: Weiterkühlen mit relaxiertem Differenz-Schwellwert.
        # Die Außen/Innen-Differenz muss nur noch (min_diff - hyst) betragen,
        # um das Pendeln am Differenz-Schwellwert zu verhindern.
        # (Analoges Totband wie bei der Zieltemperatur, aber auf der Diff-Seite.)
        elif was_cooling and outdoor <= indoor - max(0.0, self.cool_min_diff - hyst) and indoor > cool_off_temp:
            action = "cool"
        # War am Kühlen und hat den unteren Schaltpunkt erreicht -> stoppen.
        elif was_cooling and indoor <= cool_off_temp:
            action = "off"
        else:
            action = "idle"

        # Update the human-readable status every cycle (even if unchanged).
        if action == "cool":
            self.summer_status = "Kühlt (Nachtkühlung)"
        elif action == "off":
            self.summer_status = "Anlage aus (Hitze/Ziel erreicht)"
        else:
            self.summer_status = "Bereit (Schutzlüftung, wartet auf Kühlbedingungen)"

        if action == self._summer_last_action:
            return  # nothing changed, don't re-write

        # --- Mindest-Laufzeit-Schutz ---
        # Nach einem Schaltvorgang mindestens `min_runtime` Minuten warten,
        # bevor erneut geschaltet wird.
        if self._last_switch_ts is not None:
            elapsed_min = (datetime.now(timezone.utc) - self._last_switch_ts).total_seconds() / 60.0
            if elapsed_min < self.min_runtime:
                rest = self.min_runtime - elapsed_min
                # Status zeigt den TATSÄCHLICHEN Gerätezustand (letzten geschriebenen
                # Zustand), nicht den gewünschten – verhindert irreführende Anzeige.
                actual_status = (
                    "Kühlt (Nachtkühlung)"
                    if self._summer_last_action == "cool"
                    else "Bereit (Schutzlüftung, wartet auf Kühlbedingungen)"
                )
                self.summer_status = actual_status + f" – wartet {rest:.0f} min"
                return

        try:
            if action == "cool":
                _LOGGER.info(
                    "Sommermodus: Nachtkühlung an (außen %.1f°C < innen %.1f°C)",
                    outdoor, indoor,
                )
                await self._write_register(self._addr("betriebsart"), 1)  # Manuell
                await self._write_register(
                    self._addr("lueftungsstufe_write"), SUMMER_COOL_STUFE
                )
            elif action == "off":
                _LOGGER.info(
                    "Sommermodus: Anlage aus (außen %.1f°C >= innen %.1f°C oder Ziel erreicht)",
                    outdoor, indoor,
                )
                await self._write_register(self._addr("betriebsart"), 0)  # Aus
            elif action == "idle":
                # Neutral zone: not actively cooling, but keep a minimal air
                # exchange (Schutzlüftung) so humidity/CO2 don't build up.
                _LOGGER.info(
                    "Sommermodus: Bereit/Schutzlüftung (außen %.1f°C, innen %.1f°C)",
                    outdoor, indoor,
                )
                await self._write_register(self._addr("betriebsart"), 1)  # Manuell
                await self._write_register(
                    self._addr("lueftungsstufe_write"), SUMMER_IDLE_STUFE
                )

            self._summer_last_action = action
            self._last_switch_ts = datetime.now(timezone.utc)
        except Exception as err:
            _LOGGER.error("Sommermodus: Fehler beim Schreiben: %s", err)

    @staticmethod
    def _int16_to_float(value: int, scale: float = 1.0) -> float:
        """Convert 16-bit signed integer to float with scaling."""
        # Handle signed 16-bit
        if value > 32767:
            value = value - 65536
        return round(value * scale, 2)

    async def async_set_lueftungsstufe(self, stufe: int):
        """Set ventilation level (0-4).

        IMPORTANT: The Maico WS 300 Flat reads the stage from register 650
        but WRITES it to register 554. Register 650 is read-only — writing
        to it returns "Illegal Data Address". The device must be in
        Betriebsart "Manuell" for the stage to take effect.
        """
        try:
            stufe = max(0, min(4, stufe))
            result = await self._write_register(
                self._addr("lueftungsstufe_write"), stufe
            )
            
            if result.isError():
                raise UpdateFailed(f"Error setting Lüftungsstufe: {result}")
            
            await self.async_request_refresh()
            
        except Exception as err:
            _LOGGER.error(f"Error setting Lüftungsstufe: {err}")
            raise

    async def async_set_betriebsart(self, mode: int):
        """Set operation mode (Betriebsart)."""
        try:
            mode = max(0, min(5, mode))
            result = await self._write_register(self._addr("betriebsart"), mode)
            
            if result.isError():
                raise UpdateFailed(f"Error setting Betriebsart: {result}")
            
            await self.async_request_refresh()
            
        except Exception as err:
            _LOGGER.error(f"Error setting Betriebsart: {err}")
            raise

    async def async_write_raw(self, register_key: str, value: int):
        """Write a raw integer value to a named register.

        Used by the extended control entities (Stoßlüftung, T-Raum max., ...).
        The caller is responsible for passing an already-scaled raw value.
        """
        try:
            result = await self._write_register(self._addr(register_key), value)
            if result.isError():
                raise UpdateFailed(f"Error writing {register_key}: {result}")
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error writing %s: %s", register_key, err)
            raise

    async def async_trigger_stosslueftung(self):
        """Trigger boost ventilation (551 = 1).

        Also records how long the boost should run (from register 153, the
        configured duration) so the summer logic can stand down meanwhile.
        """
        # Determine the configured duration (minutes); fall back to 30.
        minutes = 30
        if self.data is not None:
            d = self.data.get("dauer_lueftungsstufe")
            if isinstance(d, (int, float)) and d > 0:
                minutes = int(d)
        self._boost_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        await self.async_write_raw("stosslueftung", 1)

    async def async_set_temp_register(self, register_key: str, celsius: float):
        """Write a temperature setpoint, scaling per the profile.

        The profile's ``scale`` is the READ factor (displayed = raw * scale).
        Writing is the inverse: raw = displayed / scale. E.g. scale 0.1 ->
        23.0 °C becomes raw 230; scale 1.0 -> 14.0 °C becomes raw 14.
        """
        scale = self._scale(register_key)
        raw = int(round(celsius / scale)) if scale else int(round(celsius))
        await self.async_write_raw(register_key, raw)

    async def async_shutdown(self):
        """Shutdown coordinator."""
        # client.close() is synchronous in pymodbus 3.x (no await!)
        try:
            self.client.close()
        except Exception as err:
            _LOGGER.debug(f"Error closing client: {err}")
