"""Concurrency checks for the Home Assistant-independent decision core."""

from __future__ import annotations

import asyncio
import unittest
from datetime import UTC, datetime, timedelta

from custom_components.smart_led_manager.core.engine import PriorityEngine
from custom_components.smart_led_manager.models import LightCommand, Request

BASE = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


def _request(request_id: str, priority: int, offset: int) -> Request:
    """Create a deterministic request for concurrent submission."""
    timestamp = BASE + timedelta(seconds=offset)
    return Request(
        request_id=request_id,
        source="concurrency-test",
        name=request_id,
        module="test",
        targets=frozenset({"light.strip"}),
        priority=priority,
        command=LightCommand(color=(offset, 0, 0)),
        activated_at=timestamp,
        updated_at=timestamp,
    )


class ConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    """Verify that competing mutations remain atomic and deterministic."""

    async def test_simultaneous_submissions_keep_all_requests(self) -> None:
        engine = PriorityEngine(clock=lambda: BASE + timedelta(minutes=1))
        requests = tuple(_request(f"request-{index}", 50, index) for index in range(20))

        await asyncio.gather(
            *(engine.async_submit(request) for request in reversed(requests))
        )

        winner = await engine.async_winner("light.strip")
        self.assertIsNotNone(winner)
        self.assertEqual(winner.request_id, "request-19")  # type: ignore[union-attr]
        self.assertEqual(len(await engine.async_requests()), len(requests))

    async def test_concurrent_lower_priority_update_stays_masked(self) -> None:
        engine = PriorityEngine(clock=lambda: BASE + timedelta(minutes=1))
        high = _request("alarm", 100, 1)
        initial_low = _request("temperature", 40, 2)
        updated_low = _request("temperature", 40, 3)
        await engine.async_submit(initial_low)
        await engine.async_submit(high)

        update_changes, _ = await asyncio.gather(
            engine.async_submit(updated_low),
            engine.async_winner("light.strip"),
        )

        self.assertEqual(update_changes, ())
        recovery = await engine.async_cancel("alarm")
        self.assertEqual(recovery[0].current, updated_low)


if __name__ == "__main__":
    unittest.main()
