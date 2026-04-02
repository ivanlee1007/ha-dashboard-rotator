"""Runtime manager for Dashboard Rotator."""
from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    ATTR_CLIENT_STATE,
    ATTR_COMMAND,
    ATTR_ENTITY_ROLE,
    ATTR_INTEGRATION_DOMAIN,
    ATTR_PROFILE,
    ATTR_VERSION,
    CONF_ENABLED,
    DOMAIN,
    SIGNAL_RUNTIME_UPDATE,
    VERSION,
)
from .helpers import get_entry_config, profile_for_frontend


class RotatorManager:
    """Hold current config and runtime command state."""

    def __init__(self, hass, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.profile = get_entry_config(entry)
        self.command_seq = 0
        self.command: dict[str, Any] = {
            "seq": 0,
            "name": "idle",
            "view_path": None,
            "issued_at": None,
        }
        self.client_state: dict[str, Any] = {
            "client_id": None,
            "status": "idle",
            "current_view": None,
            "next_view": None,
            "remaining_seconds": None,
            "page_visible": None,
            "updated_at": None,
        }

    @property
    def signal(self) -> str:
        return SIGNAL_RUNTIME_UPDATE.format(self.entry.entry_id)

    def async_write(self) -> None:
        """Notify entities that runtime state changed."""
        async_dispatcher_send(self.hass, self.signal)

    def update_entry(self, entry: ConfigEntry) -> None:
        """Refresh manager after config/options changes."""
        self.entry = entry
        self.profile = get_entry_config(entry)
        self.async_write()

    async def async_issue_command(self, name: str, view_path: str | None = None) -> None:
        """Create a new frontend command."""
        self.command_seq += 1
        self.command = {
            "seq": self.command_seq,
            "name": name,
            "view_path": view_path,
            "issued_at": datetime.now(UTC).isoformat(),
        }
        self.async_write()

    async def async_set_client_state(self, state: dict[str, Any]) -> None:
        """Store the latest client-reported runtime state."""
        self.client_state = {
            **self.client_state,
            **state,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self.async_write()

    @property
    def state(self) -> str:
        """Expose a coarse runtime state for the main sensor."""
        if not self.profile[CONF_ENABLED]:
            return "disabled"
        return self.client_state.get("status") or "idle"

    @property
    def attributes(self) -> dict[str, Any]:
        """Attributes for the runtime sensor."""
        return {
            ATTR_INTEGRATION_DOMAIN: DOMAIN,
            ATTR_ENTITY_ROLE: "runtime",
            ATTR_VERSION: VERSION,
            "entry_id": self.entry.entry_id,
            "enabled": self.profile[CONF_ENABLED],
            ATTR_PROFILE: profile_for_frontend(self.profile),
            ATTR_COMMAND: deepcopy(self.command),
            ATTR_CLIENT_STATE: deepcopy(self.client_state),
        }
