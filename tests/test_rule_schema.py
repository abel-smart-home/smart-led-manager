"""Tests for the shared rule catalog used by both administration surfaces."""

from __future__ import annotations

import pytest

from custom_components.smart_led_manager.modules.rule_schema import (
    RuleCatalog,
    RuleValidationError,
    normalize_rule,
)


def _state_rule() -> dict[str, object]:
    return {
        "id": "door",
        "name": "Door",
        "type": "state",
        "source": "binary_sensor.door",
        "operator": "equals",
        "state": "on",
        "targets": ["light.one"],
        "rgb_color": [255, 0, 0],
    }


def test_catalog_crud_preserves_update_id_and_duplicates_safely() -> None:
    catalog = RuleCatalog([_state_rule()])
    updated = catalog.update("door", {**_state_rule(), "name": "Open door"})
    duplicate = catalog.duplicate("door")

    assert updated["id"] == "door"
    assert duplicate["id"] != "door"
    assert duplicate["enabled"] is False
    assert duplicate["name"].endswith("(2)")
    assert catalog.toggle("door", False)["enabled"] is False
    catalog.delete("door")
    assert [rule["id"] for rule in catalog.snapshot()] == [duplicate["id"]]


def test_advanced_targets_conditions_and_hysteresis_are_normalized() -> None:
    rule = normalize_rule(
        {
            **_state_rule(),
            "target_selection": {
                "entities": ["light.one", "light.one"],
                "zones": ["living"],
                "areas": [],
                "labels": [],
                "groups": [],
                "all_managed": False,
            },
            "conditions": {
                "type": "numeric",
                "entity_id": "sensor.temperature",
                "operator": "above",
                "threshold": 28,
                "hysteresis": 2,
            },
        }
    )

    assert rule["target_selection"]["entities"] == ["light.one"]
    assert rule["conditions"]["threshold"] == 28.0


def test_event_rule_requires_duration_and_cannot_replay_after_dwell() -> None:
    event = {
        "id": "button",
        "name": "Button",
        "type": "event",
        "trigger": {"platform": "event", "event_type": "demo"},
        "targets": ["light.one"],
        "rgb_color": [255, 128, 0],
        "duration": 8,
    }
    normalized = normalize_rule(event)
    assert normalized["duration"] == 8.0
    with pytest.raises(RuleValidationError, match="consumed event"):
        normalize_rule({**event, "for_seconds": 1})


def test_invalid_color_and_empty_targets_have_stable_error_codes() -> None:
    with pytest.raises(RuleValidationError) as color:
        normalize_rule({**_state_rule(), "rgb_color": [999, 0, 0]})
    assert color.value.code == "invalid_color"
    with pytest.raises(RuleValidationError) as targets:
        normalize_rule({**_state_rule(), "targets": []})
    assert targets.value.code == "empty_targets"
