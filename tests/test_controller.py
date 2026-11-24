"""Tests for the capability-aware RGB controller."""

from __future__ import annotations

import asyncio
import unittest
from time import monotonic
from unittest.mock import AsyncMock, call, patch

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    ColorMode,
)
from homeassistant.const import (
    ATTR_SUPPORTED_FEATURES,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import State
from homeassistant.exceptions import HomeAssistantError

from custom_components.smart_led_manager.controllers.base import (
    ApplyStatus,
    UnsupportedLightCommandError,
)
from custom_components.smart_led_manager.controllers.rgb import RGBLightController
from custom_components.smart_led_manager.models import LightCommand


class _States:
    def __init__(self, values: dict[str, State]) -> None:
        self.values = values

    def get(self, entity_id: str) -> State | None:
        return self.values.get(entity_id)


class _Services:
    def __init__(self, outcomes: list[Exception | None] | None = None) -> None:
        self.calls: list[tuple[str, str, dict[str, object]]] = []
        self.outcomes = list(outcomes or [])
        self.attempted = asyncio.Event()

    async def async_call(
        self,
        domain: str,
        service: str,
        data: dict[str, object],
        *,
        blocking: bool,
        context,
    ) -> None:
        self.calls.append((domain, service, data))
        self.attempted.set()
        if self.outcomes:
            outcome = self.outcomes.pop(0)
            if outcome is not None:
                raise outcome


class _Hass:
    def __init__(self, state: State) -> None:
        self.states = _States({state.entity_id: state})
        self.services = _Services()


def _state(value: str = STATE_OFF, modes: list[str | ColorMode] | None = None) -> State:
    return State(
        "light.strip",
        value,
        {
            ATTR_SUPPORTED_COLOR_MODES: modes or [ColorMode.RGB],
            ATTR_SUPPORTED_FEATURES: 0,
        },
    )


class ControllerTests(unittest.IsolatedAsyncioTestCase):
    """Exercise deduplication, offline retention, and stale work replacement."""

    async def test_applies_and_deduplicates_command(self) -> None:
        hass = _Hass(_state())
        controller = RGBLightController(hass, minimum_interval=0.1)
        command = LightCommand(color=(1, 2, 3), brightness=100)

        first = await controller.async_apply("light.strip", command)
        second = await controller.async_apply("light.strip", command)

        self.assertEqual(first.status, ApplyStatus.APPLIED)
        self.assertEqual(second.status, ApplyStatus.DEDUPLICATED)
        self.assertEqual(len(hass.services.calls), 1)
        self.assertEqual(hass.services.calls[0][2][ATTR_RGB_COLOR], (1, 2, 3))
        self.assertEqual(hass.services.calls[0][2][ATTR_BRIGHTNESS], 100)
        await controller.async_shutdown()

    async def test_retains_offline_intent_and_retries_once_available(self) -> None:
        hass = _Hass(_state(STATE_UNAVAILABLE))
        controller = RGBLightController(hass, minimum_interval=0.1)

        result = await controller.async_apply(
            "light.strip", LightCommand(color=(4, 5, 6))
        )
        hass.states.values["light.strip"] = _state()
        retry = await controller.async_retry("light.strip")

        self.assertEqual(result.status, ApplyStatus.OFFLINE)
        self.assertEqual(retry.status, ApplyStatus.APPLIED)
        self.assertEqual(len(hass.services.calls), 1)
        await controller.async_shutdown()

    async def test_recovery_rechecks_group_status_and_current_authorization(
        self,
    ) -> None:
        hass = _Hass(_state(STATE_UNAVAILABLE))
        permitted = True
        target = "light.strip"
        controller = RGBLightController(hass, may_send=lambda _: permitted)
        intent = LightCommand(color=(4, 5, 6))
        assert (
            await controller.async_apply(target, intent)
        ).status is ApplyStatus.OFFLINE
        hass.states.values[target] = State(
            target, STATE_OFF, {**_state().attributes, "entity_id": ["light.other"]}
        )
        assert (await controller.async_retry(target)).status is ApplyStatus.SUPERSEDED
        assert not controller.pending_targets
        permitted = False
        hass.states.values[target] = _state()
        assert (
            await controller.async_apply(target, intent)
        ).status is ApplyStatus.SUPERSEDED
        assert not hass.services.calls
        await controller.async_shutdown()

    @patch(
        "custom_components.smart_led_manager.controllers.rgb.asyncio.sleep",
        new_callable=AsyncMock,
    )
    async def test_transient_send_failures_use_bounded_progressive_retry(
        self, sleep: AsyncMock
    ) -> None:
        hass = _Hass(_state(STATE_UNAVAILABLE))
        hass.services = _Services(
            [
                TimeoutError("Zigbee timeout 1"),
                HomeAssistantError("Zigbee timeout 2"),
                None,
            ]
        )
        controller = RGBLightController(
            hass,
            minimum_interval=0.1,
            max_recovery_attempts=3,
            retry_base_delay=1,
            retry_max_delay=4,
        )
        retained = await controller.async_apply(
            "light.strip", LightCommand(color=(0, 0, 255))
        )
        hass.states.values["light.strip"] = _state()

        result = await controller.async_retry("light.strip")

        self.assertEqual(retained.status, ApplyStatus.OFFLINE)
        self.assertEqual(result.status, ApplyStatus.APPLIED)
        self.assertEqual(len(hass.services.calls), 3)
        self.assertEqual(sleep.await_args_list, [call(1.0), call(2.0)])
        await controller.async_shutdown()

    @patch(
        "custom_components.smart_led_manager.controllers.rgb.asyncio.sleep",
        new_callable=AsyncMock,
    )
    async def test_retry_exhaustion_retains_current_intent(
        self, sleep: AsyncMock
    ) -> None:
        hass = _Hass(_state(STATE_UNAVAILABLE))
        hass.services = _Services(
            [HomeAssistantError("device did not respond") for _ in range(3)]
        )
        controller = RGBLightController(
            hass,
            minimum_interval=0.1,
            max_recovery_attempts=3,
            retry_base_delay=1,
            retry_max_delay=4,
        )
        await controller.async_apply("light.strip", LightCommand(color=(0, 0, 255)))
        hass.states.values["light.strip"] = _state()

        result = await controller.async_retry("light.strip")

        self.assertEqual(result.status, ApplyStatus.OFFLINE)
        self.assertIn("failed after 3 attempts", result.detail)
        self.assertEqual(len(hass.services.calls), 3)
        self.assertEqual(sleep.await_args_list, [call(1.0), call(2.0)])
        self.assertIn("light.strip", controller.pending_targets)
        await controller.async_shutdown()

    @patch(
        "custom_components.smart_led_manager.controllers.rgb.asyncio.sleep",
        new_callable=AsyncMock,
    )
    async def test_default_recovery_window_is_bounded_and_progressive(
        self, sleep: AsyncMock
    ) -> None:
        hass = _Hass(_state(STATE_UNAVAILABLE))
        hass.services = _Services(
            [HomeAssistantError("device did not respond") for _ in range(8)]
        )
        controller = RGBLightController(hass, minimum_interval=0.1)
        await controller.async_apply("light.strip", LightCommand(color=(255, 0, 0)))
        hass.states.values["light.strip"] = _state(STATE_ON)

        result = await controller.async_retry("light.strip")

        self.assertEqual(result.status, ApplyStatus.OFFLINE)
        self.assertIn("failed after 8 attempts", result.detail)
        self.assertEqual(len(hass.services.calls), 8)
        self.assertEqual(
            sleep.await_args_list,
            [call(5.0), call(10.0), call(20.0), call(40.0)] + [call(60.0)] * 3,
        )
        self.assertIn("light.strip", controller.pending_targets)
        await controller.async_shutdown()

    async def test_cancel_during_retry_backoff_discards_current_intent(self) -> None:
        hass = _Hass(_state(STATE_UNAVAILABLE))
        hass.services = _Services([HomeAssistantError("device did not respond")])
        controller = RGBLightController(
            hass,
            minimum_interval=0.1,
            retry_base_delay=60,
            retry_max_delay=60,
        )
        await controller.async_apply("light.strip", LightCommand(color=(255, 128, 0)))
        hass.states.values["light.strip"] = _state()
        pending = asyncio.create_task(controller.async_retry("light.strip"))
        await hass.services.attempted.wait()

        await controller.async_cancel("light.strip")
        result = await pending

        self.assertEqual(result.status, ApplyStatus.SUPERSEDED)
        self.assertEqual(len(hass.services.calls), 1)
        self.assertNotIn("light.strip", controller.pending_targets)
        await controller.async_shutdown()

    async def test_new_intent_supersedes_command_waiting_in_retry_backoff(
        self,
    ) -> None:
        hass = _Hass(_state(STATE_UNAVAILABLE))
        hass.services = _Services([HomeAssistantError("device did not respond"), None])
        controller = RGBLightController(
            hass,
            minimum_interval=0.1,
            retry_base_delay=1,
            retry_max_delay=1,
        )
        backoff_started = asyncio.Event()
        release_backoff = asyncio.Event()

        async def _wait_for_release(delay: float) -> None:
            self.assertEqual(delay, 1.0)
            backoff_started.set()
            await release_backoff.wait()

        with patch(
            "custom_components.smart_led_manager.controllers.rgb.asyncio.sleep",
            side_effect=_wait_for_release,
        ):
            await controller.async_apply(
                "light.strip", LightCommand(color=(255, 128, 0))
            )
            hass.states.values["light.strip"] = _state()
            old = asyncio.create_task(controller.async_retry("light.strip"))
            await backoff_started.wait()
            new = asyncio.create_task(
                controller.async_apply("light.strip", LightCommand(color=(0, 0, 255)))
            )
            release_backoff.set()
            old_result, new_result = await asyncio.gather(old, new)

        self.assertEqual(old_result.status, ApplyStatus.SUPERSEDED)
        self.assertEqual(new_result.status, ApplyStatus.APPLIED)
        self.assertEqual(
            [item[2][ATTR_RGB_COLOR] for item in hass.services.calls],
            [(255, 128, 0), (0, 0, 255)],
        )
        await controller.async_shutdown()

    async def test_shutdown_during_retry_backoff_cancels_all_work(self) -> None:
        hass = _Hass(_state(STATE_UNAVAILABLE))
        hass.services = _Services([HomeAssistantError("device did not respond")])
        controller = RGBLightController(
            hass,
            minimum_interval=0.1,
            retry_base_delay=60,
            retry_max_delay=60,
        )
        await controller.async_apply("light.strip", LightCommand(color=(0, 0, 255)))
        hass.states.values["light.strip"] = _state()
        pending = asyncio.create_task(controller.async_retry("light.strip"))
        await hass.services.attempted.wait()

        await controller.async_shutdown()
        result = await pending

        self.assertEqual(result.status, ApplyStatus.SUPERSEDED)
        self.assertEqual(len(hass.services.calls), 1)
        self.assertEqual(controller.pending_targets, frozenset())
        self.assertEqual(controller._workers, {})

    async def test_invalidated_cached_state_forces_physical_resend(self) -> None:
        hass = _Hass(_state())
        controller = RGBLightController(hass, minimum_interval=0.1)
        command = LightCommand(color=(0, 0, 255))
        first = await controller.async_apply("light.strip", command)
        hass.states.values["light.strip"] = State(
            "light.strip",
            STATE_ON,
            {
                ATTR_SUPPORTED_COLOR_MODES: [ColorMode.RGB],
                ATTR_SUPPORTED_FEATURES: 0,
                ATTR_RGB_COLOR: (0, 0, 255),
            },
        )
        controller.invalidate_applied_state("light.strip")

        recovered = await controller.async_retry("light.strip")

        self.assertEqual(first.status, ApplyStatus.APPLIED)
        self.assertEqual(recovered.status, ApplyStatus.APPLIED)
        self.assertEqual(len(hass.services.calls), 2)
        await controller.async_shutdown()

    async def test_rejects_rgb_for_non_color_light(self) -> None:
        hass = _Hass(_state(modes=[ColorMode.COLOR_TEMP]))
        controller = RGBLightController(hass, minimum_interval=0.1)

        with self.assertRaises(UnsupportedLightCommandError):
            await controller.async_apply("light.strip", LightCommand(color=(255, 0, 0)))

        self.assertEqual(hass.services.calls, [])
        await controller.async_shutdown()

    async def test_new_desired_state_supersedes_delayed_frame(self) -> None:
        hass = _Hass(_state())
        controller = RGBLightController(hass, minimum_interval=0.1)
        controller._last_sent["light.strip"] = monotonic()

        old = asyncio.create_task(
            controller.async_apply("light.strip", LightCommand(color=(255, 0, 0)))
        )
        await asyncio.sleep(0.01)
        new = asyncio.create_task(
            controller.async_apply("light.strip", LightCommand(color=(0, 0, 255)))
        )
        old_result, new_result = await asyncio.gather(old, new)

        self.assertEqual(old_result.status, ApplyStatus.SUPERSEDED)
        self.assertEqual(new_result.status, ApplyStatus.APPLIED)
        self.assertEqual(len(hass.services.calls), 1)
        self.assertEqual(hass.services.calls[0][2][ATTR_RGB_COLOR], (0, 0, 255))
        await controller.async_shutdown()

    async def test_cancel_discards_delayed_stale_command(self) -> None:
        """A winner release cannot leak a command waiting on the rate limit."""
        hass = _Hass(_state())
        controller = RGBLightController(hass, minimum_interval=0.1)
        controller._last_sent["light.strip"] = monotonic()

        pending = asyncio.create_task(
            controller.async_apply("light.strip", LightCommand(color=(255, 128, 0)))
        )
        await asyncio.sleep(0.01)
        await controller.async_cancel("light.strip")
        result = await pending

        self.assertEqual(result.status, ApplyStatus.SUPERSEDED)
        self.assertNotIn("light.strip", controller.pending_targets)
        self.assertEqual(hass.services.calls, [])
        await controller.async_shutdown()

    async def test_context_cache_is_pruned_without_event_context(self) -> None:
        """Platforms that drop Context cannot grow attribution memory forever."""
        controller = RGBLightController(_Hass(_state()), minimum_interval=0.1)
        controller._contexts["expired"] = 0

        self.assertFalse(controller.is_own_context(None))
        self.assertEqual(controller._contexts, {})


if __name__ == "__main__":
    unittest.main()
