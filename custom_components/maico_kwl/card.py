"""Bereitstellung der mitgelieferten Lovelace-Karte (maico-kwl-card.js).

Die Karte liegt im Ordner ``www`` der Integration und wird über einen eigenen
Pfad ausgeliefert. Ist die Option „Karte automatisch bereitstellen“ aktiv,
wird sie zusätzlich beim Laden des Dashboards eingebunden – eine manuelle
Ressource ist dann nicht nötig. Die Karte selbst fängt eine doppelte
Registrierung ab (ein zweites ``customElements.define`` wird übersprungen).
"""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url, remove_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_URL_PATH = f"/{DOMAIN}/maico-kwl-card.js"
_CARD_FILE = Path(__file__).parent / "www" / "maico-kwl-card.js"
_STATE_KEY = f"{DOMAIN}_card_state"


async def async_enable_card(hass: HomeAssistant) -> None:
    """Karte ausliefern und im Frontend registrieren (idempotent)."""
    state = hass.data.setdefault(_STATE_KEY, {"path": False, "url": None})

    if not state["path"]:
        if not _CARD_FILE.is_file():
            _LOGGER.warning("Maico KWL: Kartendatei fehlt (%s)", _CARD_FILE)
            return
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_PATH, str(_CARD_FILE), cache_headers=False)]
        )
        state["path"] = True

    if state["url"] is None:
        integration = await async_get_integration(hass, DOMAIN)
        url = f"{CARD_URL_PATH}?v={integration.version}"
        add_extra_js_url(hass, url)
        state["url"] = url
        _LOGGER.debug("Maico KWL: Karte registriert (%s)", url)


def async_disable_card(hass: HomeAssistant) -> None:
    """Automatische Registrierung wieder entfernen (greift nach Seiten-Reload)."""
    state = hass.data.get(_STATE_KEY)
    if state and state["url"]:
        remove_extra_js_url(hass, state["url"])
        state["url"] = None
        _LOGGER.debug("Maico KWL: Karten-Registrierung entfernt")
