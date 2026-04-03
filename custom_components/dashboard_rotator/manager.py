"""Runtime manager for Dashboard Rotator."""
from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    ATTR_ACTIVE_CLIENT_ALIAS,
    ATTR_ACTIVE_CLIENT_COUNT,
    ATTR_ACTIVE_CLIENT_ID,
    ATTR_CLIENT_STATE,
    ATTR_CLIENT_STATES,
    ATTR_COMMAND,
    ATTR_ENTITY_ROLE,
    ATTR_INTEGRATION_DOMAIN,
    ATTR_PROFILE,
    ATTR_TARGET_CLIENT_ID,
    ATTR_TARGET_CLIENT_IDS,
    ATTR_VERSION,
    CLIENT_STALE_SECONDS,
    CONF_CLIENT_ALIASES,
    CONF_CLIENT_ALIASES_JSON,
    CONF_ENABLED,
    CONF_TARGET_CLIENT_ID,
    CONF_TARGET_CLIENT_IDS,
    CONF_TARGET_CLIENT_IDS_JSON,
    DOMAIN,
    SIGNAL_RUNTIME_UPDATE,
    VERSION,
)
from .helpers import get_entry_config, profile_for_frontend
from .helpers import build_storage_dict, format_aliases_json, format_target_client_ids_json


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
            "target_client_id": None,
            "issued_at": None,
        }
        self.client_state: dict[str, Any] = {
            "client_id": None,
            "status": "idle",
            "current_view": None,
            "next_view": None,
            "remaining_seconds": None,
            "page_visible": None,
            "on_managed_dashboard": None,
            "page_title": None,
            "updated_at": None,
        }
        self.client_states: dict[str, dict[str, Any]] = {}
        self.active_client_id: str | None = None

    @property
    def signal(self) -> str:
        return SIGNAL_RUNTIME_UPDATE.format(self.entry.entry_id)

    def async_write(self) -> None:
        """Notify entities that runtime state changed."""
        async_dispatcher_send(self.hass, self.signal)

    def get_client_alias(self, client_id: str | None) -> str | None:
        """Return the configured alias for a client."""
        if not client_id:
            return None
        return self.profile.get(CONF_CLIENT_ALIASES, {}).get(client_id) or None

    def decorate_client_state(self, state: dict[str, Any]) -> dict[str, Any]:
        """Return a client state enriched with alias metadata."""
        client_id = state.get("client_id")
        alias = self.get_client_alias(client_id)
        return {
            **deepcopy(state),
            "client_alias": alias,
            "display_name": alias or state.get("page_title") or client_id,
        }

    def update_entry(self, entry: ConfigEntry) -> None:
        """Refresh manager after config/options changes."""
        self.entry = entry
        self.profile = get_entry_config(entry)
        self._refresh_active_state()
        self.async_write()

    async def async_issue_command(
        self,
        name: str,
        view_path: str | None = None,
        target_client_id: str | None = None,
    ) -> None:
        """Create a new frontend command."""
        self.command_seq += 1
        self.command = {
            "seq": self.command_seq,
            "name": name,
            "view_path": view_path,
            "target_client_id": (target_client_id or "").strip() or None,
            "issued_at": datetime.now(UTC).isoformat(),
        }
        self.async_write()

    async def async_set_client_state(self, state: dict[str, Any]) -> None:
        """Store the latest client-reported runtime state."""
        now = datetime.now(UTC)
        client_id = state.get("client_id") or "unknown"
        merged = {
            **self.client_states.get(client_id, self.client_state),
            **state,
            "client_id": client_id,
            "updated_at": now.isoformat(),
        }
        self.client_states[client_id] = merged
        self._prune_stale_clients(now)
        self._refresh_active_state(fallback_state=merged)
        self.async_write()

    def _refresh_active_state(self, fallback_state: dict[str, Any] | None = None) -> None:
        """Refresh active client pointers after state/config changes."""
        self.active_client_id = self._select_active_client_id()
        target_client_ids = [
            str(client_id or "").strip()
            for client_id in self.profile.get(CONF_TARGET_CLIENT_IDS, [])
            if str(client_id or "").strip()
        ]
        if target_client_ids and not any(client_id in self.client_states for client_id in target_client_ids):
            target_client_id = target_client_ids[0]
            self.client_state = self.decorate_client_state({
                "client_id": target_client_id,
                "status": "target_unavailable",
                "current_view": None,
                "next_view": None,
                "remaining_seconds": None,
                "page_visible": None,
                "on_managed_dashboard": None,
                "page_title": None,
                "updated_at": None,
            })
            return

        if self.active_client_id and self.active_client_id in self.client_states:
            self.client_state = self.decorate_client_state(
                self.client_states[self.active_client_id]
            )
            return

        if fallback_state is not None:
            self.client_state = self.decorate_client_state(fallback_state)
            return

        self.client_state = self.decorate_client_state({
            "client_id": None,
            "status": "idle",
            "current_view": None,
            "next_view": None,
            "remaining_seconds": None,
            "page_visible": None,
            "on_managed_dashboard": None,
            "page_title": None,
            "updated_at": None,
        })

    async def async_set_client_alias(self, client_id: str, alias: str | None) -> None:
        """Persist a friendly alias for a client."""
        aliases = {
            **self.profile.get(CONF_CLIENT_ALIASES, {}),
        }
        value = (alias or "").strip()
        if value:
            aliases[client_id] = value
        else:
            aliases.pop(client_id, None)

        self.profile = {
            **self.profile,
            CONF_CLIENT_ALIASES: aliases,
            CONF_CLIENT_ALIASES_JSON: format_aliases_json(aliases),
        }
        self.hass.config_entries.async_update_entry(
            self.entry,
            options=build_storage_dict(self.profile),
        )
        self._refresh_active_state()
        self.async_write()

    async def async_set_target_client(self, client_id: str | None, append: bool = False) -> None:
        """Persist the target client selection."""
        value = (client_id or "").strip()
        current = [
            str(item or "").strip()
            for item in self.profile.get(CONF_TARGET_CLIENT_IDS, [])
            if str(item or "").strip()
        ]
        if not value:
            target_client_ids: list[str] = []
        elif append:
            target_client_ids = current if value in current else [*current, value]
        else:
            target_client_ids = [value]

        self.profile = {
            **self.profile,
            CONF_TARGET_CLIENT_ID: target_client_ids[0] if len(target_client_ids) == 1 else "",
            CONF_TARGET_CLIENT_IDS: target_client_ids,
            CONF_TARGET_CLIENT_IDS_JSON: format_target_client_ids_json(target_client_ids),
        }
        self.hass.config_entries.async_update_entry(
            self.entry,
            options=build_storage_dict(self.profile),
        )
        self._refresh_active_state()
        self.async_write()

    def _prune_stale_clients(self, now: datetime) -> None:
        """Drop stale client heartbeats."""
        cutoff = now - timedelta(seconds=CLIENT_STALE_SECONDS)
        stale: list[str] = []
        for client_id, state in self.client_states.items():
            updated_at = state.get("updated_at")
            try:
                seen = datetime.fromisoformat(updated_at)
            except (TypeError, ValueError):
                stale.append(client_id)
                continue
            if seen < cutoff:
                stale.append(client_id)
        for client_id in stale:
            self.client_states.pop(client_id, None)

    def _select_active_client_id(self) -> str | None:
        """Choose the client that best represents the active runtime."""
        status_weight = {
            "running": 60,
            "navigating": 55,
            "interaction_pause": 50,
            "manual_pause": 45,
            "waiting_start": 40,
            "not_targeted": 25,
            "hidden": 20,
            "target_unavailable": 15,
            "idle": 10,
            "disabled": 0,
        }

        target_client_ids = [
            str(client_id or "").strip()
            for client_id in self.profile.get(CONF_TARGET_CLIENT_IDS, [])
            if str(client_id or "").strip()
        ]

        if not self.client_states:
            return target_client_ids[0] if target_client_ids else None

        candidates = list(self.client_states.items())
        if target_client_ids:
            targeted = [item for item in candidates if item[0] in target_client_ids]
            if targeted:
                candidates = targeted
            else:
                return target_client_ids[0]

        ranked = sorted(
            candidates,
            key=lambda item: (
                status_weight.get(str(item[1].get("status") or "idle"), 5)
                + (20 if item[1].get("on_managed_dashboard") else 0)
                + (10 if item[1].get("page_visible") else 0),
                item[1].get("updated_at") or "",
                item[0],
            ),
            reverse=True,
        )
        return ranked[0][0]

    @property
    def state(self) -> str:
        """Expose a coarse runtime state for the main sensor."""
        if not self.profile[CONF_ENABLED]:
            return "disabled"
        target_client_ids = [
            str(client_id or "").strip()
            for client_id in self.profile.get(CONF_TARGET_CLIENT_IDS, [])
            if str(client_id or "").strip()
        ]
        if target_client_ids and not any(client_id in self.client_states for client_id in target_client_ids):
            return "target_unavailable"
        if not self.client_states:
            return "idle"
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
            ATTR_ACTIVE_CLIENT_ID: self.active_client_id,
            ATTR_ACTIVE_CLIENT_ALIAS: self.get_client_alias(self.active_client_id),
            ATTR_ACTIVE_CLIENT_COUNT: len(self.client_states),
            ATTR_TARGET_CLIENT_ID: self.profile.get(CONF_TARGET_CLIENT_ID) or None,
            ATTR_TARGET_CLIENT_IDS: list(self.profile.get(CONF_TARGET_CLIENT_IDS, [])),
            ATTR_CLIENT_STATE: deepcopy(self.client_state),
            ATTR_CLIENT_STATES: {
                client_id: self.decorate_client_state(state)
                for client_id, state in self.client_states.items()
            },
        }
