
const VERSION = "1.0.8";

/**
 * Infra Power Monitor Panel
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
            padding: 16px;
            max-width: 1600px;
            margin: 0 auto;
          }
          .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            padding: 0 8px;
          }
          h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 500;
          }
          .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 16px;
          }
          @media (max-width: 600px) {
            .grid {
              grid-template-columns: 1fr;
            }
          }
          .error-msg {
            padding: 40px;
            text-align: center;
            grid-column: 1/-1;
            opacity: 0.7;
          }
        </style>
        <div class="container">
          <div class="header">
            <h1>Infra Power Monitor</h1>
          </div>
          <div id="grid" class="grid">
            <div class="error-msg">Iniciando interfaz...</div>
          </div>
        </div>
      `;
    }
  }

  async _update(hass) {
    const grid = this._root.getElementById('grid');
    if (!grid) return;

    const states = hass.states;
    // Find all power state sensors
    const powerStateEntities = Object.keys(states)
      .filter((id) => id.startsWith('sensor.') && id.includes('_power_state'))
      .sort();

    if (powerStateEntities.length === 0) {
        if (!this._emptyNotified) {
            grid.innerHTML = '<div class="error-msg">No se han encontrado sensores de estado. Verifica que la integración esté configurada.</div>';
            this._emptyNotified = true;
        }
        return;
    }
    this._emptyNotified = false;

    // Only full redraw if entities changed
    const entitiesKey = JSON.stringify(powerStateEntities);
    if (this._renderedEntities === entitiesKey) {
        Array.from(grid.children).forEach(card => {
            if (card.hass !== hass) card.hass = hass;
        });
        return;
    }

    this._renderedEntities = entitiesKey;
    grid.innerHTML = '';

    // Check for custom card availability
    const hasStackInCard = customElements.get('stack-in-card') || customElements.get('hui-stack-in-card');
    const hasButtonCard = customElements.get('button-card') || customElements.get('hui-button-card');

    const helpers = window.loadCardHelpers ? await window.loadCardHelpers() : null;

    for (const entityId of powerStateEntities) {
      const config = this._generateCardConfig(entityId, states, hasStackInCard, hasButtonCard);
      
      let card;
      if (helpers && helpers.createCardElement) {
          card = helpers.createCardElement(config);
      } else {
          // Absolute fallback if helpers are missing
          card = document.createElement('div');
          card.innerHTML = `<div style="padding: 10px; border: 1px solid red;">Error: No se pudo cargar el motor de tarjetas de HA</div>`;
      }
      
      card.hass = hass;
      grid.appendChild(card);
    }
  }

  _generateCardConfig(powerStateEntity, states, hasStackInCard, hasButtonCard) {
    const raw = powerStateEntity.replace(/^sensor\./, "");
    const match = raw.match(/^(.*?)(?:_power_state)(?:_(\d+))?$/);
    if (!match) return { type: "error", error: "Entity name pattern mismatch" };
    
    const base = match[1];
    const suffix = match[2] ? `_${match[2]}` : "";
    const name = this._prettyName(base);

    const health = `sensor.${base}_health${suffix}`;
    const firmware = `sensor.${base}_firmware_version${suffix}`;
    const temp = [`sensor.${base}_cpu_temp${suffix}`, `sensor.${base}_system_temp${suffix}`].find(id => !!states[id]) || "";

    const buttonDefs = [
      [`button.${base}_power_on${suffix}`, "ON", "mdi:power", "on"],
      [`button.${base}_power_off${suffix}`, "OFF", "mdi:power-off", "off"],
      [`button.${base}_restart${suffix}`, "RST", "mdi:restart", "restart"],
      [`button.${base}_refresh${suffix}`, "REF", "mdi:refresh", "refresh"],
    ];

    const buttons = buttonDefs.map(([entityId, label, icon, kind]) =>
      this._generateButtonConfig(powerStateEntity, entityId, label, icon, kind, hasButtonCard)
    );

    // Main Card Config
    const mainCard = hasButtonCard ? {
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
          { "border-radius": "18px 18px 0 0" },
          { padding: "18px" },
          { height: "170px" },
          {
            "background-color": `[[[
              const s = (entity.state || '').trim();
              if (s === 'Encendido') return 'rgba(5,47,20,0.95)';
              if (s === 'Apagado') return 'rgba(35,35,35,0.86)';
              return 'rgba(25,25,25,0.86)';
            ]]]`,
          },
        ],
        grid: [
          { "grid-template-areas": '"i n" "i s" "i l"' },
          { "grid-template-columns": "72px 1fr" },
          { "row-gap": "6px" },
        ],
        icon: [{ width: "54px" }, { height: "54px" }],
        name: [{ "justify-self": "start" }, { "font-size": "26px" }, { "font-weight": "700" }],
        state: [{ "justify-self": "start" }, { "font-size": "16px" }],
        label: [{ "justify-self": "start" }, { "font-size": "13px" }, { opacity: "0.82" }],
      },
    } : {
      type: "entities",
      title: name,
      entities: [powerStateEntity, health, firmware].filter(id => !!states[id])
    };

    return {
      type: hasStackInCard ? "custom:stack-in-card" : "vertical-stack",
      cards: [
        mainCard,
        {
          type: "horizontal-stack",
          cards: buttons,
        },
      ],
    };
  }

  _generateButtonConfig(powerStateEntity, entityId, name, icon, kind, hasButtonCard) {
    if (!hasButtonCard) {
        return { type: "button", entity: entityId, icon, name };
    }
    const matchState = kind === "on" ? "Encendido" : kind === "off" ? "Apagado" : kind === "restart" ? "Reiniciando" : "";
    const activeExpr = kind === "refresh" ? "false" : `states['${powerStateEntity}']?.state === '${matchState}'`;

    return {
      type: "custom:button-card",
      entity: entityId,
      icon,
      name,
      show_state: false,
      tap_action: {
        action: "call-service",
        service: "button.press",
        target: { entity_id: entityId },
      },
      styles: {
        card: [
          { height: "48px" },
          { "border-radius": "12px" },
          { background: `[[[ return (${activeExpr}) ? 'rgba(80,220,130,0.28)' : 'rgba(255,255,255,0.07)'; ]]]` },
        ],
        icon: [{ width: "22px" }, { height: "22px" }],
        name: [{ "font-size": "12px" }, { "font-weight": "700" }],
      },
    };
  }

  _prettyName(base) {
    return base.split("_").map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
  }
}

customElements.define("infra-power-panel", InfraPowerPanel);