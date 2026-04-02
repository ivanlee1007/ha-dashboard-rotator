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
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_DASHBOARD_PATH,
    CONF_DEFAULT_INTERVAL,
    CONF_ENABLED,
    CONF_NAME,
    CONF_ONLY_WHEN_VISIBLE,
    CONF_PAUSE_ON_INTERACTION,
    CONF_START_DELAY,
    CONF_VIEWS_JSON,
    DEFAULT_DASHBOARD_PATH,
    DEFAULT_ENABLED,
    DEFAULT_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_ONLY_WHEN_VISIBLE,
    DEFAULT_PAUSE_ON_INTERACTION,
    DEFAULT_START_DELAY,
    DEFAULT_VIEWS_JSON,
    DOMAIN,
    NAME,
)
from .helpers import InvalidViewsConfig, build_storage_dict, normalize_config


def _build_schema(defaults: dict[str, Any]) -> vol.Schema:
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
            except InvalidViewsConfig:
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
        return DashboardRotatorOptionsFlow(config_entry)


class DashboardRotatorOptionsFlow(OptionsFlowWithReload):
    """Options flow for Dashboard Rotator."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                normalized = normalize_config(user_input)
            except InvalidViewsConfig:
                errors["base"] = "invalid_views"
            else:
                return self.async_create_entry(title="", data=build_storage_dict(normalized))

        defaults = normalize_config({**self.config_entry.data, **self.config_entry.options})
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(_build_schema(defaults), defaults),
            errors=errors,
        )
