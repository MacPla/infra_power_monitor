from __future__ import annotations

import json
import logging
import os

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

LOVELACE_STORAGE_FILE = os.path.join(".storage", "lovelace")
INFRA_POWER_DASHBOARD_PATH = "infra-power"


def _register_infra_power_panel(hass: HomeAssistant) -> None:
    if f"{DOMAIN}_panel" in hass.data:
        return

    try:
        hass.components.frontend.async_register_built_in_panel(
            component_name="iframe",
            sidebar_title="Infra Power",
            sidebar_icon="mdi:server",
            frontend_url_path="infra-power",
            config={"url": "/lovelace/infra-power"},
        )
        hass.data[f"{DOMAIN}_panel"] = True
    except Exception as exc:
        _LOGGER.warning(
            "Infra Power sidebar panel could not be registered: %s",
            exc,
        )


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    _register_infra_power_panel(hass)

    if hass.config_entries.async_entries(DOMAIN):
        hass.async_create_task(_async_ensure_infra_power_dashboard(hass))

    return True


def _read_lovelace_storage(storage_path: str) -> dict[str, object]:
    if not os.path.exists(storage_path):
        return {
            "key": "lovelace",
            "version": 1,
            "data": {"dashboards": [], "resources": []},
        }

    with open(storage_path, "r", encoding="utf-8") as file:
        return json.load(file)


def _write_lovelace_storage(storage_path: str, data: dict[str, object]) -> None:
    os.makedirs(os.path.dirname(storage_path), exist_ok=True)
    with open(storage_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


async def _async_ensure_infra_power_dashboard(hass: HomeAssistant) -> None:
    storage_path = hass.config.path(LOVELACE_STORAGE_FILE)
    storage = await hass.async_add_executor_job(_read_lovelace_storage, storage_path)

    dashboards = storage.setdefault("data", {}).setdefault("dashboards", [])
    if any(
        dashboard.get("url_path") == INFRA_POWER_DASHBOARD_PATH
        for dashboard in dashboards
    ):
        return

    dashboards.append(
        {
            "id": "infra_power",
            "url_path": INFRA_POWER_DASHBOARD_PATH,
            "title": "Infra Power",
            "icon": "mdi:server",
            "show_in_sidebar": True,
            "sidebar_title": "Infra Power",
            "sidebar_icon": "mdi:server",
            "require_admin": False,
            "mode": "storage",
            "views": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "path": "overview",
                    "icon": "mdi:server",
                    "type": "sections",
                    "max_columns": 4,
                    "sections": [
                        {
                            "type": "grid",
                            "column_span": 4,
                            "cards": [],
                        }
                    ],
                }
            ],
        }
    )

    await hass.async_add_executor_job(_write_lovelace_storage, storage_path, storage)


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

    _register_infra_power_panel(hass)
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
