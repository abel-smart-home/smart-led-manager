"""Round-trip cases for the native visual selectors."""

import pytest

from custom_components.smart_led_manager.core.conditions import validate_condition_tree
from custom_components.smart_led_manager.modules.native_rule_controls import (
    native_condition_form,
    native_condition_tree,
    native_trigger,
    selector_clock,
)
from custom_components.smart_led_manager.modules.rule_schema import RuleValidationError


def test_nested_conditions_round_trip_without_changing_contract() -> None:
    conditions = [
        {
            "condition": "or",
            "conditions": [
                {
                    "condition": "state",
                    "entity_id": ["binary_sensor.door"],
                    "state": ["on"],
                },
                {"condition": "numeric_state", "entity_id": "sensor.room", "above": 28},
            ],
        },
        {
            "condition": "not",
            "conditions": [
                {"condition": "numeric_state", "entity_id": "sensor.room", "below": 10}
            ],
        },
        {"condition": "time", "after": "22:00:00", "before": "06:00", "weekday": "mon"},
    ]
    tree = validate_condition_tree(native_condition_tree(conditions))
    assert tree["type"] == "and"
    assert tree["conditions"][2]["weekdays"] == ["mon"]
    assert tree["conditions"][2]["after"] == "22:00"
    assert (
        validate_condition_tree(native_condition_tree(native_condition_form(tree)))
        == tree
    )
    assert native_condition_tree([]) is None
    assert native_condition_form(None) == []
    assert selector_clock("06:15:00") == "06:15"


@pytest.mark.parametrize(
    "condition",
    [
        {"condition": "template", "value_template": "{{ true }}"},
        {"condition": "state", "state": "on", "entity_id": ["light.a", "light.b"]},
        {
            "condition": "state",
            "state": "on",
            "entity_id": "light.a",
            "for": "00:00:10",
        },
        {
            "condition": "numeric_state",
            "above": 1,
            "below": 5,
            "entity_id": "sensor.temp",
        },
        {"condition": "not", "conditions": []},
    ],
)
def test_reject_native_shapes_that_would_change_semantics(condition) -> None:
    with pytest.raises(RuleValidationError, match="cannot be represented"):
        native_condition_tree([condition])


def test_not_equals_maps_to_negation_and_inside_is_preserved_for_panel() -> None:
    assert native_condition_form(
        {
            "type": "state",
            "operator": "not_equals",
            "entity_id": "light.a",
            "state": "on",
        }
    ) == [
        {
            "condition": "not",
            "conditions": [
                {"condition": "state", "entity_id": "light.a", "state": "on"}
            ],
        }
    ]
    with pytest.raises(RuleValidationError, match="cannot be represented"):
        native_condition_form({"type": "numeric", "operator": "inside"})


def test_native_trigger_preserves_advanced_details() -> None:
    trigger = {"trigger": "event", "event_type": "arrived", "event_data": {"code": 23}}
    assert native_trigger([trigger]) == {
        "platform": "event",
        "event_type": "arrived",
        "event_data": {"code": 23},
    }
    with pytest.raises(RuleValidationError, match="exactly one"):
        native_trigger([trigger, trigger])
