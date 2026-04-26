"""The Infra Power Monitor integration."""

import logging
import os

from homeassistant.components import panel_custom
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

DOMAIN = "infra_power_monitor"
VERSION = "1.0.3"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Infra Power Monitor component."""
    
    # Register static path for the dashboard JS
    # We point to the www folder
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                "/infra_power_monitor_static",
                os.path.join(os.path.dirname(__file__), "www"),
                False,
            )
        ]
    )

    # Register the custom panel (Alarmo style)
    # Using a unique path 'infra-power-monitor' to avoid conflicts with previous dashboards
    if "infra-power-monitor" not in hass.data.get("frontend_panels", {}):
        await panel_custom.async_register_panel(
            hass,
            webcomponent_name="infra-power-panel",
            frontend_url_path="infra-power-monitor",
            module_url=f"/infra_power_monitor_static/infra-power-dashboard.js?v={VERSION}",
            sidebar_title="Infra Power",
            sidebar_icon="mdi:server",
            require_admin=False,
            config={},
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Set up from a config entry."""
    return True
