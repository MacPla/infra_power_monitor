
const VERSION = "1.1.0";

/**
 * Infra Power Monitor Panel - FINAL STABLE VERSION
 */
class InfraPowerPanel extends HTMLElement {
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
            height: 100%;
            background-color: var(--primary-background-color);
            overflow-y: auto;
            color: var(--primary-text-color);
          }
          .container {
            padding: 24px;
            max-width: 1400px;
            margin: 0 auto;
          }
          .header {
            margin-bottom: 32px;
          }
          h1 {
            margin: 0;
            font-size: 32px;
            font-weight: 300;
            letter-spacing: -0.5px;
          }
          .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 24px;
          }
          @media (max-width: 600px) {
            .grid {
              grid-template-columns: 1fr;
              padding: 8px;
            }
          }
        </style>
        <div class="container">
          <div class="header">
            <h1>Infra Power Monitor</h1>
          </div>
          <div id="grid" class="grid">
            <div style="padding: 40px; text-align: center;">Cargando dispositivos...</div>
          </div>
        </div>
      `;
    }
  }

  async _update(hass) {
    const grid = this._root.getElementById('grid');
    if (!grid) return;

    const states = hass.states;
    const powerStateEntities = Object.keys(states)
      .filter((id) => id.startsWith('sensor.') && id.includes('_power_state'))
      .sort();

    if (powerStateEntities.length === 0) {
        grid.innerHTML = '<div style="padding: 40px; opacity: 0.6; text-align: center;">No hay dispositivos configurados.</div>';
        return;
    }

    const entitiesKey = JSON.stringify(powerStateEntities);
    if (this._renderedEntities === entitiesKey) {
        Array.from(grid.children).forEach(card => {
            if (card.hass !== hass) card.hass = hass;
        });
        return;
    }

    this._renderedEntities = entitiesKey;
    grid.innerHTML = '';

    // Wait for card helpers
    const helpers = window.loadCardHelpers ? await window.loadCardHelpers() : null;
    if (!helpers) return;

    for (const entityId of powerStateEntities) {
      const config = this._generateCardConfig(entityId, states);
      const card = helpers.createCardElement(config);
      card.hass = hass;
      grid.appendChild(card);
    }
  }

  _generateCardConfig(powerStateEntity, states) {
    const raw = powerStateEntity.replace(/^sensor\./, "");
    const match = raw.match(/^(.*?)(?:_power_state)(?:_(\d+))?$/);
    const base = match ? match[1] : raw;
    const suffix = (match && match[2]) ? `_${match[2]}` : "";
    const name = this._prettyName(base);

    const health = `sensor.${base}_health${suffix}`;
    const firmware = `sensor.${base}_firmware_version${suffix}`;
    const temp = [`sensor.${base}_cpu_temp${suffix}`, `sensor.${base}_system_board_inlet_temp${suffix}`, `sensor.${base}_system_temp${suffix}`].find(id => !!states[id]) || "";

    return {
      type: "custom:stack-in-card",
      cards: [
        {
          type: "custom:button-card",
          entity: powerStateEntity,
          name,
          icon: "mdi:server",
          show_state: true,
          show_label: true,
          tap_action: { action: "more-info" },
          variables: {
            health_entity: health,
            temp_entity: temp,
            firmware_entity: firmware,
          },
          label: `[[[
            const valid = v => v && v !== 'unknown' && v !== 'unavailable';
            const health = states[variables.health_entity]?.state;
            const temp = variables.temp_entity ? states[variables.temp_entity]?.state : undefined;
            const fw = states[variables.firmware_entity]?.state;

            const parts = [];
            if (valid(health)) parts.push(\`Health: \${health}\`);
            if (valid(temp)) parts.push(\`Temp: \${temp} °C\`);
            if (valid(fw)) parts.push(\`FW: \${fw}\`);
            return parts.join(' · ');
          ]]]`,
          styles: {
            card: [
              { "border-radius": "20px 20px 0 0" },
              { padding: "20px" },
              { height: "160px" },
              {
                "background": `[[[
                  const s = (entity.state || '').trim();
                  if (s === 'Encendido') return 'linear-gradient(135deg, rgba(8,77,33,0.95), rgba(5,47,20,0.95))';
                  if (s === 'Apagado') return 'linear-gradient(135deg, rgba(55,55,55,0.7), rgba(25,25,25,0.9))';
                  return 'linear-gradient(135deg, rgba(40,40,40,0.7), rgba(20,20,20,0.9))';
                ]]]`,
              },
            ],
            grid: [
              { "grid-template-areas": '"i n" "i s" "i l"' },
              { "grid-template-columns": "80px 1fr" },
              { "row-gap": "4px" },
            ],
            icon: [{ width: "60px" }, { height: "60px" }, { color: "white" }],
            name: [{ "justify-self": "start" }, { "font-size": "28px" }, { "font-weight": "600" }],
            state: [{ "justify-self": "start" }, { "font-size": "18px" }, { opacity: "0.9" }],
            label: [{ "justify-self": "start" }, { "font-size": "13px" }, { opacity: "0.7" }],
          },
        },
        {
          type: "horizontal-stack",
          cards: [
            this._btn(base, suffix, "power_on", "ON", "mdi:power"),
            this._btn(base, suffix, "power_off", "OFF", "mdi:power-off"),
            this._btn(base, suffix, "restart", "RST", "mdi:restart"),
            this._btn(base, suffix, "refresh", "REF", "mdi:refresh"),
          ],
        },
      ],
    };
  }

  _btn(base, suffix, kind, label, icon) {
    const entityId = `button.${base}_${kind}${suffix}`;
    return {
      type: "custom:button-card",
      entity: entityId,
      name: label,
      icon: icon,
      color_type: "card",
      styles: {
        card: [{ height: "50px" }, { "border-radius": "0" }, { "background-color": "rgba(255,255,255,0.05)" }, { border: "none" }],
        name: [{ "font-size": "12px" }, { "font-weight": "bold" }],
        icon: [{ width: "20px" }],
      },
    };
  }

  _prettyName(base) {
    return base.split("_").map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
  }
}

customElements.define("infra-power-panel", InfraPowerPanel);