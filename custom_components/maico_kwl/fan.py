"""Fan entity for Maico KWL.

Design:
- Percentage slider  -> Lüftungsstufe (0..4 mapped to 0/25/50/75/100 %).
  Changing the stage also forces Betriebsart to "Manuell" (550 = 1),
  because a fixed stage only makes sense in manual mode.
- Preset modes (dropdown) -> Betriebsart (Aus/Manuell/Auto Zeit/...).
"""
import logging
from typing import Any, Final

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DEVICE_MODEL, BETRIEBSART_MAPPING, LUEFTUNGSSTUFE_MAPPING
from .coordinator import MaicoKWLCoordinator

_LOGGER = logging.getLogger(__name__)

# Number of selectable ventilation stages (1..4). Stage 0 = off.
MAX_STUFE: Final = 4

# Preset modes = Betriebsarten (order follows the register values 0..5)
PRESET_MODES: Final = list(BETRIEBSART_MAPPING.values())

# Betriebsart value for "Manuell" (resolved from the mapping, fallback 1)
MANUELL_VALUE: Final = next(
    (k for k, v in BETRIEBSART_MAPPING.items() if v == "Manuell"), 1
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up fan platform."""
    coordinator: MaicoKWLCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    async_add_entities(
        [MaicoKWLFan(coordinator, config_entry)],
        update_before_add=True,
    )


class MaicoKWLFan(FanEntity):
    """Maico KWL fan: percentage = Lüftungsstufe, preset = Betriebsart."""

    _attr_name = "Lüftung"
    _attr_unique_id = "maico_kwl_lueftung"
    _attr_has_entity_name = True
    _attr_supported_features: Final = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.PRESET_MODE
    )
    _attr_preset_modes = PRESET_MODES
    # 4 selectable stages -> slider snaps to 25/50/75/100 %
    _attr_speed_count = MAX_STUFE

    def __init__(self, coordinator: MaicoKWLCoordinator, config_entry: ConfigEntry):
        """Initialize the fan."""
        self.coordinator = coordinator
        self._config_entry = config_entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": DEVICE_MODEL,
            "manufacturer": "Maico",
            "model": "WS 300 Flat",
        }

    # ---- State (reading) -------------------------------------------------

    @property
    def is_on(self) -> bool:
        """On when a ventilation stage > 0 is active."""
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.get("lueftungsstufe", 0) > 0

    @property
    def percentage(self) -> int | None:
        """Current Lüftungsstufe as percentage (stage/4 * 100)."""
        if self.coordinator.data is None:
            return None
        stufe = self.coordinator.data.get("lueftungsstufe", 0)
        stufe = max(0, min(MAX_STUFE, stufe))
        return round(stufe / MAX_STUFE * 100)

    @property
    def preset_mode(self) -> str | None:
        """Current Betriebsart as preset mode name."""
        if self.coordinator.data is None:
            return None
        mode = self.coordinator.data.get("betriebsart")
        if mode is None:
            return None
        return BETRIEBSART_MAPPING.get(mode)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose useful live values as attributes."""
        if self.coordinator.data is None:
            return {}

        stufe = self.coordinator.data.get("lueftungsstufe", 0)
        return {
            "lueftungsstufe": stufe,
            "lueftungsstufe_text": LUEFTUNGSSTUFE_MAPPING.get(stufe, "Unbekannt"),
            "betriebsart": self.coordinator.data.get("betriebsart", 0),
            "drehzahl_zuluft": self.coordinator.data.get("drehzahl_zuluft"),
            "drehzahl_abluft": self.coordinator.data.get("drehzahl_abluft"),
            "volumenstrom_zuluft": self.coordinator.data.get("volumenstrom_zuluft"),
            "volumenstrom_abluft": self.coordinator.data.get("volumenstrom_abluft"),
            "temp_zuluft": self.coordinator.data.get("temp_zuluft"),
            "temp_abluft": self.coordinator.data.get("temp_abluft"),
            "humidity": self.coordinator.data.get("humidity_abluft"),
            "co2": self.coordinator.data.get("co2_abluft"),
        }

    # ---- Commands (writing) ---------------------------------------------

    def _percentage_to_stufe(self, percentage: int) -> int:
        """Map a 0..100 % value to the write value for register 554.

        Values verified against a known-working setup:
          25 % -> 1, 50 % -> 2, 75 % -> 3, 100 % -> 4.
        "Off" (0 %) is handled separately via Betriebsart (turn_off),
        not written to 554.
        """
        if percentage <= 0:
            return 0
        if percentage <= 37:
            return 1   # niedrigste Stufe
        if percentage <= 62:
            return 2
        if percentage <= 87:
            return 3
        return 4       # höchste Stufe

    async def async_set_percentage(self, percentage: int) -> None:
        """Set Lüftungsstufe from percentage; forces Betriebsart=Manuell."""
        stufe = self._percentage_to_stufe(percentage)
        # Switch to Manuell first, so the stage is actually honored
        await self.coordinator.async_set_betriebsart(MANUELL_VALUE)
        await self.coordinator.async_set_lueftungsstufe(stufe)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set Betriebsart from preset name."""
        mode_value = next(
            (k for k, v in BETRIEBSART_MAPPING.items() if v == preset_mode), None
        )
        if mode_value is not None:
            await self.coordinator.async_set_betriebsart(mode_value)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            # Default: Manuell + Nennlüftung (stage 3)
            await self.coordinator.async_set_betriebsart(MANUELL_VALUE)
            await self.coordinator.async_set_lueftungsstufe(3)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off: set Betriebsart to Aus (0)."""
        await self.coordinator.async_set_betriebsart(0)

    # ---- Plumbing --------------------------------------------------------

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
