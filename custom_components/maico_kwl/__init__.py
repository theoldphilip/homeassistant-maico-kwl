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
]



async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""
    
    hass.data.setdefault(DOMAIN, {})
    
    coordinator = MaicoKWLCoordinator(
        hass,
        entry.data[CONF_HOST],
        entry.data.get(CONF_PORT, 502),
        entry.data.get("unit_id", 1),
        entry.data.get("scan_interval", 30),
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
