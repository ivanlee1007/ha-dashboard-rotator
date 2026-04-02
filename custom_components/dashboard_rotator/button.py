"""Button platform for Dashboard Rotator."""
from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    SERVICE_NEXT_VIEW,
    SERVICE_PAUSE,
    SERVICE_PREVIOUS_VIEW,
    SERVICE_RESUME,
)
from .entity import DashboardRotatorEntity
from .manager import RotatorManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dashboard Rotator buttons."""
    manager: RotatorManager = hass.data["dashboard_rotator"][entry.entry_id]
    async_add_entities(
        [
            DashboardRotatorCommandButton(manager, "Pause", "mdi:pause", SERVICE_PAUSE),
            DashboardRotatorCommandButton(manager, "Resume", "mdi:play", SERVICE_RESUME),
            DashboardRotatorCommandButton(
                manager, "Next View", "mdi:skip-next", SERVICE_NEXT_VIEW
            ),
            DashboardRotatorCommandButton(
                manager, "Previous View", "mdi:skip-previous", SERVICE_PREVIOUS_VIEW
            ),
        ]
    )


class DashboardRotatorCommandButton(DashboardRotatorEntity, ButtonEntity):
    """Stateless command button."""

    def __init__(
        self,
        manager: RotatorManager,
        name: str,
        icon: str,
        command: str,
    ) -> None:
        super().__init__(manager)
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{self.entry.entry_id}_{command}"
        self._command = command

    async def async_press(self) -> None:
        await self.manager.async_issue_command(self._command)
