"""Number entities for Maico KWL — Sommermodus thresholds."""
import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    DEVICE_MODEL,
    DEFAULT_COOL_MIN_DIFF,
    DEFAULT_COOL_TARGET,
    DEFAULT_COOL_HYSTERESIS,
    DEFAULT_MIN_RUNTIME,
)
from .coordinator import MaicoKWLCoordinator
from .profiles import build_unique_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number platform."""
    coordinator: MaicoKWLCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    # PushPull (Welt C) hat keine Nachtkühlung/Bypass/Temperaturen –
    # diese Plattform legt dort keine Entitäten an.
    from .profiles import PLATFORM_PUSHPULL
    if coordinator.profile.get("key") == PLATFORM_PUSHPULL:
        return

    async_add_entities([
        MaicoKWLCoolMinDiffNumber(coordinator, config_entry),
        MaicoKWLCoolTargetNumber(coordinator, config_entry),
        MaicoKWLCoolHysteresisNumber(coordinator, config_entry),
        MaicoKWLMinRuntimeNumber(coordinator, config_entry),
        # Geräte-Sollwerte (schreiben direkt ins Gerät)
        MaicoKWLDeviceTempNumber(
            coordinator, config_entry, "t_raum_max",
            "T-Raum max. (Sommer)", "mdi:thermometer-high", 18.0, 30.0),
        MaicoKWLDeviceTempNumber(
            coordinator, config_entry, "t_zuluft_min_kuehlen",
            "T-Zuluft min. (Kühlen)", "mdi:thermometer-low", 8.0, 29.0),
        MaicoKWLBoostDurationNumber(coordinator, config_entry),
    ])


class _MaicoKWLBaseNumber(NumberEntity, RestoreEntity):
    """Common plumbing for the threshold numbers."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _id_key: str | None = None  # subclasses set this for their unique_id

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        self.coordinator = coordinator
        self._config_entry = config_entry
        legacy = config_entry.data.get("legacy_ids", False)
        model = config_entry.data.get("model", DEVICE_MODEL)
        if self._id_key is not None:
            self._attr_unique_id = build_unique_id(legacy, config_entry.entry_id, self._id_key)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": model,
            "manufacturer": "Maico",
            "model": model,
        }


class MaicoKWLCoolMinDiffNumber(_MaicoKWLBaseNumber):
    """Minimum outdoor/indoor difference to start night cooling."""

    _attr_name = "Kühlung Mindest-Differenz"
    _id_key = "cool_min_diff"
    _attr_icon = "mdi:thermometer-minus"
    _attr_native_min_value = 0.5
    _attr_native_max_value = 10.0
    _attr_native_step = 0.5

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            try:
                self.coordinator.cool_min_diff = float(last.state)
            except (ValueError, TypeError):
                self.coordinator.cool_min_diff = DEFAULT_COOL_MIN_DIFF

    @property
    def native_value(self) -> float:
        return self.coordinator.cool_min_diff

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.cool_min_diff = value
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()


class MaicoKWLCoolTargetNumber(_MaicoKWLBaseNumber):
    """Indoor target temperature to cool down to."""

    _attr_name = "Kühlung Zieltemperatur"
    _id_key = "cool_target"
    _attr_icon = "mdi:thermometer-check"
    _attr_native_min_value = 16.0
    _attr_native_max_value = 28.0
    _attr_native_step = 0.5

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            try:
                self.coordinator.cool_target = float(last.state)
            except (ValueError, TypeError):
                self.coordinator.cool_target = DEFAULT_COOL_TARGET

    @property
    def native_value(self) -> float:
        return self.coordinator.cool_target

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.cool_target = value
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()


class MaicoKWLCoolHysteresisNumber(_MaicoKWLBaseNumber):
    """Hysteresis (dead band) around the target temperature, anti-cycling."""

    _attr_name = "Kühlung Hysterese"
    _id_key = "cool_hysteresis"
    _attr_icon = "mdi:arrow-expand-vertical"
    _attr_native_min_value = 0.0
    _attr_native_max_value = 2.0
    _attr_native_step = 0.1

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            try:
                self.coordinator.cool_hysteresis = float(last.state)
            except (ValueError, TypeError):
                self.coordinator.cool_hysteresis = DEFAULT_COOL_HYSTERESIS

    @property
    def native_value(self) -> float:
        return self.coordinator.cool_hysteresis

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.cool_hysteresis = value
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()


class MaicoKWLMinRuntimeNumber(_MaicoKWLBaseNumber):
    """Minimum hold time (minutes) after a switch, anti-cycling."""

    _attr_name = "Kühlung Mindest-Laufzeit"
    _id_key = "min_runtime"
    _attr_icon = "mdi:timer-lock-outline"
    _attr_native_unit_of_measurement = "min"
    _attr_native_min_value = 5
    _attr_native_max_value = 15
    _attr_native_step = 1

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            try:
                self.coordinator.min_runtime = int(float(last.state))
            except (ValueError, TypeError):
                self.coordinator.min_runtime = DEFAULT_MIN_RUNTIME

    @property
    def native_value(self) -> float:
        return self.coordinator.min_runtime

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.min_runtime = int(value)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()


class MaicoKWLDeviceTempNumber(_MaicoKWLBaseNumber):
    """A temperature setpoint that is written directly to the device.

    Reads the current value from the coordinator data and writes changes
    to the corresponding register (int16 ×10).
    """

    _attr_native_step = 0.5

    def __init__(self, coordinator, config_entry, register_key, name, icon, vmin, vmax):
        super().__init__(coordinator, config_entry)
        self._register_key = register_key
        legacy = config_entry.data.get("legacy_ids", False)
        self._attr_unique_id = build_unique_id(legacy, config_entry.entry_id, register_key)
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_min_value = vmin
        self._attr_native_max_value = vmax

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._register_key)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_set_native_value(self, value: float) -> None:
        # Scaling comes from the profile (single source of truth).
        await self.coordinator.async_set_temp_register(self._register_key, value)

    @property
    def should_poll(self) -> bool:
        return False

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class MaicoKWLBoostDurationNumber(_MaicoKWLBaseNumber):
    """Duration of the boost ventilation (register 153, minutes)."""

    _attr_name = "Dauer Stoßlüftung"
    _id_key = "dauer_lueftungsstufe"
    _attr_icon = "mdi:timer-sand"
    _attr_native_unit_of_measurement = "min"
    _attr_native_min_value = 5
    _attr_native_max_value = 90
    _attr_native_step = 1

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("dauer_lueftungsstufe")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write_raw("dauer_lueftungsstufe", int(value))

    @property
    def should_poll(self) -> bool:
        return False

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
