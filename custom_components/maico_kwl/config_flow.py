"""Config flow for Maico KWL."""
import asyncio
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from pymodbus.client import AsyncModbusTcpClient

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_CARD_AUTOLOAD,
    CONF_FILTER_WARNING_DAYS,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    DEFAULT_MODBUS_PORT,
    DEFAULT_SCAN_INTERVAL,
    entry_config,
)
from .profiles import all_models, model_to_profile_key, get_profile, DEFAULT_MODEL

_LOGGER = logging.getLogger(__name__)


def _user_schema(default_model: str = DEFAULT_MODEL) -> vol.Schema:
    """Build the user step schema with a model dropdown."""
    models = all_models()
    return vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Required("model", default=default_model): SelectSelector(
            SelectSelectorConfig(
                options=models,
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional("filter_warning_days", default=7): cv.positive_int,
    })


async def validate_modbus_connection(host: str, port: int = DEFAULT_MODBUS_PORT, unit_id: int = 1) -> bool:
    """Validate Modbus connection with a hard timeout."""
    import inspect
    client = AsyncModbusTcpClient(host=host, port=port, timeout=5)
    try:
        async with asyncio.timeout(10):
            connected = await client.connect()
            if not connected:
                return False
            params = inspect.signature(client.read_holding_registers).parameters
            slave_kwarg = "device_id" if "device_id" in params else "slave"
            kwargs = {"address": 550, "count": 1, slave_kwarg: unit_id}
            result = await client.read_holding_registers(**kwargs)
            return not result.isError()
    except (asyncio.TimeoutError, Exception) as err:
        _LOGGER.error(f"Connection validation failed: {err}")
        return False
    finally:
        try:
            client.close()
        except Exception:
            pass


class MaicoKWLConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Maico KWL."""

    VERSION = 2

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()

            if not await validate_modbus_connection(user_input[CONF_HOST]):
                errors["base"] = "cannot_connect"

            if not errors:
                model = user_input.get("model", DEFAULT_MODEL)
                profile_key = model_to_profile_key(model)
                profile = get_profile(profile_key)
                return self.async_create_entry(
                    title=f"Maico {model} ({user_input[CONF_HOST]})",
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        "port": DEFAULT_MODBUS_PORT,
                        "unit_id": 1,
                        "scan_interval": 30,
                        "filter_warning_days": user_input.get("filter_warning_days", 7),
                        # Neue Installationen: mitgelieferte Karte automatisch
                        # bereitstellen. Bestehende Einträge haben den Schlüssel
                        # nicht -> aus (keine Überraschung bei manueller Karte).
                        CONF_CARD_AUTOLOAD: True,
                        "model": model,
                        "profile": profile_key,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(),
            errors=errors,
            description_placeholders={
                "help_text": "Wähle dein Maico-Modell und gib die IP-Adresse der Anlage ein."
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Options-Dialog (IP, Abfrageintervall, Filterschwelle, Karte)."""
        return MaicoKWLOptionsFlow()

    async def async_step_import(self, import_data: Dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(import_data)


class MaicoKWLOptionsFlow(config_entries.OptionsFlow):
    """Einstellungen nachträglich ändern, ohne die Integration neu einzurichten."""

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        errors: Dict[str, str] = {}
        entry = self.config_entry
        cfg = entry_config(entry)

        if user_input is not None:
            new_host = user_input[CONF_HOST].strip()

            # Eine IP, die schon von einem anderen Eintrag genutzt wird, ablehnen.
            for other in self.hass.config_entries.async_entries(DOMAIN):
                if other.entry_id != entry.entry_id and (
                    entry_config(other).get(CONF_HOST) == new_host
                ):
                    errors[CONF_HOST] = "already_configured"

            # Verbindung nur prüfen, wenn sich die IP geändert hat.
            if not errors and new_host != cfg.get(CONF_HOST):
                ok = await validate_modbus_connection(
                    new_host,
                    cfg.get("port", DEFAULT_MODBUS_PORT),
                    cfg.get("unit_id", 1),
                )
                if not ok:
                    errors[CONF_HOST] = "cannot_connect"

            if not errors:
                options = {
                    CONF_HOST: new_host,
                    CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                    CONF_FILTER_WARNING_DAYS: int(user_input[CONF_FILTER_WARNING_DAYS]),
                    CONF_CARD_AUTOLOAD: bool(user_input[CONF_CARD_AUTOLOAD]),
                }
                if new_host != cfg.get(CONF_HOST):
                    model = entry.data.get("model", DEFAULT_MODEL)
                    self.hass.config_entries.async_update_entry(
                        entry,
                        title=f"Maico {model} ({new_host})",
                        unique_id=new_host,
                        options=options,
                    )
                return self.async_create_entry(title="", data=options)

        schema = vol.Schema({
            vol.Required(CONF_HOST, default=cfg.get(CONF_HOST, "")): cv.string,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=cfg.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=10, max=600, step=5,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Required(
                CONF_FILTER_WARNING_DAYS,
                default=cfg.get(CONF_FILTER_WARNING_DAYS, 7),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1, max=365, step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="d",
                )
            ),
            vol.Required(
                CONF_CARD_AUTOLOAD,
                default=cfg.get(CONF_CARD_AUTOLOAD, False),
            ): BooleanSelector(),
        })
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
