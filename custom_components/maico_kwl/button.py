"""Button entities for Maico KWL."""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DEVICE_MODEL
from .coordinator import MaicoKWLCoordinator
from .profiles import build_unique_id

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

    # PushPull (Welt C) hat keine Nachtkühlung/Bypass/Temperaturen –
    # diese Plattform legt dort keine Entitäten an.
    from .profiles import PLATFORM_PUSHPULL
    if coordinator.profile.get("key") == PLATFORM_PUSHPULL:
        return

    async_add_entities([MaicoKWLBoostButton(coordinator, config_entry)])


class MaicoKWLBoostButton(ButtonEntity):
    """Trigger boost ventilation (Stoßlüftung, register 551).

    Runs Intensiv for the duration configured in "Dauer Stoßlüftung"
    (register 153), then the unit returns to its previous state on its own.
    """

    _attr_name = "Stoßlüftung"
    _attr_has_entity_name = True
    _attr_icon = "mdi:fan-plus"

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        self.coordinator = coordinator
        self._config_entry = config_entry
        legacy = config_entry.data.get("legacy_ids", False)
        model = config_entry.data.get("model", DEVICE_MODEL)
        self._attr_unique_id = build_unique_id(legacy, config_entry.entry_id, "stosslueftung")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": model,
            "manufacturer": "Maico",
            "model": model,
        }

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_press(self) -> None:
        """Trigger the boost."""
        await self.coordinator.async_trigger_stosslueftung()
