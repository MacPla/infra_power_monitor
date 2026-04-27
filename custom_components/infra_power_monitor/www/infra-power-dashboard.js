
const VERSION = "1.2.1";

/**
 * Infra Power Monitor Panel - HACS STYLE (ULTRA RESILIENT)
 */
class InfraPowerPanel extends HTMLElement {
  constructor() {
    super();
    this._renderedKey = null;
  }

  set hass(hass) {
    this._hass = hass;
    if (this._root) {
      this._update(hass);
    }
  }

  connectedCallback() {
    if (!this._root) {
      this.attachShadow({ mode: 'open' });
      this._root = this.shadowRoot;
      this._root.innerHTML = `
        <style>
          :host {
            display: block;
            height: 100vh;
            background-color: var(--primary-background-color);
            color: var(--primary-text-color);
            overflow: hidden;
            font-family: var(--paper-font-body1_-_font-family, 'Roboto', sans-serif);
          }
          .app-wrapper {
            display: flex;
            flex-direction: column;
            height: 100%;
          }
          .header {
            height: 64px;
            min-height: 64px;
            background-color: var(--app-header-background-color, var(--primary-color));
            color: var(--app-header-text-color, white);
            display: flex;
            align-items: center;
            padding: 0 16px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            z-index: 10;
          }
          .menu-button {
            cursor: pointer;
            padding: 8px;
            margin-right: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: background-color 0.2s;
          }
          .menu-button:hover {
            background-color: rgba(255,255,255,0.1);
          }
          .main-title {
            font-size: 20px;
            font-weight: 400;
            flex: 1;
          }
          .content {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            -webkit-overflow-scrolling: touch;
          }
          .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 16px;
          }
          @media (max-width: 600px) {
            .content { padding: 12px 8px; }
            .grid { grid-template-columns: 1fr; gap: 12px; }
            .header { height: 56px; min-height: 56px; padding: 0 8px; }
            .main-title { font-size: 18px; }
          }
          .status-msg {
            padding: 40px;
            text-align: center;
            opacity: 0.6;
          }
          ha-icon {
            --mdc-icon-size: 24px;
          }
        </style>
        <div class="app-wrapper">
          <div class="header">
            <div id="menu-btn" class="menu-button">
              <ha-icon icon="mdi:menu"></ha-icon>
            </div>
            <div class="main-title">Infra Power Monitor</div>
          </div>
          <div class="content">
            <div id="grid" class="grid">
              <div class="status-msg">Cargando interfaz premium...</div>
            </div>
          </div>
        </div>
      `;

      this._root.getElementById('menu-btn').onclick = () => {
        this.dispatchEvent(new CustomEvent("hass-toggle-menu", {
          detail: {},
          bubbles: true,
          composed: true
        }));
      };
    }

    // Auto-refresh when custom cards load
    const checkCards = setInterval(() => {
        if (customElements.get('button-card') && customElements.get('stack-in-card')) {
            this._renderedKey = null;
            if (this._hass) this._update(this._hass);
            clearInterval(checkCards);
        }
    }, 1000);
    setTimeout(() => clearInterval(checkCards), 10000);
  }

  async _update(hass) {
    const grid = this._root.getElementById('grid');
    if (!grid) return;

    const powerStateEntities = Object.keys(hass.states)
      .filter((id) => id.startsWith('sensor.') && id.includes('_power_state'))
      .sort();

    if (powerStateEntities.length === 0) {
        grid.innerHTML = '<div class="status-msg">No se han detectado servidores.</div>';
        return;
    }

    const hasStack = !!customElements.get('stack-in-card');
    const hasButton = !!customElements.get('button-card');
    
    // Only re-render if fundamental state changes
    const key = JSON.stringify(powerStateEntities) + "_" + hasStack + "_" + hasButton;
    if (this._renderedKey === key) {
        Array.from(grid.children).forEach(c => { if (c.hass !== hass) c.hass = hass; });
        return;
    }

    this._renderedKey = key;
    grid.innerHTML = '';

    const helpers = window.loadCardHelpers ? await window.loadCardHelpers() : null;
    if (!helpers) return;

    for (const entityId of powerStateEntities) {
      const config = this._generateConfig(entityId, hass.states, hasStack, hasButton);
      const card = helpers.createCardElement(config);
      card.hass = hass;
      grid.appendChild(card);
    }
  }

  _generateConfig(entityId, states, hasStack, hasButton) {
    const raw = entityId.replace(/^sensor\./, "");
    const match = raw.match(/^(.*?)(?:_power_state)(?:_(\d+))?$/);
    const base = match ? match[1] : raw;
    const suffix = (match && match[2]) ? `_${match[2]}` : "";
    const name = base.toUpperCase().replace(/_/g, " ");

    if (!hasStack || !hasButton) {
        return {
            type: "entities",
            title: name,
            entities: [entityId, `sensor.${base}_health${suffix}`, `sensor.${base}_cpu_temp${suffix}`].filter(id => !!states[id])
        };
    }

    // PREMIUM DESIGN
    return {
      type: "custom:stack-in-card",
      keep: {
        background: true,
        box_shadow: true,
        margin: true,
        outer_padding: true,
        border_radius: true
      },
      cards: [
        {
          type: "custom:button-card",
          entity: entityId,
          name: name,
          icon: "mdi:server",
          show_state: true,
          show_label: true,
          variables: {
            health: `sensor.${base}_health${suffix}`,
            temp: [`sensor.${base}_cpu_temp${suffix}`, `sensor.${base}_system_temp${suffix}`].find(id => !!states[id]) || ""
          },
          label: `[[[
            const s = states[variables.health]?.state;
            const t = states[variables.temp]?.state;
            return (s ? 'Health: ' + s : '') + (t ? ' · Temp: ' + t + '°C' : '');
          ]]]`,
          styles: {
            card: [
              { "border-radius": "16px 16px 0 0" },
              { padding: "20px" },
              { height: "150px" },
              { background: `[[[
                  const s = (entity.state || '').toLowerCase().trim();
                  if (s === 'encendido' || s === 'on') return 'linear-gradient(135deg, #0a4a22 0%, #052f14 100%)';
                  if (s === 'apagado' || s === 'off') return 'linear-gradient(135deg, #333 0%, #1a1a1a 100%)';
                  if (s === 'arrancando' || s === 'reiniciando' || s === 'starting' || s === 'restarting') return 'linear-gradient(135deg, #122c58 0%, #0a1832 100%)';
                  if (s === 'apagando' || s === 'stopping') return 'linear-gradient(135deg, #5a360a 0%, #321e05 100%)';
                  return 'var(--card-background-color)';
                ]]]` 
              }
            ],
            grid: [{ "grid-template-areas": '"i n" "i s" "i l"' }, { "grid-template-columns": "70px 1fr" }],
            icon: [{ width: "56px" }, { height: "56px" }, { color: "white" }],
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

customElements.define("infra-power-panel", InfraPowerPanel);