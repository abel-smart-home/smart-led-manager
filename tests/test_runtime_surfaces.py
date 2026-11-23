"""Focused tests for integration lifecycle and diagnostic surfaces."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from custom_components.smart_led_manager import (
    _async_update_listener,
    async_migrate_entry,
    async_remove_entry,
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.smart_led_manager.const import CONF_ZONES, DOMAIN
from custom_components.smart_led_manager.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.smart_led_manager.sensor import (
    SmartLEDManagerStatusSensor,
)
from custom_components.smart_led_manager.sensor import (
    async_setup_entry as async_setup_sensor_entry,
)


class _ConfigEntries:
    def __init__(self, *, unload_result: bool = True) -> None:
        self.unload_result = unload_result
        self.forwarded: list[tuple[object, object]] = []
        self.unloaded: list[tuple[object, object]] = []
        self.reloaded: list[str] = []
        self.updated: list[tuple[object, dict[str, object]]] = []

    async def async_forward_entry_setups(self, entry, platforms) -> None:
        self.forwarded.append((entry, platforms))

    async def async_unload_platforms(self, entry, platforms) -> bool:
        self.unloaded.append((entry, platforms))
        return self.unload_result

    async def async_reload(self, entry_id: str) -> None:
        self.reloaded.append(entry_id)

    def async_update_entry(self, entry, **changes) -> None:
        self.updated.append((entry, changes))


class _Hass:
    def __init__(self, *, unload_result: bool = True) -> None:
        self.data: dict[str, object] = {}
        self.config_entries = _ConfigEntries(unload_result=unload_result)


class _Entry:
    def __init__(
        self,
        *,
        version: int = 1,
        minor_version: int = 1,
        options: dict[str, object] | None = None,
    ) -> None:
        self.entry_id = "entry-1"
        self.version = version
        self.minor_version = minor_version
        self.data = {"lights": ["light.strip"]}
        self.options = options or {}
        self.runtime_data = None
        self.unload_callbacks: list[object] = []

    def add_update_listener(self, listener):
        return listener

    def async_on_unload(self, callback) -> None:
        self.unload_callbacks.append(callback)


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    """Exercise setup, unload, removal and migration glue."""

    async def test_domain_setup_registers_actions_once(self) -> None:
        hass = _Hass()
        with (
            patch(
                "custom_components.smart_led_manager.async_setup_services"
            ) as setup_services,
            patch(
                "custom_components.smart_led_manager.async_setup_visual_editor",
                new=AsyncMock(),
            ) as setup_visual_editor,
        ):
            self.assertTrue(await async_setup(hass, {}))
            self.assertTrue(await async_setup(hass, {}))

        setup_services.assert_called_once_with(hass)
        self.assertEqual(setup_visual_editor.await_count, 2)
        self.assertEqual(hass.data[DOMAIN]["entries"], {})

    async def test_entry_setup_and_successful_unload(self) -> None:
        hass = _Hass()
        entry = _Entry()
        coordinator = SimpleNamespace(
            async_initialize=AsyncMock(),
            async_shutdown=AsyncMock(),
            modes=Mock(),
            catalog_valid=True,
        )
        with (
            patch(
                "custom_components.smart_led_manager.SmartLEDCoordinator",
                return_value=coordinator,
            ),
            patch(
                "custom_components.smart_led_manager.async_reconcile_registries"
            ) as reconcile,
            patch(
                "custom_components.smart_led_manager.async_register_visual_editor_panel",
                new=AsyncMock(),
            ) as register_panel,
        ):
            self.assertTrue(await async_setup_entry(hass, entry))

        coordinator.async_initialize.assert_awaited_once_with()
        reconcile.assert_called_once_with(hass, entry, coordinator.modes, cleanup=True)
        self.assertIs(entry.runtime_data, coordinator)
        self.assertIs(hass.data[DOMAIN]["entries"][entry.entry_id], coordinator)
        self.assertEqual(len(entry.unload_callbacks), 1)
        register_panel.assert_awaited_once_with(hass, entry)

        with patch(
            "custom_components.smart_led_manager.async_remove_visual_editor_panel"
        ) as remove_panel:
            self.assertTrue(await async_unload_entry(hass, entry))
        coordinator.async_shutdown.assert_awaited_once_with()
        remove_panel.assert_called_once_with(hass)
        self.assertNotIn(entry.entry_id, hass.data[DOMAIN]["entries"])

    async def test_failed_platform_unload_keeps_runtime_loaded(self) -> None:
        hass = _Hass(unload_result=False)
        coordinator = SimpleNamespace(async_shutdown=AsyncMock())
        entry = _Entry()
        entry.runtime_data = coordinator
        hass.data = {DOMAIN: {"entries": {entry.entry_id: coordinator}}}

        self.assertFalse(await async_unload_entry(hass, entry))

        coordinator.async_shutdown.assert_not_awaited()
        self.assertIn(entry.entry_id, hass.data[DOMAIN]["entries"])

    async def test_remove_migrate_and_update_listener(self) -> None:
        hass = _Hass()
        entry = _Entry()
        storage = SimpleNamespace(async_remove=AsyncMock())
        with patch(
            "custom_components.smart_led_manager.SmartLEDStorage",
            return_value=storage,
        ) as storage_type:
            await async_remove_entry(hass, entry)
        storage_type.assert_called_once_with(hass, entry.entry_id)
        storage.async_remove.assert_awaited_once_with()

        entry = _Entry(
            options={
                CONF_ZONES: [
                    {
                        "zone_id": "living",
                        "name": "Sala",
                        "targets": ["light.strip"],
                    }
                ]
            }
        )
        self.assertTrue(await async_migrate_entry(hass, entry))
        changes = hass.config_entries.updated[-1][1]
        self.assertEqual(changes["minor_version"], 2)
        self.assertIsNone(changes["options"][CONF_ZONES][0]["area_id"])
        current = _Entry(minor_version=2)
        update_count = len(hass.config_entries.updated)
        self.assertTrue(await async_migrate_entry(hass, current))
        self.assertEqual(len(hass.config_entries.updated), update_count)
        self.assertFalse(await async_migrate_entry(hass, _Entry(version=99)))
        await _async_update_listener(hass, entry)
        self.assertEqual(hass.config_entries.reloaded, [entry.entry_id])


class DiagnosticSurfaceTests(unittest.IsolatedAsyncioTestCase):
    """Verify the bounded sensor and downloadable diagnostics."""

    def _coordinator(self):
        return SimpleNamespace(
            status="active",
            targets=SimpleNamespace(authorized=frozenset({"light.strip"})),
            request_count=2,
            animations=SimpleNamespace(active_targets=frozenset({"light.strip"})),
            engine=SimpleNamespace(tie_breaker=SimpleNamespace(value="newest")),
            controller=SimpleNamespace(minimum_interval=0.75),
            manual_policy="service_only",
            last_error=None,
            async_add_listener=Mock(return_value=Mock()),
        )

    async def test_sensor_setup_and_properties(self) -> None:
        coordinator = self._coordinator()
        entry = _Entry()
        entry.runtime_data = coordinator
        added: list[SmartLEDManagerStatusSensor] = []

        await async_setup_sensor_entry(None, entry, added.extend)

        self.assertEqual(len(added), 1)
        sensor = added[0]
        self.assertEqual(sensor.native_value, "active")
        self.assertFalse(sensor.should_poll)
        self.assertEqual(sensor.unique_id, "entry-1_engine_status")
        self.assertEqual(sensor.extra_state_attributes["managed_lights"], 1)
        self.assertEqual(sensor.extra_state_attributes["request_count"], 2)
        self.assertEqual(sensor.extra_state_attributes["active_targets"], 1)
        self.assertEqual(sensor.extra_state_attributes["tie_breaker"], "newest")
        self.assertEqual(sensor.device_info.identifiers, {(DOMAIN, "entry-1")})

    async def test_downloadable_diagnostics_contains_runtime(self) -> None:
        runtime = {"status": "idle", "history": []}
        entry = _Entry()
        entry.runtime_data = SimpleNamespace(
            async_diagnostics=AsyncMock(return_value=runtime)
        )

        result = await async_get_config_entry_diagnostics(None, entry)

        self.assertEqual(result["runtime"], runtime)
        self.assertEqual(result["entry"]["version"], 1)
        self.assertEqual(result["entry"]["data"], entry.data)


if __name__ == "__main__":
    unittest.main()
