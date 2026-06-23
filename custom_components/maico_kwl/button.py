"""Button entities for Maico KWL."""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DEVICE_MODEL
from .coordinator import MaicoKWLCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button platform."""
    coordinator: MaicoKWLCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]
    async_add_entities([MaicoKWLBoostButton(coordinator, config_entry)])


class MaicoKWLBoostButton(ButtonEntity):
    """Trigger boost ventilation (Stoßlüftung, register 551).

    Runs Intensiv for the duration configured in "Dauer Stoßlüftung"
    (register 153), then the unit returns to its previous state on its own.
    """

    _attr_name = "Stoßlüftung"
    _attr_unique_id = "maico_kwl_stosslueftung"
    _attr_has_entity_name = True
    _attr_icon = "mdi:fan-plus"

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        self.coordinator = coordinator
        self._config_entry = config_entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": DEVICE_MODEL,
            "manufacturer": "Maico",
            "model": "WS 300 Flat",
        }

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_press(self) -> None:
        """Trigger the boost."""
        await self.coordinator.async_trigger_stosslueftung()
