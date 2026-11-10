"""Diagnose-Download für Maico KWL (Einstellungen → Gerät → Diagnose herunterladen)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN, entry_config

# IP-Adresse und alles, was sie enthält (Titel / unique_id), wird geschwärzt.
TO_REDACT = {"host"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    integration = await async_get_integration(hass, DOMAIN)

    absent = sorted(getattr(coordinator, "_absent_features", set()))
    optional_keys = sorted(k for k, r in coordinator.registers.items() if r.optional)
    present = [k for k in optional_keys if k not in absent]

    return {
        "integration_version": str(integration.version),
        "entry": {
            "title": "**redacted**",
            "unique_id": "**redacted**",
            "version": entry.version,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
            "effective_config": async_redact_data(entry_config(entry), TO_REDACT),
        },
        "profile": {
            "key": coordinator.profile.get("key"),
            "model": entry.data.get("model"),
        },
        "connection": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
        },
        "optional_features": {"present": present, "absent": absent},
        "registers": {
            key: {
                "address": r.address,
                "scale": r.scale,
                "width": r.width,
                "optional": r.optional,
                "writable": r.writable,
            }
            for key, r in sorted(coordinator.registers.items())
        },
        "data": dict(coordinator.data) if coordinator.data else None,
        "summer_mode": {
            "enabled": coordinator.summer_mode,
            "status": coordinator.summer_status,
            "cool_target": coordinator.cool_target,
            "cool_min_diff": coordinator.cool_min_diff,
            "cool_hysteresis": coordinator.cool_hysteresis,
            "min_runtime": coordinator.min_runtime,
        },
    }
