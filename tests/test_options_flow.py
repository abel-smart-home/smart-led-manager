"""Direct unit coverage for the native options-flow lifecycle."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from homeassistant.data_entry_flow import FlowResultType

from custom_components.smart_led_manager.config_flow import (
    SmartLEDManagerOptionsFlow,
)
from custom_components.smart_led_manager.const import (
    CONF_AREA_ID,
    CONF_LIGHTS,
    CONF_MODES,
    CONF_RULES,
    CONF_ZONES,
)


class _ConfigEntries:
    def __init__(self, entry) -> None:
        self.entry = entry

    def async_get_known_entry(self, entry_id: str):
        assert entry_id == "entry-1"
        return self.entry


def _flow(
    *,
    options: dict[str, object] | None = None,
    lights: list[str] | None = None,
) -> tuple[SmartLEDManagerOptionsFlow, SimpleNamespace]:
    entry = SimpleNamespace(
        data={CONF_LIGHTS: lights or ["light.one", "light.two"]},
        options=options or {},
    )
    flow = SmartLEDManagerOptionsFlow()
    flow.hass = SimpleNamespace(config_entries=_ConfigEntries(entry))
    flow.handler = "entry-1"
    return flow, entry


def _zone() -> dict[str, object]:
    return {
        "zone_id": "living",
        "name": "Sala",
        "targets": ["light.one", "light.two"],
    }


def _mode() -> dict[str, object]:
    return {
        "mode_id": "blue",
        "zone_id": "living",
        "name": "Azul",
        "targets": ["light.one"],
        "priority": 50,
        "rgb_color": [0, 0, 255],
        "brightness": 180,
        "transition": 1,
        "allow_turn_on": True,
        "animation": "fixed",
        "period": 1,
        "expose_switch": True,
    }


class OptionsFlowTests(unittest.IsolatedAsyncioTestCase):
    """Exercise success, rejection, and empty-catalog option paths."""

    async def test_top_level_and_submenus(self) -> None:
        flow, _ = _flow(options={CONF_ZONES: [_zone()], CONF_MODES: [_mode()]})

        top = await flow.async_step_init()
        zones = await flow.async_step_zones()
        modes = await flow.async_step_modes()
        rules = await flow.async_step_rules()

        self.assertEqual(top["type"], FlowResultType.MENU)
        self.assertEqual(
            top["menu_options"], ["lights", "zones", "modes", "rules", "advanced"]
        )
        self.assertEqual(
            zones["menu_options"], ["add_zone", "edit_zone", "delete_zone"]
        )
        self.assertEqual(
            modes["menu_options"], ["add_mode", "edit_mode", "delete_mode"]
        )
        self.assertEqual(
            rules["menu_options"],
            ["add_state_rule", "add_numeric_rule", "delete_rule"],
        )

    async def test_lights_preserve_zone_integrity_and_advanced_settings(self) -> None:
        flow, _ = _flow(options={CONF_ZONES: [_zone()]})

        form = await flow.async_step_lights()
        empty = await flow.async_step_lights({CONF_LIGHTS: []})
        removed = await flow.async_step_lights({CONF_LIGHTS: ["light.one"]})
        saved = await flow.async_step_lights(
            {CONF_LIGHTS: ["light.one", "light.two", "light.one"]}
        )
        advanced_form = await flow.async_step_advanced()
        advanced_saved = await flow.async_step_advanced(
            {
                "tie_breaker": "oldest",
                "min_command_interval": 1.25,
                "manual_policy": "respect",
            }
        )

        self.assertEqual(form["type"], FlowResultType.FORM)
        self.assertEqual(empty["errors"][CONF_LIGHTS], "at_least_one_light")
        self.assertEqual(removed["errors"][CONF_LIGHTS], "zones_use_removed_lights")
        self.assertEqual(saved["data"][CONF_LIGHTS], ["light.one", "light.two"])
        self.assertEqual(advanced_form["type"], FlowResultType.FORM)
        self.assertEqual(advanced_saved["data"]["tie_breaker"], "oldest")

    async def test_zone_create_edit_delete_and_validation(self) -> None:
        flow, entry = _flow()

        form = await flow.async_step_add_zone()
        invalid = await flow.async_step_add_zone(
            {"name": "Fuera", "targets": ["light.unknown"]}
        )
        created = await flow.async_step_add_zone(
            {"name": "Sala", "targets": ["light.one"]}
        )
        entry.options = created["data"]
        zone = entry.options[CONF_ZONES][0]

        overlap = await flow.async_step_add_zone(
            {"name": "Otra", "targets": ["light.one", "light.two"]}
        )
        duplicate_name = await flow.async_step_add_zone(
            {"name": "sala", "targets": ["light.two"]}
        )
        selection = await flow.async_step_edit_zone({"zone_id": zone["zone_id"]})
        edited = await flow.async_step_edit_zone_form(
            {"name": "Salón", "targets": ["light.one", "light.two"]}
        )

        self.assertEqual(form["type"], FlowResultType.FORM)
        self.assertEqual(invalid["errors"]["base"], "target_not_managed")
        self.assertEqual(overlap["errors"]["base"], "target_in_multiple_zones")
        self.assertEqual(duplicate_name["errors"]["base"], "duplicate_zone")
        self.assertEqual(selection["step_id"], "edit_zone_form")
        self.assertEqual(edited["data"][CONF_ZONES][0]["name"], "Salón")

        zone_mode = _mode()
        zone_mode["zone_id"] = zone["zone_id"]
        entry.options = {CONF_ZONES: [zone], CONF_MODES: [zone_mode]}
        blocked = await flow.async_step_delete_zone({"zone_id": zone["zone_id"]})
        self.assertEqual(blocked["errors"]["base"], "zone_has_modes")
        entry.options = {CONF_ZONES: [zone], CONF_MODES: []}
        deleted = await flow.async_step_delete_zone({"zone_id": zone["zone_id"]})
        self.assertEqual(deleted["data"][CONF_ZONES], [])

    async def test_zone_edit_cannot_orphan_mode_targets(self) -> None:
        flow, _ = _flow(options={CONF_ZONES: [_zone()], CONF_MODES: [_mode()]})
        await flow.async_step_edit_zone({"zone_id": "living"})

        result = await flow.async_step_edit_zone_form(
            {"name": "Sala", "targets": ["light.two"]}
        )

        self.assertEqual(result["errors"]["base"], "mode_target_outside_zone")

    async def test_zone_accepts_only_an_existing_optional_area(self) -> None:
        flow, _ = _flow()
        areas = SimpleNamespace(
            async_get_area=lambda area_id: (
                SimpleNamespace(id=area_id) if area_id == "living_room" else None
            )
        )

        with patch(
            "custom_components.smart_led_manager.config_flow.ar.async_get",
            return_value=areas,
        ):
            missing = await flow.async_step_add_zone(
                {
                    "name": "Sala",
                    "targets": ["light.one"],
                    CONF_AREA_ID: "missing",
                }
            )
            created = await flow.async_step_add_zone(
                {
                    "name": "Sala",
                    "targets": ["light.one"],
                    CONF_AREA_ID: "living_room",
                }
            )

        self.assertEqual(missing["errors"]["base"], "area_not_found")
        self.assertEqual(created["data"][CONF_ZONES][0][CONF_AREA_ID], "living_room")

    async def test_mode_create_edit_delete_and_validation(self) -> None:
        flow, entry = _flow(options={CONF_ZONES: [_zone()], CONF_MODES: []})
        form = await flow.async_step_add_mode()
        invalid = await flow.async_step_add_mode(
            {
                **_mode(),
                "name": "Fuera",
                "targets": ["light.unknown"],
            }
        )
        created = await flow.async_step_add_mode(
            {key: value for key, value in _mode().items() if key != "mode_id"}
        )
        entry.options = created["data"]
        mode = entry.options[CONF_MODES][0]

        duplicate = await flow.async_step_add_mode(
            {
                **{key: value for key, value in _mode().items() if key != "mode_id"},
                "name": "azul",
            }
        )
        selection = await flow.async_step_edit_mode({"mode_id": mode["mode_id"]})
        edited_input = {
            key: value
            for key, value in mode.items()
            if key not in {"mode_id", "rgb_color", "brightness", "transition"}
        }
        edited_input.update({"name": "Azul noche", "animation": "pulse"})
        edited = await flow.async_step_edit_mode_form(edited_input)
        deleted = await flow.async_step_delete_mode({"mode_id": mode["mode_id"]})

        self.assertEqual(form["type"], FlowResultType.FORM)
        self.assertEqual(invalid["errors"]["base"], "mode_target_outside_zone")
        self.assertEqual(duplicate["errors"]["base"], "duplicate_mode_name")
        self.assertEqual(selection["step_id"], "edit_mode_form")
        self.assertEqual(edited["data"][CONF_MODES][0]["name"], "Azul noche")
        self.assertIsNone(edited["data"][CONF_MODES][0]["rgb_color"])
        self.assertEqual(deleted["data"][CONF_MODES], [])

    async def test_empty_catalog_aborts_edit_and_delete(self) -> None:
        flow, _ = _flow(options={CONF_ZONES: [], CONF_MODES: []})

        add_mode = await flow.async_step_add_mode()
        edit_zone = await flow.async_step_edit_zone()
        delete_zone = await flow.async_step_delete_zone()
        edit_mode = await flow.async_step_edit_mode()
        delete_mode = await flow.async_step_delete_mode()

        for result in (add_mode, edit_zone, delete_zone):
            self.assertEqual(result["reason"], "no_zones")
        for result in (edit_mode, delete_mode):
            self.assertEqual(result["reason"], "no_modes")

    async def test_rule_forms_retain_existing_rule_behavior(self) -> None:
        flow, entry = _flow(options={CONF_RULES: []})
        state_form = await flow.async_step_add_state_rule()
        state_invalid = await flow.async_step_add_state_rule(
            {
                "name": "Puerta",
                "source": "binary_sensor.door",
                "operator": "equals",
                "state": "on",
                "targets": [],
                "priority": 60,
                "rgb_color": [255, 0, 0],
                "brightness": 200,
                "transition": 0,
            }
        )
        state_saved = await flow.async_step_add_state_rule(
            {
                "name": "Puerta",
                "source": "binary_sensor.door",
                "operator": "equals",
                "state": "on",
                "targets": ["light.one"],
                "priority": 60,
                "rgb_color": [255, 0, 0],
                "brightness": 200,
                "transition": 0,
            }
        )
        entry.options = state_saved["data"]
        numeric_invalid = await flow.async_step_add_numeric_rule(
            {
                "name": "Temperatura",
                "source": "sensor.temperature",
                "targets": ["light.one"],
                "priority": 40,
                "points": "bad",
                "mode": "interpolate",
                "brightness": 180,
                "transition": 1,
                "minimum_change": 0.5,
                "minimum_interval": 5,
            }
        )
        numeric_saved = await flow.async_step_add_numeric_rule(
            {
                "name": "Temperatura",
                "source": "sensor.temperature",
                "targets": ["light.one"],
                "priority": 40,
                "points": "18:0,0,255;28:255,0,0",
                "mode": "interpolate",
                "brightness": 180,
                "transition": 1,
                "minimum_change": 0.5,
                "minimum_interval": 5,
            }
        )
        entry.options = numeric_saved["data"]
        rule_id = entry.options[CONF_RULES][0]["id"]
        delete_form = await flow.async_step_delete_rule()
        deleted = await flow.async_step_delete_rule({"rule_id": rule_id})

        self.assertEqual(state_form["type"], FlowResultType.FORM)
        self.assertEqual(state_invalid["errors"]["targets"], "at_least_one_target")
        self.assertEqual(numeric_invalid["errors"]["points"], "invalid_color_points")
        self.assertEqual(delete_form["type"], FlowResultType.FORM)
        self.assertEqual(len(deleted["data"][CONF_RULES]), 1)


if __name__ == "__main__":
    unittest.main()
