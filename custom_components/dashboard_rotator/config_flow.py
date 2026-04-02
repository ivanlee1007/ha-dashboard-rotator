"""Config flow for Dashboard Rotator."""
from __future__ import annotations

from copy import deepcopy
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
    CONF_CLIENT_ALIASES_JSON,
    CONF_DASHBOARD_PATH,
    CONF_DEFAULT_INTERVAL,
    CONF_ENABLED,
    CONF_NAME,
    CONF_ONLY_WHEN_VISIBLE,
    CONF_PAUSE_ON_INTERACTION,
    CONF_START_DELAY,
    CONF_TARGET_CLIENT_ID,
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
    InvalidAliasesConfig,
    InvalidViewsConfig,
    build_storage_dict,
    format_aliases_json,
    normalize_config,
    normalize_path,
)

FIELD_SELECTED_VIEW = "selected_view"
FIELD_POSITION = "position"


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
            vol.Required(
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
            vol.Required(
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


class DashboardRotatorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dashboard Rotator."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                normalized = normalize_config(user_input)
            except (InvalidViewsConfig, InvalidAliasesConfig):
                errors["base"] = "invalid_views"
            else:
                return self.async_create_entry(
                    title=normalized[CONF_NAME],
                    data=build_storage_dict(normalized),
                )

        defaults = {
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

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(defaults),
            errors=errors,
            description_placeholders={"name": NAME},
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

    def _build_client_options(self) -> list[SelectOptionDict]:
        config = self._ensure_working()
        alias_map = config.get("client_aliases", {})
        manager = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)

        options: list[SelectOptionDict] = [
            SelectOptionDict(value="", label="All clients"),
        ]
        if not manager:
            return options

        for client_id, state in sorted(
            manager.client_states.items(),
            key=lambda item: item[1].get("updated_at") or "",
            reverse=True,
        ):
            alias = (
                alias_map.get(client_id)
                or state.get("page_title")
                or state.get("current_view")
                or ""
            )
            status = state.get("status") or "idle"
            label = " — ".join(bit for bit in [alias, client_id, status] if bit)
            options.append(SelectOptionDict(value=client_id, label=label or client_id))
        return options

    def _build_view_options(self) -> list[SelectOptionDict]:
        return [
            SelectOptionDict(value=str(index), label=_view_option_label(index, view))
            for index, view in enumerate(self._ensure_working()[CONF_VIEWS])
        ]

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        config = self._ensure_working()
        return self.async_show_menu(
            step_id="init",
            menu_options=["general", "views", "advanced", "save"],
            description_placeholders={
                "views_summary": _views_summary(config[CONF_VIEWS]),
                "target_client": config.get(CONF_TARGET_CLIENT_ID) or "all clients",
            },
        )

    async def async_step_general(self, user_input: dict[str, Any] | None = None):
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
