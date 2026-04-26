from __future__ import annotations

import logging
import os

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import (
    CONF_ICON,
    CONF_REQUIRE_ADMIN,
    CONF_SHOW_IN_SIDEBAR,
    CONF_TITLE,
    CONF_URL_PATH,
)
from homeassistant.components.lovelace.dashboard import (
    DashboardsCollection,
    LovelaceStorage,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_USERNAME
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
    PLATFORMS,
)
from .coordinator import InfraPowerCoordinator
from .providers.redfish import IdracProvider, RedfishProvider
from .providers.wol import WakeOnLanProvider
from .providers.hybrid import HybridProvider

_LOGGER = logging.getLogger(__name__)

INFRA_POWER_DASHBOARD_PATH = "infra-power"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Infra Power Monitor component."""
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                f"/{DOMAIN}",
                hass.config.path(f"custom_components/{DOMAIN}/www"),
                False,
            )
        ]
    )
    return True


async def _async_ensure_infra_power_dashboard(hass: HomeAssistant) -> None:
    dashboards_collection = DashboardsCollection(hass)
    await dashboards_collection.async_load()

    existing_dashboard = None
    for dashboard in dashboards_collection.async_items():
        if dashboard.get(CONF_URL_PATH) == INFRA_POWER_DASHBOARD_PATH:
            existing_dashboard = dashboard
            break

    if existing_dashboard:
        dashboard_id = existing_dashboard.get("id")
        dashboard_store = LovelaceStorage(
            hass,
            {"id": dashboard_id, CONF_URL_PATH: INFRA_POWER_DASHBOARD_PATH},
        )
        try:
            config = await dashboard_store.async_load()
        except Exception:
            config = None

        if not config or config.get("strategy", {}).get("type") != "infra-power-monitor":
            await dashboard_store.async_save(
                {"strategy": {"type": "infra-power-monitor"}}
            )
        return

    try:
        dashboard_item = await dashboards_collection.async_create_item(
            {
                CONF_URL_PATH: INFRA_POWER_DASHBOARD_PATH,
                CONF_TITLE: "Infra Power",
                CONF_ICON: "mdi:server",
                CONF_SHOW_IN_SIDEBAR: True,
                CONF_REQUIRE_ADMIN: False,
            }
        )

        dashboard_store = LovelaceStorage(
            hass,
            {"id": dashboard_item["id"], CONF_URL_PATH: INFRA_POWER_DASHBOARD_PATH},
        )
        await dashboard_store.async_save(
            {"strategy": {"type": "infra-power-monitor"}}
        )
    except Exception as exc:
        _LOGGER.warning(
            "Failed to create Infra Power dashboard: %s",
            exc,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    backend = entry.data[CONF_BACKEND]
    name = entry.data[CONF_NAME]

    _LOGGER.warning(
        "Infra Power Monitor setup entry: title=%s backend=%s data_keys=%s",
        entry.title,
        backend,
        sorted(entry.data.keys()),
    )

    await _async_ensure_infra_power_dashboard(hass)

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

    _LOGGER.warning(
        "Infra Power Monitor provider loaded: title=%s provider=%s "
        "supports_on=%s supports_off=%s supports_restart=%s",
        entry.title,
        provider.__class__.__name__,
        getattr(provider, "supports_power_on", None),
        getattr(provider, "supports_power_off", None),
        getattr(provider, "supports_restart", None),
    )

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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
