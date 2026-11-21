"""Focused orchestration tests independent of the HA pytest plugin."""

from __future__ import annotations

import asyncio
import unittest
from collections import deque
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.components.light import ATTR_SUPPORTED_COLOR_MODES, ColorMode
from homeassistant.const import ATTR_SUPPORTED_FEATURES, STATE_OFF, STATE_ON
from homeassistant.core import Context, State

from custom_components.smart_led_manager.const import CONF_LIGHTS, MODULE_NOTIFICATION
from custom_components.smart_led_manager.controllers.base import (
    ApplyResult,
    ApplyStatus,
)
from custom_components.smart_led_manager.coordinator import SmartLEDCoordinator
from custom_components.smart_led_manager.core.engine import PriorityEngine
from custom_components.smart_led_manager.core.scheduler import AnimationScheduler
from custom_components.smart_led_manager.core.targets import TargetResolver
from custom_components.smart_led_manager.models import (
    AnimationKind,
    AnimationSpec,
    LightCommand,
    Request,
    utc_now,
)


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


class _TrackingController:
    """Record the currently retained command without creating HA workers."""

    def __init__(self) -> None:
        self.desired: dict[str, LightCommand] = {}
        self.applied: list[tuple[str, LightCommand]] = []
        self.cancelled: list[str] = []
        self.frame_applied = asyncio.Event()

    @property
    def pending_targets(self) -> frozenset[str]:
        return frozenset(self.desired)

    async def async_apply(
        self,
        target: str,
        command: LightCommand,
        *,
        allow_turn_on: bool,
    ) -> ApplyResult:
        del allow_turn_on
        self.desired[target] = command
        self.applied.append((target, command))
        self.frame_applied.set()
        return ApplyResult(target, ApplyStatus.APPLIED)

    async def async_cancel(self, target: str) -> None:
        self.cancelled.append(target)
        self.desired.pop(target, None)


class CoordinatorTests(unittest.IsolatedAsyncioTestCase):
    """Cover safe recovery and external-state attribution boundaries."""

    def _runtime_coordinator(self, clock) -> SmartLEDCoordinator:
        coordinator = SmartLEDCoordinator.__new__(SmartLEDCoordinator)
        coordinator.engine = PriorityEngine(clock=clock)
        coordinator.animations = AnimationScheduler()
        coordinator.controller = _TrackingController()
        coordinator._mutation_lock = asyncio.Lock()
        coordinator._manual_activated = {}
        coordinator._persisted_request_ids = set()
        coordinator._winners = {}
        coordinator.history = deque(maxlen=20)
        coordinator.last_error = None
        coordinator.status = "idle"
        coordinator.hass = SimpleNamespace(bus=SimpleNamespace(async_fire=Mock()))
        coordinator._async_after_mutation = AsyncMock()
        self.addAsyncCleanup(coordinator.animations.async_shutdown)
        return coordinator

    @staticmethod
    def _animated_notification(now, *, expires_at=None) -> Request:
        return Request(
            request_id="notice:doorbell",
            source="test",
            name="Doorbell",
            module=MODULE_NOTIFICATION,
            targets=frozenset({"light.strip"}),
            priority=70,
            command=LightCommand(
                color=(255, 0, 0),
                brightness=200,
                animation=AnimationSpec(kind=AnimationKind.BLINK, interval=0.2),
            ),
            activated_at=now,
            updated_at=now,
            expires_at=expires_at,
        )

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

    async def test_late_notification_expiry_recovers_lower_and_clears_stale_work(
        self,
    ) -> None:
        now = utc_now()
        clock = SimpleNamespace(value=now)
        coordinator = self._runtime_coordinator(lambda: clock.value)
        controller = coordinator.controller
        lower = Request(
            request_id="scene:ambient",
            source="test",
            name="Ambient",
            module="scene",
            targets=frozenset({"light.strip"}),
            priority=20,
            command=LightCommand(color=(0, 0, 255), brightness=80),
            activated_at=now,
            updated_at=now,
        )
        expires_at = now + timedelta(seconds=5)
        notification = self._animated_notification(now, expires_at=expires_at)

        await coordinator._async_apply_changes(
            await coordinator.engine.async_submit(lower)
        )
        controller.frame_applied.clear()
        await coordinator._async_apply_changes(
            await coordinator.engine.async_submit(notification)
        )
        await asyncio.wait_for(controller.frame_applied.wait(), timeout=1)
        self.assertIn("light.strip", coordinator.animations.active_targets)
        self.assertEqual(controller.desired["light.strip"].color, (255, 0, 0))

        controller.cancelled.clear()
        clock.value = expires_at + timedelta(seconds=1)
        await coordinator._async_expire()

        self.assertEqual(coordinator._winners["light.strip"], lower.request_id)
        self.assertEqual(controller.cancelled, ["light.strip"])
        self.assertNotIn("light.strip", coordinator.animations.active_targets)
        self.assertEqual(controller.pending_targets, frozenset({"light.strip"}))
        self.assertEqual(controller.desired["light.strip"], lower.command)
        self.assertEqual(controller.applied[-1], ("light.strip", lower.command))
        self.assertEqual(await coordinator.engine.async_winner("light.strip"), lower)

    async def test_late_cancel_clears_animation_and_pending_command_without_fallback(
        self,
    ) -> None:
        now = utc_now()
        clock = SimpleNamespace(value=now)
        coordinator = self._runtime_coordinator(lambda: clock.value)
        controller = coordinator.controller
        expires_at = now + timedelta(seconds=5)
        notification = self._animated_notification(now, expires_at=expires_at)

        await coordinator._async_apply_changes(
            await coordinator.engine.async_submit(notification)
        )
        await asyncio.wait_for(controller.frame_applied.wait(), timeout=1)
        self.assertIn("light.strip", coordinator.animations.active_targets)
        self.assertIn("light.strip", controller.pending_targets)

        controller.cancelled.clear()
        clock.value = expires_at + timedelta(seconds=1)
        await coordinator.async_cancel(notification.request_id)
        applied_count = len(controller.applied)
        await asyncio.sleep(0)

        self.assertNotIn("light.strip", coordinator.animations.active_targets)
        self.assertEqual(controller.cancelled, ["light.strip"])
        self.assertNotIn("light.strip", controller.pending_targets)
        self.assertNotIn("light.strip", coordinator._winners)
        self.assertEqual(len(controller.applied), applied_count)


if __name__ == "__main__":
    unittest.main()
