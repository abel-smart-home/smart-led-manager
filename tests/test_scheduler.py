"""Tests for cancellable expiration and animation scheduling."""

from __future__ import annotations

import asyncio
import unittest
from datetime import timedelta

from custom_components.smart_led_manager.core.scheduler import (
    AnimationScheduler,
    DeadlineScheduler,
)
from custom_components.smart_led_manager.models import (
    AnimationKind,
    AnimationSpec,
    LightCommand,
    Request,
    utc_now,
)


def _request(animation: AnimationSpec) -> Request:
    now = utc_now()
    return Request(
        request_id="animated",
        source="test",
        name="Animated",
        module="test",
        targets=frozenset({"light.strip"}),
        priority=70,
        command=LightCommand(color=(255, 0, 0), brightness=200, animation=animation),
        activated_at=now,
        updated_at=now,
    )


class SchedulerTests(unittest.IsolatedAsyncioTestCase):
    """Verify replacement and cancellation behavior."""

    async def test_deadline_callback_can_schedule_next_deadline(self) -> None:
        scheduler = DeadlineScheduler()
        called: list[int] = []
        completed = asyncio.Event()

        async def second() -> None:
            called.append(2)
            completed.set()

        async def first() -> None:
            called.append(1)
            scheduler.schedule(utc_now() + timedelta(milliseconds=10), second)

        scheduler.schedule(utc_now() + timedelta(milliseconds=10), first)
        await asyncio.wait_for(completed.wait(), timeout=1)

        self.assertEqual(called, [1, 2])
        await scheduler.async_shutdown()

    async def test_new_winner_cancels_continuous_animation(self) -> None:
        scheduler = AnimationScheduler()
        frames: list[LightCommand] = []

        async def apply(command: LightCommand) -> None:
            frames.append(command)

        await scheduler.async_apply(
            "light.strip",
            _request(AnimationSpec(kind=AnimationKind.BLINK, interval=0.2)),
            apply,
        )
        await asyncio.sleep(0.12)
        await scheduler.async_apply("light.strip", _request(AnimationSpec()), apply)

        self.assertNotIn("light.strip", scheduler.active_targets)
        self.assertTrue(frames[-1].turn_on)
        self.assertEqual(frames[-1].color, (255, 0, 0))
        await scheduler.async_shutdown()

    async def test_finite_pulse_settles_on_base_command(self) -> None:
        scheduler = AnimationScheduler()
        frames: list[LightCommand] = []

        async def apply(command: LightCommand) -> None:
            frames.append(command)

        await scheduler.async_apply(
            "light.strip",
            _request(
                AnimationSpec(kind=AnimationKind.PULSE, interval=0.4, repetitions=1)
            ),
            apply,
        )
        await asyncio.sleep(0.55)

        self.assertEqual(frames[-1].brightness, 200)
        self.assertNotIn("light.strip", scheduler.active_targets)


if __name__ == "__main__":
    unittest.main()
