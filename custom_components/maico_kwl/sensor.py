"""Sensor entities for Maico KWL."""
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    DEVICE_MODEL,
    BETRIEBSART_MAPPING,
    LUEFTUNGSSTUFE_MAPPING,
    BYPASS_STATUS_MAPPING,
    SCHALTER_STATUS_MAPPING,
)
from .coordinator import MaicoKWLCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform."""
    coordinator: MaicoKWLCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    entities = [
        # Temperaturen
        MaicoKWLTemperatureSensor(coordinator, config_entry, "temp_aussenluft", "Temperatur - Frischluft (von draußen)"),
        MaicoKWLTemperatureSensor(coordinator, config_entry, "temp_zuluft", "Temperatur - Zuluft (in die Räume)"),
        MaicoKWLTemperatureSensor(coordinator, config_entry, "temp_abluft", "Temperatur - Raumluft (aus den Räumen)"),
        MaicoKWLTemperatureSensor(coordinator, config_entry, "temp_fortluft", "Temperatur - Abluft (nach draußen)"),
        
        # Drehzahlen
        MaicoKWLRPMSensor(coordinator, config_entry, "drehzahl_zuluft", "Drehzahl Zuluft (in die Räume)"),
        MaicoKWLRPMSensor(coordinator, config_entry, "drehzahl_abluft", "Drehzahl Raumluft (aus den Räumen)"),
        
        # Volumenströme
        MaicoKWLVolumeSensor(coordinator, config_entry, "volumenstrom_zuluft", "Volumenstrom Zuluft (in die Räume)"),
        MaicoKWLVolumeSensor(coordinator, config_entry, "volumenstrom_abluft", "Volumenstrom Raumluft (aus den Räumen)"),
        
        # Filter Restlaufzeit (nur Zuluftfilter)
        MaicoKWLFilterDaysSensor(coordinator, config_entry, "filter_restlaufzeit_zuluft", "Filterwechsel"),
        
        # Luftqualität
        MaicoKWLHumiditySensor(coordinator, config_entry),
        MaicoKWLCO2Sensor(coordinator, config_entry),
        
        # Betriebsmodi mit Mapping
        MaicoKWLBetriebsartSensor(coordinator, config_entry),
        MaicoKWLLueftungsstufeSensor(coordinator, config_entry),
        
        # Schaltzustände
        MaicoKWLSwitchStatusSensor(coordinator, config_entry, "schalter_zuluft", "Schalter Zuluft (in die Räume)", SCHALTER_STATUS_MAPPING),
        MaicoKWLSwitchStatusSensor(coordinator, config_entry, "schalter_abluft", "Schalter Raumluft (aus den Räumen)", SCHALTER_STATUS_MAPPING),
        MaicoKWLSwitchStatusSensor(coordinator, config_entry, "schalter_bypass", "Bypass Status", BYPASS_STATUS_MAPPING),
        
        # Wärmerückgewinnung (berechnet)
        MaicoKWLWaermerueckgewinnungSensor(coordinator, config_entry),

        # Sommermodus-Status
        MaicoKWLSummerStatusSensor(coordinator, config_entry),
    ]

    async_add_entities(entities, update_before_add=True)


class MaicoKWLBaseSensor(SensorEntity):
    """Base class for Maico KWL sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MaicoKWLCoordinator,
        config_entry: ConfigEntry,
        data_key: str,
        display_name: str,
    ):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._data_key = data_key
        self._attr_name = display_name
        self._attr_unique_id = f"maico_kwl_{data_key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": DEVICE_MODEL,
            "manufacturer": "Maico",
            "model": "WS 300 Flat",
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class MaicoKWLTemperatureSensor(MaicoKWLBaseSensor):
    """Temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._data_key)


class MaicoKWLRPMSensor(MaicoKWLBaseSensor):
    """RPM sensor."""

    _attr_native_unit_of_measurement = "U/min"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the state."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._data_key)


class MaicoKWLVolumeSensor(MaicoKWLBaseSensor):
    """Volume flow sensor."""

    _attr_native_unit_of_measurement = "m³/h"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the state."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._data_key)


class MaicoKWLFilterDaysSensor(MaicoKWLBaseSensor):
    """Filter remaining days sensor."""

    _attr_native_unit_of_measurement = "d"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.DURATION

    @property
    def native_value(self) -> int | None:
        """Return the state."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._data_key)


class MaicoKWLHumiditySensor(MaicoKWLBaseSensor):
    """Humidity sensor."""

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        """Initialize humidity sensor."""
        super().__init__(coordinator, config_entry, "humidity_abluft", "Luftfeuchte Raumluft (aus den Räumen)")
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the state."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._data_key)


class MaicoKWLCO2Sensor(MaicoKWLBaseSensor):
    """CO2 sensor."""

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        """Initialize CO2 sensor."""
        super().__init__(coordinator, config_entry, "co2_abluft", "CO2 Raumluft (aus den Räumen)")
        self._attr_native_unit_of_measurement = "ppm"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the state."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._data_key)


class MaicoKWLBetriebsartSensor(MaicoKWLBaseSensor):
    """Operation mode sensor with mapping."""

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        """Initialize operation mode sensor."""
        super().__init__(coordinator, config_entry, "betriebsart", "Betriebsart")

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        if self.coordinator.data is None:
            return None
        
        mode = self.coordinator.data.get(self._data_key)
        if mode is None:
            return None
        
        return BETRIEBSART_MAPPING.get(mode, f"Unbekannt ({mode})")


class MaicoKWLLueftungsstufeSensor(MaicoKWLBaseSensor):
    """Ventilation level sensor with mapping."""

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        """Initialize ventilation level sensor."""
        super().__init__(coordinator, config_entry, "lueftungsstufe", "Lüftungsstufe")

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        if self.coordinator.data is None:
            return None
        
        stufe = self.coordinator.data.get(self._data_key)
        if stufe is None:
            return None
        
        return LUEFTUNGSSTUFE_MAPPING.get(stufe, f"Unbekannt ({stufe})")


class MaicoKWLSwitchStatusSensor(MaicoKWLBaseSensor):
    """Switch status sensor with mapping."""

    def __init__(
        self,
        coordinator: MaicoKWLCoordinator,
        config_entry: ConfigEntry,
        data_key: str,
        display_name: str,
        mapping: dict,
    ):
        """Initialize switch status sensor."""
        super().__init__(coordinator, config_entry, data_key, display_name)
        self._mapping = mapping

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        if self.coordinator.data is None:
            return None
        
        value = self.coordinator.data.get(self._data_key)
        if value is None:
            return None
        
        # Handle both int and bool
        if isinstance(value, bool):
            value = 1 if value else 0
        
        return self._mapping.get(value, f"Unbekannt ({value})")


class MaicoKWLWaermerueckgewinnungSensor(MaicoKWLBaseSensor):
    """Heat recovery efficiency sensor (calculated).

    Efficiency = (T_Zuluft - T_Außenluft) / (T_Abluft - T_Außenluft) * 100

    This ratio is only physically meaningful when there is a reasonable
    temperature spread between extract air and outdoor air. When the spread
    is small (e.g. mild weather, Abluft ≈ Außenluft), the formula becomes
    numerically unstable and would jump to extreme values. In that case we
    return ``None`` (state "unbekannt") instead of a misleading number.
    """

    # Minimum spread (°C) between extract and outdoor air for a valid result.
    MIN_SPREAD = 3.0

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        """Initialize WRG sensor."""
        super().__init__(coordinator, config_entry, "wrg_efficiency", "Wärmerückgewinnung")
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0

    @property
    def native_value(self) -> float | None:
        """Calculate heat recovery efficiency robustly."""
        if self.coordinator.data is None:
            return None

        t_zu = self.coordinator.data.get("temp_zuluft")
        t_aul = self.coordinator.data.get("temp_aussenluft")
        t_ab = self.coordinator.data.get("temp_abluft")

        # All three temperatures must be present and numeric
        if any(not isinstance(v, (int, float)) for v in (t_zu, t_aul, t_ab)):
            return None

        spread = t_ab - t_aul

        # Too small a spread -> result not meaningful, report unknown
        if abs(spread) < self.MIN_SPREAD:
            return None

        try:
            wrg = (t_zu - t_aul) / spread * 100
        except ZeroDivisionError:
            return None

        # A plausible efficiency lies within 0..100 %. Values clearly outside
        # this band indicate an unusual/transition state -> report unknown
        # rather than clamping to a misleading 0 or 100.
        if wrg < -5 or wrg > 105:
            return None

        # Minor overshoot from rounding/sensor noise is clamped to 0..100.
        return round(max(0.0, min(100.0, wrg)))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the inputs so the value can be understood/debugged."""
        if self.coordinator.data is None:
            return {}
        t_aul = self.coordinator.data.get("temp_aussenluft")
        t_ab = self.coordinator.data.get("temp_abluft")
        spread = None
        if isinstance(t_aul, (int, float)) and isinstance(t_ab, (int, float)):
            spread = round(t_ab - t_aul, 1)
        return {
            "temp_zuluft": self.coordinator.data.get("temp_zuluft"),
            "temp_aussenluft": t_aul,
            "temp_abluft": t_ab,
            "spread_abluft_aussenluft": spread,
            "min_spread_fuer_berechnung": self.MIN_SPREAD,
        }


class MaicoKWLSummerStatusSensor(MaicoKWLBaseSensor):
    """Shows the current state of the summer night-cooling logic."""

    _attr_icon = "mdi:weather-night"

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        """Initialize summer status sensor."""
        super().__init__(coordinator, config_entry, "sommermodus_status", "Sommermodus Status")

    @property
    def native_value(self) -> str | None:
        """Return the human-readable summer mode status."""
        return getattr(self.coordinator, "summer_status", None)
