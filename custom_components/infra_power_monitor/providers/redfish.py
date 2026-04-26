from __future__ import annotations

import logging
import re
from typing import Any

import requests
import urllib3
from requests import Response
from requests.exceptions import RequestException

from ..const import DEFAULT_TIMEOUT, PowerState
from .base import BaseProvider, CannotConnect, DeviceSnapshot, InvalidAuth, InvalidRedfish, NumericReading

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_LOGGER = logging.getLogger(__name__)


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "sensor"


def _clean_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.lower() in {"none", "null", "n/a", "na", "unknown"}:
        return None
    return text


def _looks_like_placeholder_serial(value: str | None) -> bool:
    if not value:
        return True
    text = value.strip().lower()
    if text in {"0", "00000000", "to be filled by o.e.m."}:
        return True
    if text.startswith("00000000-0000-0000-0000-"):
        return True
    return False


class RedfishProvider(BaseProvider):
    backend_name = "redfish"
    supports_power_on = True
    supports_power_off = True
    supports_restart = True

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        *,
        verify_ssl: bool = False,
        manager_path: str | None = None,
        chassis_path: str | None = None,
        systems_path: str | None = None,
        label: str | None = None,
    ) -> None:
        self.host = host
        self.auth = (username, password)
        self.verify_ssl = verify_ssl
        self.base_url = f"https://{host}"
        self.label = label or host

        self._manager_path = manager_path
        self._chassis_path = chassis_path
        self._systems_path = systems_path
        self._cached_unique_id: str | None = None

    def _request(self, method: str, path: str, **kwargs: Any) -> Response:
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(
                method,
                url,
                auth=self.auth,
                verify=self.verify_ssl,
                timeout=kwargs.pop("timeout", DEFAULT_TIMEOUT),
                **kwargs,
            )
        except RequestException as exc:
            raise CannotConnect(f"Cannot connect to {self.host}: {exc}") from exc

        if response.status_code in (401, 403):
            raise InvalidAuth(f"Invalid authentication for {self.host}")
        if response.status_code == 404:
            raise InvalidRedfish(f"Path not found on {self.host}: {path}")
        if response.status_code >= 400:
            raise CannotConnect(f"HTTP {response.status_code} from {url}: {response.text}")
        return response

    def _json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self._request(method, path, **kwargs)
        try:
            return response.json()
        except ValueError as exc:
            raise InvalidRedfish(f"Invalid JSON from {path} on {self.host}") from exc

    def _discover_paths(self, root: dict | None = None) -> None:
        if self._systems_path and self._manager_path and self._chassis_path:
            return

        if root is None:
            root = self._json("GET", "/redfish/v1/")
        systems_root = root.get("Systems", {}).get("@odata.id")
        managers_root = root.get("Managers", {}).get("@odata.id")
        chassis_root = root.get("Chassis", {}).get("@odata.id")

        if not systems_root:
            raise InvalidRedfish(f"No Systems collection exposed by {self.host}")

        if not self._systems_path:
            systems_collection = self._json("GET", systems_root)
            members = systems_collection.get("Members", [])
            if not members:
                raise InvalidRedfish(f"No systems found for {self.host}")
            self._systems_path = members[0]["@odata.id"]

        if not self._manager_path and managers_root:
            managers_collection = self._json("GET", managers_root)
            members = managers_collection.get("Members", [])
            if members:
                self._manager_path = members[0]["@odata.id"]

        if not self._chassis_path and chassis_root:
            chassis_collection = self._json("GET", chassis_root)
            members = chassis_collection.get("Members", [])
            if members:
                self._chassis_path = members[0]["@odata.id"]

    def get_unique_id(self) -> str:
        return self._cached_unique_id or self.host

    def get_device_snapshot(self) -> DeviceSnapshot:
        root = self._json("GET", "/redfish/v1/")
        self._discover_paths(root)
        assert self._systems_path is not None

        system = self._json("GET", self._systems_path)
        manager = self._json("GET", self._manager_path) if self._manager_path else {}
        chassis = self._json("GET", self._chassis_path) if self._chassis_path else {}

        power_state = self._map_power_state(system.get("PowerState") or chassis.get("PowerState"))
        is_on = power_state == PowerState.ON if power_state not in (PowerState.UNKNOWN, PowerState.UNAVAILABLE) else None

        manufacturer = (
            _clean_optional_str(system.get("Manufacturer"))
            or _clean_optional_str(chassis.get("Manufacturer"))
            or _clean_optional_str(manager.get("Manufacturer"))
            or "Unknown"
        )
        model = (
            _clean_optional_str(system.get("Model"))
            or _clean_optional_str(chassis.get("Model"))
            or _clean_optional_str(system.get("Name"))
            or self.label
        )
        name = self.label or _clean_optional_str(system.get("Name")) or _clean_optional_str(chassis.get("Name")) or self.host

        raw_serial = (
            _clean_optional_str(system.get("SerialNumber"))
            or _clean_optional_str(chassis.get("SerialNumber"))
        )
        serial = None if _looks_like_placeholder_serial(raw_serial) else raw_serial

        stable_id = (
            serial
            or _clean_optional_str(system.get("UUID"))
            or _clean_optional_str(system.get("Id"))
            or _clean_optional_str(chassis.get("Id"))
            or self.host
        )

        firmware = _clean_optional_str(manager.get("FirmwareVersion"))
        redfish_version = _clean_optional_str(root.get("RedfishVersion"))
        health = self._extract_health(system, chassis, manager)

        self._cached_unique_id = stable_id

        power_watts, energy_kwh = self._read_power(power_state)
        temperatures, fans = self._read_thermal()

        processor_summary = system.get("ProcessorSummary", {})
        memory_summary = system.get("MemorySummary", {})

        extra = {
            "host": self.host,
            "system_path": self._systems_path,
            "manager_path": self._manager_path,
            "chassis_path": self._chassis_path,
            "raw_power_state": system.get("PowerState") or chassis.get("PowerState"),
        }

        processor_model = _clean_optional_str(processor_summary.get("Model"))
        processor_count = processor_summary.get("Count")
        memory_gib = memory_summary.get("TotalSystemMemoryGiB")

        if processor_model:
            extra["processor_model"] = processor_model
        if processor_count not in (None, "", 0):
            extra["processor_count"] = processor_count
        if memory_gib not in (None, "", 0):
            extra["memory_gib"] = memory_gib
        if health:
            extra["health_rollup"] = health
        if firmware:
            extra["firmware_version"] = firmware
        if redfish_version:
            extra["redfish_version"] = redfish_version

        return DeviceSnapshot(
            name=name,
            manufacturer=manufacturer,
            model=model,
            serial_number=serial,
            firmware_version=firmware,
            redfish_version=redfish_version,
            power_state=power_state,
            is_on=is_on,
            available=True,
            health=health,
            power_watts=power_watts,
            energy_kwh=energy_kwh,
            temperatures=temperatures,
            fans=fans,
            extra=extra,
        )

    def _extract_health(self, system: dict, chassis: dict, manager: dict) -> str | None:
        for source in (system, chassis, manager):
            status = source.get("Status", {})
            value = _clean_optional_str(status.get("HealthRollup")) or _clean_optional_str(status.get("Health"))
            if value:
                return value
        return None

    def _read_power(self, power_state: PowerState) -> tuple[float | int | None, float | None]:
        if not self._chassis_path:
            return None, None

        try:
            power = self._json("GET", f"{self._chassis_path}/Power")
        except Exception as exc:
            _LOGGER.debug("Could not read power data from %s: %s", self.host, exc)
            return None, None

        watts: float | int | None = None
        energy_kwh: float | None = None

        power_controls = power.get("PowerControl", [])
        if power_controls:
            first = power_controls[0]
            raw_watts = first.get("PowerConsumedWatts")

            if raw_watts not in (None, ""):
                try:
                    parsed_watts = float(raw_watts)
                    if not (parsed_watts == 0 and power_state == PowerState.ON):
                        watts = int(parsed_watts) if parsed_watts.is_integer() else parsed_watts
                except (TypeError, ValueError):
                    watts = None

            metrics = first.get("PowerMetrics") or {}
            energy_raw = metrics.get("EnergyConsumedkWh") or metrics.get("EnergyConsumedKWh")
            if energy_raw is not None:
                try:
                    parsed_energy = float(energy_raw)
                    if parsed_energy > 0:
                        energy_kwh = parsed_energy
                except (TypeError, ValueError):
                    energy_kwh = None

        return watts, energy_kwh

    def _read_thermal(self) -> tuple[list[NumericReading], list[NumericReading]]:
        if not self._chassis_path:
            return [], []

        try:
            thermal = self._json("GET", f"{self._chassis_path}/Thermal")
        except Exception as exc:
            _LOGGER.debug("Could not read thermal data from %s: %s", self.host, exc)
            return [], []

        temperatures: list[NumericReading] = []
        fans: list[NumericReading] = []

        for temp in thermal.get("Temperatures", []):
            name = temp.get("Name") or temp.get("SensorNumber") or "Temperature"
            value = temp.get("ReadingCelsius")
            if value in (None, 0, 0.0):
                continue
            temperatures.append(
                NumericReading(
                    key=f"temp_{_slugify(str(name))}",
                    name=str(name),
                    value=value,
                    unit="°C",
                    device_class="temperature",
                    state_class="measurement",
                    icon="mdi:thermometer",
                )
            )

        for fan in thermal.get("Fans", []):
            name = fan.get("FanName") or fan.get("Name") or fan.get("MemberId") or "Fan"
            value = fan.get("ReadingRPM")
            unit = "RPM"
            if value is None:
                value = fan.get("Reading")
                unit = fan.get("ReadingUnits") or "RPM"
            if value in (None, 0, 0.0):
                continue
            fans.append(
                NumericReading(
                    key=f"fan_{_slugify(str(name))}",
                    name=str(name),
                    value=value,
                    unit=str(unit),
                    state_class="measurement",
                    icon="mdi:fan",
                )
            )

        return temperatures, fans

    def _reset(self, reset_type: str) -> None:
        self._discover_paths()
        assert self._systems_path is not None
        path = f"{self._systems_path}/Actions/ComputerSystem.Reset"
        response = self._request("POST", path, json={"ResetType": reset_type})
        if response.status_code not in (200, 202, 204):
            raise CannotConnect(f"Reset failed on {self.host}: {response.text}")

    def power_on(self) -> None:
        self._reset("On")

    def power_off(self) -> None:
        self._reset("GracefulShutdown")

    def restart(self) -> None:
        try:
            self._reset("GracefulRestart")
        except CannotConnect:
            self._reset("ForceRestart")

    @staticmethod
    def _map_power_state(raw: str | None) -> PowerState:
        if not raw:
            return PowerState.UNKNOWN

        value = raw.lower()
        if value == "on":
            return PowerState.ON
        if value == "off":
            return PowerState.OFF
        if value in {"starting", "poweringon", "standbyspare"}:
            return PowerState.STARTING
        if value in {"stopping", "poweringoff", "quiesced"}:
            return PowerState.STOPPING
        return PowerState.UNKNOWN


class IdracProvider(RedfishProvider):
    backend_name = "idrac"

    def __init__(self, host: str, username: str, password: str, *, verify_ssl: bool = False, label: str | None = None) -> None:
        super().__init__(
            host,
            username,
            password,
            verify_ssl=verify_ssl,
            manager_path="/redfish/v1/Managers/iDRAC.Embedded.1",
            chassis_path="/redfish/v1/Chassis/System.Embedded.1",
            systems_path="/redfish/v1/Systems/System.Embedded.1",
            label=label,
        )