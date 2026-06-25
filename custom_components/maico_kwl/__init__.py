"""Integration for Maico KWL Modbus."""
import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import MaicoKWLCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: Final = [
    Platform.FAN,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.BUTTON,
]



async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries to the multi-model format.

    Version 1  -> created by the single-device (WS 300 Flat) integration.
        These installs must keep their EXACT entity unique_ids so dashboards,
        automations and the energy dashboard entry don't break. We therefore
        tag them with ``legacy_ids: True`` and assume the WS 300 Flat profile.
    Version 2  -> multi-model format (model + profile + per-entry unique ids).
    """
    from .profiles import DEFAULT_PROFILE_KEY, DEFAULT_MODEL

    if entry.version < 2:
        new_data = {**entry.data}
        # Existing single-device installs: keep behaviour and IDs identical.
        new_data.setdefault("profile", DEFAULT_PROFILE_KEY)
        new_data.setdefault("model", DEFAULT_MODEL)
        new_data["legacy_ids"] = True  # keep the original "maico_kwl_*" ids
        hass.config_entries.async_update_entry(entry, data=new_data, version=2)
        _LOGGER.info(
            "Maico KWL: Bestehende Installation auf Multi-Modell-Format migriert "
            "(Entity-IDs bleiben unverändert)."
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""
    
    hass.data.setdefault(DOMAIN, {})

    # Determine the device profile. Existing installations created before the
    # multi-model version have no "profile" key -> default to kwl_zentral
    # (WS 300 Flat), which keeps their behaviour and entity_ids identical.
    from .profiles import DEFAULT_PROFILE_KEY
    profile_key = entry.data.get("profile", DEFAULT_PROFILE_KEY)
    # legacy_ids: existing installs keep the original "maico_kwl_*" unique_ids;
    # new installs get per-entry-unique ids so multiple devices don't collide.
    legacy_ids = entry.data.get("legacy_ids", False)

    coordinator = MaicoKWLCoordinator(
        hass,
        entry.data[CONF_HOST],
        entry.data.get(CONF_PORT, 502),
        entry.data.get("unit_id", 1),
        entry.data.get("scan_interval", 30),
        profile_key,
    )
    
    # Establish the initial connection once. If it fails, HA will retry setup
    # later instead of spinning — this prevents the event loop from hanging.
    connected = await coordinator.async_connect()
    if not connected:
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(
            f"Verbindung zu {entry.data[CONF_HOST]} fehlgeschlagen"
        )
    
    # Initial data refresh
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await coordinator.async_shutdown()
        raise
    
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "legacy_ids": legacy_ids,
        "model": entry.data.get("model"),
    }
    
    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the component (legacy YAML config, not required for modern integrations)."""
    hass.data.setdefault(DOMAIN, {})
    return True
