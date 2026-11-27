"""Tests for the authenticated numeric-rule visual editor backend."""

from __future__ import annotations

import asyncio
import unittest
from copy import deepcopy
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.components import frontend
from homeassistant.exceptions import Unauthorized

from custom_components.smart_led_manager.const import (
    CONF_LIGHTS,
    CONF_RULES,
    CONF_SHOW_SIDEBAR,
    CONF_ZONES,
    DOMAIN,
)
from custom_components.smart_led_manager.modules.configuration import options_revision
from custom_components.smart_led_manager.visual_editor import (
    _DATA_LOCK,
    PANEL_PATH,
    STATIC_URL,
    async_register_visual_editor_panel,
    async_reload_visual_editor_entry,
    async_remove_visual_editor_panel,
    async_setup_visual_editor,
    websocket_admin_diagnostics,
    websocket_admin_get,
    websocket_admin_mode,
    websocket_admin_mutate,
    websocket_editor_status,
    websocket_get_numeric_rules,
    websocket_get_smart_rules,
    websocket_mutate_smart_rule,
    websocket_preview_numeric_rule,
    websocket_preview_targets,
    websocket_save_numeric_rule,
)


def _rule() -> dict[str, object]:
    return {
        "id": "temperature",
        "type": "numeric",
        "name": "Temperatura",
        "source": "sensor.temperature",
        "targets": ["light.strip"],
        "priority": 47,
        "mode": "interpolate",
        "brightness": 180,
        "transition": 1.5,
        "minimum_change": 0.5,
        "minimum_interval": 5,
        "enabled": True,
        "points": [
            {"value": -10, "rgb": [0, 0, 255]},
            {"value": 20, "rgb": [0, 255, 0]},
            {"value": 80, "rgb": [255, 0, 0]},
        ],
        "future_field": {"preserve": True},
    }


class _Entry:
    domain = DOMAIN
    entry_id = "entry-1"

    def __init__(self, rule: dict[str, object] | None = None) -> None:
        self.data = {CONF_LIGHTS: ["light.strip"]}
        self.options = {
            CONF_LIGHTS: ["light.strip"],
            CONF_RULES: [deepcopy(rule or _rule())],
            "unrelated": {"kept": True},
        }


class _ConfigEntries:
    def __init__(self, entry: _Entry, runtime: SimpleNamespace) -> None:
        self.entry = entry
        self.runtime = runtime
        self.apply_updates = True
        self.updated: list[dict[str, object]] = []

    def async_get_entry(self, entry_id: str):
        return self.entry if entry_id == self.entry.entry_id else None

    def async_update_entry(self, entry: _Entry, **changes) -> bool:
        self.updated.append(changes)
        entry.options = changes["options"]
        if self.apply_updates:
            self.runtime.options_revision = options_revision(entry.options)
        return True


class _Hass:
    def __init__(self, entry: _Entry | None = None) -> None:
        self.entry = entry or _Entry()
        self.runtime = SimpleNamespace(
            options_revision=options_revision(self.entry.options)
        )
        self.config_entries = _ConfigEntries(self.entry, self.runtime)
        self.data = {
            DOMAIN: {
                _DATA_LOCK: asyncio.Lock(),
                "entries": {self.entry.entry_id: self.runtime},
            }
        }
        self.states = SimpleNamespace(
            get=lambda entity_id: (
                SimpleNamespace(
                    entity_id=entity_id,
                    name="Temperatura del salón",
                    attributes={"unit_of_measurement": "°C"},
                )
                if entity_id == "sensor.temperature"
                else SimpleNamespace(
                    entity_id=entity_id, name="Tira del salón", attributes={}
                )
                if entity_id == "light.strip"
                else None
            )
        )


class _Connection:
    def __init__(self, *, admin: bool = True) -> None:
        self.user = SimpleNamespace(is_admin=admin)
        self.results: list[tuple[int, object]] = []
        self.errors: list[tuple[int, str, str]] = []

    def send_result(self, msg_id: int, result=None) -> None:
        self.results.append((msg_id, result))

    def send_error(self, msg_id: int, code: str, message: str, *args) -> None:
        self.errors.append((msg_id, code, message))


def _message(message_type: str, **values) -> dict[str, object]:
    return {"id": 1, "type": message_type, "entry_id": "entry-1", **values}


async def _save_handler(hass, connection, message) -> None:
    """Call through the two wrappers around the async save coroutine."""
    await websocket_save_numeric_rule.__wrapped__.__wrapped__(hass, connection, message)


async def _mutation_handler(hass, connection, message) -> None:
    """Call through the two wrappers around the async CRUD coroutine."""

    await websocket_mutate_smart_rule.__wrapped__.__wrapped__(hass, connection, message)


async def _admin_mutation(hass, **values):
    connection = _Connection()
    message = _message("smart_led_manager/admin/mutate", **values)
    await websocket_admin_mutate.__wrapped__.__wrapped__(hass, connection, message)
    return connection


def _status(hass, **kwargs):
    connection = _Connection()
    websocket_editor_status(
        hass, connection, _message("smart_led_manager/editor/status", **kwargs)
    )
    return connection.results[0][1]


class VisualEditorBackendTests(unittest.IsolatedAsyncioTestCase):
    """Exercise read, exact preview, safe save and security boundaries."""

    async def test_admin_dependencies_and_revision_preserve_ids(self) -> None:
        entry = _Entry()
        entry.options[CONF_LIGHTS] = ["light.strip", "light.secondary"]
        entry.options[CONF_ZONES] = [
            {"zone_id": "office", "name": "Oficina", "targets": ["light.strip"]}
        ]
        entry.options[CONF_RULES][0]["target_selection"] = {"zones": ["office"]}
        entry.options[CONF_RULES][0]["enabled"] = False
        hass = _Hass(entry)
        revision = hass.runtime.options_revision
        blocked = await _admin_mutation(
            hass,
            revision=revision,
            kind="lights",
            operation="save",
            item={"targets": ["light.secondary"]},
        )
        self.assertEqual(blocked.errors[0][1], "zones_use_removed_lights")
        blocked = await _admin_mutation(
            hass, revision=revision, kind="zone", operation="delete", item_id="office"
        )
        self.assertEqual(blocked.errors[0][1], "zone_has_rules")
        self.assertFalse(hass.config_entries.updated)

        edited = await _admin_mutation(
            hass,
            revision=revision,
            kind="zone",
            operation="update",
            item_id="office",
            item={"zone_id": "foreign-id", "name": "Estudio"},
        )
        self.assertFalse(edited.errors)
        self.assertEqual(edited.results[0][1]["item"]["zone_id"], "office")
        self.assertEqual(
            entry.options[CONF_RULES][0]["target_selection"]["zones"], ["office"]
        )
        stale = await _admin_mutation(
            hass,
            revision=revision,
            kind="zone",
            operation="update",
            item_id="office",
            item={"name": "Nombre obsoleto"},
        )
        self.assertEqual(stale.errors[0][1], "conflict")
        self.assertEqual(entry.options[CONF_ZONES][0]["name"], "Estudio")

    async def test_admin_cannot_remove_a_light_used_directly_by_a_rule(self) -> None:
        entry = _Entry()
        entry.options[CONF_LIGHTS] = ["light.strip", "light.secondary"]
        hass = _Hass(entry)
        connection = await _admin_mutation(
            hass,
            revision=hass.runtime.options_revision,
            kind="lights",
            operation="save",
            item={"targets": ["light.secondary"]},
        )
        self.assertEqual(connection.errors[0][1], "rules_use_removed_lights")
        self.assertFalse(hass.config_entries.updated)

    async def test_reads_existing_rule_with_unit_and_full_metadata(self) -> None:
        hass = _Hass()
        connection = _Connection()

        websocket_get_numeric_rules(
            hass,
            connection,
            _message("smart_led_manager/rules/get"),
        )

        self.assertFalse(connection.errors)
        result = connection.results[0][1]
        self.assertEqual(result["entry_id"], "entry-1")
        self.assertEqual(len(result["revision"]), 64)
        self.assertEqual(result["rules"][0]["unit"], "°C")
        self.assertEqual(result["rules"][0]["source"]["name"], "Temperatura del salón")
        self.assertEqual(result["rules"][0]["targets"][0]["name"], "Tira del salón")
        rule = result["rules"][0]["rule"]
        self.assertEqual(rule["id"], "temperature")
        self.assertEqual(rule["future_field"], {"preserve": True})
        self.assertEqual(
            [point["value"] for point in rule["points"]], [-10.0, 20.0, 80.0]
        )

    async def test_legacy_numeric_endpoint_supports_advanced_targets(self) -> None:
        rule = _rule()
        rule.pop("targets")
        rule["target_selection"] = {
            "entities": ["light.strip"],
            "zones": [],
            "areas": [],
            "labels": [],
            "groups": [],
            "all_managed": False,
        }
        hass = _Hass(_Entry(rule))
        connection = _Connection()

        websocket_get_numeric_rules(
            hass,
            connection,
            _message("smart_led_manager/rules/get"),
        )

        self.assertFalse(connection.errors)
        self.assertEqual(
            connection.results[0][1]["rules"][0]["targets"][0]["name"],
            "Tira del salón",
        )

    async def test_preview_uses_exact_core_algorithm_without_light_calls(self) -> None:
        hass = _Hass()
        connection = _Connection()
        points = _rule()["points"]

        websocket_preview_numeric_rule(
            hass,
            connection,
            _message(
                "smart_led_manager/rules/preview",
                rule_id="temperature",
                mode="interpolate",
                points=points,
                values=[-20, 5, 100],
            ),
        )

        results = connection.results[0][1]["results"]
        self.assertEqual(results[0]["rgb"], [0, 0, 255])
        self.assertEqual(results[0]["relation"], "below")
        self.assertEqual(results[1]["rgb"], [0, 128, 128])
        self.assertEqual(results[1]["lower"], -10.0)
        self.assertEqual(results[1]["upper"], 20.0)
        self.assertEqual(results[2]["relation"], "above")
        self.assertFalse(hasattr(hass, "services"))

        range_connection = _Connection()
        websocket_preview_numeric_rule(
            hass,
            range_connection,
            _message(
                "smart_led_manager/rules/preview",
                rule_id="temperature",
                mode="ranges",
                points=points,
                values=[5],
            ),
        )
        self.assertEqual(
            range_connection.results[0][1]["results"][0]["rgb"], [0, 0, 255]
        )

    async def test_save_sorts_points_and_preserves_identity_and_other_fields(
        self,
    ) -> None:
        hass = _Hass()
        read_connection = _Connection()
        websocket_get_numeric_rules(
            hass, read_connection, _message("smart_led_manager/rules/get")
        )
        revision = read_connection.results[0][1]["revision"]
        connection = _Connection()

        await _save_handler(
            hass,
            connection,
            _message(
                "smart_led_manager/rules/save",
                rule_id="temperature",
                revision=revision,
                mode="ranges",
                points=[
                    {"value": 30, "rgb": [255, 0, 0]},
                    {"value": 10, "rgb": [0, 0, 255]},
                ],
            ),
        )

        self.assertFalse(connection.errors)
        self.assertEqual(len(hass.config_entries.updated), 1)
        saved = hass.entry.options[CONF_RULES][0]
        self.assertEqual(saved["id"], "temperature")
        self.assertEqual(saved["mode"], "ranges")
        self.assertEqual([point["value"] for point in saved["points"]], [10.0, 30.0])
        self.assertEqual(saved["priority"], 47)
        self.assertEqual(saved["future_field"], {"preserve": True})
        self.assertEqual(hass.entry.options["unrelated"], {"kept": True})

    async def test_mapping_proxy_options_support_read_revision_and_save(self) -> None:
        entry = _Entry()
        rule = _rule()
        rule["future_field"] = MappingProxyType({"preserve": True})
        entry.options = MappingProxyType(
            {
                CONF_LIGHTS: ["light.strip"],
                CONF_RULES: [MappingProxyType(rule)],
                "unrelated": MappingProxyType({"kept": True}),
            }
        )
        hass = _Hass(entry)
        read = _Connection()

        websocket_get_numeric_rules(hass, read, _message("smart_led_manager/rules/get"))
        revision = read.results[0][1]["revision"]
        self.assertEqual(len(revision), 64)
        self.assertEqual(
            read.results[0][1]["rules"][0]["rule"]["future_field"],
            {"preserve": True},
        )
        unified = _Connection()
        with patch(
            "custom_components.smart_led_manager.visual_editor._selection_catalog",
            return_value={
                "managed_lights": [],
                "zones": [],
                "areas": [],
                "labels": [],
                "groups": [],
            },
        ):
            websocket_get_smart_rules(
                hass,
                unified,
                _message("smart_led_manager/smart_rules/get"),
            )
        self.assertFalse(unified.errors)
        self.assertEqual(
            unified.results[0][1]["rules"][0]["rule"]["future_field"],
            {"preserve": True},
        )

        saved = _Connection()
        await _save_handler(
            hass,
            saved,
            _message(
                "smart_led_manager/rules/save",
                rule_id="temperature",
                revision=revision,
                mode="ranges",
                points=[
                    {"value": 10, "rgb": [0, 0, 255]},
                    {"value": 30, "rgb": [255, 0, 0]},
                ],
            ),
        )

        self.assertFalse(saved.errors)
        self.assertEqual(entry.options[CONF_RULES][0]["mode"], "ranges")
        self.assertEqual(entry.options["unrelated"], {"kept": True})

    async def test_unloaded_entry_rejects_websocket_commands(self) -> None:
        hass = _Hass()
        hass.data[DOMAIN]["entries"].clear()
        connection = _Connection()

        websocket_get_numeric_rules(
            hass, connection, _message("smart_led_manager/rules/get")
        )

        self.assertEqual(connection.errors[0][1], "entry_not_loaded")
        self.assertEqual(_status(hass)["status"], "unloaded")
        self.assertEqual(_status(hass, entry_id="missing"), {"status": "missing"})

    async def test_receipt_distinguishes_accepted_options_from_applied_revision(
        self,
    ) -> None:
        hass = _Hass()
        hass.config_entries.apply_updates = False
        revision = hass.runtime.options_revision
        message = _message(
            "smart_led_manager/smart_rules/mutate",
            operation="duplicate",
            rule_id="temperature",
            mutation_id="receipt-1",
            revision=revision,
        )
        first, replay, conflict, blocked = (_Connection() for _ in range(4))
        await _mutation_handler(hass, first, message)
        receipt = _status(hass, mutation_id="receipt-1")
        self.assertEqual(receipt["status"], "reloading")
        self.assertEqual(receipt["applied_revision"], revision)
        self.assertEqual(receipt["revision"], first.results[0][1]["revision"])
        self.assertEqual(
            receipt["mutation"]["rule"]["id"], first.results[0][1]["rule"]["id"]
        )
        self.assertNotEqual(receipt["revision"], revision)

        await _mutation_handler(hass, replay, {**message, "id": 2})
        self.assertEqual(replay.results[0][1], receipt["mutation"])
        await _mutation_handler(hass, conflict, {**message, "operation": "delete"})
        self.assertEqual(conflict.errors[0][1], "conflict")
        await _mutation_handler(
            hass,
            blocked,
            {**message, "revision": receipt["revision"], "mutation_id": "receipt-2"},
        )
        self.assertEqual(blocked.errors[0][1], "entry_not_loaded")
        self.assertEqual(len(hass.config_entries.updated), 1)
        hass.runtime.options_revision = receipt["revision"]
        self.assertEqual(_status(hass, mutation_id="receipt-1")["status"], "ready")

    async def test_failed_reload_preserves_saved_revision_for_inspection(self) -> None:
        hass = _Hass()
        hass.entry.options["unrelated"] = {"updated": True}
        hass.config_entries.async_reload = AsyncMock(return_value=False)
        await async_reload_visual_editor_entry(hass, hass.entry)
        status = _status(hass)
        self.assertEqual(status["status"], "failed")
        self.assertNotEqual(status["applied_revision"], status["revision"])
        hass.config_entries.async_reload.assert_awaited_once_with(hass.entry.entry_id)

    async def test_invalid_duplicate_and_stale_edits_do_not_change_options(
        self,
    ) -> None:
        hass = _Hass()
        original = deepcopy(hass.entry.options)
        invalid = _Connection()
        await _save_handler(
            hass,
            invalid,
            _message(
                "smart_led_manager/rules/save",
                rule_id="temperature",
                revision="stale",
                mode="interpolate",
                points=[
                    {"value": 1, "rgb": [0, 0, 0]},
                    {"value": 1, "rgb": [255, 255, 255]},
                ],
            ),
        )
        self.assertEqual(invalid.errors[0][1], "conflict")
        self.assertEqual(hass.entry.options, original)

        read = _Connection()
        websocket_get_numeric_rules(hass, read, _message("smart_led_manager/rules/get"))
        duplicate = _Connection()
        await _save_handler(
            hass,
            duplicate,
            _message(
                "smart_led_manager/rules/save",
                rule_id="temperature",
                revision=read.results[0][1]["revision"],
                mode="interpolate",
                points=[
                    {"value": 1, "rgb": [0, 0, 0]},
                    {"value": 1, "rgb": [255, 255, 255]},
                ],
            ),
        )
        self.assertEqual(duplicate.errors[0][1], "invalid_points")
        self.assertEqual(hass.entry.options, original)

    async def test_rule_with_unmanaged_target_is_rejected(self) -> None:
        rule = _rule()
        rule["targets"] = ["light.not_managed"]
        hass = _Hass(_Entry(rule))
        connection = _Connection()

        websocket_get_numeric_rules(
            hass, connection, _message("smart_led_manager/rules/get")
        )

        self.assertEqual(connection.errors[0][1], "unauthorized_targets")

    async def test_unified_catalog_and_crud_preserve_ids_and_revision(self) -> None:
        hass = _Hass()
        read = _Connection()
        with patch(
            "custom_components.smart_led_manager.visual_editor._selection_catalog",
            return_value={
                "managed_lights": [],
                "zones": [],
                "areas": [],
                "labels": [],
                "groups": [],
            },
        ):
            websocket_get_smart_rules(
                hass,
                read,
                _message("smart_led_manager/smart_rules/get"),
            )
        payload = read.results[0][1]
        self.assertEqual(payload["rules"][0]["rule"]["id"], "temperature")
        self.assertEqual(payload["rules"][0]["source"]["name"], "Temperatura del salón")

        updated = deepcopy(payload["rules"][0]["rule"])
        updated["name"] = "Temperatura segura"
        connection = _Connection()
        with patch(
            "custom_components.smart_led_manager.visual_editor._async_validate_rule_catalog",
            new=AsyncMock(),
        ):
            await _mutation_handler(
                hass,
                connection,
                _message(
                    "smart_led_manager/smart_rules/mutate",
                    revision=payload["revision"],
                    operation="update",
                    rule_id="temperature",
                    rule=updated,
                ),
            )
        self.assertFalse(connection.errors)
        self.assertEqual(connection.results[0][1]["rule"]["id"], "temperature")
        self.assertEqual(
            hass.entry.options[CONF_RULES][0]["name"], "Temperatura segura"
        )

        stale = _Connection()
        with patch(
            "custom_components.smart_led_manager.visual_editor._async_validate_rule_catalog",
            new=AsyncMock(),
        ):
            await _mutation_handler(
                hass,
                stale,
                _message(
                    "smart_led_manager/smart_rules/mutate",
                    revision=payload["revision"],
                    operation="delete",
                    rule_id="temperature",
                ),
            )
        self.assertEqual(stale.errors[0][1], "conflict")

    async def test_native_update_during_trigger_validation_cannot_be_overwritten(
        self,
    ) -> None:
        hass = _Hass()
        original = deepcopy(hass.entry.options)
        revision = options_revision(original)
        connection = _Connection()

        async def validate(*_args):
            hass.entry.options["unrelated"] = {"changed_from_options_flow": True}

        with patch(
            "custom_components.smart_led_manager.visual_editor._async_validate_rule_catalog",
            side_effect=validate,
        ):
            await _mutation_handler(
                hass,
                connection,
                _message(
                    "smart_led_manager/smart_rules/mutate",
                    revision=revision,
                    operation="update",
                    rule_id="temperature",
                    rule={**_rule(), "name": "Obsoleta"},
                ),
            )
        assert connection.errors[0][1] == "conflict"
        assert hass.entry.options["unrelated"] == {"changed_from_options_flow": True}
        assert not hass.config_entries.updated

    async def test_target_preview_is_read_only_and_reports_exclusions(self) -> None:
        hass = _Hass()
        connection = _Connection()
        resolved = SimpleNamespace(
            targets=frozenset({"light.strip"}),
            excluded=frozenset({"light.outside"}),
            duplicates=frozenset({"light.strip"}),
        )
        resolver = SimpleNamespace(resolve=lambda _selection: resolved)
        original = deepcopy(hass.entry.options)
        with patch(
            "custom_components.smart_led_manager.visual_editor._advanced_target_resolver",
            return_value=resolver,
        ):
            websocket_preview_targets(
                hass,
                connection,
                _message(
                    "smart_led_manager/targets/preview",
                    target_selection={"entities": ["light.strip"]},
                ),
            )
        self.assertEqual(
            connection.results[0][1]["targets"][0]["entity_id"], "light.strip"
        )
        self.assertEqual(
            connection.results[0][1]["excluded"][0]["entity_id"], "light.outside"
        )
        self.assertEqual(
            connection.results[0][1]["duplicates"][0]["entity_id"], "light.strip"
        )
        self.assertEqual(hass.entry.options, original)

    async def test_all_commands_require_an_administrator(self) -> None:
        hass = _Hass()
        connection = _Connection(admin=False)
        messages = [
            (
                websocket_admin_diagnostics,
                _message("smart_led_manager/admin/diagnostics"),
            ),
            (websocket_admin_get, _message("smart_led_manager/admin/get")),
            (websocket_admin_mode, _message("smart_led_manager/admin/mode")),
            (websocket_admin_mutate, _message("smart_led_manager/admin/mutate")),
            (websocket_editor_status, _message("smart_led_manager/editor/status")),
            (
                websocket_get_numeric_rules,
                _message("smart_led_manager/rules/get"),
            ),
            (
                websocket_preview_numeric_rule,
                _message(
                    "smart_led_manager/rules/preview",
                    rule_id="temperature",
                    mode="interpolate",
                    points=_rule()["points"],
                    values=[20],
                ),
            ),
            (
                websocket_save_numeric_rule,
                _message(
                    "smart_led_manager/rules/save",
                    rule_id="temperature",
                    revision="unused",
                    mode="interpolate",
                    points=_rule()["points"],
                ),
            ),
            (
                websocket_get_smart_rules,
                _message("smart_led_manager/smart_rules/get"),
            ),
            (
                websocket_mutate_smart_rule,
                _message(
                    "smart_led_manager/smart_rules/mutate",
                    revision="unused",
                    operation="delete",
                    rule_id="temperature",
                ),
            ),
            (
                websocket_preview_targets,
                _message(
                    "smart_led_manager/targets/preview",
                    target_selection={"entities": ["light.strip"]},
                ),
            ),
        ]
        for handler, message in messages:
            with (
                self.subTest(handler=handler.__name__),
                self.assertRaises(Unauthorized),
            ):
                handler(hass, connection, message)


class VisualEditorSurfaceTests(unittest.IsolatedAsyncioTestCase):
    """Verify idempotent registration and clean panel removal."""

    async def test_static_commands_and_panel_lifecycle(self) -> None:
        entry = _Entry()
        hass = _Hass(entry)
        hass.data[frontend.DATA_PANELS] = {}
        hass.http = SimpleNamespace(async_register_static_paths=AsyncMock())
        with (
            patch(
                "custom_components.smart_led_manager.visual_editor.websocket_api.async_register_command"
            ) as register_command,
            patch(
                "custom_components.smart_led_manager.visual_editor.panel_custom.async_register_panel",
                new=AsyncMock(),
            ) as register_panel,
            patch(
                "custom_components.smart_led_manager.visual_editor.frontend.async_remove_panel"
            ) as remove_panel,
        ):
            await async_setup_visual_editor(hass)
            await async_setup_visual_editor(hass)
            await async_register_visual_editor_panel(hass, entry)
            await async_register_visual_editor_panel(hass, entry)
            async_remove_visual_editor_panel(hass)

        self.assertEqual(register_command.call_count, 13)
        hass.http.async_register_static_paths.assert_awaited_once()
        static_path = hass.http.async_register_static_paths.await_args.args[0][0]
        self.assertEqual(static_path.url_path, STATIC_URL)
        register_panel.assert_awaited_once()
        self.assertTrue(register_panel.await_args.kwargs["require_admin"])
        self.assertEqual(
            register_panel.await_args.kwargs["sidebar_title"], "Smart LED Manager"
        )
        self.assertEqual(
            register_panel.await_args.kwargs["config"]["version"], "0.1.0-alpha.3"
        )
        self.assertEqual(
            register_panel.await_args.kwargs["frontend_url_path"], PANEL_PATH
        )
        remove_panel.assert_called_once_with(hass, PANEL_PATH, warn_if_unknown=False)

    async def test_sidebar_can_be_hidden_without_removing_panel_route(self) -> None:
        entry = _Entry()
        entry.options[CONF_SHOW_SIDEBAR] = False
        hass = _Hass(entry)
        hass.data[frontend.DATA_PANELS] = {}

        with patch(
            "custom_components.smart_led_manager.visual_editor.panel_custom.async_register_panel",
            new=AsyncMock(),
        ) as register_panel:
            await async_register_visual_editor_panel(hass, entry)

        register_panel.assert_awaited_once()
        self.assertIsNone(register_panel.await_args.kwargs["sidebar_title"])
        self.assertEqual(
            register_panel.await_args.kwargs["frontend_url_path"], PANEL_PATH
        )


if __name__ == "__main__":
    unittest.main()
