from __future__ import annotations

import logging
import socket
import subprocess

from ..const import PowerState
from .base import BaseProvider, DeviceSnapshot, UnsupportedAction

_LOGGER = logging.getLogger(__name__)


def _normalize_mac(mac: str) -> bytes:
    clean = mac.replace(":", "").replace("-", "").replace(".", "").lower()
    if len(clean) != 12:
        raise ValueError(f"Invalid MAC address: {mac}")
    return bytes.fromhex(clean)


def _build_magic_packet(mac: str) -> bytes:
    mac_bytes = _normalize_mac(mac)
    return b"\xff" * 6 + mac_bytes * 16


def _send_magic_packet(mac: str, broadcast_address: str, port: int = 9) -> None:
    packet = _build_magic_packet(mac)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(packet, (broadcast_address, port))
    finally:
        sock.close()


class WakeOnLanProvider(BaseProvider):
    backend_name = "wake_on_lan"
    supports_power_on = True
    supports_power_off = False
    supports_restart = False

    def __init__(
        self,
        hass,
        mac: str,
        *,
        broadcast_address: str,
        status_host: str,
        status_port: int,
        use_icmp: bool,
        name: str,
    ) -> None:
        self.hass = hass
        self.mac = mac
        self.broadcast_address = broadcast_address
        self.status_host = status_host
        self.status_port = status_port
        self.use_icmp = use_icmp
        self.name = name
        self._cached_unique_id = self.mac.lower().replace(":", "").replace("-", "")

    def get_unique_id(self) -> str:
        return self._cached_unique_id

    def get_device_snapshot(self) -> DeviceSnapshot:
        is_online = self._check_online_sync()
        return DeviceSnapshot(
            name=self.name,
            manufacturer="Generic",
            model="Wake-on-LAN Device",
            serial_number=self.get_unique_id(),
            firmware_version=None,
            power_state=PowerState.ON if is_online else PowerState.OFF,
            is_on=is_online,
            available=True,
            extra={
                "host": self.status_host,
                "mac": self.mac,
                "broadcast_address": self.broadcast_address,
            },
        )

    def power_on(self) -> None:
        _send_magic_packet(self.mac, self.broadcast_address, 9)

    def power_off(self) -> None:
        raise UnsupportedAction("Wake-on-LAN cannot power off devices")

    def restart(self) -> None:
        raise UnsupportedAction("Wake-on-LAN cannot restart devices directly")

    def _check_online_sync(self) -> bool:
        if self.use_icmp:
            return self._check_icmp_sync()
        return self._check_tcp_sync()

    def _check_tcp_sync(self) -> bool:
        try:
            with socket.create_connection((self.status_host, self.status_port), timeout=2):
                return True
        except OSError:
            return False

    def _check_icmp_sync(self) -> bool:
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", self.status_host],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            return result.returncode == 0
        except Exception as err:
            _LOGGER.debug("ICMP check failed for %s: %s", self.status_host, err)
            return self._check_tcp_sync()