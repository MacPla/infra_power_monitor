from __future__ import annotations

import logging

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.http import StaticPathConfig

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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    backend = entry.data[CONF_BACKEND]
    name = entry.data[CONF_NAME]

    _LOGGER.warning(
        "Infra Power Monitor setup entry: title=%s backend=%s data_keys=%s",
        entry.title,
        backend,
        sorted(entry.data.keys()),
    )

    if f"{DOMAIN}_static" not in hass.data:
        hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    "/infra_power_monitor",
                    hass.config.path("custom_components/infra_power_monitor/www"),
                    False,
                )
            ]
        )
        hass.data[f"{DOMAIN}_static"] = True

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
