"""Constants for Dashboard Rotator."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "dashboard_rotator"
NAME = "Dashboard Rotator"
VERSION = "0.1.25"

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.BUTTON]

FRONTEND_FILE = "dashboard-rotator.js"
FRONTEND_URL = f"/{DOMAIN}_static/{FRONTEND_FILE}"

CONF_NAME = "name"
CONF_ENABLED = "enabled"
CONF_DASHBOARD_PATH = "dashboard_path"
CONF_DEFAULT_INTERVAL = "default_interval"
CONF_PAUSE_ON_INTERACTION = "pause_on_interaction"
CONF_ONLY_WHEN_VISIBLE = "only_when_visible"
CONF_START_DELAY = "start_delay"
CONF_TARGET_CLIENT_ID = "target_client_id"
CONF_TARGET_CLIENT_IDS_JSON = "target_client_ids_json"
CONF_TARGET_CLIENT_IDS = "target_client_ids"
CONF_CLIENT_ALIASES_JSON = "client_aliases_json"
CONF_CLIENT_ALIASES = "client_aliases"
CONF_VIEWS_JSON = "views_json"
CONF_VIEWS = "views"
CONF_PATH = "path"
CONF_SECONDS = "seconds"
CONF_TITLE = "title"

DEFAULT_NAME = NAME
DEFAULT_ENABLED = True
DEFAULT_DASHBOARD_PATH = "/lovelace"
DEFAULT_INTERVAL = 15
DEFAULT_PAUSE_ON_INTERACTION = 60
DEFAULT_ONLY_WHEN_VISIBLE = True
DEFAULT_START_DELAY = 3
DEFAULT_TARGET_CLIENT_ID = ""
DEFAULT_TARGET_CLIENT_IDS_JSON = "[]"
DEFAULT_CLIENT_ALIASES_JSON = "{}"
DEFAULT_VIEWS_JSON = """[
  {
    \"path\": \"/lovelace/home\",
    \"seconds\": 10,
    \"title\": \"Home\"
  },
  {
    \"path\": \"/lovelace/weather\",
    \"seconds\": 20,
    \"title\": \"Weather\"
  }
]"""

SERVICE_PAUSE = "pause"
SERVICE_RESUME = "resume"
SERVICE_NEXT_VIEW = "next_view"
SERVICE_PREVIOUS_VIEW = "previous_view"
SERVICE_JUMP_TO_VIEW = "jump_to_view"
SERVICE_CLIENT_STATE = "client_state"
SERVICE_SET_CLIENT_ALIAS = "set_client_alias"
SERVICE_SET_TARGET_CLIENT = "set_target_client"

ATTR_PROFILE = "profile"
ATTR_COMMAND = "command"
ATTR_CLIENT_STATE = "client_state"
ATTR_CLIENT_STATES = "client_states"
ATTR_ACTIVE_CLIENT_ID = "active_client_id"
ATTR_ACTIVE_CLIENT_COUNT = "active_client_count"
ATTR_TARGET_CLIENT_ID = "target_client_id"
ATTR_TARGET_CLIENT_IDS = "target_client_ids"
ATTR_ACTIVE_CLIENT_ALIAS = "active_client_alias"
ATTR_INTEGRATION_DOMAIN = "integration_domain"
ATTR_ENTITY_ROLE = "entity_role"
ATTR_VERSION = "version"

CLIENT_STALE_SECONDS = 30

SIGNAL_RUNTIME_UPDATE = f"{DOMAIN}_runtime_update_{{}}"
