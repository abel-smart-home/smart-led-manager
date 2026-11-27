"""Tests for authorization-first advanced target expansion."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import State

from custom_components.smart_led_manager.modules.admin_configuration import (
    validate_managed_lights,
)
from custom_components.smart_led_manager.modules.modes import ModeValidationError
from custom_components.smart_led_manager.modules.targeting import (
    AdvancedTargetError,
    AdvancedTargetResolver,
)


class _States:
    def __init__(self, states: dict[str, State]) -> None:
        self._states = states

    def get(self, entity_id: str):
        return self._states.get(entity_id)


def _hass(states: dict[str, State] | None = None):
    return SimpleNamespace(states=_States(states or {}))


def test_individual_zone_all_managed_and_overlap_are_deduplicated() -> None:
    resolver = AdvancedTargetResolver(
        _hass(),
        ["light.one", "light.two"],
        [{"zone_id": "living", "targets": ["light.one"]}],
    )

    resolved = resolver.resolve(
        {
            "entities": ["light.one"],
            "zones": ["living"],
            "areas": [],
            "labels": [],
            "groups": [],
            "all_managed": True,
        }
    )

    assert resolved.targets == frozenset({"light.one", "light.two"})


def test_nested_group_expands_and_cycle_or_unsafe_member_is_rejected() -> None:
    states = {
        "light.group_a": State(
            "light.group_a", "on", {ATTR_ENTITY_ID: ["light.one", "light.group_b"]}
        ),
        "light.group_b": State("light.group_b", "on", {ATTR_ENTITY_ID: ["light.two"]}),
        "light.one": State("light.one", "on"),
        "light.two": State("light.two", "unavailable"),
    }
    resolver = AdvancedTargetResolver(_hass(states), ["light.one", "light.two"], [])
    selection = {
        "entities": [],
        "zones": [],
        "areas": [],
        "labels": [],
        "groups": ["light.group_a"],
        "all_managed": False,
    }

    assert resolver.resolve(selection).targets == frozenset({"light.one", "light.two"})

    states.pop("light.two")
    with pytest.raises(AdvancedTargetError, match=r"unsafe member light\.two"):
        resolver.resolve(selection)

    states["light.group_b"] = State(
        "light.group_b", "on", {ATTR_ENTITY_ID: ["light.group_a"]}
    )
    with pytest.raises(AdvancedTargetError, match="cycle"):
        resolver.resolve(selection)

    states["light.group_b"] = State(
        "light.group_b", "on", {ATTR_ENTITY_ID: ["light.not_managed"]}
    )
    with pytest.raises(AdvancedTargetError, match="unsafe"):
        resolver.resolve(selection)


def test_opaque_empty_and_authorized_group_are_rejected() -> None:
    with pytest.raises(AdvancedTargetError, match="group, not a physical light"):
        AdvancedTargetResolver(
            _hass(
                {
                    "light.managed_group": State(
                        "light.managed_group",
                        "on",
                        {ATTR_ENTITY_ID: ["light.one"]},
                    )
                }
            ),
            ["light.managed_group"],
            [],
        )

    resolver = AdvancedTargetResolver(_hass(), ["light.one"], [])
    with pytest.raises(AdvancedTargetError, match="transparent"):
        resolver.resolve(
            {
                "entities": [],
                "zones": [],
                "areas": [],
                "labels": [],
                "groups": ["light.opaque"],
                "all_managed": False,
            }
        )
    with pytest.raises(AdvancedTargetError, match="at least one"):
        resolver.resolve({})


def test_area_and_label_filter_to_managed_and_report_exclusions() -> None:
    resolver = AdvancedTargetResolver(_hass(), ["light.one", "light.two"], [])
    area_registry = SimpleNamespace(areas={"living": object()})
    label_registry = SimpleNamespace(labels={"accent": object()})
    with (
        patch(
            "custom_components.smart_led_manager.modules.targeting.ar.async_get",
            return_value=area_registry,
        ),
        patch(
            "custom_components.smart_led_manager.modules.targeting.lr.async_get",
            return_value=label_registry,
        ),
        patch.object(
            resolver,
            "_registry_entities",
            side_effect=[
                {"light.one", "light.outside"},
                {"light.two", "light.outside_two"},
            ],
        ),
    ):
        resolved = resolver.resolve(
            {
                "entities": [],
                "zones": [],
                "areas": ["living"],
                "labels": ["accent"],
                "groups": [],
                "all_managed": False,
            }
        )

    assert resolved.targets == frozenset({"light.one", "light.two"})
    assert resolved.excluded == frozenset({"light.outside", "light.outside_two"})


def test_removal_protects_partial_area_dependencies_but_all_managed_can_shrink() -> (
    None
):
    hass = _hass()
    current = ["light.one", "light.two"]
    remaining = ["light.two"]
    rule = {"target_selection": {"areas": ["living"], "all_managed": True}}
    with (
        patch(
            "custom_components.smart_led_manager.modules.targeting.ar.async_get",
            return_value=SimpleNamespace(areas={"living": object()}),
        ),
        patch.object(
            AdvancedTargetResolver, "_registry_entities", return_value=set(current)
        ),
        pytest.raises(ModeValidationError, match="rules_use_removed_lights"),
    ):
        validate_managed_lights(hass, current, remaining, [], [rule])

    rule["target_selection"].pop("areas")
    assert validate_managed_lights(hass, current, remaining, [], [rule]) == remaining
