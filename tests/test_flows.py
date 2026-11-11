"""Config-/Options-Flow unter echtem Home Assistant."""
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "maico_kwl"
VALIDATE = "custom_components.maico_kwl.config_flow.validate_modbus_connection"


def make_entry(hass, host="10.0.0.5", **extra):
    data = {"host": host, "port": 502, "unit_id": 1, "scan_interval": 30,
            "filter_warning_days": 7, "model": "WS 300 Flat", "profile": "kwl_zentral",
            "legacy_ids": True, **extra}
    e = MockConfigEntry(domain=DOMAIN, data=data, unique_id=host, version=2,
                        title=f"Maico WS 300 Flat ({host})")
    e.add_to_hass(hass)
    return e


async def test_user_flow_new_entry_has_card_autoload(hass):
    with patch(VALIDATE, return_value=True), \
         patch("custom_components.maico_kwl.async_setup_entry", return_value=True):
        r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert r["type"] == FlowResultType.FORM
        r = await hass.config_entries.flow.async_configure(
            r["flow_id"], {"host": "10.0.0.9", "model": "WS 300 Flat", "filter_warning_days": 7})
    assert r["type"] == FlowResultType.CREATE_ENTRY
    assert r["data"]["card_autoload"] is True


async def test_options_flow_shows_form_with_defaults(hass):
    e = make_entry(hass)
    r = await hass.config_entries.options.async_init(e.entry_id)
    assert r["type"] == FlowResultType.FORM and r["step_id"] == "init"
    keys = {str(k): k for k in r["data_schema"].schema}
    # bestehender Eintrag ohne Schlüssel -> Karte standardmäßig AUS
    assert keys["card_autoload"].default() is False
    assert keys["host"].default() == "10.0.0.5"
    assert keys["scan_interval"].default() == 30


async def test_options_flow_saves_without_host_change(hass):
    e = make_entry(hass)
    with patch(VALIDATE, return_value=True) as v, \
         patch("custom_components.maico_kwl.async_setup_entry", return_value=True):
        r = await hass.config_entries.options.async_init(e.entry_id)
        r = await hass.config_entries.options.async_configure(
            r["flow_id"], {"host": "10.0.0.5", "scan_interval": 60.0,
                           "filter_warning_days": 14.0, "card_autoload": True})
    assert r["type"] == FlowResultType.CREATE_ENTRY
    assert e.options == {"host": "10.0.0.5", "scan_interval": 60,
                         "filter_warning_days": 14, "card_autoload": True}
    assert isinstance(e.options["scan_interval"], int)
    v.assert_not_called()  # IP unverändert -> keine Verbindungsprüfung


async def test_options_flow_host_change_validates_and_updates_entry(hass):
    e = make_entry(hass)
    with patch(VALIDATE, return_value=True) as v, \
         patch("custom_components.maico_kwl.async_setup_entry", return_value=True):
        r = await hass.config_entries.options.async_init(e.entry_id)
        r = await hass.config_entries.options.async_configure(
            r["flow_id"], {"host": "10.0.0.77", "scan_interval": 30,
                           "filter_warning_days": 7, "card_autoload": False})
    assert r["type"] == FlowResultType.CREATE_ENTRY
    v.assert_called_once()
    assert e.unique_id == "10.0.0.77"
    assert "10.0.0.77" in e.title
    assert e.options["host"] == "10.0.0.77"


async def test_options_flow_cannot_connect(hass):
    e = make_entry(hass)
    with patch(VALIDATE, return_value=False):
        r = await hass.config_entries.options.async_init(e.entry_id)
        r = await hass.config_entries.options.async_configure(
            r["flow_id"], {"host": "10.0.0.99", "scan_interval": 30,
                           "filter_warning_days": 7, "card_autoload": False})
    assert r["type"] == FlowResultType.FORM
    assert r["errors"] == {"host": "cannot_connect"}
    assert e.unique_id == "10.0.0.5"  # nichts verändert


async def test_options_flow_duplicate_host(hass):
    e = make_entry(hass, "10.0.0.5")
    make_entry(hass, "10.0.0.6")
    with patch(VALIDATE, return_value=True):
        r = await hass.config_entries.options.async_init(e.entry_id)
        r = await hass.config_entries.options.async_configure(
            r["flow_id"], {"host": "10.0.0.6", "scan_interval": 30,
                           "filter_warning_days": 7, "card_autoload": False})
    assert r["errors"] == {"host": "already_configured"}
