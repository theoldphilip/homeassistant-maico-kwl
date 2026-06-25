"""Sensor entities for Maico KWL."""
import logging
from typing import Any
from datetime import datetime, timezone

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, PERCENTAGE, UnitOfPower, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    DEVICE_MODEL,
    BETRIEBSART_MAPPING,
    LUEFTUNGSSTUFE_MAPPING,
    BYPASS_STATUS_MAPPING,
    SCHALTER_STATUS_MAPPING,
    SPI_WH_PER_M3,
    STANDBY_POWER_W,
)
from .coordinator import MaicoKWLCoordinator
from .profiles import build_unique_id

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

    from .profiles import PLATFORM_PUSHPULL
    if coordinator.profile.get("key") == PLATFORM_PUSHPULL:
        async_add_entities(
            _build_pushpull_sensors(coordinator, config_entry),
            update_before_add=True,
        )
        return

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

        # Stromverbrauch (Schätzung aus SPI-Wert)
        MaicoKWLPowerSensor(coordinator, config_entry),
        MaicoKWLEnergySensor(coordinator, config_entry),

        # Erweiterte Sensoren (offizielle Parameterliste)
        MaicoKWLTemperatureSensor(coordinator, config_entry, "temp_raum", "Temperatur - Raum (Gerätefühler)"),
        MaicoKWLOperatingHoursSensor(coordinator, config_entry, "bh_feuchteschutz", "Betriebsstunden Feuchteschutz"),
        MaicoKWLOperatingHoursSensor(coordinator, config_entry, "bh_reduziert", "Betriebsstunden Reduziert"),
        MaicoKWLOperatingHoursSensor(coordinator, config_entry, "bh_nenn", "Betriebsstunden Nennlüftung"),
        MaicoKWLOperatingHoursSensor(coordinator, config_entry, "bh_intensiv", "Betriebsstunden Intensiv"),
        MaicoKWLOperatingHoursSensor(coordinator, config_entry, "bh_gesamt", "Betriebsstunden Gesamt"),
        MaicoKWLDiagnosticSensor(coordinator, config_entry, "fehler", "Fehler", ("fehler_1", "fehler_2")),
        MaicoKWLDiagnosticSensor(coordinator, config_entry, "hinweis", "Hinweis", ("hinweis_1", "hinweis_2")),
    ]

    # Optionale externe Sensoren – nur anlegen, wenn das Gerät sie hat
    # (Feature-Erkennung). Bei dauerhaftem 0-Wert standardmäßig deaktiviert.
    OPTIONAL_SENSORS = [
        ("co2_sensor_2", "CO₂ Sensor 2", SensorDeviceClass.CO2, "ppm"),
        ("co2_sensor_3", "CO₂ Sensor 3", SensorDeviceClass.CO2, "ppm"),
        ("co2_sensor_4", "CO₂ Sensor 4", SensorDeviceClass.CO2, "ppm"),
        ("voc_sensor_1", "VOC Sensor 1", None, "ppb"),
        ("voc_sensor_2", "VOC Sensor 2", None, "ppb"),
        ("rf_sensor_1", "Luftfeuchte Sensor 1 (extern)", SensorDeviceClass.HUMIDITY, PERCENTAGE),
        ("rf_sensor_2", "Luftfeuchte Sensor 2 (extern)", SensorDeviceClass.HUMIDITY, PERCENTAGE),
        ("rf_sensor_3", "Luftfeuchte Sensor 3 (extern)", SensorDeviceClass.HUMIDITY, PERCENTAGE),
        ("rf_sensor_4", "Luftfeuchte Sensor 4 (extern)", SensorDeviceClass.HUMIDITY, PERCENTAGE),
    ]
    for key, name, devclass, unit in OPTIONAL_SENSORS:
        if key in coordinator.registers and coordinator.feature_present(key):
            entities.append(
                MaicoKWLOptionalSensor(coordinator, config_entry, key, name, devclass, unit)
            )

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
        legacy = config_entry.data.get("legacy_ids", False)
        model = config_entry.data.get("model", DEVICE_MODEL)
        self._attr_unique_id = build_unique_id(legacy, config_entry.entry_id, data_key)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": model,
            "manufacturer": "Maico",
            "model": model,
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


class MaicoKWLPowerSensor(MaicoKWLBaseSensor):
    """Estimated current power draw (W), derived from the SPI value.

    Power (W) = mean volume flow (m³/h) * SPI (Wh/m³).
    This is an estimate based on the manufacturer's SPI value
    (0.2 Wh/m³ per DIN EN 13141-7 A7), not a real measurement.
    """

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        """Initialize power sensor."""
        super().__init__(coordinator, config_entry, "leistung", "Leistung (geschätzt)")

    @property
    def native_value(self) -> float | None:
        """Estimate current power from the mean volume flow."""
        if self.coordinator.data is None:
            return None

        vz = self.coordinator.data.get("volumenstrom_zuluft")
        va = self.coordinator.data.get("volumenstrom_abluft")
        flows = [v for v in (vz, va) if isinstance(v, (int, float))]

        # No airflow -> unit effectively off -> standby power.
        if not flows or max(flows) <= 0:
            return round(STANDBY_POWER_W, 1)

        mean_flow = sum(flows) / len(flows)
        power = mean_flow * SPI_WH_PER_M3
        # Never report below standby.
        return round(max(power, STANDBY_POWER_W), 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose calculation basis."""
        return {
            "spi_wh_pro_m3": SPI_WH_PER_M3,
            "hinweis": "Schätzung aus Volumenstrom × SPI-Wert (laut Hersteller-Datenblatt)",
        }


class MaicoKWLEnergySensor(MaicoKWLBaseSensor, RestoreEntity):
    """Accumulated energy (kWh), integrated from the estimated power.

    This is a total_increasing counter suitable for the HA Energy
    dashboard. It integrates the estimated power over real elapsed time
    between updates and survives restarts via RestoreEntity.
    """

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 3

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        """Initialize energy sensor."""
        super().__init__(coordinator, config_entry, "energie", "Energieverbrauch (geschätzt)")
        self._total_kwh: float = 0.0
        self._last_ts: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the accumulated value across restarts."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state not in (None, "unknown", "unavailable"):
            try:
                self._total_kwh = float(last.state)
            except (ValueError, TypeError):
                self._total_kwh = 0.0
        # Start integrating from now (don't count downtime).
        self._last_ts = datetime.now(timezone.utc)

    def _current_power_w(self) -> float:
        """Same estimation as the power sensor."""
        if self.coordinator.data is None:
            return STANDBY_POWER_W
        vz = self.coordinator.data.get("volumenstrom_zuluft")
        va = self.coordinator.data.get("volumenstrom_abluft")
        flows = [v for v in (vz, va) if isinstance(v, (int, float))]
        if not flows or max(flows) <= 0:
            return STANDBY_POWER_W
        return max(sum(flows) / len(flows) * SPI_WH_PER_M3, STANDBY_POWER_W)

    @property
    def native_value(self) -> float:
        """Integrate power over elapsed time and return total kWh."""
        now = datetime.now(timezone.utc)
        if self._last_ts is not None:
            elapsed_h = (now - self._last_ts).total_seconds() / 3600.0
            # Guard against clock jumps / absurd gaps (> 1 h between polls).
            if 0 < elapsed_h <= 1:
                self._total_kwh += self._current_power_w() * elapsed_h / 1000.0
        self._last_ts = now
        return round(self._total_kwh, 4)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose calculation basis."""
        return {
            "spi_wh_pro_m3": SPI_WH_PER_M3,
            "hinweis": "Aufsummierte Schätzung; kein geeichter Zähler",
        }


class MaicoKWLOperatingHoursSensor(MaicoKWLBaseSensor):
    """Operating hours counter (32-bit, read from two registers)."""

    _attr_native_unit_of_measurement = "h"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:timer-outline"
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator, config_entry, data_key, name):
        super().__init__(coordinator, config_entry, data_key, name)
        self._data_key = data_key

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._data_key)


class MaicoKWLDiagnosticSensor(MaicoKWLBaseSensor):
    """Error/notice bitfield sensor.

    Shows "OK" when no bits are set, otherwise the raw bitfield value(s).
    The raw values are exposed as attributes for decoding.
    """

    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator, config_entry, data_key, name, source_keys):
        super().__init__(coordinator, config_entry, data_key, name)
        self._source_keys = source_keys

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        vals = [self.coordinator.data.get(k, 0) or 0 for k in self._source_keys]
        if all(v == 0 for v in vals):
            return "OK"
        # Active bits present -> report as combined hex for reference
        return "Aktiv"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self.coordinator.data is None:
            return {}
        attrs = {}
        for k in self._source_keys:
            attrs[k] = self.coordinator.data.get(k, 0)
        return attrs


class MaicoKWLOptionalSensor(MaicoKWLBaseSensor):
    """An optional external sensor (CO2/VOC/humidity), feature-detected.

    Only instantiated when the device exposes the register. Disabled by
    default in the entity registry, so a persistently-zero sensor doesn't
    clutter the dashboard but can be enabled by the user if wanted.
    """

    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, config_entry, data_key, name, device_class, unit):
        super().__init__(coordinator, config_entry, data_key, name)
        self._data_key = data_key
        if device_class is not None:
            self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._data_key)


# ---------------------------------------------------------------------------
# PushPull (Welt C) — eigene schlanke Sensoren
# ---------------------------------------------------------------------------

PUSHPULL_BETRIEBSART = {0: "Wärmerückgewinnung", 1: "Querlüftung"}
PUSHPULL_STUFE = {
    0: "Aus", 1: "Stufe 1", 2: "Stufe 2", 3: "Stufe 3", 4: "Stufe 4", 5: "Intensiv",
}


def _build_pushpull_sensors(coordinator, config_entry):
    """Build the sensor entities for a PushPull device."""
    return [
        MaicoKWLPushPullMappedSensor(
            coordinator, config_entry, "betriebsart", "Betriebsart",
            PUSHPULL_BETRIEBSART, "mdi:swap-horizontal"),
        MaicoKWLPushPullMappedSensor(
            coordinator, config_entry, "lueftungsstufe", "Lüftungsstufe",
            PUSHPULL_STUFE, "mdi:fan"),
        MaicoKWLOptionalSensor(
            coordinator, config_entry, "humidity_fmr",
            "Luftfeuchte", SensorDeviceClass.HUMIDITY, PERCENTAGE),
        MaicoKWLFilterDaysSensor(
            coordinator, config_entry, "filter_restlaufzeit", "Filterwechsel"),
        MaicoKWLOperatingHoursSensor(
            coordinator, config_entry, "bh_gesamt", "Betriebsstunden Gesamt"),
    ]


class MaicoKWLPushPullMappedSensor(MaicoKWLBaseSensor):
    """A PushPull sensor that maps a raw value to a German text label."""

    def __init__(self, coordinator, config_entry, data_key, name, mapping, icon):
        super().__init__(coordinator, config_entry, data_key, name)
        self._data_key = data_key
        self._mapping = mapping
        self._attr_icon = icon

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._data_key)
        if raw is None:
            return None
        return self._mapping.get(raw, f"Unbekannt ({raw})")
