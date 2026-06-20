"""Binary sensor for Maico KWL filter alert."""
import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, FILTER_WARNING_DAYS, DEVICE_MODEL
from .coordinator import MaicoKWLCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor platform."""
    coordinator: MaicoKWLCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    # Read configurable filter warning threshold (Tage)
    filter_warning_days = config_entry.data.get("filter_warning_days", FILTER_WARNING_DAYS)

    async_add_entities(
        [
            MaicoKWLFilterAlert(
                coordinator,
                config_entry,
                "filter_restlaufzeit_zuluft",
                "Filterwechsel notwendig",
                filter_warning_days,
            ),
        ],
        update_before_add=True,
    )


class MaicoKWLFilterAlert(BinarySensorEntity):
    """Representation of Maico KWL filter alert."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self, 
        coordinator: MaicoKWLCoordinator, 
        config_entry: ConfigEntry,
        data_key: str,
        display_name: str,
        filter_warning_days: int,
    ):
        """Initialize the binary sensor."""
        self.coordinator = coordinator
        self._config_entry = config_entry
        self._data_key = data_key
        self._filter_warning_days = filter_warning_days
        self._attr_name = display_name
        self._attr_unique_id = f"maico_kwl_{data_key}_alert"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": DEVICE_MODEL,
            "manufacturer": "Maico",
            "model": "WS 300 Flat",
        }

    @property
    def is_on(self) -> bool:
        """Return true if filter needs to be changed."""
        if self.coordinator.data is None:
            return False
        
        restlaufzeit = self.coordinator.data.get(self._data_key, 999)
        # Alert if remaining time is less than threshold
        return restlaufzeit <= self._filter_warning_days

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if self.coordinator.data is None:
            return {}
        
        restlaufzeit = self.coordinator.data.get(self._data_key, 0)
        
        return {
            "restlaufzeit_tage": restlaufzeit,
            "schwellwert_tage": self._filter_warning_days,
        }

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
