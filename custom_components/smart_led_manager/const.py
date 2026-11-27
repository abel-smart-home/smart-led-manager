"""Constants for Smart LED Manager."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "smart_led_manager"
NAME: Final = "Smart LED Manager"
VERSION: Final = "0.1.0-alpha.3"

CONF_LIGHTS: Final = "lights"
CONF_ZONES: Final = "zones"
CONF_MODES: Final = "modes"
CONF_AREA_ID: Final = "area_id"
CONF_RULES: Final = "rules"
CONF_SHOW_SIDEBAR: Final = "show_sidebar"
CONF_TIE_BREAKER: Final = "tie_breaker"
CONF_MIN_COMMAND_INTERVAL: Final = "min_command_interval"
CONF_MANUAL_POLICY: Final = "manual_policy"

DEFAULT_PRIORITY: Final = 50
DEFAULT_MIN_COMMAND_INTERVAL: Final = 0.75
DEFAULT_TIE_BREAKER: Final = "newest"
DEFAULT_MANUAL_POLICY: Final = "service_only"
DEFAULT_SHOW_SIDEBAR: Final = True

RULE_TYPE_STATE: Final = "state"
RULE_TYPE_NUMERIC: Final = "numeric"
RULE_TYPE_EVENT: Final = "event"
RULE_TYPE_CONTINUOUS: Final = "continuous"
RULE_TYPE_NOTICE: Final = "notice"

TARGET_ENTITIES: Final = "entities"
TARGET_ZONES: Final = "zones"
TARGET_AREAS: Final = "areas"
TARGET_LABELS: Final = "labels"
TARGET_GROUPS: Final = "groups"
TARGET_ALL_MANAGED: Final = "all_managed"

PLATFORMS: Final = [Platform.SELECT, Platform.SENSOR, Platform.SWITCH]

STORAGE_VERSION: Final = 1
STORAGE_MINOR_VERSION: Final = 1
STORAGE_KEY: Final = f"{DOMAIN}.{{entry_id}}"
MAX_ACTIVITY_ITEMS: Final = 100

SERVICE_ACTIVATE: Final = "activate"
SERVICE_DEACTIVATE: Final = "deactivate"
SERVICE_NOTIFY: Final = "notify"
SERVICE_RUN_NOTICE: Final = "run_notice"
SERVICE_SET_SCENE: Final = "set_scene"
SERVICE_CANCEL: Final = "cancel"
SERVICE_CLEAR_NOTIFICATIONS: Final = "clear_notifications"
SERVICE_SET_MANUAL_OVERRIDE: Final = "set_manual_override"
SERVICE_ACTIVATE_MODE: Final = "activate_mode"
SERVICE_DEACTIVATE_MODE: Final = "deactivate_mode"
SERVICE_SET_ZONE_MODE: Final = "set_zone_mode"

MODULE_NOTIFICATION: Final = "notification"
MODULE_SCENE: Final = "scene"
MODULE_MANUAL: Final = "manual"
MODULE_RULE: Final = "rule"
MODULE_MODE: Final = "mode"

EVENT_REQUEST_CHANGED: Final = f"{DOMAIN}_request_changed"
EVENT_MODE_CHANGED: Final = f"{DOMAIN}_mode_changed"
