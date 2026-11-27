"""Unit tests for lightweight Home Assistant adapters."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from homeassistant.config_entries import ConfigEntryState

from custom_components.smart_led_manager import async_migrate_entry
from custom_components.smart_led_manager.const import CONF_ZONES
from custom_components.smart_led_manager.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.smart_led_manager.sensor import SmartLEDManagerStatusSensor


class HomeAssistantHelperTests(unittest.IsolatedAsyncioTestCase):
    """Cover migration, diagnostics redaction, and the status sensor surface."""

    async def test_migration_accepts_v1_and_rejects_unknown_version(self) -> None:
        config_entries = SimpleNamespace(async_update_entry=Mock())
        hass = SimpleNamespace(config_entries=config_entries)
        entry = SimpleNamespace(
            version=1,
            minor_version=1,
            options={
                CONF_ZONES: [
                    {
                        "zone_id": "living",
                        "name": "Sala",
                        "targets": ["light.strip"],
                    }
                ]
            },
        )

        self.assertTrue(await async_migrate_entry(hass, entry))
        config_entries.async_update_entry.assert_called_once_with(
            entry,
            options={
                CONF_ZONES: [
                    {
                        "zone_id": "living",
                        "name": "Sala",
                        "targets": ["light.strip"],
                        "area_id": None,
                    }
                ]
            },
            version=1,
            minor_version=2,
        )
        self.assertFalse(await async_migrate_entry(hass, SimpleNamespace(version=99)))

    async def test_diagnostics_redact_secrets(self) -> None:
        coordinator = SimpleNamespace(
            async_diagnostics=AsyncMock(
                return_value={
                    "status": "active",
                    "access_token": "runtime-secret",
                }
            )
        )
        entry = SimpleNamespace(
            version=1,
            minor_version=0,
            state=ConfigEntryState.LOADED,
            data={"lights": ["light.strip"], "password": "entry-secret"},
            options={
                "tie_breaker": "newest",
                "rules": [
                    {
                        "trigger": {
                            "event_data": {"opaque-value": "secret"},
                            "Authorization": "private",
                        }
                    }
                ],
            },
            runtime_data=coordinator,
        )

        result = await async_get_config_entry_diagnostics(object(), entry)

        self.assertEqual(result["entry"]["data"]["password"], "**REDACTED**")
        self.assertEqual(result["runtime"]["access_token"], "**REDACTED**")
        self.assertEqual(result["runtime"]["status"], "active")
        trigger = result["entry"]["options"]["rules"][0]["trigger"]
        self.assertEqual(trigger["event_data"], "**REDACTED**")
        self.assertEqual(trigger["Authorization"], "**REDACTED**")

    async def test_status_sensor_reports_bounded_runtime_state(self) -> None:
        remove_listener = object()
        coordinator = SimpleNamespace(
            status="active",
            targets=SimpleNamespace(authorized=frozenset({"light.one", "light.two"})),
            request_count=3,
            animations=SimpleNamespace(active_targets=frozenset({"light.one"})),
            engine=SimpleNamespace(tie_breaker=SimpleNamespace(value="newest")),
            controller=SimpleNamespace(minimum_interval=0.75),
            manual_policy="service_only",
            last_error=None,
            async_add_listener=Mock(return_value=remove_listener),
        )
        entry = SimpleNamespace(entry_id="entry-123")
        sensor = SmartLEDManagerStatusSensor(coordinator, entry)

        self.assertEqual(sensor.native_value, "active")
        self.assertEqual(sensor.unique_id, "entry-123_engine_status")
        self.assertEqual(sensor.extra_state_attributes["managed_lights"], 2)
        self.assertEqual(sensor.extra_state_attributes["request_count"], 3)
        self.assertEqual(sensor.extra_state_attributes["active_targets"], 1)


if __name__ == "__main__":
    unittest.main()
