const { JSDOM } = require('jsdom');
const fs = require('fs');
const code = fs.readFileSync(require('path').join(__dirname, '..', '..', 'custom_components', 'maico_kwl', 'www', 'maico-kwl-card.js'), 'utf8');
const dom = new JSDOM('<!doctype html><body></body>', { runScripts: 'outside-only', pretendToBeVisual: true });
const w = dom.window;
w.matchMedia = () => ({ matches: false, addEventListener(){}, removeEventListener(){}, addListener(){}, removeListener(){} });
w.eval(code);
w.eval(code); // doppeltes Laden darf nicht werfen (manuell + automatisch)

let fails = 0;
const ok = (c, m) => { console.log((c ? 'OK   ' : 'FAIL ') + m); if (!c) fails++; };

const ents = { aussenluft:'s.aus', zuluft:'s.zu', abluft:'s.ab', fortluft:'s.fort', status:'s.status', stufe:'s.stufe', bypass:'s.byp' };
const states = { 's.aus': '18.0', 's.zu': '20', 's.ab': '24.0', 's.fort': '21', 's.status': 'Kühlt (Nachtkühlung)', 's.stufe': 'Intensiv', 's.byp': 'Offen' };
const hass = { states: Object.fromEntries(Object.entries(states).map(([k,v]) => [k, { state: v, attributes: {} }])), language: 'de' };

function mk(extra) {
  const el = w.document.createElement('maico-kwl-card');
  w.document.body.appendChild(el);
  el.setConfig({ name: 'T', entities: ents, ...extra });
  el.hass = hass;
  return el;
}
const html = (el) => el.shadowRoot.innerHTML;

ok(w.customCards.filter(c => c.type === 'maico-kwl-card').length === 1, 'customCards nur 1x registriert (trotz Doppel-Laden)');
let el = mk({});
ok(!html(el).includes('class="explain"'), 'ohne show_explanation: keine Zeile');
el = mk({ show_explanation: false });
ok(!html(el).includes('class="explain"'), 'show_explanation=false: keine Zeile');
el = mk({ show_explanation: true });
ok(html(el).includes('class="explain"'), 'show_explanation=true: Zeile vorhanden');
ok(html(el).includes('Außen 6.0 °C kühler als innen'), 'Text Kühlt: ' + (html(el).match(/class="explain">([^<]*)</)||[])[1]);
ok(html(el).includes('Bypass offen (Firmware)'), 'Bypass-Zusatz');

function explain(status, byp) {
  const e = w.document.createElement('maico-kwl-card');
  return e._explain(status, 18, 24, byp);
}
ok(explain('Inaktiv', null) === 'Sommermodus nicht aktiv', 'Inaktiv');
ok(explain('Anlage aus', null) === 'Außentemperatur zu hoch für Kühlung', 'Anlage aus');
ok(explain('Bereit – wartet 7 min', null).startsWith('Bereit – Δ 6.0 °C'), 'Bereit/wartet');
ok(explain('', null) === 'Sommermodus nicht aktiv', 'leerer Status wirft nicht');

// v1.5.0: Filter-Chip, Sommermodus-Schalter, kein unnötiges Neuzeichnen
{
  const calls = [];
  const h2 = { states: { ...hass.states, 's.filter': { state: '165', attributes: {} }, 'switch.sommer': { state: 'off', attributes: {} }, 's.other': { state: '1', attributes: {} } },
               callService: (d, s_, data) => calls.push([d, s_, data]) };
  const e2 = w.document.createElement('maico-kwl-card');
  w.document.body.appendChild(e2);
  e2.setConfig({ name: 'T', entities: { ...ents, filter: 's.filter', sommer: 'switch.sommer' } });
  e2.hass = h2;
  ok(html(e2).includes('Filter: noch 165 Tage'), 'Filter-Chip zeigt Resttage');
  ok(!html(e2).includes('class="chip chip-warn"'), 'Filter 165 Tage: keine Warnung');
  ok(html(e2).includes('Sommermodus aus'), 'Sommermodus-Chip: aus');
  e2.shadowRoot.getElementById('chip-sommer').click();
  ok(calls.length === 1 && calls[0][0] === 'switch' && calls[0][1] === 'toggle' && calls[0][2].entity_id === 'switch.sommer', 'Klick ruft switch.toggle');
  const before = e2.shadowRoot.getElementById('chip-sommer');
  e2.hass = { ...h2, states: { ...h2.states, 's.other': { state: '2', attributes: {} } } };
  ok(e2.shadowRoot.getElementById('chip-sommer') === before, 'unbeteiligter State: kein Neuzeichnen (Klicks bleiben erhalten)');
  e2.hass = { ...h2, states: { ...h2.states, 'switch.sommer': { state: 'on', attributes: {} }, 's.filter': { state: '12', attributes: {} } } };
  ok(html(e2).includes('Sommermodus an') && html(e2).includes('chip-btn chip-on'), 'Schalter-Änderung wird gezeichnet');
  ok(html(e2).includes('class="chip chip-warn"'), 'Filter 12 Tage (<=30): Warnfarbe');
  e2.hass = { ...h2, states: { ...h2.states, 's.filter': { state: '0', attributes: {} } } };
  ok(html(e2).includes('Filter wechseln') && html(e2).includes('class="chip chip-err"'), 'Filter 0: Fehlerfarbe + Text');
  e2.setConfig({ name: 'T', filter_warn_days: 200, entities: { ...ents, filter: 's.filter' } });
  e2.hass = { ...h2, states: { ...h2.states, 's.filter': { state: '165', attributes: {} } } };
  ok(html(e2).includes('class="chip chip-warn"'), 'filter_warn_days=200 wirkt');
  ok(!html(e2).includes('id="chip-sommer"'), 'ohne sommer-Entity kein Schalter');
  const e3 = mk({});
  ok(!html(e3).includes('class="chips"'), 'ohne optionale Entities keine Chips-Zeile');
}

// v1.6.0: neue Chips
{
  const calls = [], infos = [];
  const st = (v) => ({ state: v, attributes: {} });
  const base = { ...hass.states, 's.leist': st('26.4'), 's.wrgp': st('702.8'), 'button.stoss': st('unknown'), 'fan.l': st('on'), 's.fehler': st('OK') };
  const h3 = { states: base, callService: (d, s_, data) => calls.push([d, s_, data]) };
  const e4 = w.document.createElement('maico-kwl-card');
  w.document.body.appendChild(e4);
  e4.addEventListener('hass-more-info', (ev) => infos.push(ev.detail.entityId));
  e4.setConfig({ name: 'T', entities: { ...ents, leistung: 's.leist', wrg_leistung: 's.wrgp', stoss: 'button.stoss', fan: 'fan.l', fehler: 's.fehler' } });
  e4.hass = h3;
  ok(html(e4).includes('⚡ 26 W'), 'Chip Leistung');
  ok(html(e4).includes('WRG +703 W'), 'Chip WRG-Gewinn');
  ok(!html(e4).includes('Fehler aktiv'), 'Fehler OK: kein Chip');
  e4.shadowRoot.getElementById('chip-stoss').click();
  ok(calls.length === 1 && calls[0][0] === 'button' && calls[0][1] === 'press' && calls[0][2].entity_id === 'button.stoss', 'Stoßlüftung: button.press');
  e4.shadowRoot.getElementById('chip-fan').click();
  ok(infos.length === 1 && infos[0] === 'fan.l', 'Lüftung: more-info-Dialog');
  e4.hass = { ...h3, states: { ...base, 's.fehler': st('Aktiv') } };
  ok(html(e4).includes('Fehler aktiv') && html(e4).includes('class="chip chip-err"'), 'Fehler aktiv: roter Chip');
  e4.hass = { ...h3, states: { ...base, 's.fehler': st('unavailable') } };
  ok(!html(e4).includes('Fehler aktiv'), 'Fehler unavailable: kein Chip');
}

// Editor
const ed = w.document.createElement('maico-kwl-card-editor');
w.document.body.appendChild(ed);
let last = null;
ed.addEventListener('config-changed', (e) => { last = e.detail.config; });
ed.setConfig({ name: 'T', entities: ents });
ed.hass = hass;
setTimeout(() => {
  const cb = ed.shadowRoot.getElementById('inp-explain');
  ok(!!cb, 'Editor: Checkbox vorhanden');
  ok(ed.shadowRoot.querySelectorAll('input[data-feat]').length === 7, 'Editor: 7 Checkboxen für Zusatzanzeigen');
  ok(!ed.shadowRoot.querySelector('[data-ekey="filter"]'), 'Editor: ohne Aktivierung kein Picker für Zusatzanzeigen');
  ok(cb && cb.checked === false, 'Editor: standardmäßig aus');
  cb.checked = true; cb.dispatchEvent(new w.Event('change'));
  ok(last && last.show_explanation === true, 'Editor: Schalter setzt show_explanation=true');
  ok(last && last.entities && last.entities.status === 's.status', 'Editor: übrige Config bleibt erhalten');
  const ed2 = w.document.createElement('maico-kwl-card-editor');
  w.document.body.appendChild(ed2);
  ed2.setConfig({ name: 'T', entities: ents, show_explanation: true });
  setTimeout(() => {
    ok(ed2.shadowRoot.getElementById('inp-explain').checked === true, 'Editor: gespeicherter Wert wird angezeigt');
    // v1.6.0: Editor findet Entitäten über das Entity-Register
    const reg = [
      { entity_id: 'sensor.htr_x_sommermodus_status', platform: 'maico_kwl', unique_id: 'maico_kwl_sommermodus_status', device_id: 'D1' },
      { entity_id: 'switch.htr_x_sommermodus', platform: 'maico_kwl', unique_id: 'maico_kwl_sommermodus', device_id: 'D1' },
      { entity_id: 'sensor.x_filterwechsel', platform: 'maico_kwl', unique_id: 'maico_kwl_filter_restlaufzeit_zuluft', device_id: 'D1' },
      { entity_id: 'sensor.x_leistung', platform: 'maico_kwl', unique_id: 'maico_kwl_leistung', device_id: 'D1' },
      { entity_id: 'sensor.x_wrg_leistung', platform: 'maico_kwl', unique_id: 'maico_kwl_wrg_leistung', device_id: 'D1' },
      // zweites Gerät (neues ID-Schema mit Entry-ID) darf nicht verwechselt werden
      { entity_id: 'switch.zweit_sommermodus', platform: 'maico_kwl', unique_id: 'maico_kwl_01ARZ3NDEKTSV4RRFFQ69G5FAV_sommermodus', device_id: 'D2' },
      { entity_id: 'sensor.fremd_leistung', platform: 'andere', unique_id: 'maico_kwl_leistung', device_id: 'D1' },
    ];
    let wsCalls = 0;
    const hassWs = { ...hass, callWS: async (msg) => { wsCalls++; return msg.type === 'config/entity_registry/list' ? reg : null; } };
    const e5 = w.document.createElement('maico-kwl-card-editor');
    w.document.body.appendChild(e5);
    let cfg5 = null;
    e5.addEventListener('config-changed', (ev) => { cfg5 = ev.detail.config; });
    e5.setConfig({ name: 'T', entities: { ...ents, status: 'sensor.htr_x_sommermodus_status' } });
    e5.hass = hassWs;
    setTimeout(async () => {
      const box = (k) => e5.shadowRoot.querySelector(`input[data-feat="${k}"]`);
      box('sommer').checked = true; box('sommer').dispatchEvent(new w.Event('change'));
      await new Promise(r => setTimeout(r, 30));
      ok(cfg5 && cfg5.entities.sommer === 'switch.htr_x_sommermodus', 'Auto-Erkennung: Sommermodus-Schalter des richtigen Geräts');
      box('leistung').checked = true; box('leistung').dispatchEvent(new w.Event('change'));
      await new Promise(r => setTimeout(r, 30));
      ok(cfg5.entities.leistung === 'sensor.x_leistung', 'Auto-Erkennung: Leistung (nicht WRG-Leistung, nicht fremde Integration)');
      box('wrg_leistung').checked = true; box('wrg_leistung').dispatchEvent(new w.Event('change'));
      await new Promise(r => setTimeout(r, 30));
      ok(cfg5.entities.wrg_leistung === 'sensor.x_wrg_leistung', 'Auto-Erkennung: WRG-Leistung');
      ok(wsCalls === 1, 'Entity-Register wird nur einmal geladen');
      ok(cfg5.entities.status === 'sensor.htr_x_sommermodus_status' && cfg5.name === 'T', 'übrige Config bleibt erhalten');
      ok(!!e5.shadowRoot.querySelector('ha-entity-picker[data-ekey="sommer"]'), 'aktivierte Zusatzanzeige zeigt Picker zum Überschreiben');
      // nicht gefunden -> Hinweis + leerer Picker
      box('fehler').checked = true; box('fehler').dispatchEvent(new w.Event('change'));
      await new Promise(r => setTimeout(r, 30));
      ok(e5.shadowRoot.innerHTML.includes('Nicht automatisch gefunden'), 'Nicht gefunden: Hinweis');
      // abwählen entfernt den Eintrag
      box('sommer').checked = false; box('sommer').dispatchEvent(new w.Event('change'));
      await new Promise(r => setTimeout(r, 30));
      ok(cfg5 && !('sommer' in cfg5.entities), 'Abwählen entfernt die Entität aus der Config');
      // bestehende Config (aus 1.9.0) zeigt Haken
      const e6 = w.document.createElement('maico-kwl-card-editor');
      w.document.body.appendChild(e6);
      e6.setConfig({ name: 'T', entities: { ...ents, filter: 'sensor.x_filterwechsel', sommer: 'switch.htr_x_sommermodus' } });
      ok(e6.shadowRoot.querySelector('input[data-feat="filter"]').checked && e6.shadowRoot.querySelector('input[data-feat="sommer"]').checked, 'vorhandene Einträge: Haken gesetzt');
      ok(!e6.shadowRoot.querySelector('input[data-feat="leistung"]').checked, 'nicht vorhandene: kein Haken');
      console.log(fails ? `\n${fails} FEHLER` : '\nALLE JS-TESTS OK');
      process.exit(fails ? 1 : 0);
    }, 80);
  }, 50);
}, 50);
