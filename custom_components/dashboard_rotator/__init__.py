"""Dashboard Rotator integration."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_PATH,
    DOMAIN,
    FRONTEND_FILE,
    FRONTEND_URL,
    PLATFORMS,
    VERSION,
    SERVICE_CLIENT_STATE,
    SERVICE_JUMP_TO_VIEW,
    SERVICE_NEXT_VIEW,
    SERVICE_PAUSE,
    SERVICE_PREVIOUS_VIEW,
    SERVICE_RESUME,
)
from .helpers import normalize_path
from .manager import RotatorManager

_LOGGER = logging.getLogger(__name__)

SERVICE_BASE_SCHEMA = vol.Schema({})
SERVICE_JUMP_SCHEMA = vol.Schema({vol.Required(CONF_PATH): cv.string})
SERVICE_CLIENT_STATE_SCHEMA = vol.Schema(
    {
        vol.Optional("client_id"): cv.string,
        vol.Optional("status"): cv.string,
        vol.Optional("current_view"): vol.Any(None, cv.string),
        vol.Optional("next_view"): vol.Any(None, cv.string),
        vol.Optional("remaining_seconds"): vol.Any(None, vol.Coerce(int)),
        vol.Optional("page_visible"): vol.Any(None, bool),
    }
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up Dashboard Rotator from YAML (unused)."""
    hass.data.setdefault(DOMAIN, {})

    controller_src = Path(__file__).parent / "www" / FRONTEND_FILE
    await hass.http.async_register_static_paths(
        [StaticPathConfig(FRONTEND_URL, str(controller_src), cache_headers=False)]
    )
    frontend.add_extra_js_url(hass, f"{FRONTEND_URL}?v={VERSION}")

    async def _handle_pause(call: ServiceCall) -> None:
        manager = _get_manager(hass)
        if manager:
            await manager.async_issue_command(SERVICE_PAUSE)

    async def _handle_resume(call: ServiceCall) -> None:
        manager = _get_manager(hass)
        if manager:
            await manager.async_issue_command(SERVICE_RESUME)

    async def _handle_next(call: ServiceCall) -> None:
        manager = _get_manager(hass)
        if manager:
            await manager.async_issue_command(SERVICE_NEXT_VIEW)

    async def _handle_previous(call: ServiceCall) -> None:
        manager = _get_manager(hass)
        if manager:
            await manager.async_issue_command(SERVICE_PREVIOUS_VIEW)

    async def _handle_jump(call: ServiceCall) -> None:
        manager = _get_manager(hass)
        if manager:
            await manager.async_issue_command(
                SERVICE_JUMP_TO_VIEW, normalize_path(call.data[CONF_PATH])
            )

    async def _handle_client_state(call: ServiceCall) -> None:
        manager = _get_manager(hass)
        if manager:
            await manager.async_set_client_state(dict(call.data))

    if not hass.services.has_service(DOMAIN, SERVICE_PAUSE):
        hass.services.async_register(DOMAIN, SERVICE_PAUSE, _handle_pause, schema=SERVICE_BASE_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_RESUME, _handle_resume, schema=SERVICE_BASE_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_NEXT_VIEW, _handle_next, schema=SERVICE_BASE_SCHEMA)
        hass.services.async_register(
            DOMAIN, SERVICE_PREVIOUS_VIEW, _handle_previous, schema=SERVICE_BASE_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, SERVICE_JUMP_TO_VIEW, _handle_jump, schema=SERVICE_JUMP_SCHEMA
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_CLIENT_STATE,
            _handle_client_state,
            schema=SERVICE_CLIENT_STATE_SCHEMA,
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dashboard Rotator from a config entry."""
    manager = RotatorManager(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = manager
    hass.data[DOMAIN]["manager"] = manager

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if hass.data[DOMAIN].get("manager") and hass.data[DOMAIN]["manager"].entry.entry_id == entry.entry_id:
            hass.data[DOMAIN]["manager"] = None
    return unload_ok


def _get_manager(hass: HomeAssistant) -> RotatorManager | None:
    """Return the single active manager for MVP mode."""
    return hass.data.get(DOMAIN, {}).get("manager")
