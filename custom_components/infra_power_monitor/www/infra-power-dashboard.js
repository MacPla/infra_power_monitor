customElements.define(
  "ll-strategy-dashboard-infra-power-monitor",
  class InfraPowerMonitorDashboardStrategy {
    static async generate(config, hass) {
      const states = hass.states;
      const exists = (id) => !!states[id];

      const powerStateEntities = Object.keys(states)
        .filter((id) => /^sensor\..+_power_state(_\d+)?$/.test(id))
        .sort();

      const cards = powerStateEntities.map((powerStateEntity) => {
        const raw = powerStateEntity.replace(/^sensor\./, "");
        const match = raw.match(/^(.*)_power_state(_\d+)?$/);
        const base = match[1];
        const suffix = match[2] || "";

        const name = this._prettyName(base);

        const health = `sensor.${base}_health${suffix}`;
        const firmware = `sensor.${base}_firmware_version${suffix}`;

        const tempCandidates = [
          `sensor.${base}_cpu_temp${suffix}`,
          `sensor.${base}_system_board_inlet_temp${suffix}`,
          `sensor.${base}_system_temp${suffix}`,
          `sensor.${base}_inlet_temp${suffix}`,
          `sensor.${base}_mb_10g_temp${suffix}`,
        ];
        const temp = tempCandidates.find(exists) || "";

        const buttonDefs = [
          [`button.${base}_power_on${suffix}`, "ON", "mdi:power", "on"],
          [`button.${base}_power_off${suffix}`, "OFF", "mdi:power-off", "off"],
          [`button.${base}_restart${suffix}`, "RST", "mdi:restart", "restart"],
          [`button.${base}_refresh${suffix}`, "REF", "mdi:refresh", "refresh"],
        ];

        const buttons = buttonDefs.map(([entityId, label, icon, kind]) =>
          this._button(powerStateEntity, entityId, label, icon, kind)
        );

        return {
          type: "custom:stack-in-card",
          mode: "vertical",
          keep: {
            background: true,
            border_radius: true,
            margin: true,
          },
          card_mod: {
            style: `
              ha-card {
                border: none !important;
                box-shadow: none !important;
                background: transparent !important;
                padding: 0 !important;
                overflow: hidden !important;
              }
            `,
          },
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
                  { "border-radius": "18px 18px 0 0" },
                  { padding: "18px" },
                  { height: "170px" },
                  { "box-shadow": "none" },
                  { transition: "background 280ms ease, border 280ms ease, transform 180ms ease, filter 180ms ease" },
                  {
                    "background-color": `[[[
                      const s = (entity.state || '').trim();
                      if (s === 'Encendido') return 'rgba(5,47,20,0.95)';
                      if (s === 'Apagado') return 'rgba(35,35,35,0.86)';
                      if (s === 'Arrancando') return 'rgba(18,44,88,0.95)';
                      if (s === 'Apagando') return 'rgba(90,54,10,0.95)';
                      if (s === 'Reiniciando') return 'rgba(97,57,12,0.95)';
                      return 'rgba(25,25,25,0.86)';
                    ]]]`,
                  },
                  {
                    "background-image": `[[[
                      const s = (entity.state || '').trim();
                      if (s === 'Encendido') return 'linear-gradient(135deg, rgba(8,77,33,0.98), rgba(5,47,20,0.98))';
                      if (s === 'Apagado') return 'linear-gradient(135deg, rgba(58,58,58,0.68), rgba(32,32,32,0.92))';
                      if (s === 'Arrancando') return 'linear-gradient(135deg, rgba(24,66,130,0.98), rgba(18,44,88,0.98))';
                      if (s === 'Apagando') return 'linear-gradient(135deg, rgba(130,85,20,0.98), rgba(90,54,10,0.98))';
                      if (s === 'Reiniciando') return 'linear-gradient(135deg, rgba(146,101,23,0.98), rgba(97,57,12,0.98))';
                      return 'linear-gradient(135deg, rgba(45,45,45,0.72), rgba(25,25,25,0.92))';
                    ]]]`,
                  },
                  {
                    border: `[[[
                      const s = (entity.state || '').trim();
                      if (s === 'Encendido') return '1px solid rgba(80,220,130,0.45)';
                      if (s === 'Apagado') return '1px solid rgba(180,180,180,0.22)';
                      if (s === 'Arrancando') return '1px solid rgba(90,160,255,0.45)';
                      if (s === 'Apagando' || s === 'Reiniciando') return '1px solid rgba(255,190,80,0.45)';
                      return '1px solid rgba(160,160,160,0.18)';
                    ]]]`,
                  },
                ],
                grid: [
                  { "grid-template-areas": '"i n" "i s" "i l"' },
                  { "grid-template-columns": "72px 1fr" },
                  { "grid-template-rows": "min-content min-content 1fr" },
                  { "row-gap": "6px" },
                  { "column-gap": "14px" },
                ],
                icon: [
                  { width: "54px" },
                  { height: "54px" },
                  { "align-self": "start" },
                  { "justify-self": "center" },
                  { transition: "color 280ms ease, transform 180ms ease" },
                  {
                    color: `[[[
                      const s = (entity.state || '').trim();
                      if (s === 'Encendido') return 'rgb(110,230,140)';
                      if (s === 'Apagado') return 'rgb(180,180,180)';
                      if (s === 'Arrancando') return 'rgb(100,170,255)';
                      if (s === 'Apagando' || s === 'Reiniciando') return 'rgb(255,190,80)';
                      return 'rgb(150,150,150)';
                    ]]]`,
                  },
                ],
                name: [
                  { "justify-self": "start" },
                  { "align-self": "end" },
                  { "font-size": "26px" },
                  { "font-weight": "700" },
                ],
                state: [
                  { "justify-self": "start" },
                  { "align-self": "center" },
                  { "font-size": "16px" },
                  { opacity: "0.95" },
                ],
                label: [
                  { "justify-self": "start" },
                  { "align-self": "start" },
                  { "font-size": "13px" },
                  { opacity: "0.82" },
                  { "white-space": "normal" },
                  { "text-align": "left" },
                ],
              },
              extra_styles: `
                ha-card:hover {
                  transform: translateY(-1px);
                  filter: brightness(1.08);
                }

                ha-card:hover #img-cell {
                  transform: scale(1.03);
                }
              `,
            },
            {
              type: "sections",
              cards: buttons,
            },
          ],
        };
      });

      return {
        title: "Infra Power",
        views: [
          {
            title: "Overview",
            path: "overview",
            icon: "mdi:server",
            type: "sections",
            max_columns: 4,
            sections: [
              {
                type: "grid",
                column_span: 4,
                cards,
              },
            ],
          },
        ],
      };
    }

    static _button(powerStateEntity, entityId, name, icon, kind) {
      const matchState =
        kind === "on"
          ? "Encendido"
          : kind === "off"
          ? "Apagado"
          : kind === "restart"
          ? "Reiniciando"
          : "";

      const activeExpr =
        kind === "refresh"
          ? "false"
          : `states['${powerStateEntity}']?.state === '${matchState}'`;

      const bg =
        kind === "on"
          ? "rgba(80,220,130,0.28)"
          : kind === "off"
          ? "rgba(220,80,80,0.25)"
          : kind === "restart"
          ? "rgba(255,190,80,0.22)"
          : "rgba(90,160,255,0.20)";

      const border =
        kind === "on"
          ? "1px solid rgba(80,220,130,0.55)"
          : kind === "off"
          ? "1px solid rgba(220,80,80,0.55)"
          : kind === "restart"
          ? "1px solid rgba(255,190,80,0.45)"
          : "1px solid rgba(90,160,255,0.45)";

      const color =
        kind === "on"
          ? "rgb(110,230,140)"
          : kind === "off"
          ? "rgb(255,120,120)"
          : kind === "restart"
          ? "rgb(255,190,80)"
          : "rgb(100,170,255)";

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
            { "box-shadow": "none" },
            { transition: "background 220ms ease, border 220ms ease, filter 180ms ease, transform 180ms ease" },
            {
              background: `[[[ return (${activeExpr}) ? '${bg}' : 'rgba(255,255,255,0.07)'; ]]]`,
            },
            {
              border: `[[[ return (${activeExpr}) ? '${border}' : '1px solid rgba(255,255,255,0.08)'; ]]]`,
            },
          ],
          icon: [
            { width: "22px" },
            { height: "22px" },
            { transition: "color 220ms ease, transform 180ms ease" },
            {
              color: `[[[ return (${activeExpr}) ? '${color}' : 'var(--primary-text-color)'; ]]]`,
            },
          ],
          name: [
            { "font-size": "12px" },
            { "font-weight": "700" },
          ],
        },
        extra_styles: `
          ha-card:hover {
            filter: brightness(1.12);
            transform: translateY(-1px);
          }

          ha-card:hover ha-icon {
            transform: scale(1.08);
          }
        `,
      };
    }

    static _prettyName(base) {
      return base
        .split("_")
        .map((word) => {
          const lower = word.toLowerCase();
          if (lower === "gpu") return "GPU";
          if (lower === "nas") return "NAS";
          return word.charAt(0).toUpperCase() + word.slice(1);
        })
        .join(" ");
    }
  }
);

window.customStrategies = window.customStrategies || [];
window.customStrategies.push({
  type: "infra-power-monitor",
  strategyType: "dashboard",
  name: "Infra Power Monitor",
  description: "Auto-generated dashboard for Infra Power Monitor",
});
);