/**
 * Maico KWL Card – Custom Lovelace Card
 * Grafische Karte für Maico KWL Lüftungsanlagen mit animierten Luftströmen.
 *
 * GitHub: https://github.com/theoldphilip/homeassistant-maico-kwl
 * Version: 1.0.0
 *
 * Einbindung: wird von der Integration automatisch bereitgestellt (Option
 * „Karte automatisch bereitstellen“). Alternativ manuell als Ressource:
 *   URL: /local/maico-kwl-card.js   Typ: JavaScript-Modul
 *
 * Beispiel-Konfiguration:
 *   type: custom:maico-kwl-card
 *   name: Maico WS 300 Flat
 *   show_explanation: true      # optional: Erklärungszeile unter der Kopfzeile
 *   entities:
 *     aussenluft: sensor.maico_ws_300_flat_aussenluft
 *     zuluft:     sensor.maico_ws_300_flat_zuluft
 *     abluft:     sensor.maico_ws_300_flat_abluft
 *     fortluft:   sensor.maico_ws_300_flat_fortluft
 *     status:     sensor.htr_maico_ws_300_flat_sommermodus_status
 *     stufe:      sensor.maico_ws_300_flat_luftungsstufe
 *     volumenstrom: sensor.maico_ws_300_flat_volumenstrom_zuluft
 *     wrg:        sensor.maico_ws_300_flat_warmeruckgewinnung   # optional
 *     filter:     sensor.maico_ws_300_flat_filterwechsel        # optional: Filter-Restlaufzeit
 *     sommer:     switch.maico_ws_300_flat_sommermodus          # optional: Schalter in der Karte
 *     leistung:     sensor.maico_ws_300_flat_leistung_geschatzt   # optional: Stromleistung (W)
 *     wrg_leistung: sensor.maico_ws_300_flat_warmeruckgewinnung_leistung_geschatzt  # optional
 *     stoss:      button.maico_ws_300_flat_stosslueftung        # optional: Stoßlüftung auslösen
 *     fan:        fan.maico_ws_300_flat_lueftung                # optional: öffnet die Lüftungssteuerung
 *     fehler:     sensor.maico_ws_300_flat_fehler               # optional: Fehleranzeige (nur bei Fehler)
 *   filter_warn_days: 30    # optional: ab wie vielen Resttagen der Filter orange wird
 *   rooms:
 *     zuluft:
 *       - { name: Schlafzimmer,  icon: "🛏" }
 *       - { name: Wohnzimmer,    icon: "🛋" }
 *       - { name: Arbeitszimmer, icon: "💼" }
 *     abluft:
 *       - { name: Bad,           icon: "🚿" }
 *       - { name: Küche,         icon: "🍳" }
 *       - { name: HTR,           icon: "🔧" }
 */

class MaicoKwlCard extends HTMLElement {
  constructor() {
    super();
    this._shadow = this.attachShadow({ mode: 'open' });
    this._config = null;
    this._hass  = null;
    this._dark  = false;
  }

  /* ──────────────────────────────────── HA lifecycle ── */

  setConfig(config) {
    if (!config.entities) {
      throw new Error('[maico-kwl-card] "entities" ist erforderlich.');
    }
    this._config = config;
    this._sig = null;
    this._render();
  }

  static getConfigElement() {
    return document.createElement('maico-kwl-card-editor');
  }

  static getStubConfig() {
    return {
      name: 'Maico KWL',
      entities: {
        aussenluft:   'sensor.maico_ws_300_flat_aussenluft',
        zuluft:       'sensor.maico_ws_300_flat_zuluft',
        abluft:       'sensor.maico_ws_300_flat_abluft',
        fortluft:     'sensor.maico_ws_300_flat_fortluft',
        status:       'sensor.htr_maico_ws_300_flat_sommermodus_status',
        stufe:        'sensor.maico_ws_300_flat_luftungsstufe',
        volumenstrom: 'sensor.maico_ws_300_flat_volumenstrom_zuluft',
        wrg:          'sensor.maico_ws_300_flat_warmeruckgewinnung',
        bypass:       'sensor.maico_ws_300_flat_bypass_status',
        feuchte:      'sensor.maico_ws_300_flat_relative_feuchte_abluft',
      },
    };
  }

  set hass(hass) {
    this._hass = hass;
    this._dark = !!(hass.themes && hass.themes.darkMode) ||
                 window.matchMedia('(prefers-color-scheme: dark)').matches;
    /* Nur neu zeichnen, wenn sich ein verwendeter Zustand geändert hat –
       sonst gehen Klicks auf die Schalter beim ständigen Neuaufbau verloren. */
    const ids = Object.values((this._config && this._config.entities) || {});
    const sig = JSON.stringify([this._dark, ids.map((id) => {
      const st = hass.states[id];
      return st ? st.state : null;
    })]);
    if (sig === this._sig) return;
    this._sig = sig;
    this._render();
  }

  getCardSize() { return 5; }

  /* ──────────────────────────────────── Helpers ── */

  _state(id) {
    if (!id || !this._hass) return null;
    const s = this._hass.states[id];
    if (!s || s.state === 'unavailable' || s.state === 'unknown') return null;
    return s.state;
  }

  _num(id) {
    const s = this._state(id);
    if (s === null) return null;
    const n = parseFloat(s);
    return isNaN(n) ? null : n;
  }

  _fmt(v, d = 1) {
    return v !== null && v !== undefined ? v.toFixed(d) : '—';
  }

  /** WRG-Wirkungsgrad berechnen, falls kein eigenes Entity vorhanden */
  _calcWrg(zu, aus, ab) {
    if (zu === null || aus === null || ab === null) return null;
    const denom = ab - aus;
    if (Math.abs(denom) < 0.3) return null;
    return Math.max(0, Math.min(100, Math.round(((zu - aus) / denom) * 100)));
  }

  /** Erklärt den aktuellen Modus in einem kurzen Satz */
  _explain(status, tAus, tAb, bypass) {
    const parts = [];
    status = status || '';

    const inaktiv  = !status || status.includes('Inaktiv');
    const cooling  = status.includes('Kühlt');
    const ready    = status.includes('Bereit');
    const off      = status.includes('Anlage aus');
    const warten   = status.includes('wartet');

    if (inaktiv) {
      parts.push('Sommermodus nicht aktiv');
    } else if (cooling) {
      if (tAus !== null && tAb !== null) {
        const diff = (tAb - tAus).toFixed(1);
        parts.push(`Außen ${diff} °C kühler als innen`);
      } else {
        parts.push('Nachtkühlung aktiv');
      }
    } else if (off) {
      parts.push('Außentemperatur zu hoch für Kühlung');
    } else if (ready && warten) {
      if (tAus !== null && tAb !== null) {
        const diff = (tAb - tAus).toFixed(1);
        parts.push(`Bereit – Δ ${diff} °C (Mindestdifferenz noch nicht erreicht)`);
      } else {
        parts.push('Bereit – wartet auf Kühlbedingungen');
      }
    } else if (warten) {
      parts.push(status.split('–')[1]?.trim() || 'Mindest-Laufzeit läuft');
    }

    if (bypass === 'Offen') parts.push('Bypass offen (Firmware)');

    return parts.join(' · ');
  }

  /* ──────────────────────────────────── Arrow SVG helper ── */

  /**
   * Erzeugt einen animierten Pfeil ohne SVG-Marker (kein Shadow-DOM-ID-Problem).
   * Aufbau: Linienelement (flex:1) + fester Pfeilkopf (12 px) als separates SVG.
   *
   * dir "right": Linie l→r, Pfeilkopf rechts  (Außenluft → Zuluft)
   * dir "left" : Linie r→l, Pfeilkopf links   (Abluft   → Fortluft)
   *
   * Beide Linien nutzen dieselbe Animation (stroke-dashoffset: -9),
   * die Striche fließen immer in Zeichenrichtung des Pfades.
   */
  _arrowSvg(dir, color) {
    const right = dir === 'right';
    const lineSvg = `
      <svg width="100%" height="20" style="flex:1;display:block;overflow:visible">
        <line
          x1="${right ? '0%' : '100%'}" y1="10"
          x2="${right ? '100%' : '0%'}" y2="10"
          stroke="${color}"
          stroke-width="1.5"
          stroke-dasharray="5 4"
          style="animation:flow .7s linear infinite"
        />
      </svg>`;
    const headSvg = `
      <svg width="12" height="20" style="flex-shrink:0;display:block" viewBox="0 0 12 20">
        <polygon
          points="${right ? '0,4 12,10 0,16' : '12,4 0,10 12,16'}"
          fill="${color}"
        />
      </svg>`;
    return right
      ? `<div style="display:flex;align-items:center">${lineSvg}${headSvg}</div>`
      : `<div style="display:flex;align-items:center">${headSvg}${lineSvg}</div>`;
  }

  /* ──────────────────────────────────── CSS ── */

  _css(dark) {
    const v = dark ? {
      out:      '#52C2F0',
      zu:       '#F0883A',
      ab:       '#E8733A',
      fort:     '#2EC8A8',
      hi:       '#52C2F0',
      hiBg:     'rgba(82,194,240,0.14)',
      outPill:  'rgba(82,194,240,0.11)',
      inPill:   'rgba(240,136,58,0.11)',
      outBdr:   'rgba(82,194,240,0.30)',
      inBdr:    'rgba(240,136,58,0.30)',
    } : {
      out:      '#1A74AF',
      zu:       '#C4601A',
      ab:       '#9E3A10',
      fort:     '#157A5A',
      hi:       '#185FA5',
      hiBg:     'rgba(24,95,165,0.10)',
      outPill:  'rgba(26,116,175,0.09)',
      inPill:   'rgba(196,96,26,0.09)',
      outBdr:   'rgba(26,116,175,0.25)',
      inBdr:    'rgba(196,96,26,0.25)',
    };

    return `
<style>
  :host {
    --kwl-out:      ${v.out};
    --kwl-zu:       ${v.zu};
    --kwl-ab:       ${v.ab};
    --kwl-fort:     ${v.fort};
    --kwl-hi:       ${v.hi};
    --kwl-hi-bg:    ${v.hiBg};
    --kwl-out-pill: ${v.outPill};
    --kwl-in-pill:  ${v.inPill};
    --kwl-out-bdr:  ${v.outBdr};
    --kwl-in-bdr:   ${v.inBdr};
  }

  @keyframes flow { to { stroke-dashoffset: -9; } }

  ha-card { overflow: hidden; }

  /* ── Header ── */
  .hdr {
    padding: 14px 16px 12px;
    border-bottom: 1px solid var(--divider-color, rgba(0,0,0,.12));
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .eyebrow {
    font-size: 10px;
    font-weight: 500;
    letter-spacing: .10em;
    text-transform: uppercase;
    color: var(--secondary-text-color);
    margin-bottom: 2px;
  }
  .card-name {
    font-size: 16px;
    font-weight: 500;
    color: var(--primary-text-color);
  }
  .status-chip {
    display: inline-block;
    border-radius: 20px;
    padding: 4px 11px;
    font-size: 12px;
    font-weight: 500;
    background: var(--kwl-hi-bg);
    color: var(--kwl-hi);
  }
  .sub-info {
    font-size: 10px;
    color: var(--secondary-text-color);
    margin-top: 4px;
    text-align: right;
  }
  .explain {
    padding: 6px 16px 8px;
    font-size: 11px;
    color: var(--secondary-text-color);
    background: var(--secondary-background-color, rgba(0,0,0,.03));
    border-bottom: 1px solid var(--divider-color, rgba(0,0,0,.12));
    font-style: italic;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 8px 16px 0;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    border-radius: 14px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 500;
    font-family: inherit;
    color: var(--secondary-text-color);
    background: var(--secondary-background-color, rgba(0,0,0,.05));
    border: 1px solid var(--divider-color, rgba(0,0,0,.12));
  }
  .chip-btn { cursor: pointer; }
  .chip-btn:hover { border-color: var(--primary-color); }
  .chip-on   { color: var(--primary-color); border-color: var(--primary-color); }
  .chip-warn { color: var(--warning-color, #ff9800); border-color: var(--warning-color, #ff9800); }
  .chip-err  { color: var(--error-color, #db4437); border-color: var(--error-color, #db4437); }

  /* ── Device section ── */
  .device {
    padding: 14px 16px 12px;
    display: grid;
    grid-template-columns: auto 1fr auto;
    grid-template-rows: auto auto auto auto;
    column-gap: 10px;
    row-gap: 8px;
    align-items: center;
  }
  .pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    border-radius: 6px;
    padding: 3px 9px;
    font-size: 9px;
    font-weight: 500;
    letter-spacing: .09em;
    text-transform: uppercase;
  }
  .t-lbl {
    font-size: 9px;
    font-weight: 500;
    letter-spacing: .09em;
    text-transform: uppercase;
    margin-bottom: 2px;
  }
  .t-val {
    font-family: var(--paper-font-code_-_font-family, 'Courier New', monospace);
    font-size: 21px;
    font-weight: 500;
    line-height: 1;
  }
  .t-unit {
    font-size: 12px;
    font-weight: 400;
    color: var(--secondary-text-color);
  }
  .t-right { text-align: right; }

  .dev-box {
    background: var(--secondary-background-color, rgba(0,0,0,.05));
    border: 1px solid var(--divider-color, rgba(0,0,0,.12));
    border-radius: 10px;
    padding: 10px 8px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
  }
  .dev-lbl {
    font-size: 8px;
    font-weight: 500;
    letter-spacing: .10em;
    text-transform: uppercase;
    color: var(--secondary-text-color);
    line-height: 1.5;
  }
  .wrg-val {
    font-family: var(--paper-font-code_-_font-family, 'Courier New', monospace);
    font-size: 18px;
    font-weight: 500;
    color: var(--kwl-hi);
    line-height: 1;
  }
  .wrg-lbl {
    font-size: 7px;
    font-weight: 500;
    letter-spacing: .10em;
    text-transform: uppercase;
    color: var(--secondary-text-color);
  }
  .dev-div {
    height: 1px;
    background: var(--divider-color, rgba(0,0,0,.12));
    width: 100%;
    margin: 3px 0;
  }
  .stufe {
    font-size: 10px;
    font-weight: 500;
    color: var(--secondary-text-color);
  }
  .bypass {
    font-size: 9px;
    font-weight: 500;
    color: var(--secondary-text-color);
    letter-spacing: .03em;
  }
  .bypass-open {
    color: var(--kwl-fort);
  }
  .t-humidity {
    font-size: 11px;
    font-weight: 500;
    color: var(--secondary-text-color);
    margin-top: 3px;
  }

  /* ── Rooms ── */
  .rooms {
    border-top: 1px solid var(--divider-color, rgba(0,0,0,.12));
    padding: 12px 16px 16px;
    display: grid;
    grid-template-columns: 1fr 1px 1fr;
    gap: 0 14px;
  }
  .rg-hdr {
    display: flex;
    align-items: center;
    gap: 5px;
    margin-bottom: 8px;
  }
  .r-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .rg-lbl {
    font-size: 9px;
    font-weight: 500;
    letter-spacing: .10em;
    text-transform: uppercase;
    color: var(--secondary-text-color);
  }
  .room {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 9px;
    background: var(--secondary-background-color, rgba(0,0,0,.05));
    border-radius: 8px;
    margin-bottom: 5px;
    font-size: 13px;
    color: var(--primary-text-color);
  }
  .room:last-child { margin-bottom: 0; }
  .room-icon { font-size: 15px; }
  .v-div { background: var(--divider-color, rgba(0,0,0,.12)); }
</style>`;
  }

  /* ──────────────────────────────────── Render ── */

  _render() {
    if (!this._config || !this._shadow) return;

    const cfg  = this._config;
    const ent  = cfg.entities || {};
    const dark = this._dark;

    /* Temperaturen */
    const tAus  = this._num(ent.aussenluft);
    const tZu   = this._num(ent.zuluft);
    const tAb   = this._num(ent.abluft);
    const tFort = this._num(ent.fortluft);

    /* Status / Steuerung */
    const status = this._state(ent.status) || '';
    const stufe  = this._state(ent.stufe)  || '';
    const vol    = this._num(ent.volumenstrom);
    const wrgEnt = ent.wrg ? this._num(ent.wrg) : null;
    const wrg    = wrgEnt !== null
      ? Math.round(wrgEnt)
      : this._calcWrg(tZu, tAus, tAb);
    const bypass = ent.bypass ? this._state(ent.bypass) : null;
    const feuchte = ent.feuchte ? this._num(ent.feuchte) : null;

    /* Optionale Zusatzanzeigen: Filter-Restlaufzeit und Sommermodus-Schalter */
    const filterDays = ent.filter ? this._num(ent.filter) : null;
    const warnDays   = Number.isFinite(+cfg.filter_warn_days) ? +cfg.filter_warn_days : 30;
    const sommerOn   = ent.sommer ? this._state(ent.sommer) === 'on' : null;
    const sommerKnown = ent.sommer && this._hass && this._hass.states[ent.sommer];
    const chips = [];
    if (sommerKnown) {
      chips.push(`<button class="chip chip-btn ${sommerOn ? 'chip-on' : ''}" id="chip-sommer"
        title="Sommermodus (Nachtkühlung) umschalten">☀ Sommermodus ${sommerOn ? 'an' : 'aus'}</button>`);
    }
    if (filterDays !== null) {
      const cls = filterDays <= 0 ? 'chip-err' : filterDays <= warnDays ? 'chip-warn' : '';
      const txt = filterDays <= 0 ? 'Filter wechseln' : `Filter: noch ${Math.round(filterDays)} Tage`;
      chips.push(`<div class="chip ${cls}">🧰 ${txt}</div>`);
    }

    const leistung = ent.leistung ? this._num(ent.leistung) : null;
    if (leistung !== null) chips.push(`<div class="chip">⚡ ${Math.round(leistung)} W</div>`);
    const wrgP = ent.wrg_leistung ? this._num(ent.wrg_leistung) : null;
    if (wrgP !== null) chips.push(`<div class="chip">🔥 WRG +${Math.round(wrgP)} W</div>`);
    const known = (id) => id && this._hass && this._hass.states[id];
    if (known(ent.stoss)) {
      chips.push(`<button class="chip chip-btn" id="chip-stoss" title="Stoßlüftung starten">💨 Stoßlüftung</button>`);
    }
    if (known(ent.fan)) {
      chips.push(`<button class="chip chip-btn" id="chip-fan" title="Lüftungsstufe ändern">🌀 Lüftung</button>`);
    }
    const fehlerState = ent.fehler ? this._state(ent.fehler) : null;
    if (fehlerState !== null && fehlerState !== 'OK') {
      chips.push(`<div class="chip chip-err">⚠ Fehler aktiv</div>`);
    }

    /* Status-Chip */
    const cooling     = status.includes('Kühlt');
    const statusLabel = cooling           ? 'Kühlt'
                      : status.includes('Bereit')   ? 'Bereit'
                      : status.includes('Inaktiv')  ? 'Inaktiv'
                      : stufe || status.split(' – ')[0] || '—';
    const statusIcon  = cooling ? '❄' : '💨';

    /* Sub-Info-Zeile */
    const sub = [stufe, vol !== null ? `${Math.round(vol)} m³/h` : null]
      .filter(Boolean).join(' · ');

    /* Erklärungszeile (optional: show_explanation) */
    const explain = cfg.show_explanation
      ? this._explain(status, tAus, tAb, bypass)
      : '';

    /* Räume */
    const defaultZu = [
      { name: 'Schlafzimmer',  icon: '🛏' },
      { name: 'Wohnzimmer',    icon: '🛋' },
      { name: 'Arbeitszimmer', icon: '💼' },
    ];
    const defaultAb = [
      { name: 'Bad',   icon: '🚿' },
      { name: 'Küche', icon: '🍳' },
      { name: 'HTR',   icon: '🔧' },
    ];
    const roomsZu = cfg.rooms?.zuluft  || defaultZu;
    const roomsAb = cfg.rooms?.abluft  || defaultAb;

    const roomRow = (r) =>
      `<div class="room"><span class="room-icon">${r.icon || ''}</span><span>${r.name}</span></div>`;

    const name = cfg.name || 'Maico KWL';

    /* Farben für Arrow-SVGs (CSS-vars nicht direkt in SVG-Attributen verfügbar) */
    const colors = dark ? {
      out:  '#52C2F0', zu: '#F0883A', ab: '#E8733A', fort: '#2EC8A8',
    } : {
      out:  '#1A74AF', zu: '#C4601A', ab: '#9E3A10', fort: '#157A5A',
    };

    /* ── HTML ── */
    this._shadow.innerHTML = `
${this._css(dark)}

<ha-card>
  <!-- Header -->
  <div class="hdr">
    <div>
      <div class="eyebrow">Lüftungsanlage</div>
      <div class="card-name">${name}</div>
    </div>
    <div>
      <div class="status-chip">${statusIcon} ${statusLabel}</div>
      ${sub ? `<div class="sub-info">${sub}</div>` : ''}
    </div>
  </div>
  ${explain ? `<div class="explain">${explain}</div>` : ''}
  ${chips.length ? `<div class="chips">${chips.join('')}</div>` : ''}

  <!-- Device schema -->
  <div class="device">

    <!-- Zeile 0: Außen / Innen Badges -->
    <div class="pill"
         style="background:var(--kwl-out-pill);border:.5px solid var(--kwl-out-bdr);color:var(--kwl-out)">
      ☁ Außen
    </div>
    <div></div>
    <div class="pill"
         style="background:var(--kwl-in-pill);border:.5px solid var(--kwl-in-bdr);color:var(--kwl-zu);justify-self:end">
      🏠 Innen
    </div>

    <!-- Zeile 1: Außenluft ──→ Zuluft -->
    <div>
      <div class="t-lbl" style="color:var(--kwl-out)">Außenluft</div>
      <div class="t-val" style="color:var(--kwl-out)">
        ${this._fmt(tAus)}<span class="t-unit">°C</span>
      </div>
    </div>
    ${this._arrowSvg('right', colors.out)}
    <div class="t-right">
      <div class="t-lbl" style="color:var(--kwl-zu)">Zuluft</div>
      <div class="t-val" style="color:var(--kwl-zu)">
        ${this._fmt(tZu)}<span class="t-unit">°C</span>
      </div>
    </div>

    <!-- Zeile 2: Gerätebox -->
    <div></div>
    <div class="dev-box">
      <div class="dev-lbl">Wärme-<br>tauscher</div>
      <div class="wrg-val">${wrg !== null ? wrg : '—'}<span class="t-unit">%</span></div>
      <div class="wrg-lbl">WRG</div>
      <div class="dev-div"></div>
      <div class="stufe">${stufe || '—'}</div>
      ${bypass !== null ? `
      <div class="dev-div"></div>
      <div class="bypass ${bypass === 'Offen' ? 'bypass-open' : ''}">
        ${bypass === 'Offen' ? '↕' : '✕'} Bypass ${bypass}
      </div>` : ''}
    </div>
    <div></div>

    <!-- Zeile 3: Fortluft ←── Abluft -->
    <div>
      <div class="t-lbl" style="color:var(--kwl-fort)">Fortluft</div>
      <div class="t-val" style="color:var(--kwl-fort)">
        ${this._fmt(tFort)}<span class="t-unit">°C</span>
      </div>
    </div>
    ${this._arrowSvg('left', colors.ab)}
    <div class="t-right">
      <div class="t-lbl" style="color:var(--kwl-ab)">Abluft</div>
      <div class="t-val" style="color:var(--kwl-ab)">
        ${this._fmt(tAb)}<span class="t-unit">°C</span>
      </div>
      ${feuchte !== null ? `<div class="t-humidity">💧 ${this._fmt(feuchte, 0)} %</div>` : ''}
    </div>

  </div>

  <!-- Räume -->
  <div class="rooms">
    <div>
      <div class="rg-hdr">
        <div class="r-dot" style="background:var(--kwl-out)"></div>
        <span class="rg-lbl">Zuluft</span>
      </div>
      ${roomsZu.map(roomRow).join('')}
    </div>
    <div class="v-div"></div>
    <div>
      <div class="rg-hdr">
        <div class="r-dot" style="background:var(--kwl-ab)"></div>
        <span class="rg-lbl">Abluft</span>
      </div>
      ${roomsAb.map(roomRow).join('')}
    </div>
  </div>
</ha-card>`;

    const btn = this._shadow.getElementById('chip-sommer');
    if (btn) {
      btn.addEventListener('click', () => {
        const id = ent.sommer;
        const domain = id.split('.')[0];
        this._hass.callService(domain, 'toggle', { entity_id: id });
      });
    }
    const stossBtn = this._shadow.getElementById('chip-stoss');
    if (stossBtn) {
      stossBtn.addEventListener('click', () => {
        this._hass.callService('button', 'press', { entity_id: ent.stoss });
      });
    }
    const fanBtn = this._shadow.getElementById('chip-fan');
    if (fanBtn) {
      fanBtn.addEventListener('click', () => {
        this.dispatchEvent(new CustomEvent('hass-more-info', {
          bubbles: true, composed: true, detail: { entityId: ent.fan },
        }));
      });
    }
  }
}

/* ── GUI-Editor ──────────────────────────────────────────────────────────── */

class MaicoKwlCardEditor extends HTMLElement {
  constructor() {
    super();
    this._shadow = this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass   = null;
    this._missing = {};
  }

  setConfig(config) {
    this._config = JSON.parse(JSON.stringify(config));
    this._render();
  }

  /** Entity-Register (nur im Editor, Admin) – einmal laden */
  async _registry() {
    if (!this._reg) this._reg = await this._hass.callWS({ type: 'config/entity_registry/list' });
    return this._reg;
  }

  /** Findet die Entität einer Zusatzanzeige: gleiche Integration, gleiches Gerät wie die Sensoren der Karte */
  async _resolveFeature(uid) {
    if (!this._hass || !this._hass.callWS) return null;
    let reg;
    try { reg = await this._registry(); } catch (e) { return null; }
    const ent = this._config.entities || {};
    const anchorId = ['status', 'stufe', 'aussenluft', 'zuluft', 'abluft', 'fortluft']
      .map((k) => ent[k]).find(Boolean);
    const anchor = reg.find((e) => e.entity_id === anchorId);
    const dev = anchor ? anchor.device_id : null;
    const keyOf = (e) => {
      const m = /^maico_kwl_(?:[0-9a-z]{26}_)?(.+)$/i.exec(e.unique_id || '');
      return m ? m[1] : null;
    };
    const cands = reg.filter((e) => e.platform === 'maico_kwl' && keyOf(e) === uid && !e.disabled_by);
    const same  = cands.filter((e) => dev && e.device_id === dev);
    const pick  = (same.length ? same : cands)[0];
    return pick ? pick.entity_id : null;
  }

  set hass(hass) {
    this._hass = hass;
    this._shadow.querySelectorAll('ha-entity-picker')
      .forEach(p => { p.hass = hass; });
  }

  /* ── Defaults ── */
  _defaultRooms(group) {
    return group === 'zuluft'
      ? [{ name: 'Schlafzimmer', icon: '🛏' }, { name: 'Wohnzimmer', icon: '🛋' }, { name: 'Arbeitszimmer', icon: '💼' }]
      : [{ name: 'Bad', icon: '🚿' }, { name: 'Küche', icon: '🍳' }, { name: 'HTR', icon: '🔧' }];
  }

  _fire() {
    this.dispatchEvent(new CustomEvent('config-changed', {
      detail: { config: this._config },
      bubbles: true,
      composed: true,
    }));
  }

  /* ── Render ── */
  _render() {
    const cfg    = this._config;
    const ent    = cfg.entities || {};
    const rooms  = cfg.rooms    || {};
    const rZu    = rooms.zuluft || this._defaultRooms('zuluft');
    const rAb    = rooms.abluft || this._defaultRooms('abluft');

    const entityFields = [
      { key: 'aussenluft',   label: 'Außenluft-Sensor',              req: true  },
      { key: 'zuluft',       label: 'Zuluft-Sensor',                 req: true  },
      { key: 'abluft',       label: 'Abluft-Sensor',                 req: true  },
      { key: 'fortluft',     label: 'Fortluft-Sensor',               req: true  },
      { key: 'status',       label: 'Sommermodus Status',            req: true  },
      { key: 'stufe',        label: 'Lüftungsstufe',                req: true  },
      { key: 'volumenstrom', label: 'Volumenstrom',                  req: false },
      { key: 'wrg',          label: 'Wärmerückgewinnung (optional)', req: false },
      { key: 'bypass',       label: 'Bypass Status (optional)',       req: false },
      { key: 'feuchte',      label: 'Luftfeuchte (optional)',         req: false },
    ];

    /* Zusatzanzeigen: Checkbox, die Entität wird automatisch gefunden (uid = Schlüssel der Integration) */
    const features = MaicoKwlCardEditor.FEATURES;

    const roomRows = (group, list) => list.map((r, i) => `
      <div class="rr">
        <input class="r-icon" type="text"
               data-group="${group}" data-index="${i}" data-field="icon"
               value="${r.icon || ''}" placeholder="🏠" maxlength="2">
        <input class="r-name" type="text"
               data-group="${group}" data-index="${i}" data-field="name"
               value="${r.name || ''}" placeholder="Raumname">
        <button class="r-del" data-group="${group}" data-index="${i}"
                title="Raum entfernen">✕</button>
      </div>`).join('');

    this._shadow.innerHTML = `
<style>
  :host { display: block; }
  .wrap { padding: 4px 0 16px; }

  /* ── Sections ── */
  .sec { margin-bottom: 20px; }
  .sec-title {
    font-size: 11px; font-weight: 600; letter-spacing: .10em;
    text-transform: uppercase; color: var(--secondary-text-color);
    margin: 0 0 10px; padding-bottom: 6px;
    border-bottom: 1px solid var(--divider-color);
  }

  /* ── Fields ── */
  .field { margin-bottom: 12px; }
  .field label {
    display: block; font-size: 12px;
    color: var(--secondary-text-color); margin-bottom: 4px;
  }
  .field label .req { color: var(--error-color); margin-left: 2px; }

  ha-entity-picker { display: block; }

  input[type="text"] {
    width: 100%; padding: 8px 10px;
    border: 1px solid var(--divider-color); border-radius: 6px;
    background: var(--secondary-background-color);
    color: var(--primary-text-color); font-size: 14px;
    box-sizing: border-box;
  }
  input[type="text"]:focus {
    outline: none; border-color: var(--primary-color);
  }

  /* ── Room rows ── */
  .rr { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
  .r-icon { width: 44px !important; text-align: center; flex-shrink: 0; padding: 8px 4px !important; }
  .r-name { flex: 1; }
  .r-del {
    width: 32px; height: 36px; flex-shrink: 0;
    background: none; border: 1px solid var(--divider-color);
    border-radius: 6px; color: var(--secondary-text-color);
    cursor: pointer; font-size: 12px; transition: all .15s;
  }
  .r-del:hover { border-color: var(--error-color); color: var(--error-color); }

  /* ── Add button ── */
  .add-btn {
    display: flex; align-items: center; gap: 6px;
    width: 100%; margin-top: 2px; padding: 8px 12px;
    background: none; border: 1px dashed var(--divider-color);
    border-radius: 6px; color: var(--secondary-text-color);
    font-size: 13px; cursor: pointer; transition: all .15s;
  }
  .add-btn:hover { border-color: var(--primary-color); color: var(--primary-color); }

  /* ── Hint ── */
  .hint { font-size: 11px; color: var(--secondary-text-color); margin-top: 2px; }

  /* ── Checkbox ── */
  .chk { display: flex !important; align-items: center; gap: 8px; cursor: pointer;
         font-size: 14px !important; color: var(--primary-text-color) !important; }
  .chk input { width: 18px; height: 18px; margin: 0; }
</style>

<div class="wrap">

  <!-- Kartenname -->
  <div class="sec">
    <p class="sec-title">Allgemein</p>
    <div class="field">
      <label>Kartenname</label>
      <input id="inp-name" type="text"
             value="${cfg.name || ''}" placeholder="Maico WS 300 Flat">
    </div>
    <div class="field">
      <label class="chk">
        <input id="inp-explain" type="checkbox" ${cfg.show_explanation ? 'checked' : ''}>
        Erklärungszeile anzeigen
      </label>
      <p class="hint">Zeigt unter der Kopfzeile in einem Satz, warum die Anlage gerade so läuft (z. B. „Außen 3,2 °C kühler als innen“).</p>
    </div>
  </div>

  <!-- Sensoren -->
  <div class="sec">
    <p class="sec-title">Sensoren</p>
    ${entityFields.map(f => `
      <div class="field">
        <label>${f.label}${f.req ? '<span class="req">*</span>' : ''}</label>
        <ha-entity-picker
          data-ekey="${f.key}"
          value="${ent[f.key] || ''}"
          allow-custom-entity
        ></ha-entity-picker>
      </div>`).join('')}
  </div>

  <!-- Zusatzanzeigen -->
  <div class="sec">
    <p class="sec-title">Zusatzanzeigen</p>
    <p class="hint">Kleine Schaltflächen und Werte unter der Kopfzeile. Die passende Entität wird automatisch gefunden.</p>
    ${features.map(f => {
      const on = Object.prototype.hasOwnProperty.call(ent, f.key);
      return `
      <div class="field" style="margin-top:10px">
        <label class="chk">
          <input type="checkbox" data-feat="${f.key}" ${on ? 'checked' : ''}>
          ${f.label}
        </label>
        ${on ? `<ha-entity-picker data-ekey="${f.key}" value="${ent[f.key] || ''}" allow-custom-entity></ha-entity-picker>` : ''}
        ${on && !ent[f.key] && this._missing[f.key]
          ? '<p class="hint">Nicht automatisch gefunden – bitte die Entität auswählen.</p>' : ''}
      </div>`;
    }).join('')}
  </div>

  <!-- Zuluft-Räume -->
  <div class="sec">
    <p class="sec-title">Zuluft-Räume</p>
    <p class="hint">Räume, in die Frischluft eingeblasen wird.</p>
    <div id="rg-zuluft" style="margin-top:8px">${roomRows('zuluft', rZu)}</div>
    <button class="add-btn" data-add="zuluft">＋ Raum hinzufügen</button>
  </div>

  <!-- Abluft-Räume -->
  <div class="sec">
    <p class="sec-title">Abluft-Räume</p>
    <p class="hint">Räume, aus denen Luft abgesaugt wird.</p>
    <div id="rg-abluft" style="margin-top:8px">${roomRows('abluft', rAb)}</div>
    <button class="add-btn" data-add="abluft">＋ Raum hinzufügen</button>
  </div>

</div>`;

    /* ── Event listeners (after paint) ── */
    requestAnimationFrame(() => {

      /* Hass an Entity-Picker übergeben */
      this._shadow.querySelectorAll('ha-entity-picker').forEach(picker => {
        if (this._hass) picker.hass = this._hass;
        picker.addEventListener('value-changed', (ev) => {
          const key = picker.dataset.ekey;
          this._config = {
            ...this._config,
            entities: { ...this._config.entities, [key]: ev.detail.value },
          };
          this._fire();
        });
      });

      /* Kartenname */
      const nameInput = this._shadow.getElementById('inp-name');
      nameInput?.addEventListener('change', (ev) => {
        this._config = { ...this._config, name: ev.target.value };
        this._fire();
      });

      /* Erklärungszeile ein/aus */
      this._shadow.getElementById('inp-explain')?.addEventListener('change', (ev) => {
        this._config = { ...this._config, show_explanation: ev.target.checked };
        this._fire();
      });

      /* Zusatzanzeigen ein/aus (mit automatischer Entitäten-Suche) */
      this._shadow.querySelectorAll('input[data-feat]').forEach(box => {
        box.addEventListener('change', async (ev) => {
          const key = ev.target.dataset.feat;
          const feat = MaicoKwlCardEditor.FEATURES.find(f => f.key === key);
          const entities = { ...(this._config.entities || {}) };
          if (!ev.target.checked) {
            delete entities[key];
            delete this._missing[key];
            this._config = { ...this._config, entities };
            this._render();
            if (this._hass) this.hass = this._hass;
            this._fire();
            return;
          }
          entities[key] = '';
          this._config = { ...this._config, entities };
          const id = await this._resolveFeature(feat.uid);
          if (id) {
            delete this._missing[key];
            this._config = { ...this._config, entities: { ...this._config.entities, [key]: id } };
          } else {
            this._missing[key] = true;
          }
          this._render();
          if (this._hass) this.hass = this._hass;
          this._fire();
        });
      });

      /* Raum-Felder (icon / name) */
      this._shadow.querySelectorAll('.r-icon, .r-name').forEach(inp => {
        inp.addEventListener('change', (ev) => {
          const { group, index, field } = ev.target.dataset;
          const rooms = JSON.parse(JSON.stringify(this._config.rooms || {}));
          if (!rooms[group]) rooms[group] = this._defaultRooms(group);
          rooms[group][+index][field] = ev.target.value;
          this._config = { ...this._config, rooms };
          this._fire();
        });
      });

      /* Raum löschen */
      this._shadow.querySelectorAll('.r-del').forEach(btn => {
        btn.addEventListener('click', (ev) => {
          const { group, index } = ev.currentTarget.dataset;
          const rooms = JSON.parse(JSON.stringify(this._config.rooms || {}));
          if (!rooms[group]) rooms[group] = this._defaultRooms(group);
          rooms[group].splice(+index, 1);
          this._config = { ...this._config, rooms };
          this._render();
          if (this._hass) this.hass = this._hass;
          this._fire();
        });
      });

      /* Raum hinzufügen */
      this._shadow.querySelectorAll('[data-add]').forEach(btn => {
        btn.addEventListener('click', (ev) => {
          const group = ev.currentTarget.dataset.add;
          const rooms = JSON.parse(JSON.stringify(this._config.rooms || {}));
          if (!rooms[group]) rooms[group] = this._defaultRooms(group);
          rooms[group].push({ name: 'Neuer Raum', icon: '🏠' });
          this._config = { ...this._config, rooms };
          this._render();
          if (this._hass) this.hass = this._hass;
          this._fire();
          /* Fokus auf das neue Namens-Feld */
          setTimeout(() => {
            const all = this._shadow.querySelectorAll(`#rg-${group} .r-name`);
            all[all.length - 1]?.focus();
          }, 50);
        });
      });

    });
  }
}

MaicoKwlCardEditor.FEATURES = [
  { key: 'filter',       uid: 'filter_restlaufzeit_zuluft', label: 'Filteranzeige (Restlaufzeit)' },
  { key: 'sommer',       uid: 'sommermodus',                label: 'Sommermodus-Schalter' },
  { key: 'leistung',     uid: 'leistung',                   label: 'Stromleistung (geschätzt)' },
  { key: 'wrg_leistung', uid: 'wrg_leistung',               label: 'Wärmegewinn der Wärmerückgewinnung' },
  { key: 'stoss',        uid: 'stosslueftung',              label: 'Knopf „Stoßlüftung“' },
  { key: 'fan',          uid: 'lueftung',                   label: 'Knopf „Lüftung“ (Stufen ändern)' },
  { key: 'fehler',       uid: 'fehler',                     label: 'Fehleranzeige (nur bei Fehler)' },
];

/* ── Registrierung ── */
if (!customElements.get('maico-kwl-card')) {
  customElements.define('maico-kwl-card', MaicoKwlCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === 'maico-kwl-card')) window.customCards.push({
  type:        'maico-kwl-card',
  name:        'Maico KWL Card',
  description: 'Grafische Karte für Maico KWL Lüftungsanlagen mit animierten Luftströmen.',
  preview:     true,
});

if (!customElements.get('maico-kwl-card-editor')) {
  customElements.define('maico-kwl-card-editor', MaicoKwlCardEditor);
}

console.info(
  '%c MAICO-KWL-CARD %c v1.6.0 ',
  'background:#1A74AF;color:#fff;padding:2px 4px;border-radius:3px 0 0 3px;font-weight:bold',
  'background:#157A5A;color:#fff;padding:2px 4px;border-radius:0 3px 3px 0'
);
