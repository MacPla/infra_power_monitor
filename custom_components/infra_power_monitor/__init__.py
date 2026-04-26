"""The Infra Power Monitor integration."""

import logging
import os

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]
VERSION = "1.0.4"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Infra Power Monitor component."""
    
    # Register static path for the dashboard JS
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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Forward the setup to the platforms (sensor, button)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok
