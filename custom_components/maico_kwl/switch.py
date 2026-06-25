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
from .profiles import build_unique_id

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

    # PushPull (Welt C) hat keine Nachtkühlung/Bypass/Temperaturen –
    # diese Plattform legt dort keine Entitäten an.
    from .profiles import PLATFORM_PUSHPULL
    if coordinator.profile.get("key") == PLATFORM_PUSHPULL:
        return

    async_add_entities([
        MaicoKWLSummerModeSwitch(coordinator, config_entry),
    ])


class MaicoKWLSummerModeSwitch(SwitchEntity, RestoreEntity):
    """Enable/disable the automatic summer night-cooling logic."""

    _attr_name = "Sommermodus"
    _attr_has_entity_name = True
    _attr_icon = "mdi:weather-night"

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        """Initialize the switch."""
        self.coordinator = coordinator
        self._config_entry = config_entry
        legacy = config_entry.data.get("legacy_ids", False)
        model = config_entry.data.get("model", DEVICE_MODEL)
        self._attr_unique_id = build_unique_id(legacy, config_entry.entry_id, "sommermodus")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": model,
            "manufacturer": "Maico",
            "model": model,
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

