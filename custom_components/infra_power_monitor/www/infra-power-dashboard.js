
const VERSION = "1.2.3";

/**
 * Infra Power Monitor Panel - FINAL PERFORMANCE POLISH
 */
(function() {
  if (customElements.get('infra-power-panel')) return;

  class InfraPowerPanel extends HTMLElement {
    constructor() {
      super();
      this._renderedKey = null;
      this._powerEntities = null;
      this._lastStateCount = 0;
    }

    set hass(hass) {
      const oldHass = this._hass;
      this._hass = hass;
      if (this._root) {
        this._update(hass, oldHass);
      }
    }

    connectedCallback() {
      if (!this._root) {
        this.attachShadow({ mode: 'open' });
        this._root = this.shadowRoot;
        this._root.innerHTML = `
          <style>
            :host { display: block; height: 100vh; background-color: var(--primary-background-color); color: var(--primary-text-color); overflow: hidden; }
            .app-wrapper { display: flex; flex-direction: column; height: 100%; }
            .header { height: 64px; min-height: 64px; background-color: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, white); display: flex; align-items: center; padding: 0 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); z-index: 10; }
            .menu-button { cursor: pointer; padding: 8px; margin-right: 16px; display: flex; align-items: center; justify-content: center; border-radius: 50%; }
            .main-title { font-size: 20px; font-weight: 400; flex: 1; }
            .content { flex: 1; overflow-y: auto; padding: 16px; -webkit-overflow-scrolling: touch; }
            .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; }
            @media (max-width: 600px) { .grid { grid-template-columns: 1fr; } .header { height: 56px; min-height: 56px; } }
            .status-msg { padding: 40px; text-align: center; opacity: 0.6; }
          </style>
          <div class="app-wrapper">
            <div class="header">
              <div id="menu-btn" class="menu-button"><ha-icon icon="mdi:menu"></ha-icon></div>
              <div class="main-title">Infra Power Monitor</div>
            </div>
            <div class="content">
              <div id="grid" class="grid"><div class="status-msg">Iniciando...</div></div>
            </div>
          </div>
        `;

        this._root.getElementById('menu-btn').onclick = () => {
          this.dispatchEvent(new CustomEvent("hass-toggle-menu", { detail: {}, bubbles: true, composed: true }));
        };
      }

      this._checkInterval = setInterval(() => {
          if (customElements.get('button-card') && customElements.get('stack-in-card')) {
              this._renderedKey = null;
              if (this._hass) this._update(this._hass, null, true);
              clearInterval(this._checkInterval);
          }
      }, 1000);
    }

    disconnectedCallback() {
      if (this._checkInterval) clearInterval(this._checkInterval);
    }

    async _update(hass, oldHass, force = false) {
      const grid = this._root.getElementById('grid');
      if (!grid) return;

      const stateKeys = Object.keys(hass.states);
      if (!this._powerEntities || force || Math.abs(stateKeys.length - this._lastStateCount) > 5) {
          this._powerEntities = stateKeys.filter(id => id.includes('_power_state')).sort();
          this._lastStateCount = stateKeys.length;
      }

      let changed = force;
      if (!changed && oldHass) {
          for (const id of this._powerEntities) {
              if (hass.states[id]?.state !== oldHass.states[id]?.state) {
                  changed = true;
                  break;
              }
          }
      }

      if (!changed && this._renderedKey) {
          Array.from(grid.children).forEach(c => { if (c.hass !== hass) c.hass = hass; });
          return;
      }

      const hasStack = !!customElements.get('stack-in-card');
      const hasButton = !!customElements.get('button-card');
      const key = JSON.stringify(this._powerEntities) + "_" + hasStack + "_" + hasButton;

      if (this._renderedKey === key && !force) {
          Array.from(grid.children).forEach(c => { if (c.hass !== hass) c.hass = hass; });
          return;
      }

      this._renderedKey = key;
      grid.innerHTML = '';

      const helpers = window.loadCardHelpers ? await window.loadCardHelpers() : null;
      if (!helpers) return;

      for (const entityId of this._powerEntities) {
        const config = this._generateConfig(entityId, hass.states, hasStack, hasButton);
        const card = helpers.createCardElement(config);
        card.hass = hass;
        grid.appendChild(card);
      }
    }

    _generateConfig(entityId, states, hasStack, hasButton) {
      const base = entityId.replace(/^sensor\./, "").split("_power_state")[0];
      const suffix = entityId.includes("_power_state_") ? "_" + entityId.split("_power_state_")[1] : "";
      const name = base.toUpperCase().replace(/_/g, " ");

      if (!hasStack || !hasButton) {
          return { type: "entities", title: name, entities: [entityId].filter(id => !!states[id]) };
      }

      return {
        type: "custom:stack-in-card",
        keep: { background: true, box_shadow: true, margin: true, outer_padding: true, border_radius: true },
        cards: [
          {
            type: "custom:button-card",
            entity: entityId,
            name: name,
            icon: "mdi:server",
            show_state: true,
            show_label: true,
            variables: { health: `sensor.${base}_health${suffix}`, temp: `sensor.${base}_cpu_temp${suffix}` },
            label: `[[[
              const s = states[variables.health]?.state;
              const t = states[variables.temp]?.state;
              return (s ? 'Health: ' + s : '') + (t ? ' · Temp: ' + t + '°C' : '');
            ]]]`,
            styles: {
              card: [
                { "border-radius": "16px 16px 0 0" }, { padding: "20px" }, { height: "150px" },
                { background: `[[[
                    const s = (entity.state || '').toLowerCase();
                    if (s === 'encendido' || s === 'on') return 'linear-gradient(135deg, #0a4a22 0%, #052f14 100%)';
                    if (s === 'apagado' || s === 'off') return 'linear-gradient(135deg, #333 0%, #1a1a1a 100%)';
                    if (s.includes('arrancando') || s.includes('reiniciando') || s.includes('start')) return 'linear-gradient(135deg, #122c58 0%, #0a1832 100%)';
                    return '#222';
                  ]]]` 
                }
              ],
              grid: [{ "grid-template-areas": '"i n" "i s" "i l"' }, { "grid-template-columns": "70px 1fr" }],
              icon: [{ width: "56px" }, { color: "white" }],
              name: [{ "justify-self": "start" }, { "font-size": "24px" }, { "font-weight": "700" }, { color: "white" }],
              state: [{ "justify-self": "start" }, { color: "white" }],
              label: [{ "justify-self": "start" }, { color: "white" }, { opacity: "0.6" }, { "font-size": "12px" }]
            }
          },
          {
            type: "horizontal-stack",
            cards: ["power_on", "power_off", "restart", "refresh"].map(k => ({
              type: "custom:button-card",
              entity: `button.${base}_${k}${suffix}`,
              name: k.replace("power_", "").toUpperCase(),
              styles: { card: [{ height: "45px" }, { "border-radius": "0" }, { border: "none" }, { background: "rgba(255,255,255,0.05)" }] }
            })).filter(c => !!states[c.entity])
          }
        ]
      };
    }
  }

  try {
    customElements.define("infra-power-panel", InfraPowerPanel);
  } catch (e) {
    // Already defined
  }
})();