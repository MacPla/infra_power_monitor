"""The Infra Power Monitor integration."""

import logging
import os

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_BACKEND,
    CONF_BROADCAST_ADDRESS,
    CONF_SCAN_INTERVAL,
    CONF_STATUS_HOST,
    CONF_STATUS_PORT,
    CONF_USE_ICMP,
    CONF_VERIFY_SSL,
    CONF_OS_TYPE,
    CONF_SSH_USER,
    CONF_SSH_KEY_PATH,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSH_KEY_PATH,
    DEFAULT_HELPER_PATH,
    DOMAIN,
)
from .coordinator import InfraPowerCoordinator
from .providers.redfish import IdracProvider, RedfishProvider
from .providers.wol import WakeOnLanProvider
from .providers.hybrid import HybridProvider

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]
VERSION = "1.0.5"


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
    # Using a unique path 'infra-power-monitor' to avoid conflicts
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
    backend = entry.data[CONF_BACKEND]
    name = entry.data[CONF_NAME]

    _LOGGER.info(
        "Infra Power Monitor setup entry: title=%s backend=%s",
        entry.title,
        backend,
    )

    if backend == "idrac":
        provider = IdracProvider(
            entry.data[CONF_HOST],
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            verify_ssl=entry.data.get(CONF_VERIFY_SSL, False),
            label=name,
        )

    elif backend == "redfish":
        provider = RedfishProvider(
            entry.data[CONF_HOST],
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            verify_ssl=entry.data.get(CONF_VERIFY_SSL, False),
            label=name,
        )

    elif backend == "wake_on_lan":
        provider = WakeOnLanProvider(
            hass,
            entry.data["mac"],
            broadcast_address=entry.data.get(
                CONF_BROADCAST_ADDRESS,
                entry.data.get("broadcast", "255.255.255.255"),
            ),
            status_host=entry.data.get(
                CONF_STATUS_HOST,
                entry.data.get("host", ""),
            ),
            status_port=entry.data.get(CONF_STATUS_PORT, 443),
            use_icmp=entry.data.get(CONF_USE_ICMP, True),
            name=name,
        )

    elif backend == "hybrid":
        provider = HybridProvider(
            name=name,
            mac=entry.data["mac"],
            broadcast_address=entry.data.get(
                CONF_BROADCAST_ADDRESS,
                entry.data.get("broadcast", "255.255.255.255"),
            ),
            status_host=entry.data.get(
                CONF_STATUS_HOST,
                entry.data.get("host", ""),
            ),
            status_port=entry.data.get(CONF_STATUS_PORT, 22),
            use_icmp=entry.data.get(CONF_USE_ICMP, True),
            os_type=entry.data.get(CONF_OS_TYPE, "linux"),
            ssh_user=entry.data[CONF_SSH_USER],
            ssh_key_path=entry.data.get(CONF_SSH_KEY_PATH, DEFAULT_SSH_KEY_PATH),
            helper_path=DEFAULT_HELPER_PATH,
        )

    else:
        raise ValueError(f"Unsupported backend: {backend}")

    coordinator = InfraPowerCoordinator(
        hass,
        provider,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "provider": provider,
        "coordinator": coordinator,
    }

    # Forward the setup to the platforms (sensor, button)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
