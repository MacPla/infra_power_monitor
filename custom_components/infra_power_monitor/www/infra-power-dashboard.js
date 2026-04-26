
const VERSION = "1.0.9";

/**
 * Infra Power Monitor Panel - ULTRA STABLE VERSION
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
            font-family: var(--paper-font-body1_-_font-family, 'Roboto', sans-serif);
          }
          .container {
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
          }
          h1 {
            margin-bottom: 30px;
            font-weight: 400;
          }
          .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
          }
          .card-container {
            background: var(--card-background-color, white);
            border-radius: var(--ha-card-border-radius, 12px);
            box-shadow: var(--ha-card-box-shadow, none);
            border: 1px solid var(--divider-color, #e0e0e0);
            overflow: hidden;
          }
        </style>
        <div class="container">
          <h1>Infra Power Monitor</h1>
          <div id="grid" class="grid">
            <div style="padding: 20px;">Iniciando...</div>
          </div>
        </div>
      `;
    }
  }

  async _update(hass) {
    const grid = this._root.getElementById('grid');
    if (!grid || !hass) return;

    const states = hass.states;
    const powerStateEntities = Object.keys(states)
      .filter((id) => id.startsWith('sensor.') && id.includes('_power_state'))
      .sort();

    if (powerStateEntities.length === 0) {
        grid.innerHTML = '<div style="padding: 20px;">No se han encontrado sensores. Revisa la configuración de la integración.</div>';
        return;
    }

    const entitiesKey = JSON.stringify(powerStateEntities);
    if (this._renderedEntities === entitiesKey) {
        Array.from(grid.children).forEach(container => {
            const card = container.firstChild;
            if (card && card.hass !== hass) card.hass = hass;
        });
        return;
    }

    this._renderedEntities = entitiesKey;
    grid.innerHTML = '';

    const helpers = window.loadCardHelpers ? await window.loadCardHelpers() : null;
    if (!helpers) {
        grid.innerHTML = '<div style="padding: 20px;">Error crítico: No se pueden cargar los componentes de Home Assistant.</div>';
        return;
    }

    for (const entityId of powerStateEntities) {
      const container = document.createElement('div');
      container.className = 'card-container';
      
      const config = this._generateSimpleConfig(entityId, states);
      const card = helpers.createCardElement(config);
      card.hass = hass;
      
      container.appendChild(card);
      grid.appendChild(container);
    }
  }

  _generateSimpleConfig(powerStateEntity, states) {
    const raw = powerStateEntity.replace(/^sensor\./, "");
    const match = raw.match(/^(.*?)(?:_power_state)(?:_(\d+))?$/);
    const base = match ? match[1] : raw;
    const suffix = (match && match[2]) ? `_${match[2]}` : "";
    
    const entities = [
      powerStateEntity,
      `sensor.${base}_health${suffix}`,
      `sensor.${base}_power_usage${suffix}`,
      `sensor.${base}_firmware_version${suffix}`
    ].filter(id => !!states[id]);

    const buttons = [
      `button.${base}_power_on${suffix}`,
      `button.${base}_power_off${suffix}`,
      `button.${base}_restart${suffix}`,
      `button.${base}_refresh${suffix}`
    ].filter(id => !!states[id]).map(id => ({
        type: "button",
        entity: id,
        tap_action: { action: "call-service", service: "button.press", target: { entity_id: id } }
    }));

    return {
      type: "vertical-stack",
      cards: [
        {
          type: "entities",
          title: base.toUpperCase().replace(/_/g, " "),
          entities: entities
        },
        {
          type: "horizontal-stack",
          cards: buttons
        }
      ]
    };
  }
}

customElements.define("infra-power-panel", InfraPowerPanel);