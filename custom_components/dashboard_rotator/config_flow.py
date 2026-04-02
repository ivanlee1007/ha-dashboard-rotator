"""Config flow for Dashboard Rotator."""
from __future__ import annotations

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
    InvalidAliasesConfig,
    InvalidViewsConfig,
    build_storage_dict,
    normalize_config,
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

    def _build_client_options(self) -> list[SelectOptionDict]:
        config = normalize_config({**self.config_entry.data, **self.config_entry.options})
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

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                normalized = normalize_config(user_input)
            except (InvalidViewsConfig, InvalidAliasesConfig):
                errors["base"] = "invalid_views"
            else:
                return self.async_create_entry(data=build_storage_dict(normalized))

        defaults = normalize_config({**self.config_entry.data, **self.config_entry.options})
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _build_schema(defaults, self._build_client_options()), defaults
            ),
            errors=errors,
        )
