"""Administrator-only local visual editor for numeric color rules."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

import probatio
from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr

from .const import (
    CONF_LIGHTS,
    CONF_MODES,
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
from .modules.admin_configuration import (
    validate_managed_lights,
    validate_mode,
    validate_zone,
    validate_zone_removal,
)
from .modules.configuration import mutable_json, options_revision
from .modules.modes import ModeDefinition, ModeValidationError, ZoneDefinition
from .modules.rule_schema import RuleCatalog, RuleValidationError
from .modules.targeting import (
    AdvancedTargetError,
    AdvancedTargetResolver,
    is_aggregate_light,
)

_LOGGER = logging.getLogger(__name__)

PANEL_PATH = "smart-led-manager-editor"
STATIC_URL = "/smart_led_manager_frontend"
_FRONTEND_PATH = Path(__file__).parent / "frontend"

_DATA_COMMANDS = "visual_editor_commands_registered"
_DATA_LOCK = "visual_editor_save_lock"
_DATA_PANEL = "visual_editor_panel_registered"
_DATA_PANEL_ENTRY = "visual_editor_panel_entry"
_DATA_STATIC = "visual_editor_static_registered"
_DATA_RELOADING = "visual_editor_reloading"
_DATA_RELOAD_FAILURES = "visual_editor_reload_failures"
_DATA_RECEIPTS = "visual_editor_mutation_receipts"
_DATA_SIDEBAR = "visual_editor_sidebar"
_EVENT_ENTRY_STATUS = f"{DOMAIN}_editor_entry_status"
_MAX_MUTATION_RECEIPTS = 32
_PANEL_ASSETS_REVISION = "c2.2"

_TRANSITION_STATES = {
    ConfigEntryState.SETUP_IN_PROGRESS,
    ConfigEntryState.UNLOAD_IN_PROGRESS,
}


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
        websocket_api.async_register_command(hass, websocket_editor_status)
        websocket_api.async_register_command(hass, websocket_admin_get)
        websocket_api.async_register_command(hass, websocket_admin_mutate)
        websocket_api.async_register_command(hass, websocket_admin_mode)
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
    show_sidebar = entry.options.get(CONF_SHOW_SIDEBAR, DEFAULT_SHOW_SIDEBAR)
    if (
        domain_data.get(_DATA_PANEL)
        and domain_data.get(_DATA_PANEL_ENTRY) == entry.entry_id
    ):
        if domain_data.get(_DATA_SIDEBAR) != show_sidebar:
            existing = hass.data[frontend.DATA_PANELS][PANEL_PATH]
            frontend.async_register_built_in_panel(
                hass,
                "custom",
                sidebar_title=NAME if show_sidebar else None,
                sidebar_icon="mdi:led-strip-variant",
                frontend_url_path=PANEL_PATH,
                config=existing.config,
                require_admin=True,
                update=True,
            )
            domain_data[_DATA_SIDEBAR] = show_sidebar
        return
    if domain_data.get(_DATA_PANEL):
        frontend.async_remove_panel(hass, PANEL_PATH, warn_if_unknown=False)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_PATH,
        webcomponent_name="smart-led-manager-visual-editor",
        sidebar_title=(NAME if show_sidebar else None),
        sidebar_icon="mdi:led-strip-variant",
        module_url=(
            f"{STATIC_URL}/visual-editor-panel.mjs?v={VERSION}-{_PANEL_ASSETS_REVISION}"
        ),
        config={"entry_id": entry.entry_id, "version": VERSION},
        require_admin=True,
        handle_safe_area=True,
    )
    domain_data[_DATA_PANEL] = True
    domain_data[_DATA_PANEL_ENTRY] = entry.entry_id
    domain_data[_DATA_SIDEBAR] = show_sidebar


@callback
def async_remove_visual_editor_panel(
    hass: HomeAssistant, *, unloading_entry: str | None = None
) -> None:
    """Remove the visible panel when the config entry is unloaded."""

    domain_data = getattr(hass, "data", {}).get(DOMAIN, {})
    if not domain_data.get(_DATA_PANEL):
        return
    if unloading_entry and domain_data.get(_DATA_PANEL_ENTRY) != unloading_entry:
        return
    if unloading_entry and unloading_entry in domain_data.get(_DATA_RELOADING, set()):
        return
    frontend.async_remove_panel(hass, PANEL_PATH, warn_if_unknown=False)
    domain_data[_DATA_PANEL] = False
    domain_data.pop(_DATA_PANEL_ENTRY, None)
    domain_data.pop(_DATA_SIDEBAR, None)


@callback
def async_finish_visual_editor_unload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Let a native reload retain its route while a true unload removes it."""
    domain_data = hass.data.get(DOMAIN, {})
    if entry.entry_id in domain_data.get(_DATA_RELOADING, set()):
        return
    if not isinstance(entry, ConfigEntry) or entry.disabled_by:
        async_remove_visual_editor_panel(hass, unloading_entry=entry.entry_id)
        return
    if domain_data.get(_DATA_PANEL_ENTRY) != entry.entry_id:
        return

    _async_editor_status(hass, entry.entry_id, "reloading")

    async def finish() -> None:
        # Core holds this lock through both halves of a native reload.
        async with entry.setup_lock:
            if entry.state is ConfigEntryState.NOT_LOADED or entry.disabled_by:
                async_remove_visual_editor_panel(hass, unloading_entry=entry.entry_id)
            else:
                status = _editor_runtime_status(hass, entry)["status"]
                _async_editor_status(hass, entry.entry_id, status)

    hass.async_create_task(finish(), "Smart LED Manager editor unload completion")


@callback
def async_clear_visual_editor_state(hass: HomeAssistant, entry_id: str) -> None:
    """Forget in-memory editor acknowledgements for a removed entry."""
    domain_data = getattr(hass, "data", {}).get(DOMAIN, {})
    for key in (_DATA_RECEIPTS, _DATA_RELOAD_FAILURES):
        domain_data.get(key, {}).pop(entry_id, None)


@callback
def _async_editor_status(hass: HomeAssistant, entry_id: str, status: str) -> None:
    if hasattr(hass, "bus"):
        hass.bus.async_fire(
            _EVENT_ENTRY_STATUS, {"entry_id": entry_id, "status": status}
        )


async def async_reload_visual_editor_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Keep the route present while an options update reloads the runtime."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    reloading: set[str] = domain_data.setdefault(_DATA_RELOADING, set())
    if entry.entry_id in reloading:
        return
    failures: dict[str, str] = domain_data.setdefault(_DATA_RELOAD_FAILURES, {})
    failures.pop(entry.entry_id, None)
    reloading.add(entry.entry_id)
    _async_editor_status(hass, entry.entry_id, "reloading")
    loaded = False
    revision = options_revision(entry.options)
    try:
        # Options Flow can save a newer revision while a runtime is starting.
        for _ in range(3):
            loaded = await hass.config_entries.async_reload(entry.entry_id)
            if not loaded or getattr(entry, "disabled_by", None):
                break
            desired_revision = options_revision(entry.options)
            runtime = domain_data.get("entries", {}).get(entry.entry_id)
            applied_revision = (
                getattr(runtime, "options_revision", None)
                if isinstance(entry, ConfigEntry)
                else revision
            )
            if applied_revision == desired_revision:
                break
            revision = desired_revision
        else:
            loaded = False
            _LOGGER.error("Smart LED Manager options kept changing during reload")
    except Exception:
        loaded = False
        _LOGGER.exception("Failed to reload Smart LED Manager after updating options")
    finally:
        if not loaded:
            failures[entry.entry_id] = options_revision(entry.options)
        reloading.remove(entry.entry_id)
        if isinstance(entry, ConfigEntry):
            status = _editor_runtime_status(hass, entry)["status"]
        else:
            status = "ready" if loaded else "failed"
        _async_editor_status(hass, entry.entry_id, status)


_mutable_json = mutable_json
_options_revision = options_revision


def _editor_runtime_status(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Read the saved and runtime revisions even when normal commands are blocked."""
    data = hass.data.get(DOMAIN, {})
    runtime = data.get("entries", {}).get(entry.entry_id)
    revision = options_revision(entry.options)
    state = getattr(entry, "state", ConfigEntryState.LOADED)
    applied = (
        getattr(runtime, "options_revision", None)
        if state is ConfigEntryState.LOADED
        else None
    )
    if getattr(entry, "disabled_by", None):
        status = "disabled"
    elif entry.entry_id in data.get(_DATA_RELOADING, ()) or state in _TRANSITION_STATES:
        status = "reloading"
    elif (
        state is ConfigEntryState.LOADED and runtime is not None and applied == revision
    ):
        status = "ready"
    elif state is ConfigEntryState.NOT_LOADED:
        status = "reloading" if entry.setup_lock.locked() else "unloaded"
    elif (
        state is not ConfigEntryState.LOADED
        or data.get(_DATA_RELOAD_FAILURES, {}).get(entry.entry_id) == revision
    ):
        status = "failed"
    elif runtime is None:
        status = "unloaded"
    else:
        # async_update_entry has accepted options before the reload listener runs.
        status = "reloading"
    return {
        "status": status,
        "revision": revision,
        "applied_revision": applied,
        "entry_state": state.value,
    }


def _entry(
    hass: HomeAssistant, entry_id: str, *, revision: str | None = None
) -> ConfigEntry:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise VisualEditorError(
            "entry_not_found", "Smart LED Manager config entry was not found"
        )
    runtime = _editor_runtime_status(hass, entry)
    if revision is not None and runtime["revision"] != revision:
        raise VisualEditorError(
            "conflict", "Configuration changed in another session; reload before saving"
        )
    if runtime["status"] != "ready":
        raise VisualEditorError(
            "entry_not_loaded", "Smart LED Manager config entry is not loaded"
        )
    return entry


@websocket_api.websocket_command(
    {
        probatio.Required("type"): "smart_led_manager/editor/status",
        probatio.Required("entry_id"): str,
        probatio.Optional("mutation_id"): str,
    }
)
@websocket_api.require_admin
@callback
def websocket_editor_status(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Read the authoritative editor status without changing options or lights."""
    entry_id = msg["entry_id"]
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        connection.send_result(msg["id"], {"status": "missing"})
        return
    result = _editor_runtime_status(hass, entry)
    if mutation_id := msg.get("mutation_id"):
        receipts = hass.data.get(DOMAIN, {}).get(_DATA_RECEIPTS, {}).get(entry_id, {})
        receipt = receipts.get(mutation_id)
        result["mutation"] = receipt[1] if receipt is not None else None
    connection.send_result(msg["id"], result)


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
            entry = _entry(hass, msg["entry_id"], revision=msg["revision"])
            mode = _validated_mode(msg["mode"])
            points = _validated_points(msg["points"])
            current, _resolved_targets = _numeric_rule(hass, entry, msg["rule_id"])
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
            changed = hass.config_entries.async_update_entry(entry, options=options)
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
    connection.send_result(
        msg["id"],
        {"revision": revision, "rule": saved_rule, "reloading": changed is True},
    )


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
            audit=False,
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
        resolved = None
        target_error = str(err)
    else:
        target_error = None
    raw = _mutable_json(rule)
    source = raw.get("source")
    if raw.get("type") == RULE_TYPE_EVENT:
        trigger = raw.get("trigger", {})
        platform = (
            trigger.get("platform", "event") if isinstance(trigger, dict) else "event"
        )
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
            _friendly_entity(hass, entity_id)
            for entity_id in sorted(resolved.targets if resolved else ())
        ],
        "excluded": [
            _friendly_entity(hass, entity_id)
            for entity_id in sorted(resolved.excluded if resolved else ())
        ],
        "target_error": target_error,
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
    devices = []
    entities = []
    if isinstance(hass, HomeAssistant):
        entities = [
            {
                "entity_id": item.entity_id,
                "name": item.name or item.original_name or item.entity_id,
            }
            for item in er.async_get(hass).entities.values()
            if not item.disabled_by
        ]
        devices = [
            {"id": item.id, "name": item.name_by_user or item.name or item.id}
            for item in dr.async_get(hass).devices.values()
            if not item.disabled_by
        ]
    groups = [
        _friendly_entity(hass, state.entity_id)
        for state in states
        if state.entity_id.startswith("light.")
        and isinstance(state.attributes.get(ATTR_ENTITY_ID), (list, tuple))
    ]
    return {
        "entities": entities,
        "devices": devices,
        "managed_lights": [
            _friendly_entity(hass, entity_id)
            for entity_id in sorted(_authorized_targets(entry))
            if not is_aggregate_light(hass, entity_id)
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
            for label in sorted(
                label_registry.labels.values(), key=lambda item: item.name
            )
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
        payload = [_smart_rule_payload(hass, resolver, rule) for rule in catalog]
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
        probatio.Optional("mutation_id"): str,
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

    await _async_send_editor_mutation(hass, connection, msg, _async_prepare_rule_edit)


async def _async_prepare_rule_edit(hass, entry, msg):
    try:
        catalog = RuleCatalog(_configured_rules(entry))
        operation = msg["operation"]
        if operation == "create":
            result = catalog.create(msg.get("rule", {}))
        elif operation == "update":
            result = catalog.update(str(msg.get("rule_id", "")), msg.get("rule", {}))
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
            raise RuleValidationError("invalid_operation", "unsupported rule operation")
        rules = catalog.snapshot()
    except (RuleValidationError, ValueError) as err:
        raise VisualEditorError(getattr(err, "code", "invalid_rule"), str(err)) from err
    if (result is not None and operation in {"create", "update", "duplicate"}) or (
        result is not None and operation == "toggle" and result["enabled"]
    ):
        await _async_validate_rule_catalog(hass, entry, [result])
    return {CONF_RULES: rules}, {"rule": result}, {"rules": rules}


async def _async_send_editor_mutation(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    prepare: Callable[..., Awaitable[tuple[dict, dict, dict]]],
) -> None:
    """Write options once and issue a receipt subject to the runtime revision."""

    try:
        entry_id = msg["entry_id"]
        mutation_id = msg.get("mutation_id")
        if mutation_id is not None and not 1 <= len(mutation_id) <= 64:
            raise VisualEditorError(
                "invalid_mutation_id", "Invalid mutation identifier"
            )
        lock: asyncio.Lock = hass.data[DOMAIN][_DATA_LOCK]
        async with lock:
            receipts = None
            fingerprint = None
            if mutation_id:
                receipts = hass.data[DOMAIN].get(_DATA_RECEIPTS, {}).get(entry_id)
                fingerprint = options_revision(
                    {key: value for key, value in msg.items() if key != "id"}
                )
                if receipts is not None and (previous := receipts.get(mutation_id)):
                    if previous[0] != fingerprint:
                        raise VisualEditorError(
                            "conflict",
                            "Mutation identifier already used for another edit",
                        )
                    connection.send_result(msg["id"], previous[1])
                    return
            entry = _entry(hass, entry_id, revision=msg["revision"])
            updates, result, additional = await prepare(hass, entry, msg)
            entry = _entry(hass, entry_id, revision=msg["revision"])
            options = _mutable_json(entry.options)
            options.update(updates)
            changed = hass.config_entries.async_update_entry(entry, options=options)
            revision = _options_revision(options)
            receipt = {
                "revision": revision,
                **result,
                "reloading": changed is True,
            }
            if mutation_id is not None:
                receipts = (
                    hass.data[DOMAIN]
                    .setdefault(_DATA_RECEIPTS, {})
                    .setdefault(entry_id, {})
                )
                receipts[mutation_id] = (fingerprint, receipt)
                if len(receipts) > _MAX_MUTATION_RECEIPTS:
                    del receipts[next(iter(receipts))]
    except ModeValidationError as err:
        connection.send_error(msg["id"], err.key, str(err))
        return
    except VisualEditorError as err:
        _send_editor_error(connection, msg["id"], err)
        return
    except Exception:  # pragma: no cover - defensive HA transport boundary
        _LOGGER.exception("Unexpected editor mutation failure")
        connection.send_error(
            msg["id"], "internal_error", "Unexpected error while saving configuration"
        )
        return
    connection.send_result(msg["id"], {**receipt, **additional})


def _configured_definitions(entry: ConfigEntry, key: str) -> list[dict[str, Any]]:
    definitions = entry.options.get(key, [])
    if not isinstance(definitions, list) or not all(
        isinstance(item, Mapping) for item in definitions
    ):
        raise VisualEditorError("invalid_options", f"Configured {key} are invalid")
    return _mutable_json(definitions)


def _available_lights(
    hass: HomeAssistant, managed: frozenset[str]
) -> list[dict[str, Any]]:
    """List compatible light entities and retain references to offline managed lights."""
    entities = managed.union(
        state.entity_id for state in hass.states.async_all("light")
    )
    return sorted(
        (
            _friendly_entity(hass, entity_id)
            for entity_id in entities
            if not is_aggregate_light(hass, entity_id)
        ),
        key=lambda item: (item["name"].casefold(), item["entity_id"]),
    )


@websocket_api.websocket_command(
    {
        probatio.Required("type"): "smart_led_manager/admin/get",
        probatio.Required("entry_id"): str,
    }
)
@websocket_api.require_admin
@callback
def websocket_admin_get(hass, connection, msg) -> None:
    """Read configuration and effective modes from the single loaded entry."""
    try:
        entry = _entry(hass, msg["entry_id"])
        managed = _authorized_targets(entry)
        runtime = hass.data[DOMAIN]["entries"][entry.entry_id]
        snapshot = runtime.mode_snapshot()
        areas = ar.async_get(hass).areas.values()
        payload = {
            "revision": runtime.options_revision,
            "admin": {
                "managed": sorted(managed),
                "lights": _available_lights(hass, managed),
                "areas": [
                    {"id": area.id, "name": area.name}
                    for area in sorted(areas, key=lambda item: item.name.casefold())
                ],
                "zones": [
                    ZoneDefinition.from_dict(row).to_dict()
                    for row in _configured_definitions(entry, CONF_ZONES)
                ],
                "modes": [
                    ModeDefinition.from_dict(row).to_dict()
                    for row in _configured_definitions(entry, CONF_MODES)
                ],
                "status": snapshot["status"],
                "available": sorted(
                    light
                    for light in managed
                    if (state := hass.states.get(light)) is not None
                    and state.state not in ("unknown", "unavailable")
                ),
            },
        }
    except VisualEditorError as err:
        _send_editor_error(connection, msg["id"], err)
        return
    except ModeValidationError as err:
        connection.send_error(msg["id"], err.key, str(err))
        return
    connection.send_result(msg["id"], payload)


@websocket_api.websocket_command(
    {
        probatio.Required("type"): "smart_led_manager/admin/mutate",
        probatio.Required("entry_id"): str,
        probatio.Required("revision"): str,
        probatio.Required("kind"): str,
        probatio.Required("operation"): str,
        probatio.Optional("mutation_id"): str,
        probatio.Optional("item_id"): str,
        probatio.Optional("item"): dict,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_admin_mutate(hass, connection, msg) -> None:
    """Save one administration change with the editor's revision protocol."""
    await _async_send_editor_mutation(hass, connection, msg, _async_prepare_admin_edit)


async def _async_prepare_admin_edit(hass, entry, msg):
    kind = msg["kind"]
    operation = msg["operation"]
    item = msg.get("item", {})
    managed = _authorized_targets(entry)
    zones = _configured_definitions(entry, CONF_ZONES)
    modes = _configured_definitions(entry, CONF_MODES)
    if kind == "lights" and operation == "save":
        lights = validate_managed_lights(
            hass, managed, item.get("targets"), zones, _configured_rules(entry)
        )
        choices = {light["entity_id"] for light in _available_lights(hass, managed)}
        if set(lights).difference(managed, choices):
            raise ModeValidationError("light_not_available")
        return {CONF_LIGHTS: lights}, {"item": {"targets": lights}}, {}

    if kind not in {"zone", "mode"} or operation not in {"create", "update", "delete"}:
        raise VisualEditorError(
            "invalid_operation", "Unsupported administration operation"
        )

    id_key = f"{kind}_id"
    key, definitions = (CONF_ZONES, zones) if kind == "zone" else (CONF_MODES, modes)
    item_id = uuid4().hex if operation == "create" else msg.get("item_id")
    existing = next((row for row in definitions if row.get(id_key) == item_id), None)
    if operation != "create" and existing is None:
        raise ModeValidationError(f"{kind}_not_found")
    remaining = [row for row in definitions if row is not existing]
    if operation == "delete":
        if kind == "zone":
            validate_zone_removal(item_id, modes, _configured_rules(entry))
        return {key: remaining}, {"item": None}, {}

    data = {**(existing or {}), **item, id_key: item_id}
    if kind == "zone":
        parsed = ZoneDefinition.from_dict(data)
        validate_zone(hass, parsed, managed, zones, modes)
    else:
        parsed = ModeDefinition.from_dict(data)
        validate_mode(parsed, zones, modes)
        if parsed.transition is not None and not 0 <= parsed.transition <= 300:
            raise ModeValidationError("invalid_mode")
        if existing is not None and existing["zone_id"] != parsed.zone_id:
            runtime = hass.data[DOMAIN]["entries"][entry.entry_id]
            if runtime.modes.is_selected(item_id):
                raise ModeValidationError("deactivate_before_move")
    saved = {**(existing or {}), **parsed.to_dict()}
    result = [saved if row is existing else row for row in definitions]
    if existing is None:
        result.append(saved)
    return {key: result}, {"item": saved}, {}


@websocket_api.websocket_command(
    {
        probatio.Required("type"): "smart_led_manager/admin/mode",
        probatio.Required("entry_id"): str,
        probatio.Required("revision"): str,
        probatio.Required("mode_id"): str,
        probatio.Required("active"): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_admin_mode(hass, connection, msg) -> None:
    """Activate or clear a mode through the existing exclusive coordinator."""
    try:
        async with hass.data[DOMAIN][_DATA_LOCK]:
            entry = _entry(hass, msg["entry_id"], revision=msg["revision"])
            runtime = hass.data[DOMAIN]["entries"][entry.entry_id]
            action = (
                runtime.async_activate_mode
                if msg["active"]
                else runtime.async_deactivate_mode
            )
            await action(msg["mode_id"])
            status = runtime.mode_snapshot()["status"]
    except VisualEditorError as err:
        _send_editor_error(connection, msg["id"], err)
        return
    except ModeValidationError as err:
        connection.send_error(msg["id"], err.key, str(err))
        return
    connection.send_result(msg["id"], {"status": status})


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
            "duplicates": [
                _friendly_entity(hass, entity_id)
                for entity_id in sorted(resolved.duplicates)
            ],
        },
    )
