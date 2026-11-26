"""Shared rule normalization and catalog mutations for every UI surface."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from math import isfinite
from typing import Any
from uuid import uuid4

from ..const import RULE_TYPE_EVENT, RULE_TYPE_NUMERIC, RULE_TYPE_STATE
from ..core.color import normalize_color_points
from ..core.conditions import (
    ConditionValidationError,
    validate_condition_tree,
    validate_numeric_activation,
)
from ..models import validate_rgb
from .configuration import mutable_json
from .rule_templates import NUMERIC_TEMPLATES, STATE_TEMPLATES
from .targeting import normalize_target_definition


class RuleValidationError(ValueError):
    """One rule or catalog mutation is invalid."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _number(
    value: object,
    field: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool):
        raise RuleValidationError("invalid_rule", f"{field} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as err:
        raise RuleValidationError("invalid_rule", f"{field} must be numeric") from err
    if not isfinite(result):
        raise RuleValidationError("invalid_rule", f"{field} must be finite")
    if minimum is not None and result < minimum:
        raise RuleValidationError("invalid_rule", f"{field} is below its minimum")
    if maximum is not None and result > maximum:
        raise RuleValidationError("invalid_rule", f"{field} is above its maximum")
    return result


def normalize_rule(
    raw: Mapping[str, Any], *, rule_id: str | None = None
) -> dict[str, Any]:
    """Return a JSON-safe rule while preserving compatible extension fields."""

    rule = mutable_json(raw)
    identity = rule_id or rule.get("id")
    if not isinstance(identity, str) or not identity.strip():
        raise RuleValidationError("invalid_rule", "rule id is required")
    name = rule.get("name")
    if not isinstance(name, str) or not name.strip():
        raise RuleValidationError("invalid_rule", "rule name is required")
    kind = str(rule.get("type", ""))
    if kind not in {RULE_TYPE_STATE, RULE_TYPE_NUMERIC, RULE_TYPE_EVENT}:
        raise RuleValidationError("invalid_rule", "unsupported rule type")
    rule["id"] = identity.strip()
    rule["name"] = name.strip()
    rule["type"] = kind
    rule["enabled"] = rule.get("enabled", True) is not False

    priority = _number(rule.get("priority", 40), "priority", minimum=0, maximum=100)
    rule["priority"] = int(priority)
    brightness = _number(
        rule.get("brightness", 255), "brightness", minimum=1, maximum=255
    )
    rule["brightness"] = int(brightness)
    rule["transition"] = _number(
        rule.get("transition", 0), "transition", minimum=0, maximum=300
    )
    rule["for_seconds"] = _number(
        rule.get("for_seconds", 0), "for_seconds", minimum=0, maximum=604800
    )
    if "release_seconds" in rule:
        delay = _number(
            rule["release_seconds"], "release_seconds", minimum=0, maximum=604800
        )
        if delay and kind != RULE_TYPE_STATE:
            raise RuleValidationError(
                "invalid_rule", "release delay is only supported for state rules"
            )
        rule["release_seconds"] = delay

    categories = (
        STATE_TEMPLATES
        if kind == RULE_TYPE_STATE
        else NUMERIC_TEMPLATES
        if kind == RULE_TYPE_NUMERIC
        else ()
    )
    if (category := rule.get("category")) is not None and (
        not isinstance(category, str) or category not in categories
    ):
        raise RuleValidationError("invalid_rule", "incompatible rule category")
    if "source_unit" in rule:
        unit = rule["source_unit"]
        if (
            kind != RULE_TYPE_NUMERIC
            or not isinstance(unit, str)
            or not unit
            or (
                category in NUMERIC_TEMPLATES
                and unit not in NUMERIC_TEMPLATES[category]
            )
        ):
            raise RuleValidationError("rule_unit_changed", "incompatible rule unit")
    elif category in NUMERIC_TEMPLATES:
        raise RuleValidationError(
            "rule_unit_changed", "a numeric template requires a source unit"
        )

    if "target_selection" in rule:
        rule["target_selection"] = normalize_target_definition(rule["target_selection"])
    else:
        legacy = rule.get("targets")
        if not isinstance(legacy, list) or not legacy:
            raise RuleValidationError("empty_targets", "rule needs targets")
        if not all(isinstance(item, str) and item for item in legacy):
            raise RuleValidationError("invalid_targets", "legacy targets are invalid")
        rule["targets"] = list(dict.fromkeys(legacy))

    try:
        rule["conditions"] = validate_condition_tree(rule.get("conditions"))
        if schedule := rule.get("schedule"):
            rule["schedule"] = validate_condition_tree({"type": "time", **schedule})
        elif "schedule" in rule:
            rule["schedule"] = None
    except ConditionValidationError as err:
        raise RuleValidationError("invalid_conditions", str(err)) from err

    animation = str(rule.get("animation", "fixed"))
    if animation not in {"fixed", "blink", "pulse"}:
        raise RuleValidationError("invalid_rule", "unsupported animation")
    rule["animation"] = animation
    rule["period"] = _number(rule.get("period", 1), "period", minimum=0.1, maximum=3600)

    if kind in {RULE_TYPE_STATE, RULE_TYPE_NUMERIC}:
        source = rule.get("source")
        if not isinstance(source, str) or "." not in source:
            raise RuleValidationError("invalid_rule", "source entity is required")
    if kind == RULE_TYPE_STATE:
        operator = str(rule.get("operator", "equals"))
        if operator not in {"equals", "not_equals"}:
            raise RuleValidationError("invalid_rule", "invalid state operator")
        if not isinstance(rule.get("state"), str):
            raise RuleValidationError("invalid_rule", "expected state is required")
        rule["operator"] = operator
        try:
            rule["rgb_color"] = list(
                validate_rgb(rule.get("rgb_color", [255, 255, 255]))
            )
        except ValueError as err:
            raise RuleValidationError("invalid_color", str(err)) from err
    elif kind == RULE_TYPE_NUMERIC:
        rule["minimum_change"] = _number(
            rule.get("minimum_change", 0), "minimum_change", minimum=0
        )
        rule["minimum_interval"] = _number(
            rule.get("minimum_interval", 0), "minimum_interval", minimum=0
        )
        mode = str(rule.get("mode", "interpolate"))
        if mode not in {"interpolate", "ranges"}:
            raise RuleValidationError("invalid_rule", "invalid numeric color mode")
        rule["mode"] = mode
        if rule.get("points"):
            try:
                rule["points"] = normalize_color_points(rule["points"])
            except ValueError as err:
                raise RuleValidationError("invalid_points", str(err)) from err
        elif rule.get("rgb_color") is not None:
            try:
                rule["rgb_color"] = list(validate_rgb(rule["rgb_color"]))
            except ValueError as err:
                raise RuleValidationError("invalid_color", str(err)) from err
        else:
            raise RuleValidationError(
                "invalid_rule", "numeric rule needs color points or a fixed color"
            )
        activation = rule.get("activation")
        if activation is not None:
            if not isinstance(activation, Mapping):
                raise RuleValidationError(
                    "invalid_rule", "activation must be an object"
                )
            try:
                rule["activation"] = validate_numeric_activation(activation)
            except ConditionValidationError as err:
                raise RuleValidationError("invalid_rule", str(err)) from err
    else:
        if rule["for_seconds"]:
            raise RuleValidationError(
                "invalid_rule",
                "event rules cannot defer an already consumed event",
            )
        trigger = rule.get("trigger")
        if not isinstance(trigger, Mapping) or not isinstance(
            trigger.get("platform"), str
        ):
            raise RuleValidationError("invalid_trigger", "event rule needs a trigger")
        rule["trigger"] = mutable_json(trigger)
        rule["duration"] = _number(
            rule.get("duration", 5), "duration", minimum=0.1, maximum=86400
        )
        try:
            rule["rgb_color"] = list(
                validate_rgb(rule.get("rgb_color", [255, 255, 255]))
            )
        except ValueError as err:
            raise RuleValidationError("invalid_color", str(err)) from err
    return rule


class RuleCatalog:
    """Apply CRUD mutations with one validator and stable identifiers."""

    def __init__(self, rules: list[Mapping[str, Any]]) -> None:
        self._rules = [normalize_rule(rule) for rule in rules]
        identities = [rule["id"] for rule in self._rules]
        if len(identities) != len(set(identities)):
            raise RuleValidationError("duplicate_rule", "rule ids must be unique")

    def snapshot(self) -> list[dict[str, Any]]:
        return deepcopy(self._rules)

    def create(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        rule = normalize_rule(raw, rule_id=uuid4().hex)
        self._rules.append(rule)
        return deepcopy(rule)

    def update(self, rule_id: str, raw: Mapping[str, Any]) -> dict[str, Any]:
        index = self._index(rule_id)
        rule = normalize_rule(raw, rule_id=rule_id)
        self._rules[index] = rule
        return deepcopy(rule)

    def duplicate(self, rule_id: str) -> dict[str, Any]:
        source = deepcopy(self._rules[self._index(rule_id)])
        source["name"] = f"{source['name']} (2)"
        source["enabled"] = False
        duplicate = normalize_rule(source, rule_id=uuid4().hex)
        self._rules.append(duplicate)
        return deepcopy(duplicate)

    def toggle(self, rule_id: str, enabled: bool) -> dict[str, Any]:
        index = self._index(rule_id)
        self._rules[index]["enabled"] = bool(enabled)
        return deepcopy(self._rules[index])

    def delete(self, rule_id: str) -> None:
        del self._rules[self._index(rule_id)]

    def _index(self, rule_id: str) -> int:
        try:
            return next(
                index for index, rule in enumerate(self._rules) if rule["id"] == rule_id
            )
        except StopIteration as err:
            raise RuleValidationError("rule_not_found", "rule was not found") from err
