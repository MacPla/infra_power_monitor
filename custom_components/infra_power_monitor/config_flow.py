from __future__ import annotations

import logging
import os
import stat
import uuid
from pathlib import Path
from typing import Any

import paramiko
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_BACKEND,
    CONF_BROADCAST_ADDRESS,
    CONF_SCAN_INTERVAL,
    CONF_STATUS_HOST,
    CONF_STATUS_PORT,
    CONF_USE_ICMP,
    CONF_VERIFY_SSL,
    CONF_ENABLE_PANEL,
    DEFAULT_HELPER_PATH,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSH_KEY_PATH,
    DEFAULT_STATUS_PORT,
    DEFAULT_USE_ICMP,
    DEFAULT_VERIFY_SSL,
    DEFAULT_WOL_BROADCAST,
    DEFAULT_ENABLE_PANEL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CONF_OS_TYPE = "os_type"
CONF_SSH_USER = "ssh_user"
CONF_SSH_PASSWORD = "ssh_password"
CONF_SSH_KEY_PATH = "ssh_key_path"


HYBRID_DESCRIPTION = """
Modo híbrido:

• Wake-on-LAN se usa para encender la máquina.
• SSH se usa solo una vez durante la configuración para instalar un helper controlado de apagado/reinicio.
• El usuario y la contraseña SSH se usan únicamente durante este paso.
• La contraseña NO se guarda en Home Assistant.
• Después de la configuración, la integración usará una clave SSH local y el helper instalado para apagar o reiniciar.
"""


@config_entries.HANDLERS.register(DOMAIN)
class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Infra Power Monitor."""

    VERSION = 1

    def __init__(self) -> None:
        self._name: str = ""
        self._backend: str = ""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_BACKEND): vol.In(["idrac", "redfish", "wake_on_lan", "hybrid"]),
                }
            )
            return self.async_show_form(step_id="user", data_schema=schema)

        self._name = user_input[CONF_NAME]
        self._backend = user_input[CONF_BACKEND]

        if self._backend == "wake_on_lan":
            return await self.async_step_wol()

        if self._backend == "hybrid":
            return await self.async_step_hybrid()

        return await self.async_step_redfish()

    async def async_step_redfish(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            }
        )

        if user_input is None:
            return self.async_show_form(step_id="redfish", data_schema=schema)

        try:
            host = user_input[CONF_HOST]
            await self.async_set_unique_id(f"{self._backend}_{host}")
            self._abort_if_unique_id_configured()
        except Exception as e:
            _LOGGER.error("Config flow error: %s", e)
            errors["base"] = "cannot_connect"
        else:
            data = {
                CONF_NAME: self._name,
                CONF_BACKEND: self._backend,
                **user_input,
            }
            return self.async_create_entry(title=self._name, data=data)

        return self.async_show_form(step_id="redfish", data_schema=schema, errors=errors)

    async def async_step_wol(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        schema = vol.Schema(
            {
                vol.Required("mac"): str,
                vol.Required(CONF_STATUS_HOST): str,
                vol.Optional(CONF_BROADCAST_ADDRESS, default=DEFAULT_WOL_BROADCAST): str,
                vol.Optional(CONF_STATUS_PORT, default=DEFAULT_STATUS_PORT): int,
                vol.Optional(CONF_USE_ICMP, default=DEFAULT_USE_ICMP): bool,
                vol.Optional(CONF_SCAN_INTERVAL, default=30): int,
            }
        )

        if user_input is None:
            return self.async_show_form(step_id="wol", data_schema=schema)

        try:
            mac = user_input["mac"]
            await self.async_set_unique_id(f"wol_{mac}")
            self._abort_if_unique_id_configured()
        except Exception as e:
            _LOGGER.error("WOL config flow error: %s", e)
            errors["base"] = "cannot_connect"
        else:
            data = {
                CONF_NAME: self._name,
                CONF_BACKEND: "wake_on_lan",
                **user_input,
            }
            return self.async_create_entry(title=self._name, data=data)

        return self.async_show_form(step_id="wol", data_schema=schema, errors=errors)

    async def async_step_hybrid(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        schema = vol.Schema(
            {
                vol.Required("mac"): str,
                vol.Required(CONF_STATUS_HOST): str,
                vol.Optional(CONF_BROADCAST_ADDRESS, default=DEFAULT_WOL_BROADCAST): str,
                vol.Optional(CONF_STATUS_PORT, default=22): int,
                vol.Optional(CONF_USE_ICMP, default=True): bool,
                vol.Required(CONF_OS_TYPE, default="linux"): vol.In(["linux", "windows"]),
                vol.Required(CONF_SSH_USER): str,
                vol.Required(CONF_SSH_PASSWORD): str,
                vol.Optional(CONF_SCAN_INTERVAL, default=30): int,
            }
        )

        if user_input is None:
            return self.async_show_form(
                step_id="hybrid",
                data_schema=schema,
                description_placeholders={"description": HYBRID_DESCRIPTION},
            )

        try:
            if user_input[CONF_OS_TYPE] == "linux":
                await self.hass.async_add_executor_job(
                    _bootstrap_linux_hybrid,
                    user_input[CONF_STATUS_HOST],
                    user_input[CONF_SSH_USER],
                    user_input[CONF_SSH_PASSWORD],
                )
            else:
                await self.hass.async_add_executor_job(
                    _bootstrap_windows_key_only,
                    user_input[CONF_STATUS_HOST],
                    user_input[CONF_SSH_USER],
                    user_input[CONF_SSH_PASSWORD],
                )

            mac = user_input["mac"]
            await self.async_set_unique_id(f"hybrid_{mac.lower().replace(':', '').replace('-', '')}")
            self._abort_if_unique_id_configured()

        except Exception:
            _LOGGER.exception("Hybrid bootstrap failed")
            errors["base"] = "cannot_connect"
        else:
            data = {
                CONF_NAME: self._name,
                CONF_BACKEND: "hybrid",
                "mac": user_input["mac"],
                CONF_STATUS_HOST: user_input[CONF_STATUS_HOST],
                CONF_BROADCAST_ADDRESS: user_input.get(CONF_BROADCAST_ADDRESS, DEFAULT_WOL_BROADCAST),
                CONF_STATUS_PORT: user_input.get(CONF_STATUS_PORT, 22),
                CONF_USE_ICMP: user_input.get(CONF_USE_ICMP, True),
                CONF_OS_TYPE: user_input[CONF_OS_TYPE],
                CONF_SSH_USER: user_input[CONF_SSH_USER],
                CONF_SSH_KEY_PATH: DEFAULT_SSH_KEY_PATH,
                CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, 30),
            }
            return self.async_create_entry(title=self._name, data=data)

        return self.async_show_form(
            step_id="hybrid",
            data_schema=schema,
            errors=errors,
            description_placeholders={"description": HYBRID_DESCRIPTION},
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Infra Power Monitor."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENABLE_PANEL,
                        default=self.config_entry.options.get(
                            CONF_ENABLE_PANEL, DEFAULT_ENABLE_PANEL
                        ),
                    ): bool,
                }
            ),
        )


def _ensure_local_ssh_key() -> tuple[str, str]:
    key_path = Path(DEFAULT_SSH_KEY_PATH)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    if not key_path.exists():
        key = paramiko.RSAKey.generate(bits=4096)
        key.write_private_key_file(str(key_path))
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)

    key = paramiko.RSAKey.from_private_key_file(str(key_path))
    public_key = f"{key.get_name()} {key.get_base64()} infra_power_monitor"
    return str(key_path), public_key


def _connect_password(host: str, username: str, password: str) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host,
        username=username,
        password=password,
        timeout=15,
        look_for_keys=False,
        allow_agent=False,
    )
    return client


def _run(client: paramiko.SSHClient, command: str, password: str | None = None) -> tuple[int, str, str]:
    stdin, stdout, stderr = client.exec_command(command, get_pty=password is not None)

    if password is not None:
        stdin.write(password + "\n")
        stdin.flush()

    rc = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="ignore")
    err = stderr.read().decode(errors="ignore")
    return rc, out, err


def _bootstrap_linux_hybrid(host: str, username: str, password: str) -> None:
    _, public_key = _ensure_local_ssh_key()
    client = _connect_password(host, username, password)

    try:
        # Install SSH key for passwordless runtime access.
        escaped_key = public_key.replace("'", "'\"'\"'")
        rc, out, err = _run(
            client,
            "mkdir -p ~/.ssh && chmod 700 ~/.ssh && "
            f"grep -qxF '{escaped_key}' ~/.ssh/authorized_keys 2>/dev/null || "
            f"echo '{escaped_key}' >> ~/.ssh/authorized_keys && "
            "chmod 600 ~/.ssh/authorized_keys"
        )
        if rc != 0:
            raise RuntimeError(err or out or "Failed to install SSH public key")

        helper_script = """#!/bin/sh
set -eu

case "$1" in
  shutdown)
    /sbin/shutdown -h now
    ;;
  reboot)
    /sbin/reboot
    ;;
  status)
    exit 0
    ;;
  *)
    echo "Usage: infra_power.sh {shutdown|reboot|status}" >&2
    exit 2
    ;;
esac
"""
        sudoers = f"{username} ALL=(root) NOPASSWD: {DEFAULT_HELPER_PATH}\n"

        tmp_id = uuid.uuid4().hex
        sftp = client.open_sftp()
        helper_tmp = f"/tmp/infra_power_{tmp_id}.sh"
        sudoers_tmp = f"/tmp/infra_power_sudoers_{tmp_id}"

        with sftp.file(helper_tmp, "w") as handle:
            handle.write(helper_script)
        with sftp.file(sudoers_tmp, "w") as handle:
            handle.write(sudoers)
        sftp.close()

        commands = [
            f"sudo -S -p '' install -o root -g root -m 0755 {helper_tmp} {DEFAULT_HELPER_PATH}",
            f"sudo -S -p '' install -o root -g root -m 0440 {sudoers_tmp} /etc/sudoers.d/infra_power_monitor",
            f"sudo -S -p '' rm -f {helper_tmp} {sudoers_tmp}",
            f"sudo -n {DEFAULT_HELPER_PATH} status",
        ]

        for command in commands:
            rc, out, err = _run(client, command, password if "sudo -S" in command else None)
            if rc != 0:
                raise RuntimeError(err or out or f"Command failed: {command}")

    finally:
        client.close()


def _bootstrap_windows_key_only(host: str, username: str, password: str) -> None:
    # Windows support here only installs key-based SSH access.
    # Shutdown/reboot use native Windows commands, so no sudo helper is needed.
    _, public_key = _ensure_local_ssh_key()
    client = _connect_password(host, username, password)

    try:
        escaped_key = public_key.replace("'", "''")
        command = (
            'powershell -NoProfile -ExecutionPolicy Bypass -Command '
            '"$ssh = Join-Path $env:USERPROFILE \'.ssh\'; '
            'New-Item -ItemType Directory -Force -Path $ssh | Out-Null; '
            '$auth = Join-Path $ssh \'authorized_keys\'; '
            f'$key = \'{escaped_key}\'; '
            'if (!(Test-Path $auth) -or !(Select-String -Path $auth -SimpleMatch $key -Quiet)) '
            '{ Add-Content -Path $auth -Value $key }"'
        )
        rc, out, err = _run(client, command)
        if rc != 0:
            raise RuntimeError(err or out or "Failed to install Windows SSH key")
    finally:
        client.close()