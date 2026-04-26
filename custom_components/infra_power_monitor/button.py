from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import InfraPowerCoordinatorEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    provider = coordinator.provider
    entities: list[ButtonEntity] = []

    if getattr(provider, "supports_power_on", False):
        entities.append(InfraPowerOnButton(coordinator, entry))
    if getattr(provider, "supports_power_off", False):
        entities.append(InfraPowerOffButton(coordinator, entry))
    if getattr(provider, "supports_restart", False):
        entities.append(InfraPowerRestartButton(coordinator, entry))

    entities.append(InfraPowerRefreshButton(coordinator, entry))
    async_add_entities(entities)


class _BaseButton(InfraPowerCoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, config_entry, suffix: str) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{self._infra_unique_base}_{suffix}"


class InfraPowerOnButton(_BaseButton):
    entity_description = ButtonEntityDescription(
        key="power_on",
        name="Power on",
        icon="mdi:power",
        device_class=ButtonDeviceClass.UPDATE,
    )

    def __init__(self, coordinator, config_entry) -> None:
        super().__init__(coordinator, config_entry, "power_on")

    async def async_press(self) -> None:
        await self.coordinator.async_power_on()


class InfraPowerOffButton(_BaseButton):
    entity_description = ButtonEntityDescription(
        key="power_off",
        name="Power off",
        icon="mdi:power-off",
        device_class=ButtonDeviceClass.UPDATE,
    )

    def __init__(self, coordinator, config_entry) -> None:
        super().__init__(coordinator, config_entry, "power_off")

    async def async_press(self) -> None:
        await self.coordinator.async_power_off()


class InfraPowerRestartButton(_BaseButton):
    entity_description = ButtonEntityDescription(
        key="restart",
        name="Restart",
        icon="mdi:restart",
        device_class=ButtonDeviceClass.RESTART,
    )

    def __init__(self, coordinator, config_entry) -> None:
        super().__init__(coordinator, config_entry, "restart")

    async def async_press(self) -> None:
        await self.coordinator.async_restart()


class InfraPowerRefreshButton(_BaseButton):
    entity_description = ButtonEntityDescription(
        key="refresh",
        name="Refresh",
        icon="mdi:refresh",
        device_class=ButtonDeviceClass.UPDATE,
    )

    def __init__(self, coordinator, config_entry) -> None:
        super().__init__(coordinator, config_entry, "refresh")

    async def async_press(self) -> None:
        await self.coordinator.async_refresh_now()