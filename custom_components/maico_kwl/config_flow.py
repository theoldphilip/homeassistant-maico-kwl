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

from .const import DOMAIN, DEFAULT_MODBUS_PORT

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional("filter_warning_days", default=7): cv.positive_int,
})


async def validate_modbus_connection(host: str, port: int = DEFAULT_MODBUS_PORT, unit_id: int = 1) -> bool:
    """Validate Modbus connection with a hard timeout.

    The whole check is wrapped in asyncio.timeout so a stalled connect can
    never hang the config flow (which would take the event loop down).
    """
    import inspect
    client = AsyncModbusTcpClient(host=host, port=port, timeout=5)
    try:
        async with asyncio.timeout(10):
            connected = await client.connect()
            if not connected:
                return False
            # Detect pymodbus API (3.10+ uses device_id, older uses slave)
            params = inspect.signature(client.read_holding_registers).parameters
            slave_kwarg = "device_id" if "device_id" in params else "slave"
            kwargs = {"address": 550, "count": 1, slave_kwarg: unit_id}
            # Try to read Betriebsart register to verify connection
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

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Check if device is already configured
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()

            # Validate Modbus connection (with defaults)
            if not await validate_modbus_connection(user_input[CONF_HOST]):
                errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(
                    title=f"Maico WS 300 Flat ({user_input[CONF_HOST]})",
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        "port": DEFAULT_MODBUS_PORT,
                        "unit_id": 1,
                        "scan_interval": 30,
                        "filter_warning_days": user_input.get("filter_warning_days", 7),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "help_text": "Gib die IP-Adresse deiner Maico WS 300 Flat Lüftungsanlage ein."
            },
        )

    async def async_step_import(self, import_data: Dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(import_data)
