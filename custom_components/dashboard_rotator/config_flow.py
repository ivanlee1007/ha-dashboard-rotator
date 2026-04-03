"""Config flow for Dashboard Rotator."""
from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CLIENT_STALE_SECONDS,
    CONF_CLIENT_ALIASES,
    CONF_CLIENT_ALIASES_JSON,
    CONF_DASHBOARD_PATH,
    CONF_DEFAULT_INTERVAL,
    CONF_ENABLED,
    CONF_NAME,
    CONF_ONLY_WHEN_VISIBLE,
    CONF_PAUSE_ON_INTERACTION,
    CONF_START_DELAY,
    CONF_TARGET_CLIENT_ID,
    CONF_TARGET_CLIENT_IDS,
    CONF_TARGET_CLIENT_IDS_JSON,
    CONF_VIEWS,
    CONF_VIEWS_JSON,
    DEFAULT_CLIENT_ALIASES_JSON,
    DEFAULT_DASHBOARD_PATH,
    DEFAULT_ENABLED,
    DEFAULT_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_ONLY_WHEN_VISIBLE,
    DEFAULT_PAUSE_ON_INTERACTION,
    DEFAULT_START_DELAY,
    DEFAULT_TARGET_CLIENT_ID,
    DEFAULT_VIEWS_JSON,
    DOMAIN,
    NAME,
)
from .helpers import (
    format_views_json,
    format_target_client_ids_json,
    InvalidAliasesConfig,
    InvalidViewsConfig,
    build_storage_dict,
    format_aliases_json,
    normalize_config,
    normalize_path,
)

FIELD_SELECTED_VIEW = "selected_view"
FIELD_SELECTED_CLIENT = "selected_client"
FIELD_ALIAS = "alias"
FIELD_POSITION = "position"


def _parse_updated_at(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _age_seconds(state: dict[str, Any] | None) -> int | None:
    if not state:
        return None
    seen = _parse_updated_at(state.get("updated_at"))
    if not seen:
        return None
    return max(0, int((datetime.now(UTC) - seen).total_seconds()))


def _format_age_label(seconds: int | None) -> str:
    if seconds is None:
        return "never"
    if seconds < 60:
        return f"{seconds}s ago"
    minutes, rem = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {rem}s ago"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m ago"


def _presence_label(state: dict[str, Any] | None) -> str:
    if not state:
        return "offline"
    age = _age_seconds(state)
    if age is None:
        return "unknown"
    if age > CLIENT_STALE_SECONDS:
        return "stale"
    if not state.get("on_managed_dashboard"):
        return "other-page"
    if not state.get("page_visible") or state.get("status") == "hidden":
        return "dashboard-hidden"
    if state.get("status") in {"running", "navigating", "interaction_pause", "manual_pause", "waiting_start"}:
        return "dashboard-active"
    return "dashboard-idle"


def _view_option_label(index: int, view: dict[str, Any]) -> str:
    title = str(view.get("title") or "").strip() or view["path"]
    enabled = "enabled" if view.get("enabled", True) else "disabled"
    return f"{index + 1}. {title} — {view['path']} — {view['seconds']}s — {enabled}"


def _views_summary(views: list[dict[str, Any]]) -> str:
    if not views:
        return "- (none)"
    return "\n".join(
        f"- {index + 1}. {str(view.get('title') or '').strip() or view['path']}"
        f" | {view['path']} | {view['seconds']}s"
        f" | {'on' if view.get('enabled', True) else 'off'}"
        for index, view in enumerate(views)
    )


def _client_option_label(
    client_id: str,
    alias: str | None = None,
    state: dict[str, Any] | None = None,
) -> str:
    bits: list[str] = []
    if alias:
        bits.append(alias)
    bits.append(client_id)
    if state:
        status = state.get("status")
        if status:
            bits.append(str(status))
        bits.append(_presence_label(state))
    return " — ".join(bits)


def _clients_summary(
    aliases: dict[str, str],
    states: dict[str, dict[str, Any]] | None = None,
    target_client_ids: list[str] | None = None,
) -> str:
    states = states or {}
    target_set = {str(client_id or "").strip() for client_id in (target_client_ids or []) if str(client_id or "").strip()}
    known_client_ids = sorted(set(states) | set(aliases) | target_set)
    if not known_client_ids:
        return "- (none)"

    lines: list[str] = []
    for client_id in known_client_ids:
        alias = aliases.get(client_id) or ""
        state = states.get(client_id) or {}
        status = state.get("status") or "offline"
        presence = _presence_label(state)
        last_seen = _format_age_label(_age_seconds(state))
        marker = " 🎯" if client_id in target_set else ""
        label = alias or state.get("page_title") or client_id
        lines.append(f"- {label} | {client_id} | {status} | {presence} | {last_seen}{marker}")
    return "\n".join(lines)


def _stringify(value: Any, fallback: str = "-") -> str:
    if value is None:
        return fallback
    if isinstance(value, bool):
        return "yes" if value else "no"
    text = str(value).strip()
    return text or fallback


def _client_details_placeholders(
    client_id: str,
    alias: str | None,
    state: dict[str, Any] | None,
    target_client_ids: list[str] | None,
) -> dict[str, str]:
    state = state or {}
    target_set = {str(item or "").strip() for item in (target_client_ids or []) if str(item or "").strip()}
    return {
        "client_label": _client_option_label(client_id, alias, state),
        "status": _stringify(state.get("status"), "offline"),
        "presence": _presence_label(state),
        "last_seen": _format_age_label(_age_seconds(state)),
        "page_title": _stringify(state.get("page_title")),
        "current_view": _stringify(state.get("current_view")),
        "next_view": _stringify(state.get("next_view")),
        "page_visible": _stringify(state.get("page_visible")),
        "on_managed_dashboard": _stringify(state.get("on_managed_dashboard")),
        "updated_at": _stringify(state.get("updated_at"), "never"),
        "is_target": "yes" if client_id in target_set else "no",
    }


def _build_target_selector(
    client_options: list[SelectOptionDict] | None,
) -> SelectSelector | TextSelector:
    if client_options:
        return SelectSelector(
            SelectSelectorConfig(
                options=client_options,
                mode=SelectSelectorMode.DROPDOWN,
                sort=False,
            )
        )
    return TextSelector()


def _build_schema(
    defaults: dict[str, Any],
    client_options: list[SelectOptionDict] | None = None,
) -> vol.Schema:
    target_selector = _build_target_selector(client_options)
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): TextSelector(),
            vol.Required(
                CONF_DASHBOARD_PATH,
                default=defaults.get(CONF_DASHBOARD_PATH, DEFAULT_DASHBOARD_PATH),
            ): TextSelector(),
            vol.Required(
                CONF_ENABLED,
                default=defaults.get(CONF_ENABLED, DEFAULT_ENABLED),
            ): BooleanSelector(),
            vol.Required(
                CONF_DEFAULT_INTERVAL,
                default=defaults.get(CONF_DEFAULT_INTERVAL, DEFAULT_INTERVAL),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=3600,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Required(
                CONF_PAUSE_ON_INTERACTION,
                default=defaults.get(
                    CONF_PAUSE_ON_INTERACTION, DEFAULT_PAUSE_ON_INTERACTION
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=3600,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Required(
                CONF_ONLY_WHEN_VISIBLE,
                default=defaults.get(CONF_ONLY_WHEN_VISIBLE, DEFAULT_ONLY_WHEN_VISIBLE),
            ): BooleanSelector(),
            vol.Required(
                CONF_START_DELAY,
                default=defaults.get(CONF_START_DELAY, DEFAULT_START_DELAY),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=120,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Optional(
                CONF_TARGET_CLIENT_ID,
                default=defaults.get(CONF_TARGET_CLIENT_ID, DEFAULT_TARGET_CLIENT_ID),
            ): target_selector,
            vol.Required(
                CONF_CLIENT_ALIASES_JSON,
                default=defaults.get(
                    CONF_CLIENT_ALIASES_JSON, DEFAULT_CLIENT_ALIASES_JSON
                ),
            ): TextSelector(TextSelectorConfig(multiline=True)),
            vol.Required(
                CONF_VIEWS_JSON,
                default=defaults.get(CONF_VIEWS_JSON, DEFAULT_VIEWS_JSON),
            ): TextSelector(TextSelectorConfig(multiline=True)),
        }
    )


def _build_general_schema(
    defaults: dict[str, Any],
    client_options: list[SelectOptionDict] | None = None,
) -> vol.Schema:
    target_selector = _build_target_selector(client_options)
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): TextSelector(),
            vol.Required(
                CONF_DASHBOARD_PATH,
                default=defaults.get(CONF_DASHBOARD_PATH, DEFAULT_DASHBOARD_PATH),
            ): TextSelector(),
            vol.Required(
                CONF_ENABLED,
                default=defaults.get(CONF_ENABLED, DEFAULT_ENABLED),
            ): BooleanSelector(),
            vol.Required(
                CONF_DEFAULT_INTERVAL,
                default=defaults.get(CONF_DEFAULT_INTERVAL, DEFAULT_INTERVAL),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=3600,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Required(
                CONF_PAUSE_ON_INTERACTION,
                default=defaults.get(
                    CONF_PAUSE_ON_INTERACTION, DEFAULT_PAUSE_ON_INTERACTION
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=3600,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Required(
                CONF_ONLY_WHEN_VISIBLE,
                default=defaults.get(CONF_ONLY_WHEN_VISIBLE, DEFAULT_ONLY_WHEN_VISIBLE),
            ): BooleanSelector(),
            vol.Required(
                CONF_START_DELAY,
                default=defaults.get(CONF_START_DELAY, DEFAULT_START_DELAY),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=120,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Optional(
                CONF_TARGET_CLIENT_ID,
                default=defaults.get(CONF_TARGET_CLIENT_ID, DEFAULT_TARGET_CLIENT_ID),
            ): target_selector,
        }
    )


def _build_advanced_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_CLIENT_ALIASES_JSON,
                default=defaults.get(
                    CONF_CLIENT_ALIASES_JSON, DEFAULT_CLIENT_ALIASES_JSON
                ),
            ): TextSelector(TextSelectorConfig(multiline=True)),
            vol.Required(
                CONF_VIEWS_JSON,
                default=defaults.get(CONF_VIEWS_JSON, DEFAULT_VIEWS_JSON),
            ): TextSelector(TextSelectorConfig(multiline=True)),
        }
    )


def _build_view_select_schema(options: list[SelectOptionDict]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(FIELD_SELECTED_VIEW): SelectSelector(
                SelectSelectorConfig(
                    options=options,
                    mode=SelectSelectorMode.DROPDOWN,
                    sort=False,
                )
            )
        }
    )


def _build_client_select_schema(
    options: list[SelectOptionDict],
    field_name: str = FIELD_SELECTED_CLIENT,
    default: str | None = None,
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(field_name, default=default if default is not None else options[0]["value"]): SelectSelector(
                SelectSelectorConfig(
                    options=options,
                    mode=SelectSelectorMode.DROPDOWN,
                    sort=False,
                )
            )
        }
    )


def _build_client_alias_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(FIELD_ALIAS, default=defaults.get(FIELD_ALIAS, "")): TextSelector(),
        }
    )


def _build_view_edit_schema(defaults: dict[str, Any], max_position: int) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("path", default=defaults.get("path", "")): TextSelector(),
            vol.Required("title", default=defaults.get("title", "")): TextSelector(),
            vol.Required("seconds", default=defaults.get("seconds", DEFAULT_INTERVAL)): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=3600,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Required("enabled", default=defaults.get("enabled", True)): BooleanSelector(),
            vol.Required(FIELD_POSITION, default=defaults.get(FIELD_POSITION, max_position)): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=max_position,
                    mode=NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _build_target_payload(target_client_ids: list[str]) -> dict[str, Any]:
    clean = [str(client_id or "").strip() for client_id in target_client_ids if str(client_id or "").strip()]
    return {
        CONF_TARGET_CLIENT_ID: clean[0] if len(clean) == 1 else "",
        CONF_TARGET_CLIENT_IDS_JSON: format_target_client_ids_json(clean),
        CONF_TARGET_CLIENT_IDS: clean,
    }


def _remap_views_for_dashboard_path(
    views: list[dict[str, Any]],
    old_dashboard_path: str,
    new_dashboard_path: str,
) -> list[dict[str, Any]]:
    """Remap existing view paths when the dashboard base path changes."""
    if not old_dashboard_path or not new_dashboard_path or old_dashboard_path == new_dashboard_path:
        return deepcopy(views)

    remapped: list[dict[str, Any]] = []
    for view in deepcopy(views):
        path = normalize_path(str(view.get("path", "")))
        if path == old_dashboard_path:
            view["path"] = new_dashboard_path
        elif path.startswith(f"{old_dashboard_path}/"):
            suffix = path[len(old_dashboard_path):]
            view["path"] = f"{new_dashboard_path}{suffix}"
        remapped.append(view)
    return remapped


class DashboardRotatorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dashboard Rotator."""

    VERSION = 1

    def __init__(self) -> None:
        self._working: dict[str, Any] | None = None
        self._selected_view_index: int | None = None

    def _ensure_working(self) -> dict[str, Any]:
        if self._working is None:
            self._working = normalize_config(
                {
                    CONF_NAME: DEFAULT_NAME,
                    CONF_DASHBOARD_PATH: DEFAULT_DASHBOARD_PATH,
                    CONF_ENABLED: DEFAULT_ENABLED,
                    CONF_DEFAULT_INTERVAL: DEFAULT_INTERVAL,
                    CONF_PAUSE_ON_INTERACTION: DEFAULT_PAUSE_ON_INTERACTION,
                    CONF_ONLY_WHEN_VISIBLE: DEFAULT_ONLY_WHEN_VISIBLE,
                    CONF_START_DELAY: DEFAULT_START_DELAY,
                    CONF_TARGET_CLIENT_ID: DEFAULT_TARGET_CLIENT_ID,
                    CONF_CLIENT_ALIASES_JSON: DEFAULT_CLIENT_ALIASES_JSON,
                    CONF_VIEWS_JSON: DEFAULT_VIEWS_JSON,
                }
            )
        return self._working

    def _set_working(self, candidate: dict[str, Any]) -> dict[str, Any]:
        self._working = normalize_config(candidate)
        return self._working

    def _build_candidate(self, updates: dict[str, Any]) -> dict[str, Any]:
        return {
            **deepcopy(self._ensure_working()),
            **updates,
        }

    def _build_views_payload(self, views: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            CONF_VIEWS_JSON: format_views_json(views),
        }

    def _build_view_options(self) -> list[SelectOptionDict]:
        return [
            SelectOptionDict(value=str(index), label=_view_option_label(index, view))
            for index, view in enumerate(self._ensure_working()[CONF_VIEWS])
        ]

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        config = self._ensure_working()
        return self.async_show_menu(
            step_id="user",
            menu_options=["general", "views", "advanced", "save"],
            description_placeholders={
                "name": NAME,
                "views_summary": _views_summary(config[CONF_VIEWS]),
                "target_client": ", ".join(config.get(CONF_TARGET_CLIENT_IDS, [])) or "all clients",
            },
        )

    async def async_step_general(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        config = self._ensure_working()

        if user_input is not None:
            new_dashboard_path = normalize_path(
                str(user_input.get(CONF_DASHBOARD_PATH, config.get(CONF_DASHBOARD_PATH, DEFAULT_DASHBOARD_PATH)))
            ) or DEFAULT_DASHBOARD_PATH
            raw_target_client_id = str(user_input.get(CONF_TARGET_CLIENT_ID, "") or "").strip()
            target_payload = _build_target_payload(
                [raw_target_client_id]
                if raw_target_client_id
                else (config.get(CONF_TARGET_CLIENT_IDS, []) if len(config.get(CONF_TARGET_CLIENT_IDS, [])) > 1 else [])
            )
            remapped_views = _remap_views_for_dashboard_path(
                config[CONF_VIEWS],
                config.get(CONF_DASHBOARD_PATH, DEFAULT_DASHBOARD_PATH),
                new_dashboard_path,
            )
            user_input = {
                **user_input,
                CONF_DASHBOARD_PATH: new_dashboard_path,
                **target_payload,
                CONF_VIEWS_JSON: format_views_json(remapped_views),
            }
            try:
                self._set_working(self._build_candidate(user_input))
            except (InvalidViewsConfig, InvalidAliasesConfig):
                errors["base"] = "invalid_views"
            else:
                return await self.async_step_user()

        return self.async_show_form(
            step_id="general",
            data_schema=self.add_suggested_values_to_schema(
                _build_general_schema(config),
                config,
            ),
            errors=errors,
        )

    async def async_step_advanced(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        config = self._ensure_working()

        if user_input is not None:
            try:
                self._set_working(self._build_candidate(user_input))
            except (InvalidViewsConfig, InvalidAliasesConfig):
                errors["base"] = "invalid_views"
            else:
                return await self.async_step_user()

        return self.async_show_form(
            step_id="advanced",
            data_schema=self.add_suggested_values_to_schema(
                _build_advanced_schema(config),
                config,
            ),
            errors=errors,
        )

    async def async_step_views(self, user_input: dict[str, Any] | None = None):
        return self.async_show_menu(
            step_id="views",
            menu_options=["add_view", "edit_view_select", "delete_view_select", "user", "save"],
            description_placeholders={
                "views_summary": _views_summary(self._ensure_working()[CONF_VIEWS]),
            },
        )

    async def async_step_add_view(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        config = self._ensure_working()
        defaults = {
            "path": f"{config[CONF_DASHBOARD_PATH]}/new-view",
            "title": "",
            "seconds": config[CONF_DEFAULT_INTERVAL],
            "enabled": True,
            FIELD_POSITION: len(config[CONF_VIEWS]) + 1,
        }

        if user_input is not None:
            try:
                views = deepcopy(config[CONF_VIEWS])
                insert_at = max(0, min(len(views), int(user_input[FIELD_POSITION]) - 1))
                views.insert(
                    insert_at,
                    {
                        "path": normalize_path(str(user_input["path"])),
                        "title": str(user_input["title"] or "").strip(),
                        "seconds": int(user_input["seconds"]),
                        "enabled": bool(user_input["enabled"]),
                    },
                )
                self._set_working(self._build_candidate(self._build_views_payload(views)))
            except (InvalidViewsConfig, InvalidAliasesConfig, ValueError):
                errors["base"] = "invalid_views"
            else:
                return await self.async_step_views()

        return self.async_show_form(
            step_id="add_view",
            data_schema=_build_view_edit_schema(defaults, len(config[CONF_VIEWS]) + 1),
            errors=errors,
        )

    async def async_step_edit_view_select(self, user_input: dict[str, Any] | None = None):
        options = self._build_view_options()
        if user_input is not None:
            self._selected_view_index = int(user_input[FIELD_SELECTED_VIEW])
            return await self.async_step_edit_view()

        return self.async_show_form(
            step_id="edit_view_select",
            data_schema=_build_view_select_schema(options),
        )

    async def async_step_edit_view(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        config = self._ensure_working()
        index = self._selected_view_index
        if index is None or index >= len(config[CONF_VIEWS]):
            return await self.async_step_views()

        view = deepcopy(config[CONF_VIEWS][index])
        defaults = {
            **view,
            FIELD_POSITION: index + 1,
        }

        if user_input is not None:
            try:
                views = deepcopy(config[CONF_VIEWS])
                views.pop(index)
                insert_at = max(0, min(len(views), int(user_input[FIELD_POSITION]) - 1))
                views.insert(
                    insert_at,
                    {
                        "path": normalize_path(str(user_input["path"])),
                        "title": str(user_input["title"] or "").strip(),
                        "seconds": int(user_input["seconds"]),
                        "enabled": bool(user_input["enabled"]),
                    },
                )
                self._set_working(self._build_candidate(self._build_views_payload(views)))
            except (InvalidViewsConfig, InvalidAliasesConfig, ValueError):
                errors["base"] = "invalid_views"
            else:
                self._selected_view_index = None
                return await self.async_step_views()

        return self.async_show_form(
            step_id="edit_view",
            data_schema=_build_view_edit_schema(defaults, len(config[CONF_VIEWS])),
            errors=errors,
        )

    async def async_step_delete_view_select(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        config = self._ensure_working()
        options = self._build_view_options()

        if user_input is not None:
            try:
                delete_index = int(user_input[FIELD_SELECTED_VIEW])
                views = deepcopy(config[CONF_VIEWS])
                views.pop(delete_index)
                self._set_working(self._build_candidate(self._build_views_payload(views)))
            except (InvalidViewsConfig, InvalidAliasesConfig, ValueError, IndexError):
                errors["base"] = "invalid_views"
            else:
                return await self.async_step_views()

        return self.async_show_form(
            step_id="delete_view_select",
            data_schema=_build_view_select_schema(options),
            errors=errors,
        )

    async def async_step_save(self, user_input: dict[str, Any] | None = None):
        config = self._ensure_working()
        return self.async_create_entry(
            title=config[CONF_NAME],
            data=build_storage_dict(config),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowWithReload:
        """Return the options flow handler."""
        return DashboardRotatorOptionsFlow()


class DashboardRotatorOptionsFlow(OptionsFlowWithReload):
    """Options flow for Dashboard Rotator."""

    def __init__(self) -> None:
        super().__init__()
        self._working: dict[str, Any] | None = None
        self._selected_view_index: int | None = None
        self._selected_client_id: str | None = None

    def _ensure_working(self) -> dict[str, Any]:
        if self._working is None:
            self._working = normalize_config({**self.config_entry.data, **self.config_entry.options})
        return self._working

    def _set_working(self, candidate: dict[str, Any]) -> dict[str, Any]:
        self._working = normalize_config(candidate)
        return self._working

    def _build_candidate(self, updates: dict[str, Any]) -> dict[str, Any]:
        return {
            **deepcopy(self._ensure_working()),
            **updates,
        }

    def _build_views_payload(self, views: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            CONF_VIEWS_JSON: format_views_json(views),
        }

    def _build_aliases_payload(self, aliases: dict[str, str]) -> dict[str, Any]:
        return {
            CONF_CLIENT_ALIASES_JSON: format_aliases_json(aliases),
        }

    def _get_runtime_states(self) -> dict[str, dict[str, Any]]:
        manager = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if not manager:
            return {}
        return dict(manager.client_states)

    def _build_client_options(self, include_all: bool = True) -> list[SelectOptionDict]:
        config = self._ensure_working()
        alias_map = config.get("client_aliases", {})
        states = self._get_runtime_states()

        options: list[SelectOptionDict] = []
        if include_all:
            options.append(SelectOptionDict(value="", label="All clients"))
        if not states:
            return options

        for client_id, state in sorted(
            states.items(),
            key=lambda item: item[1].get("updated_at") or "",
            reverse=True,
        ):
            alias = alias_map.get(client_id) or state.get("page_title") or state.get("current_view") or ""
            options.append(
                SelectOptionDict(
                    value=client_id,
                    label=_client_option_label(client_id, alias, state),
                )
            )
        return options

    def _build_view_options(self) -> list[SelectOptionDict]:
        return [
            SelectOptionDict(value=str(index), label=_view_option_label(index, view))
            for index, view in enumerate(self._ensure_working()[CONF_VIEWS])
        ]

    def _get_selected_client_state(self) -> dict[str, Any]:
        if not self._selected_client_id:
            return {}
        return self._get_runtime_states().get(self._selected_client_id, {})

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        config = self._ensure_working()
        return self.async_show_menu(
            step_id="init",
            menu_options=["general", "views", "clients", "advanced", "save"],
            description_placeholders={
                "views_summary": _views_summary(config[CONF_VIEWS]),
                "target_client": ", ".join(config.get(CONF_TARGET_CLIENT_IDS, [])) or "all clients",
            },
        )

    async def async_step_clients(self, user_input: dict[str, Any] | None = None):
        config = self._ensure_working()
        return self.async_show_menu(
            step_id="clients",
            menu_options=["view_client_details_select", "edit_target_client", "clear_target_client", "edit_client_alias_select", "init", "save"],
            description_placeholders={
                "clients_summary": _clients_summary(
                    config.get(CONF_CLIENT_ALIASES, {}),
                    self._get_runtime_states(),
                    config.get(CONF_TARGET_CLIENT_IDS, []),
                ),
            },
        )

    async def async_step_clear_target_client(self, user_input: dict[str, Any] | None = None):
        self._set_working(self._build_candidate(_build_target_payload([])))
        return await self.async_step_clients()

    async def async_step_view_client_details_select(self, user_input: dict[str, Any] | None = None):
        options = self._build_client_options(include_all=False)
        if not options:
            return await self.async_step_clients()
        if user_input is not None:
            self._selected_client_id = str(user_input[FIELD_SELECTED_CLIENT])
            return await self.async_step_view_client_details()

        return self.async_show_form(
            step_id="view_client_details_select",
            data_schema=_build_client_select_schema(options),
        )

    async def async_step_view_client_details(self, user_input: dict[str, Any] | None = None):
        config = self._ensure_working()
        client_id = self._selected_client_id
        if not client_id:
            return await self.async_step_clients()

        aliases = dict(config.get(CONF_CLIENT_ALIASES, {}))
        state = self._get_selected_client_state()
        return self.async_show_menu(
            step_id="view_client_details",
            menu_options=["add_selected_target_client", "remove_selected_target_client", "edit_client_alias", "clear_selected_client_alias", "clients"],
            description_placeholders=_client_details_placeholders(
                client_id,
                aliases.get(client_id),
                state,
                config.get(CONF_TARGET_CLIENT_IDS, []),
            ),
        )

    async def async_step_add_selected_target_client(self, user_input: dict[str, Any] | None = None):
        client_id = self._selected_client_id
        if not client_id:
            return await self.async_step_clients()
        config = self._ensure_working()
        current = list(config.get(CONF_TARGET_CLIENT_IDS, []))
        if client_id not in current:
            current.append(client_id)
        self._set_working(self._build_candidate(_build_target_payload(current)))
        return await self.async_step_view_client_details()

    async def async_step_remove_selected_target_client(self, user_input: dict[str, Any] | None = None):
        client_id = self._selected_client_id
        if not client_id:
            return await self.async_step_clients()
        config = self._ensure_working()
        current = [item for item in config.get(CONF_TARGET_CLIENT_IDS, []) if item != client_id]
        self._set_working(self._build_candidate(_build_target_payload(current)))
        return await self.async_step_view_client_details()

    async def async_step_clear_selected_client_alias(self, user_input: dict[str, Any] | None = None):
        config = self._ensure_working()
        client_id = self._selected_client_id
        if not client_id:
            return await self.async_step_clients()

        aliases = dict(config.get(CONF_CLIENT_ALIASES, {}))
        aliases.pop(client_id, None)
        self._set_working(self._build_candidate(self._build_aliases_payload(aliases)))
        return await self.async_step_view_client_details()

    async def async_step_edit_target_client(self, user_input: dict[str, Any] | None = None):
        config = self._ensure_working()
        options = self._build_client_options(include_all=True)
        if user_input is not None:
            try:
                client_id = str(user_input.get(CONF_TARGET_CLIENT_ID, "") or "").strip()
                current = list(config.get(CONF_TARGET_CLIENT_IDS, []))
                if not client_id:
                    next_targets: list[str] = []
                elif client_id in current:
                    next_targets = current
                else:
                    next_targets = [*current, client_id]
                self._set_working(self._build_candidate(_build_target_payload(next_targets)))
            except (InvalidViewsConfig, InvalidAliasesConfig):
                return self.async_show_form(
                    step_id="edit_target_client",
                    data_schema=_build_client_select_schema(
                        options,
                        field_name=CONF_TARGET_CLIENT_ID,
                        default=config.get(CONF_TARGET_CLIENT_ID, ""),
                    ),
                    errors={"base": "invalid_views"},
                )
            return await self.async_step_clients()

        return self.async_show_form(
            step_id="edit_target_client",
            data_schema=_build_client_select_schema(
                options,
                field_name=CONF_TARGET_CLIENT_ID,
                default="",
            ),
        )

    async def async_step_edit_client_alias_select(self, user_input: dict[str, Any] | None = None):
        options = self._build_client_options(include_all=False)
        if not options:
            return await self.async_step_clients()
        if user_input is not None:
            self._selected_client_id = str(user_input[FIELD_SELECTED_CLIENT])
            return await self.async_step_edit_client_alias()

        return self.async_show_form(
            step_id="edit_client_alias_select",
            data_schema=_build_client_select_schema(options),
        )

    async def async_step_edit_client_alias(self, user_input: dict[str, Any] | None = None):
        config = self._ensure_working()
        client_id = self._selected_client_id
        aliases = dict(config.get(CONF_CLIENT_ALIASES, {}))
        states = self._get_runtime_states()
        if not client_id:
            return await self.async_step_clients()

        if user_input is not None:
            alias = str(user_input.get(FIELD_ALIAS) or "").strip()
            if alias:
                aliases[client_id] = alias
            else:
                aliases.pop(client_id, None)
            self._set_working(self._build_candidate(self._build_aliases_payload(aliases)))
            return await self.async_step_view_client_details()

        defaults = {
            FIELD_ALIAS: aliases.get(client_id, ""),
        }
        state = states.get(client_id) or {}
        return self.async_show_form(
            step_id="edit_client_alias",
            data_schema=_build_client_alias_schema(defaults),
            description_placeholders={
                "client_label": _client_option_label(client_id, aliases.get(client_id), state),
            },
        )

    async def async_step_general(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        config = self._ensure_working()

        if user_input is not None:
            new_dashboard_path = normalize_path(
                str(user_input.get(CONF_DASHBOARD_PATH, config.get(CONF_DASHBOARD_PATH, DEFAULT_DASHBOARD_PATH)))
            ) or DEFAULT_DASHBOARD_PATH
            raw_target_client_id = str(user_input.get(CONF_TARGET_CLIENT_ID, "") or "").strip()
            target_payload = _build_target_payload(
                [raw_target_client_id]
                if raw_target_client_id
                else (config.get(CONF_TARGET_CLIENT_IDS, []) if len(config.get(CONF_TARGET_CLIENT_IDS, [])) > 1 else [])
            )
            remapped_views = _remap_views_for_dashboard_path(
                config[CONF_VIEWS],
                config.get(CONF_DASHBOARD_PATH, DEFAULT_DASHBOARD_PATH),
                new_dashboard_path,
            )
            user_input = {
                **user_input,
                CONF_DASHBOARD_PATH: new_dashboard_path,
                **target_payload,
                CONF_VIEWS_JSON: format_views_json(remapped_views),
            }
            try:
                self._set_working(self._build_candidate(user_input))
            except (InvalidViewsConfig, InvalidAliasesConfig):
                errors["base"] = "invalid_views"
            else:
                return await self.async_step_init()

        return self.async_show_form(
            step_id="general",
            data_schema=self.add_suggested_values_to_schema(
                _build_general_schema(config, self._build_client_options()), config
            ),
            errors=errors,
        )

    async def async_step_advanced(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        config = self._ensure_working()

        if user_input is not None:
            try:
                self._set_working(self._build_candidate(user_input))
            except (InvalidViewsConfig, InvalidAliasesConfig):
                errors["base"] = "invalid_views"
            else:
                return await self.async_step_init()

        return self.async_show_form(
            step_id="advanced",
            data_schema=self.add_suggested_values_to_schema(
                _build_advanced_schema(config),
                config,
            ),
            errors=errors,
        )

    async def async_step_views(self, user_input: dict[str, Any] | None = None):
        return self.async_show_menu(
            step_id="views",
            menu_options=["add_view", "edit_view_select", "delete_view_select", "init", "save"],
            description_placeholders={
                "views_summary": _views_summary(self._ensure_working()[CONF_VIEWS]),
            },
        )

    async def async_step_add_view(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        config = self._ensure_working()
        defaults = {
            "path": f"{config[CONF_DASHBOARD_PATH]}/new-view",
            "title": "",
            "seconds": config[CONF_DEFAULT_INTERVAL],
            "enabled": True,
            FIELD_POSITION: len(config[CONF_VIEWS]) + 1,
        }

        if user_input is not None:
            try:
                views = deepcopy(config[CONF_VIEWS])
                insert_at = max(0, min(len(views), int(user_input[FIELD_POSITION]) - 1))
                views.insert(
                    insert_at,
                    {
                        "path": normalize_path(str(user_input["path"])),
                        "title": str(user_input["title"] or "").strip(),
                        "seconds": int(user_input["seconds"]),
                        "enabled": bool(user_input["enabled"]),
                    },
                )
                self._set_working(self._build_candidate(self._build_views_payload(views)))
            except (InvalidViewsConfig, InvalidAliasesConfig, ValueError):
                errors["base"] = "invalid_views"
            else:
                return await self.async_step_views()

        return self.async_show_form(
            step_id="add_view",
            data_schema=_build_view_edit_schema(defaults, len(config[CONF_VIEWS]) + 1),
            errors=errors,
        )

    async def async_step_edit_view_select(self, user_input: dict[str, Any] | None = None):
        options = self._build_view_options()
        if user_input is not None:
            self._selected_view_index = int(user_input[FIELD_SELECTED_VIEW])
            return await self.async_step_edit_view()

        return self.async_show_form(
            step_id="edit_view_select",
            data_schema=_build_view_select_schema(options),
        )

    async def async_step_edit_view(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        config = self._ensure_working()
        index = self._selected_view_index
        if index is None or index >= len(config[CONF_VIEWS]):
            return await self.async_step_views()

        view = deepcopy(config[CONF_VIEWS][index])
        defaults = {
            **view,
            FIELD_POSITION: index + 1,
        }

        if user_input is not None:
            try:
                views = deepcopy(config[CONF_VIEWS])
                views.pop(index)
                insert_at = max(0, min(len(views), int(user_input[FIELD_POSITION]) - 1))
                views.insert(
                    insert_at,
                    {
                        "path": normalize_path(str(user_input["path"])),
                        "title": str(user_input["title"] or "").strip(),
                        "seconds": int(user_input["seconds"]),
                        "enabled": bool(user_input["enabled"]),
                    },
                )
                self._set_working(self._build_candidate(self._build_views_payload(views)))
            except (InvalidViewsConfig, InvalidAliasesConfig, ValueError):
                errors["base"] = "invalid_views"
            else:
                self._selected_view_index = None
                return await self.async_step_views()

        return self.async_show_form(
            step_id="edit_view",
            data_schema=_build_view_edit_schema(defaults, len(config[CONF_VIEWS])),
            errors=errors,
        )

    async def async_step_delete_view_select(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        config = self._ensure_working()
        options = self._build_view_options()

        if user_input is not None:
            try:
                delete_index = int(user_input[FIELD_SELECTED_VIEW])
                views = deepcopy(config[CONF_VIEWS])
                views.pop(delete_index)
                self._set_working(self._build_candidate(self._build_views_payload(views)))
            except (InvalidViewsConfig, InvalidAliasesConfig, ValueError, IndexError):
                errors["base"] = "invalid_views"
            else:
                return await self.async_step_views()

        return self.async_show_form(
            step_id="delete_view_select",
            data_schema=_build_view_select_schema(options),
            errors=errors,
        )

    async def async_step_save(self, user_input: dict[str, Any] | None = None):
        return self.async_create_entry(data=build_storage_dict(self._ensure_working()))
