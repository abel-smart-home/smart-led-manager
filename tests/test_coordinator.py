"""Focused orchestration tests independent of the HA pytest plugin."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.components.light import ATTR_SUPPORTED_COLOR_MODES, ColorMode
from homeassistant.const import ATTR_SUPPORTED_FEATURES, STATE_OFF, STATE_ON
from homeassistant.core import Context, State

from custom_components.smart_led_manager.const import CONF_LIGHTS
from custom_components.smart_led_manager.coordinator import SmartLEDCoordinator
from custom_components.smart_led_manager.core.targets import TargetResolver
from custom_components.smart_led_manager.models import LightCommand, Request, utc_now


def _request(request_id: str, target: str) -> Request:
    now = utc_now()
    return Request(
        request_id=request_id,
        source="test",
        name=request_id,
        module="scene",
        targets=frozenset({target}),
        priority=50,
        command=LightCommand(color=(1, 2, 3)),
        activated_at=now,
        updated_at=now,
        persistent=True,
    )


class CoordinatorTests(unittest.IsolatedAsyncioTestCase):
    """Cover safe recovery and external-state attribution boundaries."""

    @patch(
        "custom_components.smart_led_manager.coordinator.async_track_state_change_event"
    )
    @patch("custom_components.smart_led_manager.coordinator.SmartLEDStorage")
    async def test_recovery_isolates_corrupt_and_unauthorized_records(
        self, storage_type, track_state
    ) -> None:
        """One bad record cannot block valid intent or escape the allowlist."""
        storage = storage_type.return_value
        storage.async_load = AsyncMock(
            return_value=[
                _request("valid", "light.allowed").to_dict(),
                _request("forbidden", "light.removed").to_dict(),
                {"request_id": "corrupt"},
            ]
        )
        entry = SimpleNamespace(
            entry_id="entry-1",
            data={CONF_LIGHTS: ["light.allowed"]},
            options={},
        )
        coordinator = SmartLEDCoordinator(SimpleNamespace(), entry)
        coordinator.rules.async_setup = AsyncMock()
        coordinator._async_apply_changes = AsyncMock()
        coordinator._async_schedule_expiry = AsyncMock()
        track_state.return_value = Mock()

        await coordinator.async_initialize()

        requests = await coordinator.engine.async_requests()
        self.assertEqual([request.request_id for request in requests], ["valid"])
        changes = coordinator._async_apply_changes.await_args.args[0]
        self.assertEqual({change.target for change in changes}, {"light.allowed"})
        self.assertIn("Ignored 2", coordinator.last_error)
        track_state.assert_called_once()

    def test_service_only_external_change_invalidates_and_reasserts(self) -> None:
        """Opting out of manual intent cannot preserve stale dedupe state."""
        coordinator = SmartLEDCoordinator.__new__(SmartLEDCoordinator)
        coordinator._started = True
        coordinator.targets = TargetResolver(["light.strip"])
        coordinator.manual_policy = "service_only"
        coordinator.controller = SimpleNamespace(
            is_own_context=Mock(return_value=False),
            invalidate_applied_state=Mock(),
            async_retry=AsyncMock(),
        )
        coordinator.hass = SimpleNamespace(async_create_task=Mock())
        attributes = {
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.RGB],
            ATTR_SUPPORTED_FEATURES: 0,
        }
        event = SimpleNamespace(
            data={
                "entity_id": "light.strip",
                "old_state": State("light.strip", STATE_OFF, attributes),
                "new_state": State("light.strip", STATE_ON, attributes),
            },
            context=Context(),
        )

        coordinator._async_light_state_changed(event)

        coordinator.controller.invalidate_applied_state.assert_called_once_with(
            "light.strip"
        )
        task_call = coordinator.hass.async_create_task.call_args
        self.assertEqual(task_call.args[1], "smart_led_manager_reassert_light.strip")
        task_call.args[0].close()


if __name__ == "__main__":
    unittest.main()
