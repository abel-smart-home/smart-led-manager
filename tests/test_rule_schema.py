"""Tests for the shared rule catalog used by both administration surfaces."""

from __future__ import annotations

import pytest
from homeassistant.core import State

from custom_components.smart_led_manager.modules.rule_schema import (
    RuleCatalog,
    RuleValidationError,
    normalize_rule,
)
from custom_components.smart_led_manager.modules.rule_templates import (
    source_template,
    template_source_error,
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


def test_source_free_schedule_and_notice_share_the_catalog() -> None:
    targets = ["light.one"]
    schedule = {"after": "22:00", "before": "06:00", "weekdays": ["mon"]}
    plan = {"id": "plan", "name": "Night", "type": "continuous", "targets": targets}
    saved = normalize_rule({**plan, "schedule": schedule})
    assert "source" not in saved
    assert saved["schedule"]["weekdays"] == ["mon"]
    with pytest.raises(RuleValidationError, match="Start and end"):
        normalize_rule({**plan, "schedule": {**schedule, "before": "22:00"}})
    with pytest.raises(RuleValidationError, match="Add conditions"):
        normalize_rule(plan)
    notice = normalize_rule({**plan, "type": "notice", "duration": 15})
    catalog = RuleCatalog([saved, notice | {"id": "notice"}])
    duplicate = catalog.duplicate("notice")
    assert duplicate["id"] != "notice"
    assert duplicate["enabled"] is False and duplicate["duration"] == 15


def test_optional_state_delay_preserves_legacy_shape_and_duplicate() -> None:
    assert "release_seconds" not in normalize_rule(_state_rule())
    raw = {
        **_state_rule(),
        "category": "security",
        "release_seconds": 12,
        "for_seconds": 3,
    }
    duplicate = RuleCatalog([raw]).duplicate("door")
    assert duplicate["release_seconds"] == 12 and duplicate["for_seconds"] == 3
    with pytest.raises(RuleValidationError, match="below its minimum"):
        normalize_rule({**raw, "release_seconds": -1})
    with pytest.raises(RuleValidationError, match="only supported for state"):
        normalize_rule({**raw, "type": "event"})


@pytest.mark.parametrize(
    ("device_class", "unit", "expected"),
    [
        ("power", "W", "power"),
        ("power", "Wh", None),
        ("energy", "kWh", "energy"),
        ("energy", "kW", None),
        ("temperature", "°F", "temperature"),
        ("humidity", "%", "humidity"),
    ],
)
def test_template_sources_require_exact_class_and_unit(
    device_class, unit, expected
) -> None:
    state = State(
        "sensor.demo",
        "unavailable",
        {"device_class": device_class, "unit_of_measurement": unit},
    )
    assert source_template(state) == expected


def test_numeric_calibration_refuses_a_different_live_unit() -> None:
    raw = {
        **_state_rule(),
        "source": "sensor.demo",
        "type": "numeric",
        "category": "power",
        "source_unit": "W",
        "points": [
            {"value": 0, "rgb": [0, 0, 255]},
            {"value": 400, "rgb": [255, 0, 0]},
        ],
    }
    normalized = normalize_rule(raw)
    live = State(
        "sensor.demo", "1", {"device_class": "power", "unit_of_measurement": "kW"}
    )
    assert template_source_error(live, normalized) == "rule_unit_changed"
    assert normalized["points"][1]["value"] == 400
    with pytest.raises(RuleValidationError, match="incompatible rule unit"):
        normalize_rule({**raw, "source_unit": "Wh"})
