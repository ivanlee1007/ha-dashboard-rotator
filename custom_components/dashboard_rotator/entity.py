"""Shared entity helpers for Dashboard Rotator."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, NAME
from .manager import RotatorManager


class DashboardRotatorEntity(Entity):
    """Base entity for Dashboard Rotator."""

    _attr_has_entity_name = True

    def __init__(self, manager: RotatorManager) -> None:
        self.manager = manager
        self.entry = manager.entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=self.manager.profile["name"],
            manufacturer="UNiNUS",
            model=NAME,
        )
