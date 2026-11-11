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

const st = (v) => ({ state: v, attributes: {} });
const q = (e, sel) => e.shadowRoot.querySelector(sel);
const calls = [];
const mkc = (extraEnts, extraStates, extraCfg) => {
  const e = w.document.createElement('maico-kwl-card');
  w.document.body.appendChild(e);
  e.setConfig({ name: 'T', entities: { ...ents, ...extraEnts }, ...(extraCfg || {}) });
  const h = { states: { ...hass.states, ...extraStates }, callService: (d, s_, data) => calls.push([d, s_, data]) };
  e.hass = h;
  e._h = h;
  return e;
};
const upd = (e, states) => { e._h = { ...e._h, states: { ...e._h.states, ...states } }; e.hass = e._h; };
const header = (e) => (html(e).match(/class="status-chip[^"]*">(?:<svg.*?<\/svg>)?([^<]*)</s) || [])[1];

// v2.0: Grundlayout, Räume eingeklappt
{
  const e = mkc({}, {});
  ok(!html(e).includes('class="banners"') && !html(e).includes('class="tiles"') && !html(e).includes('class="actions"'), 'ohne optionale Entities: keine Banner/Kacheln/Bedienung');
  ok(q(e, '#btn-rooms').getAttribute('aria-expanded') === 'false' && !q(e, '.rooms'), 'Räume: standardmäßig eingeklappt');
  ok(html(e).includes('3 Zuluft · 3 Abluft'), 'Räume: Zähler in der Zeile');
  q(e, '#btn-rooms').click();
  ok(q(e, '#btn-rooms').getAttribute('aria-expanded') === 'true' && html(e).includes('Schlafzimmer') && html(e).includes('Küche'), 'Räume: Klick klappt auf');
  q(e, '#btn-rooms').click();
  ok(!q(e, '.rooms'), 'Räume: zweiter Klick klappt zu');
  const e2 = mkc({}, {}, { rooms: { zuluft: [{ name: '<b>X</b>', icon: '&' }], abluft: [] } });
  q(e2, '#btn-rooms').click();
  ok(!html(e2).includes('<b>X</b>') && html(e2).includes('&lt;b&gt;X&lt;/b&gt;') && html(e2).includes('1 Zuluft · 0 Abluft'), 'Raumnamen werden maskiert');
  ok(html(e).includes('@media (hover: hover)') && html(e).includes('prefers-reduced-motion'), 'Hover nur mit Maus, reduzierte Bewegung respektiert');
}

// Kopf
{
  let e = mkc({ volumenstrom: 's.vol' }, { 's.vol': st('130'), 's.status': st('Inaktiv'), 's.stufe': st('Reduziert') });
  ok(header(e).trim() === 'Reduziert', 'Kopf: Stufe statt „Inaktiv“ (' + header(e) + ')');
  ok(html(e).includes('<div class="sub-info">130 m³/h</div>'), 'Kopf: darunter nur der Volumenstrom');
  e = mkc({ volumenstrom: 's.vol' }, { 's.vol': st('150'), 's.status': st('Kühlt (Nachtkühlung)'), 's.stufe': st('Nennlüftung') });
  ok(header(e).trim() === 'Kühlt' && html(e).includes('Nennlüftung · 150 m³/h'), 'Kopf: Kühlt, Stufe in der Zeile darunter');
  e = mkc({}, { 's.status': st('Inaktiv'), 's.stufe': st('') });
  ok(header(e).trim() === 'Inaktiv', 'ohne Stufe: Fallback „Inaktiv“');
}

// Sommermodus-Schalter
{
  const e = mkc({ sommer: 'switch.sommer' }, { 'switch.sommer': st('off'), 's.other': st('1') });
  ok(html(e).includes('id="btn-sommer"') && html(e).includes('<small>aus</small>') && !html(e).includes('act act-on'), 'Sommermodus: Knopf, Status „aus“');
  calls.length = 0;
  q(e, '#btn-sommer').click();
  ok(calls.length === 1 && calls[0][0] === 'switch' && calls[0][1] === 'toggle' && calls[0][2].entity_id === 'switch.sommer', 'Sommermodus: switch.toggle');
  const before = q(e, '#btn-sommer');
  upd(e, { 's.other': st('2') });
  ok(q(e, '#btn-sommer') === before, 'unbeteiligter State: kein Neuzeichnen');
  upd(e, { 'switch.sommer': st('on') });
  ok(html(e).includes('act act-on') && html(e).includes('<small>an</small>'), 'Sommermodus an: hervorgehoben');
}

// Kennzahlen
{
  const e = mkc({ leistung: 's.leist', wrg_leistung: 's.wrgp' }, { 's.leist': st('26.4'), 's.wrgp': st('702.8') });
  ok(html(e).includes('Strom</span><span class="tile-val">26<small> W') && html(e).includes('WRG-Gewinn</span><span class="tile-val">703<small> W'), 'Kacheln: Strom und WRG-Gewinn');
  ok(html(e).includes('repeat(2,'), 'Kacheln: Raster passt sich der Anzahl an');
}

// Filter: Banner, Kachel, Quittier-Menü
{
  const fb = { filter: 's.filter', filter_geraet: 'button.fg', filter_aussen: 'button.fa', filter_raum: 'button.fr' };
  const fs = { 's.filter': st('165'), 'button.fg': st('unknown'), 'button.fa': st('unknown'), 'button.fr': st('unknown') };
  const e = mkc(fb, fs);
  ok(!html(e).includes('class="banner banner-warn"') && html(e).includes('Filter</span><span class="tile-val">165<small> Tage') && !html(e).includes('tile tile-warn'), 'Filter 165 Tage: nur Kachel, keine Warnung');
  upd(e, { 's.filter': st('12') });
  ok(html(e).includes('Filterwechsel fällig') && html(e).includes('Restlaufzeit noch 12 Tage') && html(e).includes('tile tile-warn'), 'Filter 12 Tage: Banner + orange Kachel');
  ok(!!q(e, '#btn-filter'), 'Banner hat „Gewechselt“');
  upd(e, { 's.filter': st('1') });
  ok(html(e).includes('noch 1 Tag<'), 'Filter 1 Tag: Einzahl');
  upd(e, { 's.filter': st('0') });
  ok(html(e).includes('Filter jetzt wechseln') && html(e).includes('tile tile-err'), 'Filter 0: rot');
  // Menü
  const sheet = q(e, '#sheet-filter');
  ok(!!sheet && sheet.querySelectorAll('input[data-fkey]').length === 3, 'Filtermenü: drei Häkchen');
  q(e, '#btn-filter').click();
  ok(sheet.hasAttribute('open'), 'Filtermenü öffnet');
  const ok1 = q(e, '#filter-ok');
  ok(ok1.disabled === true, 'Quittieren gesperrt, solange nichts angehakt ist');
  const boxes = [...sheet.querySelectorAll('input[data-fkey]')];
  boxes[0].checked = true; boxes[0].dispatchEvent(new w.Event('change'));
  boxes[2].checked = true; boxes[2].dispatchEvent(new w.Event('change'));
  ok(ok1.disabled === false, 'Quittieren frei nach Auswahl');
  calls.length = 0;
  ok1.click();
  ok(calls.length === 2 && calls.every((c) => c[0] === 'button' && c[1] === 'press') &&
     calls[0][2].entity_id === 'button.fg' && calls[1][2].entity_id === 'button.fr', 'nur angehakte Filter werden quittiert (Gerät + Raumluft)');
  ok(e._sheet === null, 'Menü-Status zurückgesetzt');
  // nur ein Filter vorhanden: vorangehakt
  const e1 = mkc({ filter: 's.filter', filter_geraet: 'button.fg' }, { ...fs, 's.filter': st('3') });
  const b1 = q(e1, '#sheet-filter input[data-fkey]');
  ok(q(e1, '#sheet-filter').querySelectorAll('input').length === 1 && b1.checked && q(e1, '#filter-ok').disabled === false, 'ein einziger Filter: vorangehakt');
  // ohne Knopf-Entitäten: Banner ohne „Gewechselt“
  const e0 = mkc({ filter: 's.filter' }, { 's.filter': st('3') });
  ok(html(e0).includes('class="banner banner-warn"') && !q(e0, '#btn-filter') && !q(e0, '#sheet-filter'), 'ohne Filter-Knöpfe: Banner ohne „Gewechselt“');
  // Abbrechen
  q(e, '#btn-filter') && q(e, '#btn-filter').click();
  calls.length = 0;
  q(e, '#filter-cancel').click();
  ok(calls.length === 0 && e._sheet === null, 'Abbrechen quittiert nichts');
  // eigener Schwellenwert
  const e3 = mkc({ filter: 's.filter' }, { 's.filter': st('165') }, { filter_warn_days: 200 });
  ok(html(e3).includes('Filterwechsel fällig'), 'filter_warn_days=200 wirkt');
}

// Fehler
{
  const e = mkc({ fehler: 's.fehler', fehler_reset: 'button.fr0' }, { 's.fehler': st('OK'), 'button.fr0': st('unknown') });
  ok(!html(e).includes('class="banner banner-err"'), 'Fehler OK: kein Banner');
  upd(e, { 's.fehler': st('Aktiv') });
  ok(html(e).includes('role="alert"') && html(e).includes('Fehler am Gerät') && !!q(e, '#btn-fehler'), 'Fehler aktiv: Banner mit „Quittieren“');
  calls.length = 0;
  q(e, '#btn-fehler').click();
  ok(calls.length === 1 && calls[0][0] === 'button' && calls[0][2].entity_id === 'button.fr0', 'Quittieren: button.press auf fehler_reset');
  upd(e, { 's.fehler': st('unavailable') });
  ok(!html(e).includes('class="banner banner-err"'), 'Fehler unavailable: kein Banner');
  const e2 = mkc({ fehler: 's.fehler' }, { 's.fehler': st('Aktiv') });
  ok(html(e2).includes('class="banner banner-err"') && !q(e2, '#btn-fehler'), 'ohne fehler_reset: Banner ohne Knopf');
}

// Stoßlüftung
{
  const e = mkc({ volumenstrom: 's.vol', stoss: 'button.stoss', stoss_rest: 's.rest' },
                { 's.vol': st('200'), 'button.stoss': st('unknown'), 's.rest': st('7'), 's.status': st('Inaktiv'), 's.stufe': st('Intensiv') }, { show_explanation: true });
  ok(header(e).includes('Stoßlüftung · 7 min') && html(e).includes('status-chip boost'), 'Stoßlüftung: Kopf mit Restzeit');
  ok(html(e).includes('Intensiv · 200 m³/h'), 'Stoßlüftung: Stufe und Volumenstrom darunter');
  ok(html(e).includes('act act-on" id="btn-stoss"') && html(e).includes('<small>noch 7 min</small>'), 'Stoßlüftung: Knopf aktiv mit Restzeit');
  ok(html(e).includes('Stoßlüftung läuft noch 7 min · Sommermodus nicht aktiv'), 'Erklärungszeile mit Restzeit');
  calls.length = 0;
  q(e, '#btn-stoss').click();
  ok(calls.length === 1 && calls[0][0] === 'button' && calls[0][1] === 'press' && calls[0][2].entity_id === 'button.stoss', 'Stoßlüftung: button.press');
  upd(e, { 's.rest': st('0'), 's.stufe': st('Reduziert') });
  ok(header(e).trim() === 'Reduziert' && !html(e).includes('noch 0 min') && !html(e).includes('act act-on'), 'Restzeit 0: normal');
  upd(e, { 's.rest': st('unavailable') });
  ok(!html(e).includes('noch'), 'Restzeit unavailable: nichts');
}

// Stufenmenü
{
  const ve = { fan: 'fan.l', vol_reduziert: 'n.r', vol_nenn: 'n.n', vol_intensiv: 'n.i' };
  const vs = { 'fan.l': st('on'), 'n.r': st('100'), 'n.n': st('150'), 'n.i': st('200'), 's.stufe': st('Reduziert') };
  const e = mkc(ve, vs);
  let sheet = q(e, '#sheet-stufe');
  const opts = [...sheet.querySelectorAll('[data-pct]')];
  ok(opts.length === 4 && opts.map((o) => o.dataset.pct).join() === '25,50,75,100', 'Stufenmenü: vier Stufen (25/50/75/100 %)');
  ok(sheet.innerHTML.includes('100 m³/h') && sheet.innerHTML.includes('150 m³/h') && sheet.innerHTML.includes('200 m³/h'), 'Stufenmenü: eingestellte m³/h');
  ok(opts[1].classList.contains('opt-on') && !opts[0].classList.contains('opt-on') && !opts[2].classList.contains('opt-on') && opts[1].innerHTML.includes('<svg'), 'Stufenmenü: aktuelle Stufe (Reduziert) markiert');
  upd(e, { 's.stufe': st('Schutzlüftung') });
  ok(q(e, '#sheet-stufe [data-pct="25"]').classList.contains('opt-on') && q(e, '#sheet-stufe [data-pct="25"]').textContent.includes('Schutzlüftung'), 'Stufenmenü: Schutzlüftung wählbar und markiert');
  upd(e, { 's.stufe': st('Reduziert') });
  sheet = q(e, '#sheet-stufe');
  q(e, '#btn-stufe').click();
  ok(sheet.hasAttribute('open') && e._sheet === 'stufe', 'Stufenmenü öffnet');
  // Während das Menü offen ist, wird nicht neu gezeichnet
  const before = q(e, '#sheet-stufe');
  upd(e, { 's.stufe': st('Nennlüftung') });
  ok(q(e, '#sheet-stufe') === before && before.hasAttribute('open'), 'offenes Menü bleibt bei Zustandsänderung stehen');
  calls.length = 0;
  q(e, '#sheet-stufe [data-pct="75"]').click();
  ok(calls.length === 1 && calls[0][0] === 'fan' && calls[0][1] === 'set_percentage' && calls[0][2].entity_id === 'fan.l' && calls[0][2].percentage === 75, 'Nennlüftung: fan.set_percentage 75');
  ok(e._sheet === null && q(e, '#sheet-stufe [data-pct="75"]').classList.contains('opt-on'), 'nach Auswahl: zu, nachgeholtes Neuzeichnen zeigt neue Stufe');
  // Betriebsart
  const modes = [...q(e, '#sheet-stufe').querySelectorAll('[data-mode]')];
  ok(modes.map((m) => m.dataset.mode).join() === 'Manuell,Auto Sensor,Eco-Zuluft,Eco-Abluft', 'Betriebsart: vier Modi, ohne Auto Zeit und Aus');
  ok(!q(e, '#btn-fan-more'), 'Link „Weitere Einstellungen“ entfällt');
  q(e, '#btn-stufe').click();
  calls.length = 0;
  q(e, '#sheet-stufe [data-mode="Auto Sensor"]').click();
  ok(calls.length === 1 && calls[0][0] === 'fan' && calls[0][1] === 'set_preset_mode' && calls[0][2].entity_id === 'fan.l' && calls[0][2].preset_mode === 'Auto Sensor' && e._sheet === null, 'Betriebsart wählen: fan.set_preset_mode');
  ok(!modes.some((m) => m.classList.contains('mode-on')), 'ohne betriebsart-Entity und Preset: keine Markierung');
  // aktuelle Betriebsart: Sensor hat Vorrang, sonst Preset des fan
  const eM = mkc({ ...ve, betriebsart: 's.mode' }, { ...vs, 's.mode': st('Eco-Zuluft') });
  ok(q(eM, '#sheet-stufe [data-mode="Eco-Zuluft"]').classList.contains('mode-on') && eM.shadowRoot.querySelectorAll('.mode-on').length === 1, 'Betriebsart: aktive aus Sensor markiert');
  const eP = mkc(ve, { ...vs, 'fan.l': { state: 'on', attributes: { preset_mode: 'Manuell' } } });
  ok(q(eP, '#sheet-stufe [data-mode="Manuell"]').classList.contains('mode-on'), 'Betriebsart: Fallback auf Preset des Lüftungs-Entity');
  upd(eP, { 'fan.l': { state: 'on', attributes: { preset_mode: 'Auto Sensor' } } });
  ok(q(eP, '#sheet-stufe [data-mode="Auto Sensor"]').classList.contains('mode-on'), 'Preset-Wechsel zeichnet neu (Signatur)');
  // Rand-Tipp schließt
  q(e, '#btn-stufe').click();
  q(e, '#sheet-stufe').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  ok(e._sheet === null, 'Tipp auf den Rand schließt das Menü');
  // ohne Volumenstrom-Entitäten: nur Namen
  const e2 = mkc({ fan: 'fan.l' }, vs);
  ok(!q(e2, '#sheet-stufe').innerHTML.includes('m³/h'), 'ohne vol_*: keine m³/h im Menü');
  ok(!q(mkc({}, {}), '#btn-stufe'), 'ohne fan: kein Stufen-Knopf');
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
      { entity_id: 'button.x_stoss', platform: 'maico_kwl', unique_id: 'maico_kwl_stosslueftung', device_id: 'D1' },
      { entity_id: 'sensor.x_stoss_rest', platform: 'maico_kwl', unique_id: 'maico_kwl_stosslueftung_restzeit', device_id: 'D1' },
      { entity_id: 'fan.x_lueftung', platform: 'maico_kwl', unique_id: 'maico_kwl_lueftung', device_id: 'D1' },
      { entity_id: 'number.x_vol_red', platform: 'maico_kwl', unique_id: 'maico_kwl_volumenstrom_reduziert', device_id: 'D1' },
      { entity_id: 'number.x_vol_nenn', platform: 'maico_kwl', unique_id: 'maico_kwl_volumenstrom_nennlueftung', device_id: 'D1' },
      { entity_id: 'number.x_vol_int', platform: 'maico_kwl', unique_id: 'maico_kwl_volumenstrom_intensiv', device_id: 'D1' },
      { entity_id: 'sensor.x_betriebsart', platform: 'maico_kwl', unique_id: 'maico_kwl_betriebsart', device_id: 'D1' },
      { entity_id: 'button.x_fg', platform: 'maico_kwl', unique_id: 'maico_kwl_filterwechsel_geraet', device_id: 'D1' },
      { entity_id: 'button.x_fr', platform: 'maico_kwl', unique_id: 'maico_kwl_filterwechsel_raum', device_id: 'D1' },
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
      box('stoss').checked = true; box('stoss').dispatchEvent(new w.Event('change'));
      await new Promise(r => setTimeout(r, 30));
      ok(cfg5.entities.stoss === 'button.x_stoss' && cfg5.entities.stoss_rest === 'sensor.x_stoss_rest', 'Auto-Erkennung: Stoßlüftung inkl. Restzeit');
      box('stoss').checked = false; box('stoss').dispatchEvent(new w.Event('change'));
      await new Promise(r => setTimeout(r, 30));
      ok(!('stoss' in cfg5.entities) && !('stoss_rest' in cfg5.entities), 'Abwählen entfernt Stoßlüftung und Restzeit');
      box('fan').checked = true; box('fan').dispatchEvent(new w.Event('change'));
      await new Promise(r => setTimeout(r, 30));
      ok(cfg5.entities.fan === 'fan.x_lueftung' && cfg5.entities.vol_reduziert === 'number.x_vol_red' && cfg5.entities.vol_nenn === 'number.x_vol_nenn' && cfg5.entities.vol_intensiv === 'number.x_vol_int' && cfg5.entities.betriebsart === 'sensor.x_betriebsart', 'Auto-Erkennung: Stufen-Knopf inkl. m³/h-Einstellungen und Betriebsart');
      box('filter').checked = true; box('filter').dispatchEvent(new w.Event('change'));
      await new Promise(r => setTimeout(r, 30));
      ok(cfg5.entities.filter === 'sensor.x_filterwechsel' && cfg5.entities.filter_geraet === 'button.x_fg' && cfg5.entities.filter_raum === 'button.x_fr' && !('filter_aussen' in cfg5.entities), 'Auto-Erkennung: Filter inkl. vorhandener Quittier-Knöpfe (fehlende werden ausgelassen)');
      box('filter').checked = false; box('filter').dispatchEvent(new w.Event('change'));
      await new Promise(r => setTimeout(r, 30));
      ok(!('filter' in cfg5.entities) && !('filter_geraet' in cfg5.entities) && !('filter_raum' in cfg5.entities), 'Abwählen entfernt Filter samt Quittier-Knöpfen');
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
