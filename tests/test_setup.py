"""Kompletter Setup unter echtem Home Assistant mit simuliertem Modbus-Gerät."""
import json
from unittest.mock import patch

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "maico_kwl"
HOST = "10.0.0.5"

# Adresse -> Rohwert; Adressen in ERRORS liefern einen Modbus-Fehler ("nicht vorhanden")
VALUES = {550: 1, 650: 3, 651: 1500, 652: 1500, 653: 150, 654: 150,
          655: 165, 656: 165, 657: 165, 703: 254, 704: 200, 705: 258, 706: 210,
          750: 61, 755: 600, 800: 1, 801: 1, 802: 0, 700: 230, 302: 250, 301: 14,
          153: 10, 551: 0, 401: 0, 402: 0, 403: 0, 404: 0, 900: 100, 109: 0,
          154: 100, 155: 150, 156: 200, 157: 0, 158: 0}
ERRORS = {159, 751, 752, 753, 754, 756, 757, 758, 759, 760, 701}


class FakeResult:
    def __init__(self, regs, err=False):
        self.registers, self._err = regs, err

    def isError(self):
        return self._err


class FakeClient:
    instances = []

    def __init__(self, *a, **k):
        self.connected = True
        self.writes = []
        FakeClient.instances.append(self)

    async def connect(self):
        return True

    def close(self):
        pass

    async def read_holding_registers(self, address, count=1, **kw):
        if any(a in ERRORS for a in range(address, address + count)):
            return FakeResult([], err=True)
        return FakeResult([VALUES.get(a, 0) for a in range(address, address + count)])

    async def write_register(self, address, value, **kw):
        self.writes.append((address, value))
        return FakeResult([value])


def make_entry(hass, **extra):
    data = {"host": HOST, "port": 502, "unit_id": 1, "scan_interval": 30,
            "filter_warning_days": 7, "model": "WS 300 Flat", "profile": "kwl_zentral",
            "legacy_ids": True, **extra}
    e = MockConfigEntry(domain=DOMAIN, data=data, unique_id=HOST, version=2,
                        title=f"Maico WS 300 Flat ({HOST})")
    e.add_to_hass(hass)
    return e


async def setup(hass, **extra):
    FakeClient.instances.clear()
    e = make_entry(hass, **extra)
    with patch("custom_components.maico_kwl.coordinator.AsyncModbusTcpClient", FakeClient):
        assert await hass.config_entries.async_setup(e.entry_id)
        await hass.async_block_till_done()
    return e


def extra_urls(hass):
    mgr = hass.data.get(DATA_EXTRA_MODULE_URL)
    return set(mgr.urls) if mgr else set()


async def test_setup_filter_buttons_only_for_present_registers(hass):
    e = await setup(hass)
    reg = er.async_get(hass)
    buttons = {x.original_name: x for x in er.async_entries_for_config_entry(reg, e.entry_id)
               if x.domain == "button"}
    names = set(buttons)
    assert "Filter gewechselt (Gerät)" in names
    assert "Filter gewechselt (Außenluft)" in names
    assert "Filter gewechselt (Raumluft)" not in names      # R159 = Modbus-Fehler
    assert buttons["Fehler quittieren"].entity_category == EntityCategory.DIAGNOSTIC
    assert buttons["Filter gewechselt (Gerät)"].entity_category == EntityCategory.DIAGNOSTIC
    # legacy_ids -> alte unique_id-Form bleibt
    assert buttons["Filter gewechselt (Außenluft)"].unique_id == "maico_kwl_filterwechsel_aussen"


async def test_press_filter_button_writes_one(hass):
    e = await setup(hass)
    reg = er.async_get(hass)
    ent = next(x for x in er.async_entries_for_config_entry(reg, e.entry_id)
               if x.original_name == "Filter gewechselt (Außenluft)")
    await hass.services.async_call("button", "press", {"entity_id": ent.entity_id}, blocking=True)
    assert (158, 1) in FakeClient.instances[-1].writes


async def test_fehler_hinweis_sensors_are_diagnostic(hass):
    e = await setup(hass)
    reg = er.async_get(hass)
    sens = {x.original_name: x for x in er.async_entries_for_config_entry(reg, e.entry_id)
            if x.domain == "sensor"}
    assert sens["Fehler"].entity_category == EntityCategory.DIAGNOSTIC
    assert sens["Hinweis"].entity_category == EntityCategory.DIAGNOSTIC
    assert sens["Temperatur - Raumluft (aus den Räumen)"].entity_category is None


async def test_card_not_registered_for_existing_entry(hass):
    await setup(hass)  # kein card_autoload-Schlüssel = bestehender Eintrag
    assert not any("maico-kwl-card" in u for u in extra_urls(hass))


async def test_card_registered_for_new_entry_and_served(hass, hass_client):
    await setup(hass, card_autoload=True)
    urls = [u for u in extra_urls(hass) if "maico-kwl-card" in u]
    assert len(urls) == 1 and urls[0].startswith("/maico_kwl/maico-kwl-card.js?v=")
    client = await hass_client()
    resp = await client.get("/maico_kwl/maico-kwl-card.js")
    assert resp.status == 200
    body = await resp.text()
    assert "customElements.get('maico-kwl-card')" in body


async def test_options_change_applies_and_card_toggle(hass):
    e = await setup(hass, card_autoload=True)
    assert any("maico-kwl-card" in u for u in extra_urls(hass))
    with patch("custom_components.maico_kwl.coordinator.AsyncModbusTcpClient", FakeClient):
        r = await hass.config_entries.options.async_init(e.entry_id)
        r = await hass.config_entries.options.async_configure(
            r["flow_id"], {"host": HOST, "scan_interval": 90, "filter_warning_days": 21,
                           "card_autoload": False})
        await hass.async_block_till_done()
    coord = hass.data[DOMAIN][e.entry_id]["coordinator"]
    assert coord.update_interval.total_seconds() == 90
    assert not any("maico-kwl-card" in u for u in extra_urls(hass))
    # Filterschwelle wirkt auf den Binary-Sensor
    reg = er.async_get(hass)
    ent = next(x for x in er.async_entries_for_config_entry(reg, e.entry_id)
               if x.domain == "binary_sensor")
    st = hass.states.get(ent.entity_id)
    assert st.attributes.get("schwellwert_tage") == 21


async def test_diagnostics_redacts_host_and_is_json(hass):
    from custom_components.maico_kwl.diagnostics import async_get_config_entry_diagnostics
    e = await setup(hass)
    diag = await async_get_config_entry_diagnostics(hass, e)
    dump = json.dumps(diag, default=str)
    assert HOST not in dump
    assert diag["entry"]["data"]["host"] == "**REDACTED**"
    assert diag["profile"]["key"] == "kwl_zentral"
    assert "filterwechsel_raum" in diag["optional_features"]["absent"]
    assert "filterwechsel_geraet" in diag["optional_features"]["present"]
    assert diag["data"]["temp_aussenluft"] == 25.4
    assert diag["integration_version"]


async def test_unload(hass):
    e = await setup(hass)
    assert await hass.config_entries.async_unload(e.entry_id)
    await hass.async_block_till_done()


async def test_wrg_sensors_power_and_energy(hass):
    """WRG-Leistung = 0,34 · Volumenstrom · (T_Zuluft − T_Außen); Energie integriert."""
    from datetime import timedelta
    from homeassistant.util import dt as dt_util
    e = await setup(hass)
    reg = er.async_get(hass)
    ents = {x.original_name: x.entity_id for x in er.async_entries_for_config_entry(reg, e.entry_id)
            if x.domain == "sensor"}
    p_id = ents["Wärmerückgewinnung Leistung (geschätzt)"]
    e_id = ents["Wärmerückgewinnung Energie (geschätzt)"]
    coord = hass.data[DOMAIN][e.entry_id]["coordinator"]

    # Winter: außen 0 °C, Zuluft 17 °C, 150 m³/h  ->  0,34 · 150 · 17 = 867 W
    coord.async_set_updated_data({**coord.data, "temp_aussenluft": 0.0, "temp_zuluft": 17.0,
                                  "volumenstrom_zuluft": 150})
    await hass.async_block_till_done()
    assert float(hass.states.get(p_id).state) == 867.0

    # Sommer/Bypass: Zuluft nicht wärmer als außen -> 0 W (nie negativ)
    coord.async_set_updated_data({**coord.data, "temp_aussenluft": 25.0, "temp_zuluft": 22.0})
    await hass.async_block_till_done()
    assert float(hass.states.get(p_id).state) == 0.0

    # Fehlende Werte -> unbekannt
    coord.async_set_updated_data({**coord.data, "temp_zuluft": None})
    await hass.async_block_till_done()
    assert hass.states.get(p_id).state == "unknown"

    # Energie: 1 h mit konstant 867 W -> 0,867 kWh (Trapezregel)
    start = dt_util.utcnow()
    with patch("custom_components.maico_kwl.sensor.datetime") as dtm:
        dtm.now.return_value = start
        coord.async_set_updated_data({**coord.data, "temp_aussenluft": 0.0, "temp_zuluft": 17.0})
        await hass.async_block_till_done()
        base = float(hass.states.get(e_id).state)
        dtm.now.return_value = start + timedelta(minutes=30)
        coord.async_set_updated_data({**coord.data})
        await hass.async_block_till_done()
        dtm.now.return_value = start + timedelta(minutes=60)
        coord.async_set_updated_data({**coord.data})
        await hass.async_block_till_done()
    assert abs(float(hass.states.get(e_id).state) - base - 0.867) < 0.002

    # Lücke > 1 h wird nicht mitgezählt
    with patch("custom_components.maico_kwl.sensor.datetime") as dtm:
        dtm.now.return_value = start + timedelta(hours=5)
        before = float(hass.states.get(e_id).state)
        coord.async_set_updated_data({**coord.data})
        await hass.async_block_till_done()
    assert float(hass.states.get(e_id).state) == before


async def test_filter_repair_issue_lifecycle(hass):
    """Reparaturhinweis erscheint bei fälligem Filter und verschwindet nach dem Wechsel."""
    from homeassistant.helpers import issue_registry as ir
    # Restlaufzeit 165 Tage, Schwelle 7 -> kein Hinweis
    e = await setup(hass)
    issue_id = f"filter_due_{e.entry_id}"
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
    coord = hass.data[DOMAIN][e.entry_id]["coordinator"]

    # Restlaufzeit fällt auf die Schwelle -> Hinweis mit Platzhaltern
    coord.async_set_updated_data({**coord.data, "filter_restlaufzeit_zuluft": 7})
    await hass.async_block_till_done()
    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_key == "filter_due"
    assert issue.translation_placeholders["days"] == "7"
    assert issue.translation_placeholders["threshold"] == "7"
    assert issue.is_fixable is False

    # Filter gewechselt (Restlaufzeit wieder hoch) -> Hinweis verschwindet
    coord.async_set_updated_data({**coord.data, "filter_restlaufzeit_zuluft": 180})
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

    # Fehlende Daten ändern nichts
    coord.async_set_updated_data({**coord.data, "filter_restlaufzeit_zuluft": 3})
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None
    data = dict(coord.data); data.pop("filter_restlaufzeit_zuluft")
    coord.async_set_updated_data(data)
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None

    # Entladen räumt den Hinweis auf
    assert await hass.config_entries.async_unload(e.entry_id)
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


async def test_filter_issue_already_due_at_startup(hass):
    from homeassistant.helpers import issue_registry as ir
    e = await setup(hass, filter_warning_days=200)   # Restlaufzeit 165 <= 200
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"filter_due_{e.entry_id}") is not None
