"""Integration for Maico KWL Modbus."""
import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir

from .const import (
    CONF_CARD_AUTOLOAD,
    CONF_FILTER_WARNING_DAYS,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    FILTER_WARNING_DAYS,
    entry_config,
)
from .coordinator import MaicoKWLCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: Final = [
    Platform.FAN,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.BUTTON,
    Platform.SELECT,
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

    # Optionen (aus dem Options-Dialog) überschreiben die Einrichtungsdaten.
    cfg = entry_config(entry)

    coordinator = MaicoKWLCoordinator(
        hass,
        cfg[CONF_HOST],
        cfg.get(CONF_PORT, 502),
        cfg.get("unit_id", 1),
        cfg.get(CONF_SCAN_INTERVAL, 30),
        profile_key,
    )
    
    # Establish the initial connection once. If it fails, HA will retry setup
    # later instead of spinning — this prevents the event loop from hanging.
    connected = await coordinator.async_connect()
    if not connected:
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(
            f"Verbindung zu {cfg[CONF_HOST]} fehlgeschlagen"
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

    # Mitgelieferte Lovelace-Karte automatisch bereitstellen (Option je Eintrag;
    # aktiv, sobald mindestens ein Eintrag sie wünscht).
    await _async_update_card_registration(hass)

    # Reparaturhinweis, solange der Filter fällig ist (unter Einstellungen → Reparaturen).
    _update_filter_issue(hass, entry, coordinator)
    entry.async_on_unload(
        coordinator.async_add_listener(
            lambda: _update_filter_issue(hass, entry, coordinator)
        )
    )

    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        ir.async_delete_issue(hass, DOMAIN, _filter_issue_id(entry))
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


def _filter_issue_id(entry: ConfigEntry) -> str:
    return f"filter_due_{entry.entry_id}"


def _update_filter_issue(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: MaicoKWLCoordinator
) -> None:
    """Reparaturhinweis anlegen, solange die Filter-Restlaufzeit die Schwelle erreicht hat.

    Die Schwelle ist dieselbe wie beim Binary-Sensor „Filterwechsel notwendig“
    (Option „Filterschwelle“). Der Hinweis verschwindet von selbst, sobald die
    Restlaufzeit wieder darüber liegt (nach dem Filterwechsel).
    """
    issue_id = _filter_issue_id(entry)
    days = (coordinator.data or {}).get("filter_restlaufzeit_zuluft")
    if not isinstance(days, int) or isinstance(days, bool):
        return  # keine Daten (oder Gerät ohne dieses Register): nichts ändern
    threshold = int(
        entry_config(entry).get(CONF_FILTER_WARNING_DAYS, FILTER_WARNING_DAYS)
    )
    if days <= threshold:
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="filter_due",
            translation_placeholders={
                "name": entry.title,
                "days": str(days),
                "threshold": str(threshold),
            },
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, issue_id)


async def _async_update_card_registration(hass: HomeAssistant) -> None:
    """Karte registrieren oder entfernen, je nach Option der Einträge."""
    from .card import async_disable_card, async_enable_card

    want = any(
        entry_config(e).get(CONF_CARD_AUTOLOAD, False)
        for e in hass.config_entries.async_entries(DOMAIN)
    )
    try:
        if want:
            await async_enable_card(hass)
        else:
            async_disable_card(hass)
    except Exception as err:  # Karte darf das Laden der Integration nie verhindern
        _LOGGER.warning("Maico KWL: Karten-Bereitstellung fehlgeschlagen: %s", err)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the component (legacy YAML config, not required for modern integrations)."""
    hass.data.setdefault(DOMAIN, {})
    return True
