from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PowerState
from .entity import InfraPowerCoordinatorEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    snapshot = coordinator.data

    entities: list[SensorEntity] = [
        InfraPowerStateSensor(coordinator, entry),
    ]

    if snapshot.health:
        entities.append(InfraPowerHealthSensor(coordinator, entry))

    if snapshot.firmware_version:
        entities.append(InfraFirmwareVersionSensor(coordinator, entry))

    if snapshot.redfish_version:
        entities.append(InfraRedfishVersionSensor(coordinator, entry))

    if snapshot.power_watts is not None:
        entities.append(InfraPowerUsageSensor(coordinator, entry))

    if snapshot.energy_kwh is not None:
        entities.append(InfraEnergySensor(coordinator, entry))

    for reading in snapshot.temperatures:
        entities.append(InfraDynamicNumericSensor(coordinator, entry, reading.key, reading.name, "temperature"))

    for reading in snapshot.fans:
        entities.append(InfraDynamicNumericSensor(coordinator, entry, reading.key, reading.name, "fan"))

    async_add_entities(entities)


class InfraPowerStateSensor(InfraPowerCoordinatorEntity, SensorEntity):
    entity_description = SensorEntityDescription(
        key="power_state",
        name="Power state",
        icon="mdi:power",
    )

    def __init__(self, coordinator, config_entry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{self._infra_unique_base}_power_state"

    @property
    def native_value(self) -> str:
        return self.coordinator.effective_power_state.value

    @property
    def icon(self) -> str:
        state = self.coordinator.effective_power_state
        if state == PowerState.ON:
            return "mdi:power"
        if state == PowerState.OFF:
            return "mdi:power-off"
        if state == PowerState.STARTING:
            return "mdi:progress-upload"
        if state == PowerState.STOPPING:
            return "mdi:progress-download"
        if state == PowerState.RESTARTING:
            return "mdi:restart"
        return "mdi:help-circle-outline"

    @property
    def extra_state_attributes(self) -> dict:
        snapshot = self.coordinator.data
        attrs = dict(snapshot.extra) if snapshot else {}

        if snapshot:
            attrs["health"] = snapshot.health
            attrs["firmware_version"] = snapshot.firmware_version
            attrs["redfish_version"] = snapshot.redfish_version
            attrs["is_on"] = snapshot.is_on

        return attrs


class InfraPowerHealthSensor(InfraPowerCoordinatorEntity, SensorEntity):
    entity_description = SensorEntityDescription(
        key="health",
        name="Health",
        icon="mdi:heart-pulse",
    )

    def __init__(self, coordinator, config_entry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{self._infra_unique_base}_health"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.health

    @property
    def icon(self) -> str:
        value = (self.coordinator.data.health or "").lower()
        if value == "ok":
            return "mdi:check-circle"
        if value in {"warning", "warn"}:
            return "mdi:alert"
        if value in {"critical", "error"}:
            return "mdi:alert-circle"
        return "mdi:heart-pulse"


class InfraFirmwareVersionSensor(InfraPowerCoordinatorEntity, SensorEntity):
    entity_description = SensorEntityDescription(
        key="firmware_version",
        name="Firmware version",
        icon="mdi:chip",
    )

    def __init__(self, coordinator, config_entry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{self._infra_unique_base}_firmware_version"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.firmware_version


class InfraRedfishVersionSensor(InfraPowerCoordinatorEntity, SensorEntity):
    entity_description = SensorEntityDescription(
        key="redfish_version",
        name="Redfish version",
        icon="mdi:api",
    )

    def __init__(self, coordinator, config_entry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{self._infra_unique_base}_redfish_version"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.redfish_version


class InfraPowerUsageSensor(InfraPowerCoordinatorEntity, SensorEntity):
    entity_description = SensorEntityDescription(
        key="power_usage",
        name="Power usage",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )

    def __init__(self, coordinator, config_entry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{self._infra_unique_base}_power_usage"

    @property
    def native_value(self):
        return self.coordinator.data.power_watts


class InfraEnergySensor(InfraPowerCoordinatorEntity, SensorEntity):
    entity_description = SensorEntityDescription(
        key="energy_consumption",
        name="Energy consumption",
        icon="mdi:lightning-bolt-circle",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    )

    def __init__(self, coordinator, config_entry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{self._infra_unique_base}_energy"

    @property
    def native_value(self):
        return self.coordinator.data.energy_kwh


class InfraDynamicNumericSensor(InfraPowerCoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, config_entry, reading_key: str, reading_name: str, family: str) -> None:
        super().__init__(coordinator, config_entry)
        self.reading_key = reading_key
        self.family = family
        self._attr_unique_id = f"{self._infra_unique_base}_{reading_key}"

        if family == "temperature":
            self.entity_description = SensorEntityDescription(
                key=reading_key,
                name=reading_name,
                icon="mdi:thermometer",
                native_unit_of_measurement="°C",
                device_class=SensorDeviceClass.TEMPERATURE,
                state_class=SensorStateClass.MEASUREMENT,
            )
        else:
            self.entity_description = SensorEntityDescription(
                key=reading_key,
                name=reading_name,
                icon="mdi:fan",
                state_class=SensorStateClass.MEASUREMENT,
            )

    def _get_reading(self):
        readings = self.coordinator.data.temperatures if self.family == "temperature" else self.coordinator.data.fans
        for item in readings:
            if item.key == self.reading_key:
                return item
        return None

    @property
    def native_value(self):
        reading = self._get_reading()
        return None if reading is None else reading.value

    @property
    def native_unit_of_measurement(self):
        reading = self._get_reading()
        if reading is None:
            return None
        return reading.unit