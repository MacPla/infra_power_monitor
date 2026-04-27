
const VERSION = "1.2.5";

/**
 * Infra Power Monitor Panel - ULTRA FAST NATIVE UI
 * Optimized for large installations. Zero lag.
 */
(function() {
  if (customElements.get('infra-power-panel')) return;

  class InfraPowerPanel extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: 'open' });
      this._powerEntities = null;
      this._cardElements = {};
      this._lastUpdate = 0;
    }

    set hass(hass) {
      this._hass = hass;
      // Only process updates if at least 100ms have passed (throttling)
      const now = Date.now();
      if (now - this._lastUpdate > 100) {
          this._lastUpdate = now;
          this._update();
      }
    }

    connectedCallback() {
      this._setupLayout();
    }

    _setupLayout() {
      this.shadowRoot.innerHTML = `
        <style>
          :host { --primary-bg: var(--primary-background-color); --card-bg: var(--card-background-color, #1c1c1c); --header-bg: var(--app-header-background-color, var(--primary-color)); --header-text: var(--app-header-text-color, white); display: block; height: 100vh; background: var(--primary-bg); color: var(--primary-text-color); font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); overflow: hidden; }
          .app-wrapper { display: flex; flex-direction: column; height: 100%; }
          .header { height: 64px; background: var(--header-bg); color: var(--header-text); display: flex; align-items: center; padding: 0 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.3); z-index: 100; }
          .menu-btn { cursor: pointer; padding: 10px; margin-right: 15px; border-radius: 50%; transition: background 0.2s; display: flex; }
          .menu-btn:hover { background: rgba(255,255,255,0.1); }
          .title { font-size: 20px; font-weight: 500; flex: 1; letter-spacing: 0.5px; }
          .content { flex: 1; overflow-y: auto; padding: 20px; scroll-behavior: smooth; -webkit-overflow-scrolling: touch; }
          .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; max-width: 1600px; margin: 0 auto; }
          @media (max-width: 600px) { .grid { grid-template-columns: 1fr; } .header { height: 56px; } .content { padding: 12px; } }
          
          /* Server Card Styling */
          .server-card { background: var(--card-bg); border-radius: 20px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.2); transition: transform 0.2s, box-shadow 0.2s; display: flex; flex-direction: column; border: 1px solid rgba(255,255,255,0.05); }
          .server-card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,0,0,0.3); }
          
          .card-header { padding: 24px; position: relative; color: white; min-height: 120px; display: flex; align-items: center; transition: background 0.5s ease; }
          .card-header.on { background: linear-gradient(135deg, #0d4a25 0%, #052612 100%); }
          .card-header.off { background: linear-gradient(135deg, #2c2c2c 0%, #1a1a1a 100%); }
          .card-header.process { background: linear-gradient(135deg, #153e7e 0%, #0a2144 100%); }
          
          .icon-box { width: 64px; height: 64px; background: rgba(255,255,255,0.1); border-radius: 16px; display: flex; align-items: center; justify-content: center; margin-right: 20px; backdrop-filter: blur(5px); }
          .icon-box ha-icon { --mdc-icon-size: 32px; }
          
          .info-box { flex: 1; }
          .server-name { font-size: 22px; font-weight: 700; margin: 0; line-height: 1.2; }
          .server-state { font-size: 14px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }
          .server-extra { font-size: 12px; opacity: 0.6; margin-top: 6px; }
          
          .card-actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(60px, 1fr)); background: rgba(0,0,0,0.2); border-top: 1px solid rgba(255,255,255,0.05); }
          .action-btn { padding: 12px 8px; border: none; background: transparent; color: inherit; cursor: pointer; font-size: 11px; font-weight: 600; text-transform: uppercase; display: flex; flex-direction: column; align-items: center; gap: 4px; transition: background 0.2s; opacity: 0.8; }
          .action-btn:hover { background: rgba(255,255,255,0.05); opacity: 1; }
          .action-btn ha-icon { --mdc-icon-size: 20px; }
          
          .empty-msg { padding: 50px; text-align: center; opacity: 0.5; font-size: 18px; }
        </style>
        <div class="app-wrapper">
          <div class="header">
            <div id="menu-btn" class="menu-btn"><ha-icon icon="mdi:menu"></ha-icon></div>
            <div class="title">Infra Power Monitor</div>
          </div>
          <div class="content">
            <div id="grid" class="grid"></div>
          </div>
        </div>
      `;

      this.shadowRoot.getElementById('menu-btn').onclick = () => {
        this.dispatchEvent(new CustomEvent("hass-toggle-menu", { detail: {}, bubbles: true, composed: true }));
      };
    }

    _update() {
      const hass = this._hass;
      const grid = this.shadowRoot.getElementById('grid');
      if (!hass || !grid) return;

      // OPTIMIZATION: Only search for entities once, or when a manual refresh is needed
      if (this._powerEntities === null) {
          console.log("InfraPowerPanel: Scanning for servers...");
          this._powerEntities = Object.keys(hass.states).filter(id => id.includes('_power_state')).sort();
      }

      if (this._powerEntities.length === 0) {
          grid.innerHTML = '<div class="empty-msg">No se han encontrado servidores configurados.</div>';
          return;
      }

      this._powerEntities.forEach(id => {
          if (!this._cardElements[id]) {
              const card = document.createElement('div');
              card.className = 'server-card';
              grid.appendChild(card);
              this._cardElements[id] = card;
          }
          this._renderCard(this._cardElements[id], id);
      });
    }

    _renderCard(container, entityId) {
      const stateObj = this._hass.states[entityId];
      if (!stateObj) return;

      const state = (stateObj.state || 'unknown').toLowerCase();
      const base = entityId.replace(/^sensor\./, "").split("_power_state")[0];
      const suffix = entityId.includes("_power_state_") ? "_" + entityId.split("_power_state_")[1] : "";
      const name = base.toUpperCase().replace(/_/g, " ");

      const health = this._hass.states[`sensor.${base}_health${suffix}`]?.state || '';
      const temp = this._hass.states[`sensor.${base}_cpu_temp${suffix}`]?.state || '';
      const extra = (health ? `Health: ${health}` : '') + (temp ? ` · Temp: ${temp}°C` : '');

      let colorClass = 'off';
      if (['encendido', 'on', 'online'].includes(state)) colorClass = 'on';
      else if (['arrancando', 'reiniciando', 'apaguando', 'starting', 'restarting', 'stopping'].some(s => state.includes(s))) colorClass = 'process';

      const versionKey = `${state}_${extra}_${name}`;
      if (container._versionKey === versionKey) return;
      container._versionKey = versionKey;

      container.innerHTML = `
        <div class="card-header ${colorClass}">
          <div class="icon-box">
            <ha-icon icon="mdi:server"></ha-icon>
          </div>
          <div class="info-box">
            <div class="server-name">${name}</div>
            <div class="server-state">${stateObj.state}</div>
            <div class="server-extra">${extra}</div>
          </div>
        </div>
        <div class="card-actions">
          ${this._renderAction(base, suffix, 'power_on', 'mdi:power', 'Encender')}
          ${this._renderAction(base, suffix, 'power_off', 'mdi:power-off', 'Apagar')}
          ${this._renderAction(base, suffix, 'restart', 'mdi:restart', 'Reiniciar')}
          ${this._renderAction(base, suffix, 'refresh', 'mdi:refresh', 'Refrescar')}
        </div>
      `;

      container.querySelectorAll('.action-btn').forEach(btn => {
          btn.onclick = (e) => {
              e.stopPropagation();
              const eid = btn.dataset.entity;
              const [domain, service] = eid.split('.');
              this._hass.callService(domain, 'press', { entity_id: eid });
          };
      });
    }

    _renderAction(base, suffix, key, icon, label) {
      const entityId = `button.${base}_${key}${suffix}`;
      const exists = !!this._hass.states[entityId];
      if (!exists) return '';
      return `
        <button class="action-btn" data-entity="${entityId}">
          <ha-icon icon="${icon}"></ha-icon>
          <span>${label}</span>
        </button>
      `;
    }
  }

  try {
    customElements.define("infra-power-panel", InfraPowerPanel);
  } catch (e) {
    // Already defined
  }
})();