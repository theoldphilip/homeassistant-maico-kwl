"""Select entities for Maico KWL."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DEVICE_MODEL
from .coordinator import MaicoKWLCoordinator
from .profiles import ROOM_TEMP_SOURCE_OPTIONS, build_unique_id, room_temp_source_from_value, room_temp_source_to_value


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select platform."""
    coordinator: MaicoKWLCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    from .profiles import PLATFORM_PUSHPULL
    if coordinator.profile.get("key") == PLATFORM_PUSHPULL:
        return

    entities = []
    if "raumtempauswahl" in coordinator.registers and coordinator.feature_present("raumtempauswahl"):
        entities.append(MaicoKWLRoomTempSourceSelect(coordinator, config_entry))

    async_add_entities(entities)


class MaicoKWLRoomTempSourceSelect(SelectEntity):
    """Select the source used by the device for room temperature."""

    _attr_has_entity_name = True
    _attr_name = "Raumtempauswahl"
    _attr_icon = "mdi:thermometer-check"
    _attr_options = ROOM_TEMP_SOURCE_OPTIONS

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self._config_entry = config_entry
        legacy = config_entry.data.get("legacy_ids", False)
        model = config_entry.data.get("model", DEVICE_MODEL)
        self._attr_unique_id = build_unique_id(legacy, config_entry.entry_id, "raumtempauswahl")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": model,
            "manufacturer": "Maico",
            "model": model,
        }

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def current_option(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return room_temp_source_from_value(self.coordinator.data.get("raumtempauswahl"))

    @property
    def should_poll(self) -> bool:
        return False

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_room_temp_source(option)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
