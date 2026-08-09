"""Select entity for Maico KWL – Raumtemperaturauswahl (Register 109).

Legt fest, welche Temperaturquelle das Gerät intern für die Bypass-Steuerung
verwendet (Vergleich gegen T-Raum max., Register 302):

  0 = Komfort-BDE   – interner Sensor der Bedieneinheit
  1 = Extern         – externer Sensor (Register 701, Temperatur Raum Ext.)
  2 = Intern         – interner Gerätesensor
  3 = Bus            – Temperaturwert wird per Modbus in Register 707 geschrieben

Nur bei Auswahl „Bus" (3) berücksichtigt das Gerät den über
number.maico_kwl_t_raum_bus gesetzten Wert.
"""
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DEVICE_MODEL
from .coordinator import MaicoKWLCoordinator
from .profiles import build_unique_id, PLATFORM_PUSHPULL

_LOGGER = logging.getLogger(__name__)

# Mapping: Anzeigename → Register-Rohwert
RAUMTEMP_OPTIONS: dict[str, int] = {
    "Komfort-BDE":          0,
    "Extern (Sensor R701)": 1,
    "Intern":               2,
    "Bus (R707)":           3,
}
# Umgekehrtes Mapping: Rohwert → Anzeigename
RAUMTEMP_BY_VALUE: dict[int, str] = {v: k for k, v in RAUMTEMP_OPTIONS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select platform."""
    coordinator: MaicoKWLCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    # PushPull (Welt C) hat kein Register 109 → keine Entity anlegen.
    if coordinator.profile.get("key") == PLATFORM_PUSHPULL:
        return

    async_add_entities([MaicoKWLRaumtempSelect(coordinator, config_entry)])


class MaicoKWLRaumtempSelect(SelectEntity):
    """Auswahl der Raumtemperaturquelle (Register 109).

    Bestimmt, welchen Temperaturwert das Gerät für die interne
    Bypass-Entscheidung heranzieht. Relevant für Setups, in denen ein
    externer oder über Modbus gelieferter Wert als Referenz dienen soll.
    """

    _attr_name = "Raumtemperaturauswahl"
    _attr_has_entity_name = True
    _attr_icon = "mdi:thermometer-lines"
    _attr_options = list(RAUMTEMP_OPTIONS.keys())

    def __init__(
        self,
        coordinator: MaicoKWLCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        self.coordinator = coordinator
        self._config_entry = config_entry
        legacy = config_entry.data.get("legacy_ids", False)
        model = config_entry.data.get("model", DEVICE_MODEL)
        self._attr_unique_id = build_unique_id(
            legacy, config_entry.entry_id, "raumtempauswahl"
        )
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": model,
            "manufacturer": "Maico",
            "model": model,
        }

    @property
    def current_option(self) -> str | None:
        """Aktuell aktive Raumtemperaturquelle."""
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get("raumtempauswahl")
        if raw is None:
            return None
        return RAUMTEMP_BY_VALUE.get(int(raw))

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_select_option(self, option: str) -> None:
        """Raumtemperaturquelle wählen und sofort ins Gerät schreiben."""
        value = RAUMTEMP_OPTIONS.get(option)
        if value is None:
            _LOGGER.error("Unbekannte Raumtempauswahl-Option: %s", option)
            return
        await self.coordinator.async_write_raw("raumtempauswahl", value)
        _LOGGER.debug("Raumtempauswahl → %s (R109 = %d)", option, value)
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """Coordinator-Updates abonnieren."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
