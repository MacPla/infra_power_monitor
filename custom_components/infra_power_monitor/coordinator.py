from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import PowerState, UPDATE_INTERVAL_FALLBACK
from .providers.base import CannotConnect, InvalidAuth, InvalidRedfish

_LOGGER = logging.getLogger(__name__)


class InfraPowerCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, provider, scan_interval: int) -> None:
        self.provider = provider
        self._transient_state: PowerState | None = None
        self._transient_until: float = 0.0

        super().__init__(
            hass,
            _LOGGER,
            name=f"infra_power_monitor_{provider.get_unique_id()}",
            update_interval=timedelta(seconds=scan_interval) if scan_interval else UPDATE_INTERVAL_FALLBACK,
        )

    @property
    def effective_power_state(self) -> PowerState:
        if self._transient_state and asyncio.get_running_loop().time() < self._transient_until:
            return self._transient_state
        if self.data is None:
            return PowerState.UNAVAILABLE
        return self.data.power_state

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.provider.get_device_snapshot)
        except (CannotConnect, InvalidAuth, InvalidRedfish) as exc:
            raise UpdateFailed(str(exc)) from exc
        except Exception as exc:
            raise UpdateFailed(f"Unexpected provider error: {exc}") from exc

    def _set_transient(self, state: PowerState, seconds: int = 15) -> None:
        self._transient_state = state
        self._transient_until = asyncio.get_running_loop().time() + seconds

    def _clear_transient(self) -> None:
        self._transient_state = None
        self._transient_until = 0.0

    async def async_power_on(self) -> None:
        self._set_transient(PowerState.STARTING)
        await self.hass.async_add_executor_job(self.provider.power_on)
        await asyncio.sleep(2)
        await self.async_request_refresh()
        self._clear_transient()

    async def async_power_off(self) -> None:
        self._set_transient(PowerState.STOPPING)
        await self.hass.async_add_executor_job(self.provider.power_off)
        await asyncio.sleep(2)
        await self.async_request_refresh()
        self._clear_transient()

    async def async_restart(self) -> None:
        self._set_transient(PowerState.RESTARTING)
        await self.hass.async_add_executor_job(self.provider.restart)
        await asyncio.sleep(2)
        await self.async_request_refresh()
        self._clear_transient()

    async def async_refresh_now(self) -> None:
        await self.async_request_refresh()