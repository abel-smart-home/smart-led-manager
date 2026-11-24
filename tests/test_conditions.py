"""Tests for pure advanced condition and threshold semantics."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from custom_components.smart_led_manager.core.conditions import (
    ConditionResult,
    ConditionValidationError,
    condition_entity_ids,
    condition_schedules,
    evaluate_condition,
    numeric_activation_matches,
    schedule_is_active,
    validate_condition_tree,
    validate_numeric_activation,
)


def _states(values: dict[str, str]):
    return lambda entity_id: (
        SimpleNamespace(state=values[entity_id]) if entity_id in values else None
    )


def test_nested_and_or_not_preserve_unknown() -> None:
    condition = validate_condition_tree(
        {
            "type": "and",
            "conditions": [
                {
                    "type": "or",
                    "conditions": [
                        {
                            "type": "state",
                            "entity_id": "binary_sensor.door",
                            "state": "on",
                        },
                        {
                            "type": "state",
                            "entity_id": "person.owner",
                            "state": "home",
                        },
                    ],
                },
                {
                    "type": "not",
                    "condition": {
                        "type": "state",
                        "entity_id": "binary_sensor.alarm",
                        "state": "on",
                    },
                },
            ],
        }
    )
    now = datetime(2026, 11, 23, 21, 0, tzinfo=ZoneInfo("America/Tijuana"))

    assert (
        evaluate_condition(
            condition,
            _states(
                {
                    "binary_sensor.door": "off",
                    "person.owner": "home",
                    "binary_sensor.alarm": "off",
                }
            ),
            now,
        )
        is ConditionResult.TRUE
    )
    assert (
        evaluate_condition(
            condition,
            _states(
                {
                    "binary_sensor.door": "off",
                    "person.owner": "home",
                    "binary_sensor.alarm": "unknown",
                }
            ),
            now,
        )
        is ConditionResult.UNKNOWN
    )


def test_schedule_uses_start_day_when_crossing_midnight() -> None:
    schedule = {
        "after": "22:00",
        "before": "06:00",
        "weekdays": ["mon"],
    }
    timezone = ZoneInfo("America/Tijuana")

    assert schedule_is_active(schedule, datetime(2026, 11, 23, 23, 0, tzinfo=timezone))
    assert schedule_is_active(schedule, datetime(2026, 11, 24, 5, 59, tzinfo=timezone))
    assert not schedule_is_active(
        schedule, datetime(2026, 11, 24, 22, 30, tzinfo=timezone)
    )


@pytest.mark.parametrize(
    ("policy", "sequence"),
    [
        (
            {"operator": "above", "threshold": 28, "hysteresis": 2},
            [False, True, True, False],
        ),
        (
            {"operator": "below", "threshold": 10, "hysteresis": 1},
            [False, True, True, False],
        ),
        (
            {"operator": "inside", "lower": 10, "upper": 20, "hysteresis": 2},
            [False, True, True, False],
        ),
        (
            {"operator": "outside", "lower": 10, "upper": 20, "hysteresis": 2},
            [False, True, True, False],
        ),
    ],
)
def test_numeric_hysteresis(policy: dict[str, object], sequence: list[bool]) -> None:
    activation = validate_numeric_activation(policy)
    values = {
        "above": [28, 29, 27, 25.9],
        "below": [10, 9, 10.5, 11.1],
        "inside": [9, 10, 9, 7.9],
        "outside": [10, 9, 11, 12],
    }[str(policy["operator"])]
    previous = False
    actual = []
    for value in values:
        previous = numeric_activation_matches(value, activation, previous=previous)
        actual.append(previous)
    assert actual == sequence


def test_condition_limits_and_invalid_numeric_values() -> None:
    nested: dict[str, object] = {
        "type": "state",
        "entity_id": "sensor.example",
        "state": "on",
    }
    for _ in range(6):
        nested = {"type": "not", "condition": nested}
    with pytest.raises(ConditionValidationError, match="deep"):
        validate_condition_tree(nested)
    with pytest.raises(ConditionValidationError, match="finite"):
        validate_numeric_activation({"operator": "above", "threshold": float("nan")})


@pytest.mark.parametrize(
    "value",
    [
        12,
        {"type": "and", "conditions": []},
        {"type": "not"},
        {"type": "state", "entity_id": "invalid", "state": "on"},
        {
            "type": "state",
            "entity_id": "switch.a",
            "operator": "contains",
            "state": "on",
        },
        {"type": "state", "entity_id": "switch.a", "state": False},
        {"type": "numeric", "entity_id": "", "threshold": 10},
        {"type": "numeric", "entity_id": "sensor.temp", "threshold": True},
        {"type": "time", "after": "22:00+02:00"},
        {"type": "time", "after": "invalid"},
        {"type": "time", "after": 22},
        {"type": "time", "weekdays": []},
        {"type": "time", "weekdays": ["holiday"]},
        {"type": "unsupported"},
        {
            "type": "or",
            "conditions": [
                {"type": "or", "conditions": [{"type": "time"}] * 16},
                {"type": "or", "conditions": [{"type": "time"}] * 16},
            ],
        },
    ],
)
def test_rejects_unsafe_or_malformed_visual_tree(value) -> None:
    with pytest.raises(ConditionValidationError):
        validate_condition_tree(value)


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("19", ConditionResult.TRUE),
        ("23", ConditionResult.FALSE),
        ("unknown", ConditionResult.UNKNOWN),
        ("unavailable", ConditionResult.UNKNOWN),
        ("NaN", ConditionResult.UNKNOWN),
        ("infinity", ConditionResult.UNKNOWN),
        ("garbage", ConditionResult.UNKNOWN),
    ],
)
def test_numeric_node_and_time_tree_use_secondary_sources(state, expected) -> None:
    tree = validate_condition_tree(
        {
            "type": "and",
            "conditions": [
                {
                    "type": "numeric",
                    "entity_id": "sensor.temp",
                    "operator": "below",
                    "threshold": 20,
                },
                {
                    "type": "time",
                    "after": "07:00",
                    "before": "20:00",
                    "weekdays": ["mon", "mon"],
                },
            ],
        }
    )
    local = datetime(2026, 11, 23, 8, tzinfo=ZoneInfo("America/Tijuana"))
    assert condition_entity_ids(tree) == frozenset({"sensor.temp"})
    assert condition_schedules(tree)[0]["weekdays"] == ["mon"]
    assert evaluate_condition(tree, _states({"sensor.temp": state}), local) is expected
    assert (
        evaluate_condition(tree, _states({}), local.replace(hour=21))
        is ConditionResult.FALSE
    )


@pytest.mark.parametrize(
    "value",
    [
        {"operator": "unknown", "threshold": 4},
        {"operator": "above", "threshold": "not a number"},
        {"operator": "below", "threshold": 4, "hysteresis": -1},
        {"operator": "inside", "lower": 4, "upper": 4},
        {"operator": "outside", "lower": 4, "upper": 5, "hysteresis": 0.5},
    ],
)
def test_rejects_out_of_contract_activation_values(value) -> None:
    with pytest.raises(ConditionValidationError):
        validate_numeric_activation(value)
