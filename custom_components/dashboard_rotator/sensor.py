"""Sensor platform for Dashboard Rotator."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import DashboardRotatorEntity
from .manager import RotatorManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dashboard Rotator sensors."""
    manager: RotatorManager = hass.data["dashboard_rotator"][entry.entry_id]
    async_add_entities([DashboardRotatorRuntimeSensor(manager)])


class DashboardRotatorRuntimeSensor(DashboardRotatorEntity, SensorEntity):
    """Expose current runtime/profile data to HA and the frontend card."""

    _attr_name = "Runtime"
    _attr_icon = "mdi:view-carousel-outline"

    def __init__(self, manager: RotatorManager) -> None:
        super().__init__(manager)
        self._attr_unique_id = f"{self.entry.entry_id}_runtime"

    @property
    def native_value(self) -> str:
        return self.manager.state

    @property
    def extra_state_attributes(self) -> dict:
        return self.manager.attributes

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
