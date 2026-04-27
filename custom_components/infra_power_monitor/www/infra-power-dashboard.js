
const VERSION = "1.2.0";

/**
 * Infra Power Monitor Panel - NATIVE & PREMIUM VERSION
 */
class InfraPowerPanel extends HTMLElement {
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
          :host {
            display: block;
            height: 100%;
            background-color: var(--primary-background-color);
            color: var(--primary-text-color);
          }
          ha-app-layout {
            height: 100%;
          }
          app-header {
            background-color: var(--app-header-background-color, var(--primary-color));
            color: var(--app-header-text-color, white);
            font-weight: 400;
          }
          app-toolbar {
            display: flex;
            align-items: center;
          }
          .main-title {
            margin-left: 20px;
            flex: 1;
            font-size: 20px;
          }
          .content {
            padding: 16px;
            max-width: 1600px;
            margin: 0 auto;
          }
          .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
            gap: 20px;
          }
          @media (max-width: 600px) {
            .content { padding: 8px; }
            .grid { grid-template-columns: 1fr; gap: 12px; }
            .main-title { margin-left: 8px; font-size: 18px; }
          }
          .loading-msg {
            padding: 50px;
            text-align: center;
            opacity: 0.6;
          }
        </style>
        <ha-app-layout>
          <app-header slot="header" fixed>
            <app-toolbar>
              <ha-menu-button .hass=${this._hass} .narrow=${true}></ha-menu-button>
              <div class="main-title">Infra Power Monitor</div>
            </app-toolbar>
          </app-header>
          <div class="content">
            <div id="grid" class="grid">
              <div class="loading-msg">Cargando infraestructura...</div>
            </div>
          </div>
        </ha-app-layout>
      `;
    }
  }

  async _update(hass, oldHass) {
    const grid = this._root.getElementById('grid');
    if (!grid) return;

    const states = hass.states;
    const powerStateEntities = Object.keys(states)
      .filter((id) => id.startsWith('sensor.') && id.includes('_power_state'))
      .sort();

    if (powerStateEntities.length === 0) {
        grid.innerHTML = '<div class="loading-msg">No se han encontrado dispositivos. Revisa la configuración.</div>';
        return;
    }

    // Only full render if entities changed or cards registered
    const hasStack = !!customElements.get('stack-in-card') || !!customElements.get('hui-stack-in-card');
    const hasButton = !!customElements.get('button-card') || !!customElements.get('hui-button-card');
    const key = JSON.stringify(powerStateEntities) + "_" + hasStack + "_" + hasButton;

    if (this._renderedKey === key) {
        // Just propagate hass to existing children
        Array.from(grid.children).forEach(card => {
            if (card.hass !== hass) card.hass = hass;
        });
        return;
    }

    this._renderedKey = key;
    grid.innerHTML = '';

    const helpers = window.loadCardHelpers ? await window.loadCardHelpers() : null;
    if (!helpers) return;

    for (const entityId of powerStateEntities) {
      const config = this._generateCardConfig(entityId, states, hasStack, hasButton);
      const card = helpers.createCardElement(config);
      card.hass = hass;
      grid.appendChild(card);
    }
  }

  _generateCardConfig(entityId, states, hasStack, hasButton) {
    const raw = entityId.replace(/^sensor\./, "");
    const match = raw.match(/^(.*?)(?:_power_state)(?:_(\d+))?$/);
    const base = match ? match[1] : raw;
    const suffix = (match && match[2]) ? `_${match[2]}` : "";
    const name = this._prettyName(base);

    if (!hasStack || !hasButton) {
        return {
            type: "entities",
            title: name,
            show_header_toggle: false,
            entities: [
                entityId,
                `sensor.${base}_health${suffix}`,
                `sensor.${base}_cpu_temp${suffix}`,
                `sensor.${base}_power_usage${suffix}`,
                { type: "divider" },
                { type: "button", entity: `button.${base}_power_on${suffix}`, name: "ON" },
                { type: "button", entity: `button.${base}_power_off${suffix}`, name: "OFF" }
            ].filter(id => typeof id === 'object' || !!states[id])
        };
    }

    // Premium Version
    return {
      type: "custom:stack-in-card",
      cards: [
        {
          type: "custom:button-card",
          entity: entityId,
          name: name,
          icon: "mdi:server",
          show_state: true,
          show_label: true,
          variables: {
            health_ent: `sensor.${base}_health${suffix}`,
            temp_ent: [`sensor.${base}_cpu_temp${suffix}`, `sensor.${base}_system_temp${suffix}`].find(id => !!states[id]) || "",
            fw_ent: `sensor.${base}_firmware_version${suffix}`
          },
          label: `[[[
            const v = (id) => states[id]?.state;
            const valid = (x) => x && x !== 'unknown' && x !== 'unavailable';
            const parts = [];
            if (valid(v(variables.health_ent))) parts.push('Health: ' + v(variables.health_ent));
            if (valid(v(variables.temp_ent))) parts.push('Temp: ' + v(variables.temp_ent) + '°C');
            return parts.join(' · ');
          ]]]`,
          styles: {
            card: [
              { "border-radius": "16px 16px 0 0" },
              { padding: "20px" },
              { height: "160px" },
              { border: "1px solid rgba(255,255,255,0.1)" },
              { background: `[[[
                  const s = (entity.state || '').trim();
                  if (s === 'Encendido') return 'linear-gradient(135deg, #0a4a22 0%, #052f14 100%)';
                  if (s === 'Apagado') return 'linear-gradient(135deg, #333 0%, #1a1a1a 100%)';
                  if (s === 'Arrancando' || s === 'Reiniciando') return 'linear-gradient(135deg, #122c58 0%, #0a1832 100%)';
                  if (s === 'Apagando') return 'linear-gradient(135deg, #5a360a 0%, #321e05 100%)';
                  return 'var(--card-background-color)';
                ]]]` 
              }
            ],
            grid: [{ "grid-template-areas": '"i n" '"i s" '"i l"' }, { "grid-template-columns": "80px 1fr" }, { "row-gap": "4px" }],
            icon: [{ width: "64px" }, { height: "64px" }, { color: "white" }],
            name: [{ "justify-self": "start" }, { "font-size": "26px" }, { "font-weight": "700" }, { color: "white" }],
            state: [{ "justify-self": "start" }, { "font-size": "16px" }, { color: "white" }, { opacity: "0.9" }],
            label: [{ "justify-self": "start" }, { "font-size": "13px" }, { color: "white" }, { opacity: "0.7" }]
          }
        },
        {
          type: "horizontal-stack",
          cards: ["power_on", "power_off", "restart", "refresh"].map(k => ({
            type: "custom:button-card",
            entity: `button.${base}_${k}${suffix}`,
            name: k.replace("power_", "").toUpperCase(),
            styles: { 
                card: [
                    { height: "50px" }, 
                    { "border-radius": "0" }, 
                    { border: "none" }, 
                    { background: "rgba(255,255,255,0.05)" },
                    { border: "1px solid rgba(255,255,255,0.05)" }
                ],
                name: [{ "font-size": "12px" }, { "font-weight": "bold" }]
            }
          })).filter(c => !!states[c.entity])
        }
      ]
    };
  }

  _prettyName(base) {
    return base.split("_").map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
  }
}

customElements.define("infra-power-panel", InfraPowerPanel);