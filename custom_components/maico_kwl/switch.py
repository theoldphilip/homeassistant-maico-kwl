"""Switch entity for Maico KWL — Sommermodus (night cooling)."""
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, DEVICE_MODEL
from .coordinator import MaicoKWLCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch platform."""
    coordinator: MaicoKWLCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]
    async_add_entities([
        MaicoKWLSummerModeSwitch(coordinator, config_entry),
    ])


class MaicoKWLSummerModeSwitch(SwitchEntity, RestoreEntity):
    """Enable/disable the automatic summer night-cooling logic."""

    _attr_name = "Sommermodus"
    _attr_unique_id = "maico_kwl_sommermodus"
    _attr_has_entity_name = True
    _attr_icon = "mdi:weather-night"

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        """Initialize the switch."""
        self.coordinator = coordinator
        self._config_entry = config_entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": DEVICE_MODEL,
            "manufacturer": "Maico",
            "model": "WS 300 Flat",
        }

    async def async_added_to_hass(self) -> None:
        """Restore the last known state across restarts."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self.coordinator.summer_mode = last_state.state == "on"

    @property
    def is_on(self) -> bool:
        """Return whether summer mode is active."""
        return self.coordinator.summer_mode

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable summer mode."""
        self.coordinator.summer_mode = True
        self.async_write_ha_state()
        # Re-evaluate immediately so the action happens without waiting a poll
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable summer mode."""
        self.coordinator.summer_mode = False
        self.async_write_ha_state()

