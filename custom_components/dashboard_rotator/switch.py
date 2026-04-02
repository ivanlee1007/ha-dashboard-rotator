"""Switch platform for Dashboard Rotator."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import DashboardRotatorEntity
from .helpers import build_storage_dict
from .manager import RotatorManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dashboard Rotator switches."""
    manager: RotatorManager = hass.data["dashboard_rotator"][entry.entry_id]
    async_add_entities([DashboardRotatorEnabledSwitch(manager)])


class DashboardRotatorEnabledSwitch(DashboardRotatorEntity, SwitchEntity):
    """Enable/disable the rotator profile."""

    _attr_name = "Enabled"
    _attr_icon = "mdi:play-pause"

    def __init__(self, manager: RotatorManager) -> None:
        super().__init__(manager)
        self._attr_unique_id = f"{self.entry.entry_id}_enabled"

    @property
    def is_on(self) -> bool:
        return self.manager.profile["enabled"]

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        new_profile = {**self.manager.profile, "enabled": enabled}
        self.manager.profile = new_profile
        self.manager.async_write()
        self.hass.config_entries.async_update_entry(
            self.entry,
            options=build_storage_dict(new_profile),
        )
        await self.hass.config_entries.async_reload(self.entry.entry_id)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self.manager.signal,
                self._handle_runtime_update,
            )
        )

    @callback
    def _handle_runtime_update(self) -> None:
        self.async_write_ha_state()
