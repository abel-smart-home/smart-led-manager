"""Adapt native Home Assistant selector values to the shared rule schema."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, override

from homeassistant.helpers.selector import StateSelector

from ..core.conditions import WEEKDAYS
from .rule_schema import RuleValidationError


class RuleStateSelector(StateSelector):
    """Bind the native state picker to the current source field."""

    @override
    def serialize(self) -> dict[str, Any]:
        return {**super().serialize(), "context": {"filter_entity": "source"}}


def _unsupported() -> RuleValidationError:
    return RuleValidationError(
        "unsupported_condition",
        "This condition cannot be represented by Smart LED Manager",
    )


def _single_string(value: object) -> str:
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if not isinstance(value, str):
        raise _unsupported()
    return value


def native_condition_tree(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Convert selected conditions without altering Smart LED semantics."""
    if not items:
        return None
    nodes = [_from_native(item) for item in items]
    return nodes[0] if len(nodes) == 1 else {"type": "and", "conditions": nodes}


def _from_native(item: Mapping[str, Any]) -> dict[str, Any]:
    kind = item.get("condition")
    keys = set(item) - {"condition", "alias"}
    if item.get("enabled") is True:
        keys.discard("enabled")
    if kind in {"and", "or", "not"} and keys == {"conditions"}:
        children = [_from_native(child) for child in item["conditions"]]
        if kind == "not" and len(children) == 1:
            return {"type": "not", "condition": children[0]}
        if kind != "not":
            return {"type": kind, "conditions": children}
    if kind == "state" and keys in (
        {"entity_id", "state"},
        {"entity_id", "state", "match"},
    ):
        return {
            "type": "state",
            "entity_id": _single_string(item["entity_id"]),
            "state": _single_string(item["state"]),
            "operator": "equals",
        }
    if kind == "numeric_state" and keys in (
        {"entity_id", "above"},
        {"entity_id", "below"},
    ):
        operator = "above" if "above" in keys else "below"
        return {
            "type": "numeric",
            "entity_id": _single_string(item["entity_id"]),
            "operator": operator,
            "threshold": item[operator],
        }
    if kind == "time" and keys <= {"after", "before", "weekday"}:
        days = item.get("weekday", list(WEEKDAYS))
        return {
            "type": "time",
            "after": _clock(item.get("after", "00:00")),
            "before": _clock(item.get("before", "00:00")),
            "weekdays": [days] if isinstance(days, str) else list(days),
        }
    raise _unsupported()


def _clock(value: object) -> str:
    if isinstance(value, str) and value.endswith(":00") and len(value) == 8:
        return value[:5]
    return str(value)


def native_condition_form(condition: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Represent a stored tree only when the native editor can round-trip it."""
    if not condition:
        return []
    kind = condition["type"]
    if kind in {"and", "or"}:
        return [
            {
                "condition": kind,
                "conditions": [
                    native_condition_form(child)[0] for child in condition["conditions"]
                ],
            }
        ]
    if kind == "not":
        return [
            {
                "condition": "not",
                "conditions": native_condition_form(condition["condition"]),
            }
        ]
    if kind == "state":
        leaf = {
            "condition": "state",
            "entity_id": condition["entity_id"],
            "state": condition["state"],
        }
        if condition.get("operator") == "not_equals":
            return [{"condition": "not", "conditions": [leaf]}]
        return [leaf]
    if kind == "numeric" and (operator := condition["operator"]) in {"above", "below"}:
        return [
            {
                "condition": "numeric_state",
                "entity_id": condition["entity_id"],
                operator: condition["threshold"],
            }
        ]
    if kind == "time":
        return [
            {
                "condition": "time",
                "after": condition["after"],
                "before": condition["before"],
                "weekday": condition["weekdays"],
            }
        ]
    raise _unsupported()


def native_trigger(value: object) -> dict[str, Any]:
    """Take a single native trigger and retain existing advanced parameters."""
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if not isinstance(value, Mapping):
        raise RuleValidationError("invalid_trigger", "Select exactly one trigger")
    definition = dict(value)
    if "trigger" in definition:
        definition["platform"] = definition.pop("trigger")
    return definition


def selector_clock(value: object) -> str:
    """Remove zero seconds from Home Assistant's time picker values."""
    return _clock(value)
