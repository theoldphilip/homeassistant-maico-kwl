"""Config flow for Maico KWL."""
import asyncio
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from pymodbus.client import AsyncModbusTcpClient

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import DOMAIN, DEFAULT_MODBUS_PORT, DEFAULT_T_RAUM_BUS_WRITE_CYCLE_MINUTES
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
        vol.Optional(
            "bus_write_cycle_minutes",
            default=DEFAULT_T_RAUM_BUS_WRITE_CYCLE_MINUTES,
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
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

    async def async_get_options_flow(self, config_entry):
        return MaicoKWLOptionsFlowHandler(config_entry)

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
                "bus_write_cycle_minutes": user_input.get(
                    "bus_write_cycle_minutes",
                    DEFAULT_T_RAUM_BUS_WRITE_CYCLE_MINUTES,
                ),
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

    async def async_step_import(self, import_data: Dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(import_data)


class MaicoKWLOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Maico KWL."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_cycle = self.config_entry.options.get(
            "bus_write_cycle_minutes",
            self.config_entry.data.get(
                "bus_write_cycle_minutes",
                DEFAULT_T_RAUM_BUS_WRITE_CYCLE_MINUTES,
            ),
        )

        schema = vol.Schema({
            vol.Optional(
                "bus_write_cycle_minutes",
                default=current_cycle,
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
        })

        return self.async_show_form(step_id="init", data_schema=schema)
