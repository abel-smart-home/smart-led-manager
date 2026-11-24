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
    CONF_SHOW_SIDEBAR,
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


def _state_rule(*, enabled: bool | None = None) -> dict[str, object]:
    rule: dict[str, object] = {
        "id": "door",
        "type": "state",
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
    if enabled is not None:
        rule["enabled"] = enabled
    return rule


def _numeric_rule() -> dict[str, object]:
    return {
        "id": "temperature",
        "type": "numeric",
        "name": "Temperatura",
        "source": "sensor.temperature",
        "targets": ["light.one"],
        "priority": 40,
        "points": [
            {"value": 18.0, "rgb": [0, 0, 255]},
            {"value": 28.0, "rgb": [255, 0, 0]},
        ],
        "mode": "interpolate",
        "brightness": 180,
        "transition": 1,
        "minimum_change": 0.5,
        "minimum_interval": 5,
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
            top["menu_options"],
            ["admin_center", "lights", "zones", "modes", "rules", "advanced"],
        )
        self.assertEqual(
            zones["menu_options"], ["add_zone", "edit_zone", "delete_zone"]
        )
        self.assertEqual(
            modes["menu_options"], ["add_mode", "edit_mode", "delete_mode"]
        )
        self.assertEqual(
            rules["menu_options"],
            [
                "open_visual_editor",
                "add_state_rule",
                "add_numeric_rule",
                "edit_rule",
                "duplicate_rule",
                "toggle_rule",
                "delete_rule",
            ],
        )

        visual_access = await flow.async_step_open_visual_editor()
        self.assertEqual(visual_access["type"], FlowResultType.FORM)
        self.assertEqual(
            visual_access["description_placeholders"]["path"],
            "/smart-led-manager-editor",
        )
        returned = await flow.async_step_open_visual_editor({})
        self.assertEqual(returned["step_id"], "rules")

        admin_center = await flow.async_step_admin_center()
        self.assertEqual(admin_center["type"], FlowResultType.FORM)
        self.assertEqual(
            admin_center["description_placeholders"]["path"],
            "/smart-led-manager-editor",
        )
        saved_access = await flow.async_step_admin_center({CONF_SHOW_SIDEBAR: False})
        self.assertFalse(saved_access["data"][CONF_SHOW_SIDEBAR])

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
                "enabled": True,
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
                "enabled": True,
            }
        )
        entry.options = state_saved["data"]
        numeric_invalid = await flow.async_step_add_numeric_rule(
            {
                "name": "Temperatura",
                "source": "sensor.temperature",
                "targets": ["light.unknown"],
                "priority": 40,
                "mode": "interpolate",
                "brightness": 180,
                "transition": 1,
                "minimum_change": 0.5,
                "minimum_interval": 5,
                "enabled": True,
            }
        )
        point_editor = await flow.async_step_add_numeric_rule(
            {
                "name": "Temperatura",
                "source": "sensor.temperature",
                "targets": ["light.one"],
                "priority": 40,
                "mode": "interpolate",
                "brightness": 180,
                "transition": 1,
                "minimum_change": 0.5,
                "minimum_interval": 5,
                "enabled": True,
            }
        )
        numeric_saved = await flow.async_step_save_numeric_rule()
        entry.options = numeric_saved["data"]
        rule_id = entry.options[CONF_RULES][0]["id"]
        delete_form = await flow.async_step_delete_rule()
        deleted = await flow.async_step_delete_rule({"rule_id": rule_id})

        self.assertEqual(state_form["type"], FlowResultType.FORM)
        self.assertEqual(state_invalid["errors"]["targets"], "at_least_one_target")
        self.assertEqual(numeric_invalid["errors"]["targets"], "target_not_managed")
        self.assertEqual(point_editor["step_id"], "numeric_points")
        self.assertEqual(delete_form["type"], FlowResultType.FORM)
        self.assertEqual(len(deleted["data"][CONF_RULES]), 1)

    async def test_state_rule_edit_duplicate_and_toggle_preserve_identity(self) -> None:
        original = _state_rule()
        flow, entry = _flow(options={CONF_RULES: [original]})

        selected = await flow.async_step_edit_rule({"rule_id": "door"})
        edited = await flow.async_step_edit_state_rule(
            {
                **{
                    key: value
                    for key, value in original.items()
                    if key not in {"id", "type"}
                },
                "name": "Puerta trasera",
                "source": "binary_sensor.back_door",
                "targets": ["light.two"],
                "priority": 75,
                "rgb_color": [255, 128, 0],
                "enabled": True,
            }
        )
        entry.options = edited["data"]
        duplicated_form = await flow.async_step_duplicate_rule({"rule_id": "door"})
        duplicate_defaults = duplicated_form["data_schema"]({})
        self.assertNotIn("enabled", duplicate_defaults)
        duplicate_defaults["enabled"] = True
        duplicated = await flow.async_step_duplicate_state_rule(duplicate_defaults)

        self.assertEqual(selected["step_id"], "edit_state_rule")
        self.assertEqual(edited["data"][CONF_RULES][0]["id"], "door")
        self.assertEqual(edited["data"][CONF_RULES][0]["targets"], ["light.two"])
        self.assertEqual(edited["data"][CONF_RULES][0]["priority"], 75)
        self.assertEqual(duplicated_form["step_id"], "duplicate_state_rule")
        rules = duplicated["data"][CONF_RULES]
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0]["id"], "door")
        self.assertNotEqual(rules[1]["id"], "door")
        self.assertFalse(rules[1]["enabled"])
        self.assertTrue(str(rules[1]["name"]).endswith("(2)"))

        entry.options = {CONF_RULES: [original]}
        disabled = await flow.async_step_toggle_rule({"rule_id": "door"})
        self.assertFalse(disabled["data"][CONF_RULES][0]["enabled"])
        entry.options = disabled["data"]
        enabled = await flow.async_step_toggle_rule({"rule_id": "door"})
        self.assertTrue(enabled["data"][CONF_RULES][0]["enabled"])

    async def test_numeric_rule_visual_editor_adds_edits_deletes_and_sorts(
        self,
    ) -> None:
        rule = _numeric_rule()
        flow, entry = _flow(options={CONF_RULES: [rule]})
        flow.hass.states = SimpleNamespace(
            get=lambda entity_id: SimpleNamespace(
                attributes={"unit_of_measurement": "°C"}
            )
            if entity_id in {"sensor.temperature", "sensor.office_temperature"}
            else None
        )

        selected = await flow.async_step_edit_rule({"rule_id": "temperature"})
        current = selected["data_schema"]({})
        current.update(
            {
                "name": "Temperatura editada",
                "source": "sensor.office_temperature",
                "priority": 55,
                "targets": ["light.two"],
                "enabled": True,
            }
        )
        editor = await flow.async_step_edit_numeric_rule(current)
        duplicate = await flow.async_step_add_numeric_point(
            {"value": 18, "rgb": [1, 2, 3]}
        )
        invalid = await flow.async_step_add_numeric_point(
            {"value": float("nan"), "rgb": [1, 2, 3]}
        )
        added = await flow.async_step_add_numeric_point(
            {"value": 10, "rgb": [0, 255, 0]}
        )
        await flow.async_step_edit_numeric_point({"point_index": "2"})
        edited_point = await flow.async_step_edit_numeric_point_form(
            {"value": 30, "rgb": [255, 255, 0]}
        )
        deleted_point = await flow.async_step_delete_numeric_point({"point_index": "0"})
        saved = await flow.async_step_save_numeric_rule()

        self.assertEqual(selected["step_id"], "edit_numeric_rule")
        self.assertEqual(editor["step_id"], "numeric_points")
        self.assertEqual(editor["description_placeholders"]["unit"], "°C")
        self.assertEqual(
            duplicate["errors"]["base"], "invalid_or_duplicate_color_point"
        )
        self.assertEqual(invalid["errors"]["base"], "invalid_or_duplicate_color_point")
        self.assertEqual(added["step_id"], "numeric_points")
        self.assertEqual(edited_point["step_id"], "numeric_points")
        self.assertEqual(deleted_point["step_id"], "numeric_points")
        stored = saved["data"][CONF_RULES][0]
        self.assertEqual(stored["id"], "temperature")
        self.assertEqual(stored["source"], "sensor.office_temperature")
        self.assertEqual(stored["priority"], 55)
        self.assertEqual(stored["targets"], ["light.two"])
        self.assertEqual([point["value"] for point in stored["points"]], [18.0, 30.0])
        entry.options = saved["data"]

    async def test_numeric_duplicate_is_disabled_and_insufficient_points_block_save(
        self,
    ) -> None:
        original = _numeric_rule()
        flow, _ = _flow(options={CONF_RULES: [original]})

        form = await flow.async_step_duplicate_rule({"rule_id": "temperature"})
        defaults = form["data_schema"]({})
        self.assertNotIn("enabled", defaults)
        defaults["enabled"] = True
        editor = await flow.async_step_duplicate_numeric_rule(defaults)
        self.assertFalse(flow._numeric_rule_draft["enabled"])
        flow._numeric_rule_draft["points"] = [{"value": 18.0, "rgb": [0, 0, 255]}]
        blocked = await flow.async_step_save_numeric_rule()
        await flow.async_step_save_numeric_rule({})
        await flow.async_step_add_numeric_point({"value": 28, "rgb": [255, 0, 0]})
        saved = await flow.async_step_save_numeric_rule()

        self.assertEqual(editor["step_id"], "numeric_points")
        self.assertEqual(blocked["errors"]["base"], "at_least_two_color_points")
        rules = saved["data"][CONF_RULES]
        self.assertEqual(len(rules), 2)
        self.assertNotEqual(rules[0]["id"], rules[1]["id"])
        self.assertFalse(rules[1]["enabled"])

    async def test_invalid_legacy_numeric_points_are_not_silently_replaced(
        self,
    ) -> None:
        corrupt = _numeric_rule()
        corrupt["points"] = [{"value": 18, "rgb": [0, 0, 999]}]
        flow, _ = _flow(options={CONF_RULES: [corrupt]})

        result = await flow.async_step_edit_rule({"rule_id": "temperature"})

        self.assertEqual(result["type"], FlowResultType.ABORT)
        self.assertEqual(result["reason"], "invalid_rule")

    async def test_stale_toggle_and_delete_selections_abort_without_changes(
        self,
    ) -> None:
        flow, _ = _flow(options={CONF_RULES: [_state_rule()]})

        toggled = await flow.async_step_toggle_rule({"rule_id": "missing"})
        deleted = await flow.async_step_delete_rule({"rule_id": "missing"})

        self.assertEqual(toggled["reason"], "rule_not_found")
        self.assertEqual(deleted["reason"], "rule_not_found")


if __name__ == "__main__":
    unittest.main()
