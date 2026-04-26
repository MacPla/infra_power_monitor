from __future__ import annotations

import logging
import socket
import subprocess

from ..const import PowerState
from .base import BaseProvider, DeviceSnapshot

_LOGGER = logging.getLogger(__name__)


def _normalize_mac(mac: str) -> bytes:
    return bytes.fromhex(mac.replace(":", "").replace("-", ""))


def _send_magic_packet(mac: str, broadcast_address: str):
    mac_bytes = _normalize_mac(mac)
    packet = b"\xff" * 6 + mac_bytes * 16

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(packet, (broadcast_address, 9))
    sock.close()


class HybridProvider(BaseProvider):
    backend_name = "hybrid"
    supports_power_on = True
    supports_power_off = True
    supports_restart = True

    def __init__(
        self,
        *,
        name,
        mac,
        broadcast_address,
        status_host,
        status_port,
        use_icmp,
        os_type,
        ssh_user,
        ssh_key_path,
        helper_path,
    ):
        self.name = name
        self.mac = mac
        self.broadcast_address = broadcast_address
        self.host = status_host
        self.port = status_port
        self.use_icmp = use_icmp
        self.os_type = os_type
        self.ssh_user = ssh_user
        self.ssh_key_path = ssh_key_path
        self.helper_path = helper_path
        self._uid = mac.lower().replace(":", "")

    def get_unique_id(self):
        return self._uid

    def get_device_snapshot(self):
        is_on = self._ping()

        return DeviceSnapshot(
            name=self.name,
            manufacturer="Generic",
            model=f"Hybrid ({self.os_type})",
            power_state=PowerState.ON if is_on else PowerState.OFF,
            is_on=is_on,
            available=True,
        )

    def power_on(self):
        _send_magic_packet(self.mac, self.broadcast_address)

    def power_off(self):
        if self.os_type == "windows":
            cmd = "shutdown /s /t 0"
        else:
            cmd = f"sudo -n {self.helper_path} shutdown"
        self._ssh(cmd)

    def restart(self):
        if self.os_type == "windows":
            cmd = "shutdown /r /t 0"
        else:
            cmd = f"sudo -n {self.helper_path} reboot"
        self._ssh(cmd)

    def _ssh(self, command):
        cmd = [
            "ssh",
            "-i",
            self.ssh_key_path,
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=no",
            f"{self.ssh_user}@{self.host}",
            command,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(result.stderr)

    def _ping(self):
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", self.host],
                capture_output=True,
            )
            return result.returncode == 0
        except Exception:
            return False