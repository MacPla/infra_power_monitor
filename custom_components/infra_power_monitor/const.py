from __future__ import annotations

from datetime import timedelta
from enum import Enum

DOMAIN = "infra_power_monitor"

CONF_BACKEND = "backend"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_BROADCAST_ADDRESS = "broadcast_address"
CONF_STATUS_HOST = "status_host"
CONF_STATUS_PORT = "status_port"
CONF_USE_ICMP = "use_icmp"

# NEW
CONF_OS_TYPE = "os_type"
CONF_SSH_USER = "ssh_user"
CONF_SSH_KEY_PATH = "ssh_key_path"

DEFAULT_VERIFY_SSL = False
DEFAULT_SCAN_INTERVAL = 60
DEFAULT_WOL_BROADCAST = "255.255.255.255"
DEFAULT_STATUS_PORT = 443
DEFAULT_USE_ICMP = True
DEFAULT_TIMEOUT = 5

# NEW
DEFAULT_SSH_KEY_PATH = "/config/.ssh/infra_power_monitor_id_rsa"
DEFAULT_HELPER_PATH = "/usr/local/bin/infra_power.sh"

PLATFORMS = ["binary_sensor", "sensor", "button"]

UPDATE_INTERVAL_FALLBACK = timedelta(seconds=60)


class PowerState(str, Enum):
    ON = "Encendido"
    OFF = "Apagado"
    STARTING = "Arrancando"
    STOPPING = "Apagando"
    RESTARTING = "Reiniciando"
    UNKNOWN = "Desconocido"
    UNAVAILABLE = "No disponible"