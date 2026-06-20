"""Data coordinator for Maico KWL."""
import logging
from datetime import timedelta
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
    SUMMER_DAY_HYSTERESIS,
    SUMMER_COOL_STUFE,
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

    def __init__(self, hass: HomeAssistant, host: str, port: int, unit_id: int, scan_interval: int):
        """Initialize the coordinator."""
        self.host = host
        self.port = port
        self.unit_id = unit_id
        # timeout=5 prevents the event loop from hanging on a stalled connect.
        # pymodbus handles automatic reconnects internally after the first connect.
        self.client = AsyncModbusTcpClient(host=host, port=port, timeout=5)

        # --- Sommermodus state (loaded/persisted by the platforms) ---
        self.summer_mode: bool = False
        self.cool_min_diff: float = DEFAULT_COOL_MIN_DIFF
        self.cool_target: float = DEFAULT_COOL_TARGET
        # Remembers what the automation last commanded, so we don't spam the
        # device with identical writes on every poll.
        self._summer_last_action: str | None = None
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
            return self.client.connected
        except Exception as err:
            _LOGGER.error(f"Initial connection to {self.host} failed: {err}")
            return False

    async def _read_registers(self, address: int, count: int):
        """Read holding registers (pymodbus API-compatible)."""
        kwargs = {"address": address, "count": count, _SLAVE_KWARG: self.unit_id}
        return await self.client.read_holding_registers(**kwargs)

    async def _write_register(self, address: int, value: int):
        """Write a single holding register (pymodbus API-compatible)."""
        kwargs = {"address": address, "value": value, _SLAVE_KWARG: self.unit_id}
        return await self.client.write_register(**kwargs)

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Modbus device."""
        # Do NOT manually call connect() here on every poll — pymodbus reconnects
        # automatically. Manually reconnecting collides with that and can spin
        # the event loop. If not connected, report a failed update cleanly.
        if not self.client.connected:
            raise UpdateFailed("Modbus client not connected")

        try:
            data = {}
            
            # Read all registers in one batch where possible
            # Betriebsart
            result = await self._read_registers(MODBUS_REGISTERS["betriebsart"], 1)
            if not result.isError():
                data["betriebsart"] = result.registers[0]
            
            # Lüftungsstufe + Drehzahlen + Volumenströme (650-654)
            result = await self._read_registers(MODBUS_REGISTERS["lueftungsstufe"], 5)
            if not result.isError():
                data["lueftungsstufe"] = result.registers[0]
                data["drehzahl_zuluft"] = result.registers[1]
                data["drehzahl_abluft"] = result.registers[2]
                data["volumenstrom_zuluft"] = result.registers[3]
                data["volumenstrom_abluft"] = result.registers[4]
            
            # Filter Restlaufzeiten (655-657)
            result = await self._read_registers(MODBUS_REGISTERS["filter_restlaufzeit_zuluft"], 3)
            if not result.isError():
                data["filter_restlaufzeit_zuluft"] = result.registers[0]
                data["filter_restlaufzeit_aussenluft"] = result.registers[1]
                data["filter_restlaufzeit_abluft"] = result.registers[2]
            
            # Temperaturen (703-706) - int16 mit scale 0.1
            result = await self._read_registers(MODBUS_REGISTERS["temp_aussenluft"], 4)
            if not result.isError():
                # Signed 16-bit conversion
                data["temp_aussenluft"] = self._int16_to_float(result.registers[0], 0.1)
                data["temp_zuluft"] = self._int16_to_float(result.registers[1], 0.1)
                data["temp_abluft"] = self._int16_to_float(result.registers[2], 0.1)
                data["temp_fortluft"] = self._int16_to_float(result.registers[3], 0.1)
            
            # Humidity + CO2 (750, 755)
            result = await self._read_registers(MODBUS_REGISTERS["humidity_abluft"], 1)
            if not result.isError():
                data["humidity_abluft"] = result.registers[0]
            
            result = await self._read_registers(MODBUS_REGISTERS["co2_abluft"], 1)
            if not result.isError():
                data["co2_abluft"] = result.registers[0]
            
            # Schaltzustände (800-802)
            result = await self._read_registers(MODBUS_REGISTERS["schalter_zuluft"], 3)
            if not result.isError():
                data["schalter_zuluft"] = bool(result.registers[0])
                data["schalter_abluft"] = bool(result.registers[1])
                data["schalter_bypass"] = bool(result.registers[2])

            # --- Sommermodus / Nachtkühlung ---
            # Evaluated after a successful read, using the fresh temperatures.
            await self._evaluate_summer_mode(data)

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

        t_aul = data.get("temp_aussenluft")  # outdoor
        t_ab = data.get("temp_abluft")       # indoor (extract air)
        if not isinstance(t_aul, (int, float)) or not isinstance(t_ab, (int, float)):
            self.summer_status = "Keine Temperaturdaten"
            return  # no valid temps this cycle

        indoor = t_ab
        outdoor = t_aul

        action: str  # one of: "cool", "off", "idle"
        if outdoor <= indoor - self.cool_min_diff and indoor > self.cool_target:
            action = "cool"
        elif outdoor >= indoor + SUMMER_DAY_HYSTERESIS:
            action = "off"
        else:
            # Neutral zone. If we were cooling and reached the target, stop.
            if self._summer_last_action == "cool" and indoor <= self.cool_target:
                action = "off"
            else:
                action = "idle"

        # Update the human-readable status every cycle (even if unchanged).
        if action == "cool":
            self.summer_status = "Kühlt (Nachtkühlung)"
        elif action == "off":
            self.summer_status = "Anlage aus (Hitze/Ziel erreicht)"
        else:
            self.summer_status = "Bereit (wartet auf Kühlbedingungen)"

        if action == self._summer_last_action:
            return  # nothing changed, don't re-write

        try:
            if action == "cool":
                _LOGGER.info(
                    "Sommermodus: Nachtkühlung an (außen %.1f°C < innen %.1f°C)",
                    outdoor, indoor,
                )
                await self._write_register(MODBUS_REGISTERS["betriebsart"], 1)  # Manuell
                await self._write_register(
                    MODBUS_REGISTERS["lueftungsstufe_write"], SUMMER_COOL_STUFE
                )
            elif action == "off":
                _LOGGER.info(
                    "Sommermodus: Anlage aus (außen %.1f°C >= innen %.1f°C oder Ziel erreicht)",
                    outdoor, indoor,
                )
                await self._write_register(MODBUS_REGISTERS["betriebsart"], 0)  # Aus
            # "idle" -> do nothing on the device

            self._summer_last_action = action
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
                MODBUS_REGISTERS["lueftungsstufe_write"], stufe
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
            result = await self._write_register(MODBUS_REGISTERS["betriebsart"], mode)
            
            if result.isError():
                raise UpdateFailed(f"Error setting Betriebsart: {result}")
            
            await self.async_request_refresh()
            
        except Exception as err:
            _LOGGER.error(f"Error setting Betriebsart: {err}")
            raise

    async def async_shutdown(self):
        """Shutdown coordinator."""
        # client.close() is synchronous in pymodbus 3.x (no await!)
        try:
            self.client.close()
        except Exception as err:
            _LOGGER.debug(f"Error closing client: {err}")
