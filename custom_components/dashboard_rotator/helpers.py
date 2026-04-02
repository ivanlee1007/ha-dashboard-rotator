"""Helpers for Dashboard Rotator."""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_DASHBOARD_PATH,
    CONF_DEFAULT_INTERVAL,
    CONF_ENABLED,
    CONF_NAME,
    CONF_ONLY_WHEN_VISIBLE,
    CONF_PATH,
    CONF_PAUSE_ON_INTERACTION,
    CONF_SECONDS,
    CONF_START_DELAY,
    CONF_TARGET_CLIENT_ID,
    CONF_TITLE,
    CONF_VIEWS,
    CONF_VIEWS_JSON,
    DEFAULT_DASHBOARD_PATH,
    DEFAULT_ENABLED,
    DEFAULT_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_ONLY_WHEN_VISIBLE,
    DEFAULT_PAUSE_ON_INTERACTION,
    DEFAULT_START_DELAY,
    DEFAULT_TARGET_CLIENT_ID,
    DEFAULT_VIEWS_JSON,
)


class InvalidViewsConfig(ValueError):
    """Raised when the views JSON is invalid."""


def normalize_path(path: str) -> str:
    """Normalize a Lovelace path."""
    stripped = (path or "").split("?", 1)[0].split("#", 1)[0].strip()
    if not stripped:
        return ""
    if not stripped.startswith("/"):
        stripped = f"/{stripped}"
    stripped = stripped.rstrip("/")
    return stripped or "/"


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def format_views_json(views: list[dict[str, Any]]) -> str:
    """Format the views list as pretty JSON."""
    return json.dumps(views, indent=2, ensure_ascii=False)


def parse_views_json(raw: str, dashboard_path: str, default_interval: int) -> list[dict[str, Any]]:
    """Parse and validate the views JSON."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as err:
        raise InvalidViewsConfig(f"Invalid JSON: {err.msg}") from err

    if not isinstance(parsed, list):
        raise InvalidViewsConfig("Views JSON must be a list of objects")

    views: list[dict[str, Any]] = []
    for idx, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            raise InvalidViewsConfig(f"View #{idx} must be an object")

        path = normalize_path(str(item.get(CONF_PATH, "")))
        if not path:
            raise InvalidViewsConfig(f"View #{idx} is missing a path")

        if not path.startswith(dashboard_path):
            raise InvalidViewsConfig(
                f"View #{idx} path '{path}' must start with dashboard path '{dashboard_path}'"
            )

        seconds = _coerce_int(item.get(CONF_SECONDS), default_interval)
        if seconds <= 0:
            raise InvalidViewsConfig(f"View #{idx} seconds must be > 0")

        title = str(item.get(CONF_TITLE) or "").strip()
        enabled = _coerce_bool(item.get(CONF_ENABLED, True), True)

        views.append(
            {
                CONF_PATH: path,
                CONF_SECONDS: seconds,
                CONF_TITLE: title,
                CONF_ENABLED: enabled,
            }
        )

    if not any(view[CONF_ENABLED] for view in views):
        raise InvalidViewsConfig("At least one view must be enabled")

    return views


def normalize_config(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize stored config into a predictable shape."""
    dashboard_path = normalize_path(
        str(data.get(CONF_DASHBOARD_PATH, DEFAULT_DASHBOARD_PATH))
    ) or DEFAULT_DASHBOARD_PATH
    default_interval = max(
        1, _coerce_int(data.get(CONF_DEFAULT_INTERVAL), DEFAULT_INTERVAL)
    )
    pause_on_interaction = max(
        0,
        _coerce_int(data.get(CONF_PAUSE_ON_INTERACTION), DEFAULT_PAUSE_ON_INTERACTION),
    )
    start_delay = max(0, _coerce_int(data.get(CONF_START_DELAY), DEFAULT_START_DELAY))
    views_json = str(data.get(CONF_VIEWS_JSON, DEFAULT_VIEWS_JSON)).strip() or DEFAULT_VIEWS_JSON
    views = parse_views_json(views_json, dashboard_path, default_interval)
    target_client_id = str(
        data.get(CONF_TARGET_CLIENT_ID, DEFAULT_TARGET_CLIENT_ID) or ""
    ).strip()

    return {
        CONF_NAME: str(data.get(CONF_NAME, DEFAULT_NAME)).strip() or DEFAULT_NAME,
        CONF_ENABLED: _coerce_bool(data.get(CONF_ENABLED), DEFAULT_ENABLED),
        CONF_DASHBOARD_PATH: dashboard_path,
        CONF_DEFAULT_INTERVAL: default_interval,
        CONF_PAUSE_ON_INTERACTION: pause_on_interaction,
        CONF_ONLY_WHEN_VISIBLE: _coerce_bool(
            data.get(CONF_ONLY_WHEN_VISIBLE), DEFAULT_ONLY_WHEN_VISIBLE
        ),
        CONF_START_DELAY: start_delay,
        CONF_TARGET_CLIENT_ID: target_client_id,
        CONF_VIEWS_JSON: format_views_json(views),
        CONF_VIEWS: views,
    }


def get_entry_config(entry: ConfigEntry) -> dict[str, Any]:
    """Return merged and normalized config entry data."""
    merged = {**entry.data, **entry.options}
    return normalize_config(merged)


def build_storage_dict(config: dict[str, Any]) -> dict[str, Any]:
    """Build a storage-safe dictionary for data/options."""
    return {
        CONF_NAME: config[CONF_NAME],
        CONF_ENABLED: config[CONF_ENABLED],
        CONF_DASHBOARD_PATH: config[CONF_DASHBOARD_PATH],
        CONF_DEFAULT_INTERVAL: config[CONF_DEFAULT_INTERVAL],
        CONF_PAUSE_ON_INTERACTION: config[CONF_PAUSE_ON_INTERACTION],
        CONF_ONLY_WHEN_VISIBLE: config[CONF_ONLY_WHEN_VISIBLE],
        CONF_START_DELAY: config[CONF_START_DELAY],
        CONF_TARGET_CLIENT_ID: config[CONF_TARGET_CLIENT_ID],
        CONF_VIEWS_JSON: config[CONF_VIEWS_JSON],
    }


def profile_for_frontend(config: dict[str, Any]) -> dict[str, Any]:
    """Build the frontend profile payload."""
    payload = deepcopy(config)
    payload.pop(CONF_VIEWS_JSON, None)
    return payload
