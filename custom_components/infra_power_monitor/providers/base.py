from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..const import PowerState


class ProviderError(Exception):
    """Base provider error."""


class CannotConnect(ProviderError):
    """Raised when a provider cannot connect."""


class InvalidAuth(ProviderError):
    """Raised when authentication fails."""


class InvalidRedfish(ProviderError):
    """Raised when Redfish is not usable."""


class UnsupportedAction(ProviderError):
    """Raised when a provider cannot perform an action."""


@dataclass(slots=True)
class NumericReading:
    key: str
    name: str
    value: float | int | None
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    icon: str | None = None


@dataclass(slots=True)
class DeviceSnapshot:
    name: str
    manufacturer: str
    model: str
    serial_number: str | None = None
    firmware_version: str | None = None
    redfish_version: str | None = None
    power_state: PowerState = PowerState.UNKNOWN
    is_on: bool | None = None
    available: bool = True
    health: str | None = None
    power_watts: float | int | None = None
    energy_kwh: float | None = None
    temperatures: list[NumericReading] = field(default_factory=list)
    fans: list[NumericReading] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class BaseProvider(ABC):
    backend_name: str = "base"
    supports_power_on: bool = True
    supports_power_off: bool = True
    supports_restart: bool = True

    @abstractmethod
    def get_unique_id(self) -> str:
        """Return a stable unique ID for the device."""

    @abstractmethod
    def get_device_snapshot(self) -> DeviceSnapshot:
        """Fetch the current device snapshot."""

    @abstractmethod
    def power_on(self) -> None:
        """Power on the device."""

    @abstractmethod
    def power_off(self) -> None:
        """Power off the device."""

    @abstractmethod
    def restart(self) -> None:
        """Restart the device."""