"""Administrator-only local visual editor for numeric color rules."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import probatio
from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import label_registry as lr

from .const import (
    CONF_LIGHTS,
    CONF_RULES,
    CONF_SHOW_SIDEBAR,
    CONF_ZONES,
    DEFAULT_SHOW_SIDEBAR,
    DOMAIN,
    NAME,
    RULE_TYPE_EVENT,
    RULE_TYPE_NUMERIC,
    VERSION,
)
from .core.color import (
    ColorPoint,
    evaluate_rgb,
    normalize_color_points,
    parse_numeric_state,
    rgb_to_hex,
)
from .modules.configuration import mutable_json, options_revision
from .modules.rule_schema import RuleCatalog, RuleValidationError
from .modules.targeting import AdvancedTargetError, AdvancedTargetResolver

_LOGGER = logging.getLogger(__name__)

PANEL_PATH = "smart-led-manager-editor"
STATIC_URL = "/smart_led_manager_frontend"
_FRONTEND_PATH = Path(__file__).parent / "frontend"

_DATA_COMMANDS = "visual_editor_commands_registered"
_DATA_LOCK = "visual_editor_save_lock"
_DATA_PANEL = "visual_editor_panel_registered"
_DATA_PANEL_ENTRY = "visual_editor_panel_entry"
_DATA_STATIC = "visual_editor_static_registered"


class VisualEditorError(ValueError):
    """A client-visible editor request error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


async def async_setup_visual_editor(hass: HomeAssistant) -> None:
    """Register static files and authenticated WebSocket commands once."""

    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data.setdefault(_DATA_LOCK, asyncio.Lock())
    if not domain_data.get(_DATA_COMMANDS):
        websocket_api.async_register_command(hass, websocket_get_numeric_rules)
        websocket_api.async_register_command(hass, websocket_preview_numeric_rule)
        websocket_api.async_register_command(hass, websocket_save_numeric_rule)
        websocket_api.async_register_command(hass, websocket_get_smart_rules)
        websocket_api.async_register_command(hass, websocket_mutate_smart_rule)
        websocket_api.async_register_command(hass, websocket_preview_targets)
        domain_data[_DATA_COMMANDS] = True
    if not domain_data.get(_DATA_STATIC):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    STATIC_URL,
                    str(_FRONTEND_PATH),
                    cache_headers=False,
                )
            ]
        )
        domain_data[_DATA_STATIC] = True


async def async_register_visual_editor_panel(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Expose the administrator route and optionally show it in the sidebar."""

    domain_data = hass.data.setdefault(DOMAIN, {})
    if frontend.DATA_PANELS not in hass.data:
        _LOGGER.debug("Frontend is not loaded; visual editor panel is unavailable")
        return
    if (
        domain_data.get(_DATA_PANEL)
        and domain_data.get(_DATA_PANEL_ENTRY) == entry.entry_id
    ):
        return
    if domain_data.get(_DATA_PANEL):
        frontend.async_remove_panel(hass, PANEL_PATH, warn_if_unknown=False)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_PATH,
        webcomponent_name="smart-led-manager-visual-editor",
        sidebar_title=(
            NAME if entry.options.get(CONF_SHOW_SIDEBAR, DEFAULT_SHOW_SIDEBAR) else None
        ),
        sidebar_icon="mdi:led-strip-variant",
        module_url=f"{STATIC_URL}/visual-editor-panel.mjs?v={VERSION}",
        config={"entry_id": entry.entry_id, "version": VERSION},
        require_admin=True,
        handle_safe_area=True,
    )
    domain_data[_DATA_PANEL] = True
    domain_data[_DATA_PANEL_ENTRY] = entry.entry_id


@callback
def async_remove_visual_editor_panel(hass: HomeAssistant) -> None:
    """Remove the visible panel when the config entry is unloaded."""

    domain_data = getattr(hass, "data", {}).get(DOMAIN, {})
    if not domain_data.get(_DATA_PANEL):
        return
    frontend.async_remove_panel(hass, PANEL_PATH, warn_if_unknown=False)
    domain_data[_DATA_PANEL] = False
    domain_data.pop(_DATA_PANEL_ENTRY, None)


_mutable_json = mutable_json
_options_revision = options_revision


def _entry(hass: HomeAssistant, entry_id: str) -> ConfigEntry:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise VisualEditorError(
            "entry_not_found", "Smart LED Manager config entry was not found"
        )
    loaded_entries = hass.data.get(DOMAIN, {}).get("entries", {})
    if entry_id not in loaded_entries:
        raise VisualEditorError(
            "entry_not_loaded", "Smart LED Manager config entry is not loaded"
        )
    return entry


def _authorized_targets(entry: ConfigEntry) -> frozenset[str]:
    raw = entry.options.get(CONF_LIGHTS, entry.data.get(CONF_LIGHTS, []))
    if not isinstance(raw, (list, tuple)) or not all(
        isinstance(item, str) and item for item in raw
    ):
        raise VisualEditorError("invalid_options", "Managed lights are invalid")
    return frozenset(raw)


def _numeric_rule(
    hass: HomeAssistant, entry: ConfigEntry, rule_id: str
) -> tuple[Mapping[str, Any], frozenset[str]]:
    rules = entry.options.get(CONF_RULES, [])
    if not isinstance(rules, list):
        raise VisualEditorError("invalid_options", "Configured rules are invalid")
    matches = [
        rule
        for rule in rules
        if isinstance(rule, Mapping) and str(rule.get("id")) == rule_id
    ]
    if len(matches) != 1:
        raise VisualEditorError("rule_not_found", "Numeric rule was not found")
    rule = matches[0]
    if rule.get("type") != RULE_TYPE_NUMERIC:
        raise VisualEditorError("invalid_rule", "Selected rule is not numeric")
    try:
        targets = _advanced_target_resolver(hass, entry).resolve_rule(rule).targets
    except AdvancedTargetError as err:
        raise VisualEditorError(err.code, str(err)) from err
    return rule, targets


def _validated_mode(value: object) -> str:
    if value not in {"interpolate", "ranges"}:
        raise VisualEditorError(
            "invalid_mode", "Mode must be 'interpolate' or 'ranges'"
        )
    return str(value)


def _validated_points(raw: object) -> list[dict[str, Any]]:
    try:
        return normalize_color_points(raw)
    except ValueError as err:
        raise VisualEditorError("invalid_points", str(err)) from err


def _rule_payload(
    hass: HomeAssistant, entry: ConfigEntry, rule: Mapping[str, Any]
) -> dict[str, Any]:
    rule_id = rule.get("id")
    source = rule.get("source")
    if not isinstance(rule_id, str) or not rule_id:
        raise VisualEditorError("invalid_rule", "Numeric rule identifier is invalid")
    if not isinstance(source, str) or not source:
        raise VisualEditorError("invalid_rule", "Numeric rule source is invalid")
    _validated_rule, resolved_targets = _numeric_rule(hass, entry, rule_id)
    payload = _mutable_json(rule)
    payload["points"] = _validated_points(rule.get("points"))
    payload["mode"] = _validated_mode(rule.get("mode", "interpolate"))
    state = hass.states.get(source)
    unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) if state else None
    source_name = getattr(state, "name", source) if state else source
    target_details = []
    for target in sorted(resolved_targets):
        target_state = hass.states.get(target)
        target_details.append(
            {
                "entity_id": target,
                "name": getattr(target_state, "name", target)
                if target_state
                else target,
            }
        )
    return {
        "rule": payload,
        "unit": unit if isinstance(unit, str) and unit else None,
        "source": {"entity_id": source, "name": source_name},
        "targets": target_details,
    }


def _send_editor_error(
    connection: websocket_api.ActiveConnection,
    msg_id: int,
    err: VisualEditorError,
) -> None:
    connection.send_error(msg_id, err.code, str(err))


@websocket_api.websocket_command(
    {
        probatio.Required("type"): "smart_led_manager/rules/get",
        probatio.Required("entry_id"): str,
    }
)
@websocket_api.require_admin
@callback
def websocket_get_numeric_rules(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return validated numeric rules and a concurrency revision."""

    try:
        entry = _entry(hass, msg["entry_id"])
        rules = entry.options.get(CONF_RULES, [])
        if not isinstance(rules, list):
            raise VisualEditorError("invalid_options", "Configured rules are invalid")
        payload = [
            _rule_payload(hass, entry, rule)
            for rule in rules
            if isinstance(rule, Mapping) and rule.get("type") == RULE_TYPE_NUMERIC
        ]
    except VisualEditorError as err:
        _send_editor_error(connection, msg["id"], err)
        return
    connection.send_result(
        msg["id"],
        {
            "entry_id": entry.entry_id,
            "revision": _options_revision(entry.options),
            "rules": payload,
        },
    )


@websocket_api.websocket_command(
    {
        probatio.Required("type"): "smart_led_manager/rules/preview",
        probatio.Required("entry_id"): str,
        probatio.Required("rule_id"): str,
        probatio.Required("mode"): str,
        probatio.Required("points"): list,
        probatio.Required("values"): list,
    }
)
@websocket_api.require_admin
@callback
def websocket_preview_numeric_rule(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Simulate draft points with the production algorithm and no light I/O."""

    try:
        _entry(hass, msg["entry_id"])
        mode = _validated_mode(msg["mode"])
        raw_points = _validated_points(msg["points"])
        points = tuple(
            ColorPoint(point["value"], tuple(point["rgb"])) for point in raw_points
        )
        if not 1 <= len(msg["values"]) <= 201:
            raise VisualEditorError(
                "invalid_values", "Preview requires between 1 and 201 values"
            )
        values: list[float] = []
        for raw_value in msg["values"]:
            value = parse_numeric_state(raw_value)
            if value is None:
                raise VisualEditorError(
                    "invalid_values", "Preview values must be finite numbers"
                )
            values.append(value)
        results = []
        for value in values:
            evaluation = evaluate_rgb(value, points, mode=mode)
            results.append(
                {
                    "value": value,
                    "rgb": list(evaluation.color),
                    "hex": rgb_to_hex(evaluation.color),
                    "relation": evaluation.relation,
                    "lower": evaluation.lower,
                    "upper": evaluation.upper,
                    "ratio": evaluation.ratio,
                }
            )
    except VisualEditorError as err:
        _send_editor_error(connection, msg["id"], err)
        return
    connection.send_result(msg["id"], {"results": results})


@websocket_api.websocket_command(
    {
        probatio.Required("type"): "smart_led_manager/rules/save",
        probatio.Required("entry_id"): str,
        probatio.Required("rule_id"): str,
        probatio.Required("revision"): str,
        probatio.Required("mode"): str,
        probatio.Required("points"): list,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_save_numeric_rule(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Persist only a numeric rule's mode and points after revision checking."""

    try:
        lock: asyncio.Lock = hass.data[DOMAIN][_DATA_LOCK]
        async with lock:
            entry = _entry(hass, msg["entry_id"])
            current_revision = _options_revision(entry.options)
            if msg["revision"] != current_revision:
                raise VisualEditorError(
                    "conflict",
                    "Configuration changed in another session; reload before saving",
                )
            mode = _validated_mode(msg["mode"])
            points = _validated_points(msg["points"])
            current, _resolved_targets = _numeric_rule(
                hass, entry, msg["rule_id"]
            )
            options = _mutable_json(entry.options)
            rules = list(options.get(CONF_RULES, []))
            for index, rule in enumerate(rules):
                if isinstance(rule, dict) and rule.get("id") == current["id"]:
                    rules[index]["mode"] = mode
                    rules[index]["points"] = points
                    saved_rule = _mutable_json(rules[index])
                    break
            else:
                raise VisualEditorError("rule_not_found", "Numeric rule was not found")
            options[CONF_RULES] = rules
            hass.config_entries.async_update_entry(entry, options=options)
            revision = _options_revision(options)
    except VisualEditorError as err:
        _send_editor_error(connection, msg["id"], err)
        return
    except Exception:  # pragma: no cover - defensive HA transport boundary
        _LOGGER.exception("Unexpected visual editor save failure")
        connection.send_error(
            msg["id"], "internal_error", "Unexpected error while saving the rule"
        )
        return
    connection.send_result(msg["id"], {"revision": revision, "rule": saved_rule})


def _configured_rules(entry: ConfigEntry) -> list[Mapping[str, Any]]:
    raw = entry.options.get(CONF_RULES, [])
    if not isinstance(raw, list) or not all(isinstance(rule, Mapping) for rule in raw):
        raise VisualEditorError("invalid_options", "Configured rules are invalid")
    return raw


def _advanced_target_resolver(
    hass: HomeAssistant, entry: ConfigEntry
) -> AdvancedTargetResolver:
    zones = entry.options.get(CONF_ZONES, [])
    if not isinstance(zones, list):
        raise VisualEditorError("invalid_options", "Configured zones are invalid")
    try:
        return AdvancedTargetResolver(
            hass,
            _authorized_targets(entry),
            [zone for zone in zones if isinstance(zone, Mapping)],
        )
    except AdvancedTargetError as err:
        raise VisualEditorError(err.code, str(err)) from err


def _friendly_entity(hass: HomeAssistant, entity_id: str) -> dict[str, str]:
    state = hass.states.get(entity_id)
    return {
        "entity_id": entity_id,
        "name": getattr(state, "name", entity_id) if state is not None else entity_id,
    }


def _condition_summary(condition: object) -> str | None:
    if not isinstance(condition, Mapping):
        return None
    kind = str(condition.get("type", ""))
    if kind in {"and", "or"}:
        children = condition.get("conditions", [])
        count = len(children) if isinstance(children, list) else 0
        return f"{kind.upper()} · {count}"
    if kind == "not":
        return "NOT"
    if kind in {"state", "numeric"}:
        return f"{kind} · {condition.get('entity_id', '')}"
    if kind == "time":
        return f"{condition.get('after', '')}-{condition.get('before', '')}"
    return None


def _smart_rule_payload(
    hass: HomeAssistant,
    resolver: AdvancedTargetResolver,
    rule: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        resolved = resolver.resolve_rule(rule)
    except AdvancedTargetError as err:
        raise VisualEditorError(err.code, str(err)) from err
    raw = _mutable_json(rule)
    source = raw.get("source")
    if raw.get("type") == RULE_TYPE_EVENT:
        trigger = raw.get("trigger", {})
        platform = trigger.get("platform", "event") if isinstance(trigger, dict) else "event"
        source_detail = {"entity_id": "", "name": f"Evento · {platform}"}
    elif isinstance(source, str):
        source_detail = _friendly_entity(hass, source)
    else:
        source_detail = {"entity_id": "", "name": "—"}
    unit = None
    if raw.get("type") == RULE_TYPE_NUMERIC and isinstance(source, str):
        state = hass.states.get(source)
        candidate = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) if state else None
        unit = candidate if isinstance(candidate, str) and candidate else None
    return {
        "rule": raw,
        "source": source_detail,
        "unit": unit,
        "targets": [
            _friendly_entity(hass, entity_id) for entity_id in sorted(resolved.targets)
        ],
        "excluded": [
            _friendly_entity(hass, entity_id) for entity_id in sorted(resolved.excluded)
        ],
        "condition_summary": _condition_summary(raw.get("conditions")),
        "schedule_summary": _condition_summary(
            {"type": "time", **raw["schedule"]}
            if isinstance(raw.get("schedule"), dict)
            else None
        ),
    }


def _selection_catalog(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    zones = entry.options.get(CONF_ZONES, [])
    area_registry = ar.async_get(hass)
    label_registry = lr.async_get(hass)
    states = hass.states.async_all() if hasattr(hass.states, "async_all") else []
    groups = [
        _friendly_entity(hass, state.entity_id)
        for state in states
        if state.entity_id.startswith("light.")
        and isinstance(state.attributes.get(ATTR_ENTITY_ID), (list, tuple))
    ]
    return {
        "managed_lights": [
            _friendly_entity(hass, entity_id)
            for entity_id in sorted(_authorized_targets(entry))
        ],
        "zones": [
            {
                "id": str(zone.get("zone_id")),
                "name": str(zone.get("name", zone.get("zone_id"))),
            }
            for zone in zones
            if isinstance(zone, Mapping) and zone.get("zone_id")
        ],
        "areas": [
            {"id": area.id, "name": area.name}
            for area in sorted(area_registry.areas.values(), key=lambda item: item.name)
        ],
        "labels": [
            {"id": label.label_id, "name": label.name}
            for label in sorted(label_registry.labels.values(), key=lambda item: item.name)
        ],
        "groups": groups,
    }


async def _async_validate_rule_catalog(
    hass: HomeAssistant,
    entry: ConfigEntry,
    rules: list[dict[str, Any]],
) -> None:
    resolver = _advanced_target_resolver(hass, entry)
    for rule in rules:
        try:
            resolver.resolve_rule(rule)
        except AdvancedTargetError as err:
            raise VisualEditorError(err.code, str(err)) from err
        if rule.get("type") == RULE_TYPE_EVENT:
            from homeassistant.helpers import trigger as trigger_helper

            try:
                await trigger_helper.async_validate_trigger_config(
                    hass, [dict(rule["trigger"])]
                )
            except Exception as err:  # Home Assistant trigger validation boundary
                raise VisualEditorError("invalid_trigger", str(err)) from err


@websocket_api.websocket_command(
    {
        probatio.Required("type"): "smart_led_manager/smart_rules/get",
        probatio.Required("entry_id"): str,
    }
)
@websocket_api.require_admin
@callback
def websocket_get_smart_rules(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return one normalized catalog for every rule type."""

    try:
        entry = _entry(hass, msg["entry_id"])
        try:
            catalog = RuleCatalog(_configured_rules(entry)).snapshot()
        except (RuleValidationError, ValueError) as err:
            raise VisualEditorError(
                getattr(err, "code", "invalid_rule"), str(err)
            ) from err
        resolver = _advanced_target_resolver(hass, entry)
        payload = [
            _smart_rule_payload(hass, resolver, rule)
            for rule in catalog
        ]
        selections = _selection_catalog(hass, entry)
    except VisualEditorError as err:
        _send_editor_error(connection, msg["id"], err)
        return
    connection.send_result(
        msg["id"],
        {
            "entry_id": entry.entry_id,
            "revision": _options_revision(entry.options),
            "rules": payload,
            "selections": selections,
        },
    )


@websocket_api.websocket_command(
    {
        probatio.Required("type"): "smart_led_manager/smart_rules/mutate",
        probatio.Required("entry_id"): str,
        probatio.Required("revision"): str,
        probatio.Required("operation"): str,
        probatio.Optional("rule_id"): str,
        probatio.Optional("rule"): dict,
        probatio.Optional("enabled"): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_mutate_smart_rule(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Apply one validated CRUD mutation with optimistic concurrency."""

    try:
        lock: asyncio.Lock = hass.data[DOMAIN][_DATA_LOCK]
        async with lock:
            entry = _entry(hass, msg["entry_id"])
            if msg["revision"] != _options_revision(entry.options):
                raise VisualEditorError(
                    "conflict",
                    "Configuration changed in another session; reload before saving",
                )
            try:
                catalog = RuleCatalog(_configured_rules(entry))
                operation = msg["operation"]
                if operation == "create":
                    result = catalog.create(msg.get("rule", {}))
                elif operation == "update":
                    result = catalog.update(
                        str(msg.get("rule_id", "")), msg.get("rule", {})
                    )
                elif operation == "duplicate":
                    result = catalog.duplicate(str(msg.get("rule_id", "")))
                elif operation == "toggle":
                    result = catalog.toggle(
                        str(msg.get("rule_id", "")), bool(msg.get("enabled"))
                    )
                elif operation == "delete":
                    catalog.delete(str(msg.get("rule_id", "")))
                    result = None
                else:
                    raise RuleValidationError(
                        "invalid_operation", "unsupported rule operation"
                    )
                rules = catalog.snapshot()
            except (RuleValidationError, ValueError) as err:
                raise VisualEditorError(
                    getattr(err, "code", "invalid_rule"), str(err)
                ) from err
            await _async_validate_rule_catalog(hass, entry, rules)
            options = _mutable_json(entry.options)
            options[CONF_RULES] = rules
            hass.config_entries.async_update_entry(entry, options=options)
            revision = _options_revision(options)
    except VisualEditorError as err:
        _send_editor_error(connection, msg["id"], err)
        return
    except Exception:  # pragma: no cover - defensive HA transport boundary
        _LOGGER.exception("Unexpected smart-rule mutation failure")
        connection.send_error(
            msg["id"], "internal_error", "Unexpected error while saving the rule"
        )
        return
    connection.send_result(
        msg["id"],
        {"revision": revision, "rule": result, "rules": rules},
    )


@websocket_api.websocket_command(
    {
        probatio.Required("type"): "smart_led_manager/targets/preview",
        probatio.Required("entry_id"): str,
        probatio.Required("target_selection"): dict,
    }
)
@websocket_api.require_admin
@callback
def websocket_preview_targets(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Resolve a draft selection without changing intent or persistence."""

    try:
        entry = _entry(hass, msg["entry_id"])
        resolver = _advanced_target_resolver(hass, entry)
        try:
            resolved = resolver.resolve(msg["target_selection"])
        except AdvancedTargetError as err:
            raise VisualEditorError(err.code, str(err)) from err
    except VisualEditorError as err:
        _send_editor_error(connection, msg["id"], err)
        return
    connection.send_result(
        msg["id"],
        {
            "targets": [
                _friendly_entity(hass, entity_id)
                for entity_id in sorted(resolved.targets)
            ],
            "excluded": [
                _friendly_entity(hass, entity_id)
                for entity_id in sorted(resolved.excluded)
            ],
        },
    )
