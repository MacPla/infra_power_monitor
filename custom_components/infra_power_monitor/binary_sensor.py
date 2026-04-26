from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PowerState
from .entity import InfraPowerCoordinatorEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([InfraPowerOnlineBinarySensor(coordinator, entry)])


class InfraPowerOnlineBinarySensor(InfraPowerCoordinatorEntity, BinarySensorEntity):
    entity_description = BinarySensorEntityDescription(
        key="online",
        name="Online",
        icon="mdi:server",
        device_class=BinarySensorDeviceClass.RUNNING,
    )

    def __init__(self, coordinator, config_entry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{self._infra_unique_base}_online"

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.effective_power_state
        if state in {PowerState.UNKNOWN, PowerState.UNAVAILABLE}:
            return None
        return state in {PowerState.ON, PowerState.STARTING, PowerState.RESTARTING}

    @property
    def icon(self) -> str:
        state = self.coordinator.effective_power_state
        if state == PowerState.ON:
            return "mdi:server"
        if state == PowerState.OFF:
            return "mdi:server-off"
        if state in {PowerState.STARTING, PowerState.RESTARTING}:
            return "mdi:server-plus"
        if state == PowerState.STOPPING:
            return "mdi:server-minus"
        return "mdi:server-network"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None