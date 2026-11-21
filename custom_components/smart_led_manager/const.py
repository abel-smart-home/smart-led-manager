"""Constants for Smart LED Manager."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "smart_led_manager"
NAME: Final = "Smart LED Manager"
VERSION: Final = "0.1.0-alpha.1"

CONF_LIGHTS: Final = "lights"
CONF_RULES: Final = "rules"
CONF_TIE_BREAKER: Final = "tie_breaker"
CONF_MIN_COMMAND_INTERVAL: Final = "min_command_interval"
CONF_MANUAL_POLICY: Final = "manual_policy"

DEFAULT_PRIORITY: Final = 50
DEFAULT_MIN_COMMAND_INTERVAL: Final = 0.75
DEFAULT_TIE_BREAKER: Final = "newest"
DEFAULT_MANUAL_POLICY: Final = "service_only"

RULE_TYPE_STATE: Final = "state"
RULE_TYPE_NUMERIC: Final = "numeric"

PLATFORMS: Final = [Platform.SENSOR]

STORAGE_VERSION: Final = 1
STORAGE_MINOR_VERSION: Final = 1
STORAGE_KEY: Final = f"{DOMAIN}.{{entry_id}}"
MAX_ACTIVITY_ITEMS: Final = 100

SERVICE_ACTIVATE: Final = "activate"
SERVICE_DEACTIVATE: Final = "deactivate"
SERVICE_NOTIFY: Final = "notify"
SERVICE_SET_SCENE: Final = "set_scene"
SERVICE_CANCEL: Final = "cancel"
SERVICE_CLEAR_NOTIFICATIONS: Final = "clear_notifications"
SERVICE_SET_MANUAL_OVERRIDE: Final = "set_manual_override"

MODULE_NOTIFICATION: Final = "notification"
MODULE_SCENE: Final = "scene"
MODULE_MANUAL: Final = "manual"
MODULE_RULE: Final = "rule"

EVENT_REQUEST_CHANGED: Final = f"{DOMAIN}_request_changed"
