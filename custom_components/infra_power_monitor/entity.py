from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class InfraPowerCoordinatorEntity(CoordinatorEntity):
    def __init__(self, coordinator, config_entry) -> None:
        super().__init__(coordinator)
        self.config_entry = config_entry
        snapshot = coordinator.data

        unique_base = coordinator.provider.get_unique_id()

        device_kwargs = {
            "identifiers": {(DOMAIN, unique_base)},
            "name": snapshot.name,
            "manufacturer": snapshot.manufacturer,
            "model": snapshot.model,
            "configuration_url": f"https://{snapshot.extra['host']}" if "host" in snapshot.extra else None,
        }

        if snapshot.serial_number:
            device_kwargs["serial_number"] = snapshot.serial_number
        if snapshot.firmware_version:
            device_kwargs["sw_version"] = snapshot.firmware_version

        self._attr_device_info = DeviceInfo(**device_kwargs)
        self._attr_has_entity_name = True
        self._infra_unique_base = unique_base