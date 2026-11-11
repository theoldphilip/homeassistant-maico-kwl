/**
 * Maico KWL Card – Custom Lovelace Card
 * Grafische Karte für Maico KWL Lüftungsanlagen mit animierten Luftströmen.
 *
 * GitHub: https://github.com/theoldphilip/homeassistant-maico-kwl
 * Version: 2.0.0
 *
 * Einbindung: wird von der Integration automatisch bereitgestellt (Option
 * „Karte automatisch bereitstellen“). Alternativ manuell als Ressource:
 *   URL: /local/maico-kwl-card.js   Typ: JavaScript-Modul
 *
 * Beispiel-Konfiguration (alles außer den ersten sechs Sensoren ist optional;
 * der GUI-Editor findet die Entitäten der Zusatzanzeigen automatisch):
 *   type: custom:maico-kwl-card
 *   name: Maico WS 300 Flat
 *   show_explanation: true      # optional: Erklärungszeile unter der Kopfzeile
 *   filter_warn_days: 30        # optional: ab wie vielen Resttagen der Filter warnt
 *   entities:
 *     aussenluft: sensor.maico_ws_300_flat_aussenluft
 *     zuluft:     sensor.maico_ws_300_flat_zuluft
 *     abluft:     sensor.maico_ws_300_flat_abluft
 *     fortluft:   sensor.maico_ws_300_flat_fortluft
 *     status:     sensor.htr_maico_ws_300_flat_sommermodus_status
 *     stufe:      sensor.maico_ws_300_flat_luftungsstufe
 *     volumenstrom: sensor.maico_ws_300_flat_volumenstrom_zuluft
 *     wrg:        sensor.maico_ws_300_flat_warmeruckgewinnung
 *     bypass:     sensor.maico_ws_300_flat_bypass_status
 *     feuchte:    sensor.maico_ws_300_flat_relative_feuchte_abluft
 *     # Kennzahlen
 *     leistung:     sensor.maico_ws_300_flat_leistung_geschatzt
 *     wrg_leistung: sensor.maico_ws_300_flat_warmeruckgewinnung_leistung_geschatzt
 *     # Filter: Restlaufzeit + Knöpfe zum Quittieren (nur die, die das Gerät hat)
 *     filter:        sensor.maico_ws_300_flat_filterwechsel
 *     filter_geraet: button.maico_ws_300_flat_filter_gewechselt_gerat
 *     filter_aussen: button.maico_ws_300_flat_filter_gewechselt_aussenluft
 *     filter_raum:   button.maico_ws_300_flat_filter_gewechselt_raumluft
 *     # Bedienung
 *     sommer:     switch.maico_ws_300_flat_sommermodus
 *     stoss:      button.maico_ws_300_flat_stosslueftung
 *     stoss_rest: sensor.maico_ws_300_flat_stosslueftung_restzeit
 *     fan:        fan.maico_ws_300_flat_lueftung          # Knopf „Stufe“ (Auswahlmenü)
 *     vol_reduziert: number.maico_ws_300_flat_volumenstrom_reduziert  # m³/h im Stufenmenü
 *     vol_nenn:      number.maico_ws_300_flat_volumenstrom_nennlueftung
 *     vol_intensiv:  number.maico_ws_300_flat_volumenstrom_intensiv
 *     betriebsart:   sensor.maico_ws_300_flat_betriebsart     # aktive Betriebsart im Stufenmenü
 *     # Fehler: Hinweis nur bei Fehler, Knopf zum Quittieren
 *     fehler:       sensor.maico_ws_300_flat_fehler
 *     fehler_reset: button.maico_ws_300_flat_fehler_quittieren
 *   rooms:                      # werden eingeklappt unter „Räume“ angezeigt
 *     zuluft:
 *       - { name: Schlafzimmer,  icon: "🛏" }
 *       - { name: Wohnzimmer,    icon: "🛋" }
 *       - { name: Arbeitszimmer, icon: "💼" }
 *     abluft:
 *       - { name: Bad,           icon: "🚿" }
 *       - { name: Küche,         icon: "🍳" }
 *       - { name: HTR,           icon: "🔧" }
 */

/* Zeichenkette für HTML maskieren (Namen aus der Konfiguration) */
const kwlEsc = (s) => String(s === undefined || s === null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/* Symbole (Linien-Icons, erben die Textfarbe) */
const KWL_ICONS = {
  fan:     '<path d="M12 12c0-4 1-8 4-8s3 4 0 6l-4 2z"/><path d="M12 12c4 0 8 1 8 4s-4 3-6 0l-2-4z"/><path d="M12 12c0 4-1 8-4 8s-3-4 0-6l4-2z"/><path d="M12 12c-4 0-8-1-8-4s4-3 6 0l2 4z"/>',
  wind:    '<path d="M3 8h11a3 3 0 1 0-3-3"/><path d="M3 12h16a3 3 0 1 1-3 3"/><path d="M3 16h7"/>',
  snow:    '<path d="M12 3v18M4.2 7.5l15.6 9M4.2 16.5l15.6-9"/>',
  sun:     '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  sliders: '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2" style="fill:var(--card-background-color,#1b1d20)"/><circle cx="15" cy="12" r="2" style="fill:var(--card-background-color,#1b1d20)"/><circle cx="8" cy="18" r="2" style="fill:var(--card-background-color,#1b1d20)"/>',
  home:    '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/>',
  chevron: '<path d="M6 9l6 6 6-6"/>',
  alert:   '<path d="M12 3l10 18H2L12 3z"/><path d="M12 10v5M12 18v.5"/>',
  filter:  '<path d="M3 5h18l-7 8v6l-4 2v-8L3 5z"/>',
  check:   '<path d="M5 12l5 5 9-10"/>',
};
const kwlIcon = (name, size = 20) =>
  `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${KWL_ICONS[name]}</svg>`;

/* Wählbare Lüftungsstufen (Prozent = Wert für fan.set_percentage) */
const KWL_STAGES = [
  { id: 'schutz',    label: 'Schutzlüftung', match: 'schutz', pct: 25 },
  { id: 'reduziert', label: 'Reduziert',   match: 'reduz',   pct: 50,  vol: 'vol_reduziert' },
  { id: 'nenn',      label: 'Nennlüftung', match: 'nenn',    pct: 75,  vol: 'vol_nenn' },
  { id: 'intensiv',  label: 'Intensiv',    match: 'intensiv', pct: 100, vol: 'vol_intensiv' },
];

/* Wählbare Betriebsarten (Auto Zeit bewusst nicht dabei; Name = Preset des Lüftungs-Entity) */
const KWL_MODES = ['Manuell', 'Auto Sensor', 'Eco-Zuluft', 'Eco-Abluft'];

/* Filter, die quittiert werden können (Schlüssel in entities → Anzeigename) */
const KWL_FILTER_BUTTONS = [
  { key: 'filter_geraet', label: 'Filter Gerät' },
  { key: 'filter_aussen', label: 'Filter Außenluft' },
  { key: 'filter_raum',   label: 'Filter Raumluft' },
];

class MaicoKwlCard extends HTMLElement {
  constructor() {
    super();
    this._shadow = this.attachShadow({ mode: 'open' });
    this._config = null;
    this._hass  = null;
    this._dark  = false;
    this._roomsOpen = false;   /* Räume ein-/ausgeklappt */
    this._sheet = null;        /* offenes Menü: 'stufe' | 'filter' | null */
    this._dirty = false;       /* Neuzeichnen wartet, bis das Menü zu ist */
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
    const fanSt = this._config && this._config.entities && hass.states[this._config.entities.fan];
    const sig = JSON.stringify([this._dark, ids.map((id) => {
      const st = hass.states[id];
      return st ? st.state : null;
    }), fanSt && fanSt.attributes ? fanSt.attributes.preset_mode : null]);
    if (sig === this._sig) return;
    this._sig = sig;
    this._render();
  }

  getCardSize() { return 7; }

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

  _known(id) {
    return !!(id && this._hass && this._hass.states[id]);
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
   * Aufbau: Linienelement (flex:1) + fester Pfeilkopf als separates SVG.
   *
   * dir "right": Linie l→r, Pfeilkopf rechts  (Außenluft → Zuluft)
   * dir "left" : Linie r→l, Pfeilkopf links   (Abluft   → Fortluft)
   */
  _arrowSvg(dir, color) {
    const right = dir === 'right';
    const lineSvg = `
      <svg class="arrow-line" height="20" aria-hidden="true">
        <line class="flow" x1="${right ? '0%' : '100%'}" y1="10" x2="${right ? '100%' : '0%'}" y2="10" stroke="${color}"/>
      </svg>`;
    const headSvg = `
      <svg class="arrow-head" width="12" height="16" viewBox="0 0 12 16" aria-hidden="true">
        <polygon points="${right ? '0,0 12,8 0,16' : '12,0 0,8 12,16'}" fill="${color}"/>
      </svg>`;
    return `<div class="arrow">${right ? lineSvg + headSvg : headSvg + lineSvg}</div>`;
  }

  /* ──────────────────────────────────── CSS ── */

  _css(dark, boost) {
    const v = dark ? {
      out: '#52C2F0', zu: '#F0883A', ab: '#E8733A', fort: '#2EC8A8',
      hi: '#7fd3f5', hiBg: 'rgba(82,194,240,0.16)', hiBdr: '#52C2F0',
      errTx: '#ffb4b4', errBg: 'rgba(242,96,96,.14)', errBdr: 'rgba(242,96,96,.55)',
      warnTx: '#ffd08a', warnBg: 'rgba(255,171,64,.12)', warnBdr: 'rgba(255,171,64,.5)',
    } : {
      out: '#1A74AF', zu: '#C4601A', ab: '#9E3A10', fort: '#157A5A',
      hi: '#185FA5', hiBg: 'rgba(24,95,165,0.10)', hiBdr: '#185FA5',
      errTx: '#b3261e', errBg: 'rgba(219,68,55,.10)', errBdr: 'rgba(219,68,55,.5)',
      warnTx: '#8a5300', warnBg: 'rgba(255,152,0,.12)', warnBdr: 'rgba(230,130,0,.55)',
    };

    return `
<style>
  :host {
    --kwl-out:  ${v.out};
    --kwl-zu:   ${v.zu};
    --kwl-ab:   ${v.ab};
    --kwl-fort: ${v.fort};
    --kwl-hi:   ${v.hi};
    --kwl-hi-bg:  ${v.hiBg};
    --kwl-hi-bdr: ${v.hiBdr};
    --kwl-err-tx: ${v.errTx};  --kwl-err-bg: ${v.errBg};  --kwl-err-bdr: ${v.errBdr};
    --kwl-warn-tx: ${v.warnTx}; --kwl-warn-bg: ${v.warnBg}; --kwl-warn-bdr: ${v.warnBdr};
    --kwl-tile:  var(--secondary-background-color, rgba(127,127,127,.10));
    --kwl-line:  var(--divider-color, rgba(127,127,127,.28));
    --kwl-mono:  var(--code-font-family, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace);
  }

  @keyframes flow { to { stroke-dashoffset: -10; } }
  @keyframes sheet-up { from { transform: translateY(24px); opacity: 0; } to { transform: none; opacity: 1; } }

  ha-card { overflow: hidden; }
  button { font-family: inherit; color: inherit; }

  /* ── Kopf ── */
  .hdr {
    padding: 16px 16px 12px;
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
  }
  .hdr > div:first-child { min-width: 0; }
  .eyebrow {
    font-size: 11px; font-weight: 500; letter-spacing: .12em; text-transform: uppercase;
    color: var(--secondary-text-color); margin-bottom: 2px;
  }
  .card-name { font-size: 20px; font-weight: 600; color: var(--primary-text-color); }
  .hdr-r { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
  .status-chip {
    display: inline-flex; align-items: center; gap: 6px;
    border-radius: 999px; padding: 6px 12px;
    font-size: 13px; font-weight: 500;
    background: var(--kwl-hi-bg); color: var(--kwl-hi);
    border: 1px solid transparent; white-space: nowrap;
  }
  .status-chip.boost { font-weight: 600; border-color: var(--kwl-hi-bdr); }
  .sub-info { font-size: 12px; color: var(--secondary-text-color); }

  /* ── Warnhinweise ── */
  .banners { display: flex; flex-direction: column; gap: 8px; padding: 0 16px 12px; }
  .banner {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 12px; border-radius: 12px; border: 1px solid;
  }
  .banner svg { flex-shrink: 0; }
  .banner-txt { display: flex; flex-direction: column; gap: 1px; flex: 1; min-width: 0; }
  .banner-title { font-size: 13px; font-weight: 600; }
  .banner-sub { font-size: 12px; opacity: .85; }
  .banner-btn {
    min-height: 40px; padding: 0 12px; border-radius: 8px; border: 1px solid;
    background: transparent; font-size: 12px; font-weight: 500; cursor: pointer;
  }
  .banner-err  { background: var(--kwl-err-bg);  border-color: var(--kwl-err-bdr);  color: var(--kwl-err-tx); }
  .banner-warn { background: var(--kwl-warn-bg); border-color: var(--kwl-warn-bdr); color: var(--kwl-warn-tx); }
  .banner-btn  { border-color: currentColor; color: inherit; }

  .explain {
    padding: 8px 16px; font-size: 12px; font-style: italic;
    color: var(--secondary-text-color);
    background: var(--kwl-tile);
    border-top: 1px solid var(--kwl-line); border-bottom: 1px solid var(--kwl-line);
  }

  /* ── Schema ── */
  .device { padding: 16px 16px 6px; display: flex; flex-direction: column; gap: 10px; }
  .row { display: flex; align-items: center; gap: 8px; }
  .t-col { width: 96px; display: flex; flex-direction: column; gap: 2px; flex-shrink: 0; }
  .t-col.r { align-items: flex-end; text-align: right; }
  .t-lbl { font-size: 11px; font-weight: 500; letter-spacing: .08em; text-transform: uppercase; }
  .t-val { font-family: var(--kwl-mono); font-size: 22px; font-weight: 500; line-height: 1.1; }
  .t-unit { font-size: 12px; font-weight: 400; color: var(--secondary-text-color); }
  .t-humidity { font-size: 12px; color: var(--secondary-text-color); }

  .arrow { flex: 1; display: flex; align-items: center; min-width: 0; }
  .arrow-line { flex: 1; display: block; overflow: visible; min-width: 0; width: 100%; }
  .arrow-head { flex-shrink: 0; display: block; }
  .arrow-line line { stroke-width: ${boost ? 3 : 2}; stroke-dasharray: 6 4; animation: flow ${boost ? '.6s' : '1.2s'} linear infinite; }

  .dev-box {
    align-self: center; width: 168px; box-sizing: border-box; padding: 10px 12px;
    border-radius: 12px; background: var(--kwl-tile); border: 1px solid var(--kwl-line);
    display: flex; flex-direction: column; align-items: center; gap: 2px;
  }
  .dev-lbl { font-size: 11px; font-weight: 500; letter-spacing: .10em; text-transform: uppercase; color: var(--secondary-text-color); }
  .wrg-val { font-family: var(--kwl-mono); font-size: 24px; font-weight: 500; color: var(--kwl-hi); line-height: 1.1; }
  .bypass {
    font-size: 12px; color: var(--secondary-text-color);
    padding-top: 4px; margin-top: 2px; border-top: 1px solid var(--kwl-line); width: 100%; text-align: center;
  }
  .bypass-open { color: var(--kwl-fort); }

  /* ── Kennzahlen ── */
  .tiles { display: grid; gap: 8px; padding: 12px 16px 0; }
  .tile {
    padding: 10px 12px; border-radius: 12px; border: 1px solid var(--kwl-line);
    background: var(--kwl-tile); display: flex; flex-direction: column; justify-content: space-between; gap: 4px; min-width: 0;
  }
  .tile-lbl { font-size: 11px; font-weight: 500; letter-spacing: .04em; text-transform: uppercase; color: var(--secondary-text-color); }
  .tile-val { font-family: var(--kwl-mono); font-size: 18px; font-weight: 500; }
  .tile-val small { font-size: 12px; font-weight: 400; color: var(--secondary-text-color); }
  .tile-hi .tile-val { color: var(--kwl-hi); }
  .tile-warn { background: var(--kwl-warn-bg); border-color: var(--kwl-warn-bdr); }
  .tile-warn .tile-val, .tile-warn .tile-lbl { color: var(--kwl-warn-tx); }
  .tile-err  { background: var(--kwl-err-bg); border-color: var(--kwl-err-bdr); }
  .tile-err .tile-val, .tile-err .tile-lbl { color: var(--kwl-err-tx); }

  /* ── Bedienung ── */
  .actions { display: grid; gap: 8px; padding: 12px 16px 0; }
  .act {
    min-height: 68px; border-radius: 12px; border: 1px solid var(--kwl-line);
    background: var(--kwl-tile); cursor: pointer;
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
    font-size: 12px; font-weight: 500; padding: 6px;
  }
  .act small { font-size: 11px; font-weight: 400; color: var(--secondary-text-color); margin-top: -2px; }
  .act-on { background: var(--kwl-hi-bg); border-color: var(--kwl-hi-bdr); color: var(--kwl-hi); font-weight: 600; }
  .act-on small { color: var(--kwl-hi); font-weight: 500; }
  @media (hover: hover) { .act:hover, .banner-btn:hover { border-color: var(--primary-color); } }

  /* ── Räume ── */
  .rooms-btn {
    margin: 12px 16px 16px; width: calc(100% - 32px); min-height: 48px; padding: 0 14px;
    border-radius: 12px; border: 1px solid var(--kwl-line); background: transparent; cursor: pointer;
    display: flex; align-items: center; justify-content: space-between; font-size: 13px;
  }
  .rooms-btn .l, .rooms-btn .r { display: inline-flex; align-items: center; gap: 8px; }
  .rooms-btn .r { color: var(--secondary-text-color); font-size: 12px; }
  .rooms-btn .chev { transition: transform .15s; }
  .rooms-btn[aria-expanded="true"] .chev { transform: rotate(180deg); }
  .rooms { padding: 0 16px 16px; display: grid; grid-template-columns: 1fr 1px 1fr; gap: 0 14px; margin-top: -4px; }
  .rg-hdr { display: flex; align-items: center; gap: 5px; margin-bottom: 8px; }
  .r-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
  .rg-lbl { font-size: 10px; font-weight: 500; letter-spacing: .10em; text-transform: uppercase; color: var(--secondary-text-color); }
  .room {
    display: flex; align-items: center; gap: 8px; padding: 5px 9px;
    background: var(--kwl-tile); border-radius: 8px; margin-bottom: 5px;
    font-size: 13px; color: var(--primary-text-color);
  }
  .room:last-child { margin-bottom: 0; }
  .room-icon { font-size: 15px; }
  .v-div { background: var(--kwl-line); }

  /* ── Menüs (Bottom-Sheet) ── */
  dialog.sheet {
    border: 0; padding: 0; margin: auto auto 0; width: 100%; max-width: 480px; box-sizing: border-box;
    background: var(--card-background-color, #1b1d20); color: var(--primary-text-color);
    border-radius: 20px 20px 0 0; border-top: 1px solid var(--kwl-line);
    max-height: 92vh; overflow-y: auto;
    animation: sheet-up .18s ease-out;
  }
  dialog.sheet::backdrop { background: rgba(0,0,0,.62); }
  .sheet-in { outline: none; padding: 10px 16px 24px; display: flex; flex-direction: column; gap: 12px; }
  .grab { align-self: center; width: 40px; height: 4px; border-radius: 2px; background: var(--kwl-line); }
  .sheet-hd { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
  .sheet-title { font-size: 17px; font-weight: 600; }
  .sheet-sub { font-size: 12px; color: var(--secondary-text-color); }
  .sheet-note { margin: 0; font-size: 12px; line-height: 1.5; color: var(--secondary-text-color); }
  .opts { display: flex; flex-direction: column; gap: 8px; }
  .opt {
    min-height: 56px; padding: 0 14px; border-radius: 12px; border: 1px solid var(--kwl-line);
    background: var(--kwl-tile); cursor: pointer; text-align: left;
    display: flex; align-items: center; justify-content: space-between; font-size: 15px; font-weight: 500;
  }
  .opt .o-txt { display: flex; flex-direction: column; align-items: flex-start; gap: 1px; }
  .opt .o-sub { font-size: 12px; font-weight: 400; color: var(--secondary-text-color); }
  .opt-on { background: var(--kwl-hi-bg); border-color: var(--kwl-hi-bdr); font-weight: 600; }
  .opt-on svg { color: var(--kwl-hi); }
  label.opt { cursor: pointer; justify-content: flex-start; gap: 12px; min-height: 52px; }
  label.opt input { width: 20px; height: 20px; margin: 0; accent-color: var(--primary-color, #52C2F0); }
  .sheet-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .sbtn {
    min-height: 48px; border-radius: 12px; border: 1px solid var(--kwl-line); background: transparent;
    font-size: 14px; font-weight: 500; cursor: pointer;
  }
  .sbtn-primary { background: var(--primary-color, #52C2F0); border-color: var(--primary-color, #52C2F0); color: var(--text-primary-color, #0b1a22); font-weight: 600; }
  .sbtn[disabled] { opacity: .45; cursor: default; }
  .sheet-sec { font-size: 11px; font-weight: 500; letter-spacing: .10em; text-transform: uppercase; color: var(--secondary-text-color); margin-top: 4px; }
  .modes { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .mode {
    min-height: 44px; padding: 0 10px; border-radius: 12px; border: 1px solid var(--kwl-line);
    background: var(--kwl-tile); cursor: pointer; font-size: 14px; font-weight: 500;
  }
  .mode-on { background: var(--kwl-hi-bg); border-color: var(--kwl-hi-bdr); color: var(--kwl-hi); font-weight: 600; }
  .link-btn { align-self: center; background: none; border: 0; padding: 6px 8px; font-size: 12px; color: var(--primary-color); cursor: pointer; }

  @media (prefers-reduced-motion: reduce) {
    .arrow-line line, dialog.sheet { animation: none; }
  }
</style>`;
  }

  /* ──────────────────────────────────── Render ── */

  _render() {
    if (!this._config || !this._shadow) return;
    /* Solange ein Menü offen ist, nicht neu aufbauen (sonst springt/schließt es) */
    if (this._sheet) { this._dirty = true; return; }

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
    const restRaw = ent.stoss_rest ? this._num(ent.stoss_rest) : null;
    const restMin = restRaw !== null && restRaw > 0 ? Math.round(restRaw) : 0;
    const feuchte = ent.feuchte ? this._num(ent.feuchte) : null;
    const cooling = status.includes('Kühlt');

    /* ── Kopf: Stufe (oder Stoßlüftung / Kühlt) ── */
    /* „Inaktiv“ meint nur den Sommermodus – im Kopf besser die Lüftungsstufe zeigen */
    const statusLabel = restMin > 0               ? `Stoßlüftung · ${restMin} min`
                      : cooling                   ? 'Kühlt'
                      : status.includes('Bereit') ? 'Bereit'
                      : stufe || (status.includes('Inaktiv') ? 'Inaktiv' : status.split(' – ')[0]) || '—';
    const statusIcon  = restMin > 0 ? 'wind' : cooling ? 'snow' : 'fan';
    const showsStufe  = !(restMin > 0 || cooling || status.includes('Bereit'));
    const sub = [showsStufe ? null : stufe, vol !== null ? `${Math.round(vol)} m³/h` : null]
      .filter(Boolean).join(' · ');

    /* ── Warnhinweise ── */
    const fehlerState = ent.fehler ? this._state(ent.fehler) : null;
    const fehlerAktiv = fehlerState !== null && fehlerState !== 'OK';
    const filterDays  = ent.filter ? this._num(ent.filter) : null;
    const warnDays    = Number.isFinite(+cfg.filter_warn_days) ? +cfg.filter_warn_days : 30;
    const filterDue   = filterDays !== null && filterDays <= warnDays;
    const filterBtns  = KWL_FILTER_BUTTONS.filter((f) => this._known(ent[f.key]));

    const banners = [];
    if (fehlerAktiv) {
      banners.push(`<div class="banner banner-err" role="alert">
        ${kwlIcon('alert')}
        <div class="banner-txt"><span class="banner-title">Fehler am Gerät</span>
          <span class="banner-sub">Das Gerät meldet einen Fehler.</span></div>
        ${this._known(ent.fehler_reset) ? '<button type="button" class="banner-btn" id="btn-fehler">Quittieren</button>' : ''}
      </div>`);
    }
    if (filterDue) {
      const n = Math.round(filterDays);
      banners.push(`<div class="banner banner-warn" role="status">
        ${kwlIcon('filter')}
        <div class="banner-txt"><span class="banner-title">${n <= 0 ? 'Filter jetzt wechseln' : 'Filterwechsel fällig'}</span>
          <span class="banner-sub">${n <= 0 ? 'Die Restlaufzeit ist abgelaufen.' : `Restlaufzeit noch ${n} ${n === 1 ? 'Tag' : 'Tage'}`}</span></div>
        ${filterBtns.length ? '<button type="button" class="banner-btn" id="btn-filter">Gewechselt</button>' : ''}
      </div>`);
    }

    /* Erklärungszeile (optional: show_explanation) */
    const explain = cfg.show_explanation
      ? [restMin > 0 ? `Stoßlüftung läuft noch ${restMin} min` : '',
         this._explain(status, tAus, tAb, bypass)].filter(Boolean).join(' · ')
      : '';

    /* ── Kennzahlen ── */
    const tiles = [];
    const leistung = ent.leistung ? this._num(ent.leistung) : null;
    if (leistung !== null) {
      tiles.push(`<div class="tile"><span class="tile-lbl">Strom</span><span class="tile-val">${Math.round(leistung)}<small> W</small></span></div>`);
    }
    const wrgP = ent.wrg_leistung ? this._num(ent.wrg_leistung) : null;
    if (wrgP !== null) {
      tiles.push(`<div class="tile tile-hi"><span class="tile-lbl">WRG-Gewinn</span><span class="tile-val">${Math.round(wrgP)}<small> W</small></span></div>`);
    }
    if (filterDays !== null) {
      const cls = filterDays <= 0 ? 'tile-err' : filterDays <= warnDays ? 'tile-warn' : '';
      tiles.push(`<div class="tile ${cls}"><span class="tile-lbl">Filter</span><span class="tile-val">${Math.round(filterDays)}<small> Tage</small></span></div>`);
    }

    /* ── Bedienung ── */
    const sommerKnown = this._known(ent.sommer);
    const sommerOn    = sommerKnown && this._state(ent.sommer) === 'on';
    const acts = [];
    if (sommerKnown) {
      acts.push(`<button type="button" class="act ${sommerOn ? 'act-on' : ''}" id="btn-sommer" title="Sommermodus (Nachtkühlung) umschalten">
        ${kwlIcon('sun')}<span>Sommermodus</span><small>${sommerOn ? 'an' : 'aus'}</small></button>`);
    }
    if (this._known(ent.stoss)) {
      acts.push(`<button type="button" class="act ${restMin > 0 ? 'act-on' : ''}" id="btn-stoss" title="${restMin > 0 ? 'Stoßlüftung erneut starten' : 'Stoßlüftung starten'}">
        ${kwlIcon('wind')}<span>Stoßlüftung</span>${restMin > 0 ? `<small>noch ${restMin} min</small>` : ''}</button>`);
    }
    const fanKnown = this._known(ent.fan);
    if (fanKnown) {
      acts.push(`<button type="button" class="act" id="btn-stufe" title="Lüftungsstufe wählen">
        ${kwlIcon('sliders')}<span>Stufe</span></button>`);
    }

    /* ── Räume ── */
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
      `<div class="room"><span class="room-icon">${kwlEsc(r.icon)}</span><span>${kwlEsc(r.name)}</span></div>`;

    const name = kwlEsc(cfg.name || 'Maico KWL');

    /* Farben für Arrow-SVGs (CSS-vars nicht direkt in SVG-Attributen verfügbar) */
    const colors = dark ? {
      out:  '#52C2F0', zu: '#F0883A', ab: '#E8733A', fort: '#2EC8A8',
    } : {
      out:  '#1A74AF', zu: '#C4601A', ab: '#9E3A10', fort: '#157A5A',
    };

    /* ── Menü „Stufe wählen“ ── */
    const stufeLc = stufe.toLowerCase();
    const stageOpts = KWL_STAGES.map((s) => {
      const on = stufeLc.includes(s.match);
      const v = ent[s.vol] ? this._num(ent[s.vol]) : null;
      return `<button type="button" class="opt ${on ? 'opt-on' : ''}" data-pct="${s.pct}">
        <span class="o-txt"><span>${s.label}</span>${v !== null ? `<span class="o-sub">${Math.round(v)} m³/h</span>` : ''}</span>
        ${on ? kwlIcon('check') : ''}</button>`;
    }).join('');
    const modeNow = (ent.betriebsart ? this._state(ent.betriebsart) : null) ||
      (fanKnown && this._hass.states[ent.fan].attributes ? this._hass.states[ent.fan].attributes.preset_mode : null);
    const modeOpts = KWL_MODES.map((m) =>
      `<button type="button" class="mode ${modeNow === m ? 'mode-on' : ''}" data-mode="${kwlEsc(m)}">${kwlEsc(m)}</button>`).join('');
    const stufeSheet = fanKnown ? `
  <dialog class="sheet" id="sheet-stufe" aria-label="Lüftungsstufe wählen">
    <div class="sheet-in" tabindex="-1" autofocus>
      <div class="grab"></div>
      <div class="sheet-hd"><span class="sheet-title">Lüftungsstufe</span><span class="sheet-sub">${name}</span></div>
      <div class="opts">${stageOpts}</div>
      <p class="sheet-note">Die Stufe bleibt, bis du sie wieder änderst. Für eine zeitlich begrenzte Intensivlüftung nimm die Stoßlüftung.</p>
      <div class="sheet-sec">Betriebsart</div>
      <div class="modes">${modeOpts}</div>
      <p class="sheet-note">In den Auto-Modi wählt das Gerät die Stufe selbst. Eine Stufe von Hand zu wählen schaltet auf Manuell.</p>
    </div>
  </dialog>` : '';

    /* ── Menü „Filter quittieren“ ── */
    const preChecked = filterBtns.length === 1;
    const filterSheet = filterBtns.length ? `
  <dialog class="sheet" id="sheet-filter" aria-label="Filterwechsel quittieren">
    <div class="sheet-in" tabindex="-1" autofocus>
      <div class="grab"></div>
      <div style="display:flex;flex-direction:column;gap:4px">
        <span class="sheet-title">Welche Filter hast du gewechselt?</span>
        <span class="sheet-note">Quittiere nur die Filter, die du wirklich getauscht hast. Das setzt den Zähler im Gerät zurück.</span>
      </div>
      <div class="opts">${filterBtns.map((f) => `
        <label class="opt ${preChecked ? 'opt-on' : ''}"><input type="checkbox" data-fkey="${f.key}" ${preChecked ? 'checked' : ''}>${f.label}</label>`).join('')}
      </div>
      <p class="sheet-note">Es erscheinen nur die Filter, die dein Gerät meldet.</p>
      <div class="sheet-btns">
        <button type="button" class="sbtn" id="filter-cancel">Abbrechen</button>
        <button type="button" class="sbtn sbtn-primary" id="filter-ok" ${preChecked ? '' : 'disabled'}>Quittieren</button>
      </div>
    </div>
  </dialog>` : '';

    /* ── HTML ── */
    this._shadow.innerHTML = `
${this._css(dark, restMin > 0)}

<ha-card>
  <!-- Kopf -->
  <div class="hdr">
    <div>
      <div class="eyebrow">Lüftungsanlage</div>
      <div class="card-name">${name}</div>
    </div>
    <div class="hdr-r">
      <div class="status-chip ${restMin > 0 ? 'boost' : ''}">${kwlIcon(statusIcon, 16)}${kwlEsc(statusLabel)}</div>
      ${sub ? `<div class="sub-info">${kwlEsc(sub)}</div>` : ''}
    </div>
  </div>
  ${banners.length ? `<div class="banners">${banners.join('')}</div>` : ''}
  ${explain ? `<div class="explain">${kwlEsc(explain)}</div>` : ''}

  <!-- Schema -->
  <div class="device">
    <div class="row">
      <div class="t-col">
        <span class="t-lbl" style="color:var(--kwl-out)">Außenluft</span>
        <span class="t-val" style="color:var(--kwl-out)">${this._fmt(tAus)}<span class="t-unit">°C</span></span>
      </div>
      ${this._arrowSvg('right', colors.out)}
      <div class="t-col r">
        <span class="t-lbl" style="color:var(--kwl-zu)">Zuluft</span>
        <span class="t-val" style="color:var(--kwl-zu)">${this._fmt(tZu)}<span class="t-unit">°C</span></span>
      </div>
    </div>

    <div class="dev-box">
      <span class="dev-lbl">Wärmetauscher</span>
      <span class="wrg-val">${wrg !== null ? wrg : '—'}<span class="t-unit">% WRG</span></span>
      ${bypass !== null ? `<span class="bypass ${bypass === 'Offen' ? 'bypass-open' : ''}">Bypass ${kwlEsc(String(bypass).toLowerCase())}</span>` : ''}
    </div>

    <div class="row">
      <div class="t-col">
        <span class="t-lbl" style="color:var(--kwl-fort)">Fortluft</span>
        <span class="t-val" style="color:var(--kwl-fort)">${this._fmt(tFort)}<span class="t-unit">°C</span></span>
      </div>
      ${this._arrowSvg('left', colors.ab)}
      <div class="t-col r">
        <span class="t-lbl" style="color:var(--kwl-ab)">Abluft</span>
        <span class="t-val" style="color:var(--kwl-ab)">${this._fmt(tAb)}<span class="t-unit">°C</span></span>
        ${feuchte !== null ? `<span class="t-humidity">${this._fmt(feuchte, 0)} % Feuchte</span>` : ''}
      </div>
    </div>
  </div>

  ${tiles.length ? `<div class="tiles" style="grid-template-columns:repeat(${tiles.length},minmax(0,1fr))">${tiles.join('')}</div>` : ''}
  ${acts.length ? `<div class="actions" style="grid-template-columns:repeat(${acts.length},minmax(0,1fr))">${acts.join('')}</div>` : ''}

  <!-- Räume (eingeklappt) -->
  <button type="button" class="rooms-btn" id="btn-rooms" aria-expanded="${this._roomsOpen}">
    <span class="l">${kwlIcon('home', 18)}Räume</span>
    <span class="r">${roomsZu.length} Zuluft · ${roomsAb.length} Abluft<span class="chev">${kwlIcon('chevron', 16)}</span></span>
  </button>
  ${this._roomsOpen ? `
  <div class="rooms">
    <div>
      <div class="rg-hdr"><div class="r-dot" style="background:var(--kwl-out)"></div><span class="rg-lbl">Zuluft</span></div>
      ${roomsZu.map(roomRow).join('')}
    </div>
    <div class="v-div"></div>
    <div>
      <div class="rg-hdr"><div class="r-dot" style="background:var(--kwl-ab)"></div><span class="rg-lbl">Abluft</span></div>
      ${roomsAb.map(roomRow).join('')}
    </div>
  </div>` : ''}
  ${stufeSheet}${filterSheet}
</ha-card>`;

    this._bind(ent);
  }

  /* ──────────────────────────────────── Interaktion ── */

  _on(id, fn) {
    const el = this._shadow.getElementById(id);
    if (el) el.addEventListener('click', fn);
  }

  _bind(ent) {
    this._on('btn-sommer', () => {
      this._hass.callService(ent.sommer.split('.')[0], 'toggle', { entity_id: ent.sommer });
    });
    this._on('btn-stoss', () => {
      this._hass.callService('button', 'press', { entity_id: ent.stoss });
    });
    this._on('btn-fehler', () => {
      this._hass.callService('button', 'press', { entity_id: ent.fehler_reset });
    });
    this._on('btn-rooms', () => {
      this._roomsOpen = !this._roomsOpen;
      this._render();
    });
    this._on('btn-stufe', () => this._openSheet('sheet-stufe', 'stufe'));
    this._on('btn-filter', () => this._openSheet('sheet-filter', 'filter'));

    /* Stufenmenü */
    this._shadow.querySelectorAll('#sheet-stufe [data-pct]').forEach((b) => {
      b.addEventListener('click', () => {
        this._hass.callService('fan', 'set_percentage', { entity_id: ent.fan, percentage: +b.dataset.pct });
        this._closeSheet();
      });
    });
    this._shadow.querySelectorAll('#sheet-stufe [data-mode]').forEach((b) => {
      b.addEventListener('click', () => {
        this._hass.callService('fan', 'set_preset_mode', { entity_id: ent.fan, preset_mode: b.dataset.mode });
        this._closeSheet();
      });
    });

    /* Filtermenü: Quittieren erst, wenn mindestens ein Filter angehakt ist */
    const boxes = [...this._shadow.querySelectorAll('#sheet-filter input[data-fkey]')];
    const ok = this._shadow.getElementById('filter-ok');
    boxes.forEach((b) => b.addEventListener('change', () => {
      b.closest('label').classList.toggle('opt-on', b.checked);
      if (ok) ok.disabled = !boxes.some((x) => x.checked);
    }));
    this._on('filter-cancel', () => this._closeSheet());
    if (ok) ok.addEventListener('click', () => {
      boxes.filter((x) => x.checked).forEach((x) => {
        this._hass.callService('button', 'press', { entity_id: ent[x.dataset.fkey] });
      });
      this._closeSheet();
    });

    /* Menüs: Tipp auf den abgedunkelten Rand oder Escape schließt */
    this._shadow.querySelectorAll('dialog.sheet').forEach((d) => {
      d.addEventListener('click', (ev) => { if (ev.target === d) this._closeSheet(); });
      d.addEventListener('close', () => this._sheetClosed());
      d.addEventListener('cancel', () => this._sheetClosed());
    });
  }

  _openSheet(id, kind) {
    const d = this._shadow.getElementById(id);
    if (!d) return;
    this._sheet = kind;
    if (typeof d.showModal === 'function') d.showModal();
    else d.setAttribute('open', '');
  }

  _closeSheet() {
    const d = this._shadow.querySelector('dialog.sheet[open]');
    this._sheetClosed();
    if (d) {
      if (typeof d.close === 'function') d.close();
      else d.removeAttribute('open');
    }
  }

  /** Menü ist zu: ausstehendes Neuzeichnen nachholen */
  _sheetClosed() {
    if (!this._sheet) return;
    this._sheet = null;
    if (this._dirty) {
      this._dirty = false;
      this._render();
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
    <p class="hint">Kennzahlen, Schaltflächen und Warnhinweise der Karte. Die passenden Entitäten werden automatisch gefunden.</p>
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
            (feat.also || []).forEach((a) => { delete entities[a.key]; });
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
            /* Zugehörige Entitäten (Restzeit, Filter-Knöpfe, …): nur eintragen, was es gibt */
            for (const a of (feat.also || [])) {
              const rid = await this._resolveFeature(a.uid);
              if (rid) this._config = { ...this._config, entities: { ...this._config.entities, [a.key]: rid } };
            }
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
  { key: 'filter',       uid: 'filter_restlaufzeit_zuluft', label: 'Filteranzeige mit Knopf „Gewechselt“',
    also: [ { key: 'filter_geraet', uid: 'filterwechsel_geraet' },
            { key: 'filter_aussen', uid: 'filterwechsel_aussen' },
            { key: 'filter_raum',   uid: 'filterwechsel_raum' } ] },
  { key: 'sommer',       uid: 'sommermodus',                label: 'Knopf „Sommermodus“' },
  { key: 'leistung',     uid: 'leistung',                   label: 'Stromleistung (geschätzt)' },
  { key: 'wrg_leistung', uid: 'wrg_leistung',               label: 'Wärmegewinn der Wärmerückgewinnung' },
  { key: 'stoss',        uid: 'stosslueftung',              label: 'Knopf „Stoßlüftung“ (mit Restzeit)',
    also: [ { key: 'stoss_rest', uid: 'stosslueftung_restzeit' } ] },
  { key: 'fan',          uid: 'lueftung',                   label: 'Knopf „Stufe“ (Auswahlmenü)',
    also: [ { key: 'vol_reduziert', uid: 'volumenstrom_reduziert' },
            { key: 'vol_nenn',      uid: 'volumenstrom_nennlueftung' },
            { key: 'vol_intensiv',  uid: 'volumenstrom_intensiv' },
            { key: 'betriebsart',   uid: 'betriebsart' } ] },
  { key: 'fehler',       uid: 'fehler',                     label: 'Fehlerhinweis mit Knopf „Quittieren“',
    also: [ { key: 'fehler_reset', uid: 'fehler_reset' } ] },
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
  '%c MAICO-KWL-CARD %c v2.0.0 ',
  'background:#1A74AF;color:#fff;padding:2px 4px;border-radius:3px 0 0 3px;font-weight:bold',
  'background:#157A5A;color:#fff;padding:2px 4px;border-radius:0 3px 3px 0'
);
