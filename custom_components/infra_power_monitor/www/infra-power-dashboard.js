
const VERSION = "1.1.2";

/**
 * Infra Power Monitor Panel - SMART RESILIENT VERSION
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
          :host { display: block; height: 100%; background-color: var(--primary-background-color); overflow-y: auto; color: var(--primary-text-color); }
          .container { padding: 24px; max-width: 1400px; margin: 0 auto; }
          h1 { margin: 0 0 32px 0; font-size: 32px; font-weight: 300; }
          .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 24px; }
        </style>
        <div class="container">
          <h1>Infra Power Monitor</h1>
          <div id="grid" class="grid"><div style="padding: 20px;">Iniciando...</div></div>
        </div>
      `;
    }
    
    // Auto-retry once custom cards are defined
    ["button-card", "stack-in-card"].forEach(card => {
        customElements.whenDefined(card).then(() => {
            this._renderedKey = null; // Force re-render
            if (this._hass) this._update(this._hass);
        });
    });
  }

  async _update(hass) {
    const grid = this._root.getElementById('grid');
    if (!grid) return;

    const states = hass.states;
    const powerStateEntities = Object.keys(states)
      .filter((id) => id.startsWith('sensor.') && id.includes('_power_state'))
      .sort();

    if (powerStateEntities.length === 0) {
        grid.innerHTML = '<div style="padding: 20px; opacity: 0.5;">No hay dispositivos detectados.</div>';
        return;
    }

    const hasStack = !!customElements.get('stack-in-card') || !!customElements.get('hui-stack-in-card');
    const hasButton = !!customElements.get('button-card') || !!customElements.get('hui-button-card');
    
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
      const config = this._generateConfig(entityId, states, hasStack, hasButton);
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
            entities: [
                entityId,
                `sensor.${base}_health${suffix}`,
                `sensor.${base}_cpu_temp${suffix}`,
                `sensor.${base}_power_usage${suffix}`,
                { type: "divider" },
                `button.${base}_power_on${suffix}`,
                `button.${base}_power_off${suffix}`,
                `button.${base}_restart${suffix}`,
                `button.${base}_refresh${suffix}`
            ].filter(id => typeof id === 'object' || !!states[id])
        };
    }

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
            health: `sensor.${base}_health${suffix}`,
            temp: `sensor.${base}_cpu_temp${suffix}`,
            fw: `sensor.${base}_firmware_version${suffix}`
          },
          label: `[[[
            const v = (id) => states[id]?.state;
            const parts = [];
            if (v(variables.health)) parts.push('Health: ' + v(variables.health));
            if (v(variables.temp)) parts.push('Temp: ' + v(variables.temp) + '°C');
            return parts.join(' · ');
          ]]]`,
          styles: {
            card: [
              { "border-radius": "16px 16px 0 0" },
              { padding: "16px" },
              { background: "linear-gradient(135deg, rgba(50,50,50,0.5), rgba(20,20,20,0.8))" }
            ],
            grid: [{ "grid-template-areas": '"i n" "i s" "i l"' }, { "grid-template-columns": "70px 1fr" }],
            name: [{ "justify-self": "start" }, { "font-size": "24px" }, { "font-weight": "bold" }],
            state: [{ "justify-self": "start" }],
            label: [{ "justify-self": "start" }, { opacity: "0.6" }, { "font-size": "12px" }]
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