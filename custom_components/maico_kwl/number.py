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
)
from .coordinator import MaicoKWLCoordinator

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
    async_add_entities([
        MaicoKWLCoolMinDiffNumber(coordinator, config_entry),
        MaicoKWLCoolTargetNumber(coordinator, config_entry),
    ])


class _MaicoKWLBaseNumber(NumberEntity, RestoreEntity):
    """Common plumbing for the threshold numbers."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        self.coordinator = coordinator
        self._config_entry = config_entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": DEVICE_MODEL,
            "manufacturer": "Maico",
            "model": "WS 300 Flat",
        }


class MaicoKWLCoolMinDiffNumber(_MaicoKWLBaseNumber):
    """Minimum outdoor/indoor difference to start night cooling."""

    _attr_name = "Kühlung Mindest-Differenz"
    _attr_unique_id = "maico_kwl_cool_min_diff"
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
    _attr_unique_id = "maico_kwl_cool_target"
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
