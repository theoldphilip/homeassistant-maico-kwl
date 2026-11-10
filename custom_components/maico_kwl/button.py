"""Button entities for Maico KWL."""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DEVICE_MODEL
from .coordinator import MaicoKWLCoordinator
from .profiles import build_unique_id

_LOGGER = logging.getLogger(__name__)

# Register-Key -> Anzeigename (R157/158/159, „1 = Filter gewechselt“)
FILTERWECHSEL_BUTTONS = {
    "filterwechsel_geraet": "Filter gewechselt (Gerät)",
    "filterwechsel_aussen": "Filter gewechselt (Außenluft)",
    "filterwechsel_raum": "Filter gewechselt (Raumluft)",
}


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

    entities: list[ButtonEntity] = [
        MaicoKWLBoostButton(coordinator, config_entry),
        MaicoKWLFehlerResetButton(coordinator, config_entry),
    ]

    # Filterwechsel quittieren: nur für Register, die das Gerät beantwortet.
    for key, name in FILTERWECHSEL_BUTTONS.items():
        if key in coordinator.registers and coordinator.feature_present(key):
            entities.append(
                MaicoKWLFilterWechselButton(coordinator, config_entry, key, name)
            )

    async_add_entities(entities)


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


class MaicoKWLFehlerResetButton(ButtonEntity):
    """Fehler quittieren (Fehler Reset, Register 405).

    Schreibt 1 in R405 → das Gerät quittiert alle aktiven Fehler.
    Entspricht dem manuellen Reset-Button in der Maico-App.

    Hinweis: Das Register ist write-only (kein Lesen). Die Entität ist
    in der Kategorie „Diagnose" eingeordnet, damit sie nicht das
    normale Dashboard überfrachtet.
    """

    _attr_name = "Fehler quittieren"
    _attr_has_entity_name = True
    _attr_icon = "mdi:alert-circle-check"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        self.coordinator = coordinator
        self._config_entry = config_entry
        legacy = config_entry.data.get("legacy_ids", False)
        model = config_entry.data.get("model", DEVICE_MODEL)
        self._attr_unique_id = build_unique_id(legacy, config_entry.entry_id, "fehler_reset")
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
        """Fehler quittieren: schreibt 1 → R405."""
        await self.coordinator.async_write_raw("fehler_reset", 1)
        _LOGGER.info("Maico KWL: Fehler quittiert (R405 = 1)")


class MaicoKWLFilterWechselButton(ButtonEntity):
    """Filterwechsel quittieren (Register 157 / 158 / 159).

    Schreibt 1 → das Gerät setzt den Zähler des jeweiligen Filters zurück.
    Bewusst je Filter ein eigener Button, damit nur quittiert wird, was auch
    wirklich getauscht wurde. Die Buttons entstehen nur, wenn das Gerät das
    Register beantwortet (automatische Feature-Erkennung).
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:air-filter"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: MaicoKWLCoordinator,
        config_entry: ConfigEntry,
        register_key: str,
        name: str,
    ):
        self.coordinator = coordinator
        self._config_entry = config_entry
        self._register_key = register_key
        self._attr_name = name
        legacy = config_entry.data.get("legacy_ids", False)
        model = config_entry.data.get("model", DEVICE_MODEL)
        self._attr_unique_id = build_unique_id(legacy, config_entry.entry_id, register_key)
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
        """Filterwechsel quittieren: schreibt 1 → R157/158/159."""
        await self.coordinator.async_write_raw(self._register_key, 1)
        _LOGGER.info("Maico KWL: %s quittiert (%s = 1)", self._attr_name, self._register_key)
