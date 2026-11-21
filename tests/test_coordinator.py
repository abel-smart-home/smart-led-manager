"""Focused orchestration tests independent of the HA pytest plugin."""

from __future__ import annotations

import asyncio
import unittest
from collections import deque
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.components.light import ATTR_SUPPORTED_COLOR_MODES, ColorMode
from homeassistant.const import (
    ATTR_SUPPORTED_FEATURES,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import Context, State
from homeassistant.exceptions import HomeAssistantError

from custom_components.smart_led_manager.const import CONF_LIGHTS, MODULE_NOTIFICATION
from custom_components.smart_led_manager.controllers.base import (
    ApplyResult,
    ApplyStatus,
)
from custom_components.smart_led_manager.controllers.rgb import RGBLightController
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

    def invalidate_applied_state(self, target: str) -> None:
        """Mirror the production cache invalidation boundary."""

        del target


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
        coordinator._recovery_tasks = {}
        coordinator._failed_send_recovery_delay = 60
        coordinator._winners = {}
        coordinator._listeners = set()
        coordinator.history = deque(maxlen=20)
        coordinator.last_error = None
        coordinator.status = "idle"
        coordinator.hass = SimpleNamespace(
            bus=SimpleNamespace(async_fire=Mock()),
            async_create_task=lambda coroutine, name: asyncio.create_task(
                coroutine, name=name
            ),
        )
        coordinator._async_after_mutation = AsyncMock()
        self.addAsyncCleanup(coordinator._async_cancel_recoveries)
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

    async def test_available_event_contains_recovery_task_exception(self) -> None:
        """A premature ZHA availability event cannot leak its send failure."""
        coordinator = SmartLEDCoordinator.__new__(SmartLEDCoordinator)
        coordinator._started = True
        coordinator.targets = TargetResolver(["light.strip"])
        coordinator.controller = SimpleNamespace(
            async_retry=AsyncMock(
                side_effect=HomeAssistantError(
                    "Failed to send request: device did not respond"
                )
            ),
            invalidate_applied_state=Mock(),
        )
        coordinator._recovery_tasks = {}
        coordinator._winners = {"light.strip": "scene:blue"}
        coordinator._listeners = set()
        coordinator.last_error = None
        coordinator.status = "active"
        tasks: list[asyncio.Task[None]] = []

        def _create_task(coroutine, name: str) -> asyncio.Task[None]:
            task = asyncio.create_task(coroutine, name=name)
            tasks.append(task)
            return task

        coordinator.hass = SimpleNamespace(async_create_task=_create_task)
        attributes = {
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.RGB],
            ATTR_SUPPORTED_FEATURES: 0,
        }
        event = SimpleNamespace(
            data={
                "entity_id": "light.strip",
                "old_state": State("light.strip", STATE_UNAVAILABLE, attributes),
                "new_state": State("light.strip", STATE_ON, attributes),
            },
            context=Context(),
        )

        coordinator._async_light_state_changed(event)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        self.assertEqual(results, [None])
        self.assertIn("device did not respond", coordinator.last_error)
        coordinator.controller.invalidate_applied_state.assert_called_once_with(
            "light.strip"
        )

    async def test_reassert_event_contains_recovery_task_exception(self) -> None:
        """A failed service-only reassertion is diagnostic, not an orphan task."""
        coordinator = SmartLEDCoordinator.__new__(SmartLEDCoordinator)
        coordinator._started = True
        coordinator.targets = TargetResolver(["light.strip"])
        coordinator.manual_policy = "service_only"
        coordinator.controller = SimpleNamespace(
            is_own_context=Mock(return_value=False),
            invalidate_applied_state=Mock(),
            async_retry=AsyncMock(side_effect=HomeAssistantError("ZHA did not answer")),
        )
        coordinator._recovery_tasks = {}
        coordinator._winners = {"light.strip": "scene:blue"}
        coordinator._listeners = set()
        coordinator.last_error = None
        coordinator.status = "active"
        tasks: list[asyncio.Task[None]] = []

        def _create_task(coroutine, name: str) -> asyncio.Task[None]:
            task = asyncio.create_task(coroutine, name=name)
            tasks.append(task)
            return task

        coordinator.hass = SimpleNamespace(async_create_task=_create_task)
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
        results = await asyncio.gather(*tasks, return_exceptions=True)

        self.assertEqual(results, [None])
        self.assertIn("ZHA did not answer", coordinator.last_error)
        coordinator.controller.invalidate_applied_state.assert_called_once_with(
            "light.strip"
        )

    async def test_duplicate_recovery_events_share_one_task_without_new_animation(
        self,
    ) -> None:
        coordinator = SmartLEDCoordinator.__new__(SmartLEDCoordinator)
        coordinator._recovery_tasks = {}
        coordinator._winners = {"light.strip": "notice:active"}
        coordinator._listeners = set()
        coordinator.last_error = None
        coordinator.status = "active"
        retry_started = asyncio.Event()
        release_retry = asyncio.Event()
        tasks: list[asyncio.Task[None]] = []

        async def _retry(target: str) -> ApplyResult:
            retry_started.set()
            await release_retry.wait()
            return ApplyResult(target, ApplyStatus.APPLIED)

        def _create_task(coroutine, name: str) -> asyncio.Task[None]:
            task = asyncio.create_task(coroutine, name=name)
            tasks.append(task)
            return task

        coordinator.controller = SimpleNamespace(
            async_retry=AsyncMock(side_effect=_retry)
        )
        coordinator.animations = SimpleNamespace(
            active_targets=frozenset({"light.strip"})
        )
        coordinator.hass = SimpleNamespace(async_create_task=_create_task)

        coordinator._schedule_recovery("light.strip", "resync")
        coordinator._schedule_recovery("light.strip", "reassert")
        await retry_started.wait()

        self.assertEqual(len(tasks), 1)
        self.assertEqual(coordinator.controller.async_retry.await_count, 1)
        self.assertEqual(
            coordinator.animations.active_targets, frozenset({"light.strip"})
        )

        release_retry.set()
        await tasks[0]
        await asyncio.sleep(0)
        self.assertNotIn("light.strip", coordinator._recovery_tasks)

    async def test_exhausted_recovery_is_diagnostic_and_later_success_clears_it(
        self,
    ) -> None:
        coordinator = SmartLEDCoordinator.__new__(SmartLEDCoordinator)
        coordinator._winners = {"light.strip": "scene:blue"}
        coordinator._listeners = set()
        coordinator.last_error = None
        coordinator.status = "active"
        coordinator.controller = SimpleNamespace(
            async_retry=AsyncMock(
                return_value=ApplyResult(
                    "light.strip",
                    ApplyStatus.OFFLINE,
                    "send failed after 3 attempts: device did not respond",
                )
            )
        )

        await coordinator._async_retry_target("light.strip", "resync")

        self.assertEqual(coordinator.status, "error")
        self.assertIn("failed after 3 attempts", coordinator.last_error)

        coordinator.controller.async_retry.return_value = ApplyResult(
            "light.strip", ApplyStatus.APPLIED
        )
        await coordinator._async_retry_target("light.strip", "resync")

        self.assertEqual(coordinator.status, "active")
        self.assertIsNone(coordinator.last_error)

    async def test_winner_change_cancels_owned_recovery_task(self) -> None:
        now = utc_now()
        coordinator = self._runtime_coordinator(lambda: now)
        recovery_started = asyncio.Event()
        never_release = asyncio.Event()

        async def _wait_for_recovery() -> None:
            recovery_started.set()
            await never_release.wait()

        recovery = asyncio.create_task(_wait_for_recovery())
        coordinator._recovery_tasks["light.strip"] = recovery
        await recovery_started.wait()
        winner = Request(
            request_id="scene:blue",
            source="test",
            name="Blue",
            module="scene",
            targets=frozenset({"light.strip"}),
            priority=20,
            command=LightCommand(color=(0, 0, 255)),
            activated_at=now,
            updated_at=now,
        )

        await coordinator._async_apply_changes(
            await coordinator.engine.async_submit(winner)
        )

        self.assertTrue(recovery.cancelled())
        self.assertNotIn("light.strip", coordinator._recovery_tasks)
        self.assertEqual(coordinator.controller.desired["light.strip"], winner.command)

    async def test_exhausted_normal_send_remains_diagnostic(self) -> None:
        now = utc_now()
        coordinator = self._runtime_coordinator(lambda: now)
        coordinator.controller.async_apply = AsyncMock(
            return_value=ApplyResult(
                "light.strip",
                ApplyStatus.OFFLINE,
                "send failed after 1 attempt: device did not respond",
            )
        )
        winner = Request(
            request_id="scene:blue",
            source="test",
            name="Blue",
            module="scene",
            targets=frozenset({"light.strip"}),
            priority=20,
            command=LightCommand(color=(0, 0, 255)),
            activated_at=now,
            updated_at=now,
        )

        await coordinator._async_apply_changes(
            await coordinator.engine.async_submit(winner)
        )

        self.assertEqual(coordinator.status, "error")
        self.assertIn("device did not respond", coordinator.last_error)

    async def test_cancel_stops_scheduled_failure_recovery(self) -> None:
        now = utc_now()
        coordinator = self._runtime_coordinator(lambda: now)
        coordinator.controller.async_apply = AsyncMock(
            return_value=ApplyResult(
                "light.strip",
                ApplyStatus.OFFLINE,
                "send failed after 1 attempt: device did not respond",
            )
        )
        coordinator.controller.async_retry = AsyncMock()
        request = _request("scene:offline", "light.strip")

        await coordinator._async_apply_changes(
            await coordinator.engine.async_submit(request)
        )
        recovery = coordinator._recovery_tasks["light.strip"]

        await coordinator.async_cancel(request.request_id)

        self.assertTrue(recovery.cancelled())
        self.assertNotIn("light.strip", coordinator._recovery_tasks)
        coordinator.controller.async_retry.assert_not_awaited()
        self.assertIsNone(await coordinator.engine.async_winner("light.strip"))

    async def test_higher_priority_replaces_scheduled_failure_recovery(self) -> None:
        now = utc_now()
        coordinator = self._runtime_coordinator(lambda: now)
        coordinator.controller.async_apply = AsyncMock(
            side_effect=[
                ApplyResult(
                    "light.strip",
                    ApplyStatus.OFFLINE,
                    "send failed after 1 attempt: device did not respond",
                ),
                ApplyResult("light.strip", ApplyStatus.APPLIED),
            ]
        )
        coordinator.controller.async_retry = AsyncMock()
        lower = _request("scene:lower", "light.strip")
        higher = Request(
            request_id="alarm:higher",
            source="test",
            name="Higher",
            module="scene",
            targets=frozenset({"light.strip"}),
            priority=100,
            command=LightCommand(color=(255, 0, 0)),
            activated_at=now,
            updated_at=now,
        )

        await coordinator._async_apply_changes(
            await coordinator.engine.async_submit(lower)
        )
        stale_recovery = coordinator._recovery_tasks["light.strip"]
        await coordinator._async_apply_changes(
            await coordinator.engine.async_submit(higher)
        )

        self.assertTrue(stale_recovery.cancelled())
        self.assertNotIn("light.strip", coordinator._recovery_tasks)
        coordinator.controller.async_retry.assert_not_awaited()
        self.assertEqual(await coordinator.engine.async_winner("light.strip"), higher)
        self.assertEqual(
            coordinator.controller.async_apply.await_args.args[1], higher.command
        )

    async def test_shutdown_cancels_scheduled_failure_recovery(self) -> None:
        coordinator = SmartLEDCoordinator.__new__(SmartLEDCoordinator)
        recovery_started = asyncio.Event()
        never_release = asyncio.Event()

        async def _recovery() -> None:
            recovery_started.set()
            await never_release.wait()

        recovery = asyncio.create_task(_recovery())
        coordinator._recovery_tasks = {"light.strip": recovery}
        coordinator._started = True
        coordinator.rules = SimpleNamespace(async_shutdown=AsyncMock())
        coordinator._unsub_lights = None
        coordinator.expiry = SimpleNamespace(async_shutdown=AsyncMock())
        coordinator.animations = SimpleNamespace(async_shutdown=AsyncMock())
        coordinator.controller = SimpleNamespace(async_shutdown=AsyncMock())
        coordinator._async_save = AsyncMock()
        coordinator._listeners = set()
        coordinator.status = "active"
        await recovery_started.wait()

        await coordinator.async_shutdown()

        self.assertTrue(recovery.cancelled())
        self.assertEqual(coordinator._recovery_tasks, {})
        coordinator.controller.async_shutdown.assert_awaited_once_with()
        self.assertEqual(coordinator.status, "stopped")

    def test_service_only_external_change_invalidates_and_reasserts(self) -> None:
        """Opting out of manual intent cannot preserve stale dedupe state."""
        coordinator = SmartLEDCoordinator.__new__(SmartLEDCoordinator)
        coordinator._started = True
        coordinator.targets = TargetResolver(["light.strip"])
        coordinator.manual_policy = "service_only"
        coordinator._recovery_tasks = {}
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

    async def test_r02_reconnect_retries_only_current_blue_winner(self) -> None:
        now = utc_now()
        clock = SimpleNamespace(value=now)
        attributes = {
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.RGB],
            ATTR_SUPPORTED_FEATURES: 0,
        }
        state = SimpleNamespace(
            value=State("light.strip", STATE_UNAVAILABLE, attributes)
        )
        services = SimpleNamespace(
            async_call=AsyncMock(
                side_effect=[
                    HomeAssistantError("device did not respond"),
                    None,
                ]
            )
        )
        recovery_tasks: list[asyncio.Task[None]] = []

        def _create_task(coroutine, name: str) -> asyncio.Task[None]:
            task = asyncio.create_task(coroutine, name=name)
            recovery_tasks.append(task)
            return task

        hass = SimpleNamespace(
            states=SimpleNamespace(get=lambda target: state.value),
            services=services,
            bus=SimpleNamespace(async_fire=Mock()),
            async_create_task=_create_task,
        )
        coordinator = SmartLEDCoordinator.__new__(SmartLEDCoordinator)
        coordinator.hass = hass
        coordinator.targets = TargetResolver(["light.strip"])
        coordinator.manual_policy = "service_only"
        coordinator.engine = PriorityEngine(clock=lambda: clock.value)
        coordinator.controller = RGBLightController(
            hass,
            minimum_interval=0.1,
            retry_base_delay=0,
            retry_max_delay=0,
        )
        coordinator.animations = AnimationScheduler()
        coordinator._mutation_lock = asyncio.Lock()
        coordinator._manual_activated = {}
        coordinator._persisted_request_ids = set()
        coordinator._recovery_tasks = {}
        coordinator._winners = {}
        coordinator._listeners = set()
        coordinator.history = deque(maxlen=20)
        coordinator.last_error = None
        coordinator.status = "idle"
        coordinator._started = True
        coordinator._async_after_mutation = AsyncMock()
        self.addAsyncCleanup(coordinator.animations.async_shutdown)
        self.addAsyncCleanup(coordinator.controller.async_shutdown)

        lower = Request(
            request_id="scene:blue",
            source="test",
            name="Blue",
            module="scene",
            targets=frozenset({"light.strip"}),
            priority=20,
            command=LightCommand(color=(0, 0, 255)),
            activated_at=now,
            updated_at=now,
        )
        expires_at = now + timedelta(seconds=8)
        notification = Request(
            request_id="notice:r02",
            source="test",
            name="R-02 orange",
            module=MODULE_NOTIFICATION,
            targets=frozenset({"light.strip"}),
            priority=70,
            command=LightCommand(
                color=(255, 128, 0),
                animation=AnimationSpec(kind=AnimationKind.BLINK, interval=0.2),
            ),
            activated_at=now,
            updated_at=now,
            expires_at=expires_at,
        )
        await coordinator._async_apply_changes(
            await coordinator.engine.async_submit(lower)
        )
        await coordinator._async_apply_changes(
            await coordinator.engine.async_submit(notification)
        )
        await asyncio.sleep(0)
        self.assertIn("light.strip", coordinator.animations.active_targets)

        clock.value = expires_at + timedelta(seconds=1)
        await coordinator._async_expire()
        self.assertNotIn("light.strip", coordinator.animations.active_targets)
        self.assertEqual(await coordinator.engine.async_winner("light.strip"), lower)

        state.value = State("light.strip", STATE_ON, attributes)
        coordinator._async_light_state_changed(
            SimpleNamespace(
                data={
                    "entity_id": "light.strip",
                    "old_state": State("light.strip", STATE_UNAVAILABLE, attributes),
                    "new_state": state.value,
                },
                context=Context(),
            )
        )
        await asyncio.gather(*recovery_tasks)

        colors = [
            item.args[2]["rgb_color"] for item in services.async_call.await_args_list
        ]
        self.assertEqual(colors, [(0, 0, 255), (0, 0, 255)])
        self.assertNotIn((255, 128, 0), colors)
        self.assertNotIn("light.strip", coordinator.animations.active_targets)
        self.assertIsNone(coordinator.last_error)

    async def test_r01_stale_available_state_recovers_current_red_without_event(
        self,
    ) -> None:
        now = utc_now()
        attributes = {
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.RGB],
            ATTR_SUPPORTED_FEATURES: 0,
        }
        state = SimpleNamespace(value=State("light.strip", STATE_ON, attributes))
        device = SimpleNamespace(responding=True)

        async def _send_command(*args, **kwargs) -> None:
            del args, kwargs
            if not device.responding:
                raise HomeAssistantError(
                    "Failed to send request: device did not respond"
                )

        services = SimpleNamespace(async_call=AsyncMock(side_effect=_send_command))
        recovery_tasks: list[asyncio.Task[None]] = []

        def _create_task(coroutine, name: str) -> asyncio.Task[None]:
            task = asyncio.create_task(coroutine, name=name)
            recovery_tasks.append(task)
            return task

        hass = SimpleNamespace(
            states=SimpleNamespace(get=lambda target: state.value),
            services=services,
            bus=SimpleNamespace(async_fire=Mock()),
            async_create_task=_create_task,
        )
        coordinator = SmartLEDCoordinator.__new__(SmartLEDCoordinator)
        coordinator.hass = hass
        coordinator.engine = PriorityEngine()
        coordinator.controller = RGBLightController(
            hass,
            minimum_interval=0.1,
            retry_base_delay=0,
            retry_max_delay=0,
        )
        coordinator.animations = AnimationScheduler()
        coordinator._mutation_lock = asyncio.Lock()
        coordinator._manual_activated = {}
        coordinator._persisted_request_ids = set()
        coordinator._recovery_tasks = {}
        coordinator._winners = {}
        coordinator._listeners = set()
        coordinator.history = deque(maxlen=20)
        coordinator.last_error = None
        coordinator.status = "idle"
        coordinator._failed_send_recovery_delay = 0.05
        coordinator._async_after_mutation = AsyncMock()
        self.addAsyncCleanup(coordinator.animations.async_shutdown)
        self.addAsyncCleanup(coordinator.controller.async_shutdown)

        blue = Request(
            request_id="persistent:main",
            source="test",
            name="Persistent",
            module="scene",
            targets=frozenset({"light.strip"}),
            priority=95,
            command=LightCommand(color=(0, 0, 255)),
            activated_at=now,
            updated_at=now,
            persistent=True,
        )
        red = Request(
            request_id=blue.request_id,
            source=blue.source,
            name=blue.name,
            module=blue.module,
            targets=blue.targets,
            priority=blue.priority,
            command=LightCommand(color=(255, 0, 0)),
            activated_at=blue.activated_at,
            updated_at=now + timedelta(seconds=1),
            persistent=True,
        )
        await coordinator._async_apply_changes(
            await coordinator.engine.async_submit(blue)
        )
        state.value = State(
            "light.strip",
            STATE_ON,
            {
                **attributes,
                "rgb_color": (0, 0, 255),
            },
        )
        device.responding = False

        await coordinator._async_apply_changes(
            await coordinator.engine.async_submit(red)
        )

        self.assertEqual(len(recovery_tasks), 1)
        self.assertIn("device did not respond", coordinator.last_error)
        # ZHA may optimistically cache the requested red even though the
        # physical controller never received it. Recovery must still resend.
        state.value = State(
            "light.strip",
            STATE_ON,
            {
                **attributes,
                "rgb_color": (255, 0, 0),
            },
        )
        device.responding = True
        await asyncio.gather(*recovery_tasks)

        colors = [
            item.args[2]["rgb_color"] for item in services.async_call.await_args_list
        ]
        self.assertEqual(
            colors,
            [(0, 0, 255), (255, 0, 0), (255, 0, 0)],
        )
        self.assertEqual(await coordinator.engine.async_winner("light.strip"), red)
        self.assertIsNone(coordinator.last_error)

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
