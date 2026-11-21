"""Tests for the capability-aware RGB controller."""

from __future__ import annotations

import asyncio
import unittest
from time import monotonic

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    ColorMode,
)
from homeassistant.const import ATTR_SUPPORTED_FEATURES, STATE_OFF, STATE_UNAVAILABLE
from homeassistant.core import State

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
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, object]]] = []

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
