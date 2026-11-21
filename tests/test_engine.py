"""Behavioral tests for the per-target priority engine."""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from custom_components.smart_led_manager.core.engine import PriorityEngine
from custom_components.smart_led_manager.models import LightCommand, Request, TieBreaker

BASE = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


class MutableClock:
    """Deterministic clock used by expiration tests."""

    def __init__(self, value: datetime = BASE) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def request(
    request_id: str,
    priority: int,
    color: tuple[int, int, int],
    *,
    targets: frozenset[str] = frozenset({"light.one"}),
    activated_at: datetime = BASE,
    expires_at: datetime | None = None,
    persistent: bool = False,
) -> Request:
    """Build a valid engine request."""

    return Request(
        request_id=request_id,
        source="test",
        name=request_id,
        module="test",
        targets=targets,
        priority=priority,
        command=LightCommand(color=color),
        activated_at=activated_at,
        updated_at=activated_at,
        expires_at=expires_at,
        persistent=persistent,
    )


class EngineTests(unittest.IsolatedAsyncioTestCase):
    """Verify priority, lifetime and concurrency-facing semantics."""

    async def asyncSetUp(self) -> None:
        self.clock = MutableClock()
        self.engine = PriorityEngine(clock=self.clock)

    async def test_higher_priority_wins_and_lower_is_retained(self) -> None:
        low = request("temperature", 40, (0, 0, 255))
        high = request("alarm", 100, (255, 0, 0))

        await self.engine.async_submit(low)
        changes = await self.engine.async_submit(high)

        self.assertEqual(changes[0].previous, low)
        self.assertEqual(changes[0].current, high)
        self.assertEqual(await self.engine.async_winner("light.one"), high)
        self.assertEqual(len(await self.engine.async_requests()), 2)

    async def test_ending_winner_recovers_updated_lower_request(self) -> None:
        low = request("sensor", 40, (0, 0, 255))
        high = request("notification", 70, (128, 0, 255))
        await self.engine.async_submit(low)
        await self.engine.async_submit(high)
        updated_low = replace(
            low,
            command=LightCommand(color=(0, 255, 0)),
            updated_at=BASE + timedelta(seconds=1),
        )

        hidden_change = await self.engine.async_submit(updated_low)
        recovery = await self.engine.async_cancel(high.request_id)

        self.assertEqual(hidden_change, ())
        self.assertEqual(recovery[0].current, updated_low)

    async def test_resolution_is_independent_for_each_target(self) -> None:
        shared = request(
            "shared",
            50,
            (1, 2, 3),
            targets=frozenset({"light.one", "light.two"}),
        )
        only_one = request("only-one", 60, (4, 5, 6))

        await self.engine.async_submit(shared)
        await self.engine.async_submit(only_one)

        self.assertEqual(await self.engine.async_winner("light.one"), only_one)
        self.assertEqual(await self.engine.async_winner("light.two"), shared)

    async def test_ties_are_deterministic_for_all_policies(self) -> None:
        oldest = request("z-old", 50, (1, 1, 1), activated_at=BASE)
        newest = request(
            "a-new", 50, (2, 2, 2), activated_at=BASE + timedelta(seconds=1)
        )
        await self.engine.async_submit(oldest)
        await self.engine.async_submit(newest)

        self.assertEqual(
            (await self.engine.async_winner("light.one")).request_id, "a-new"
        )  # type: ignore[union-attr]
        await self.engine.async_set_tie_breaker(TieBreaker.OLDEST)
        self.assertEqual(
            (await self.engine.async_winner("light.one")).request_id, "z-old"
        )  # type: ignore[union-attr]
        await self.engine.async_set_tie_breaker(TieBreaker.LEXICAL)
        self.assertEqual(
            (await self.engine.async_winner("light.one")).request_id, "a-new"
        )  # type: ignore[union-attr]

    async def test_lexical_fallback_breaks_identical_newest_tie(self) -> None:
        await self.engine.async_submit(request("b", 50, (1, 1, 1)))
        await self.engine.async_submit(request("a", 50, (2, 2, 2)))

        winner = await self.engine.async_winner("light.one")

        self.assertEqual(winner.request_id, "a")  # type: ignore[union-attr]

    async def test_expiration_discards_request_and_recovers_lower(self) -> None:
        low = request("base", 20, (1, 1, 1))
        temporary = request(
            "temporary",
            70,
            (2, 2, 2),
            expires_at=BASE + timedelta(seconds=5),
        )
        await self.engine.async_submit(low)
        await self.engine.async_submit(temporary)
        self.clock.value = BASE + timedelta(seconds=5)

        changes = await self.engine.async_expire()

        self.assertEqual(changes[0].previous, temporary)
        self.assertEqual(changes[0].current, low)
        self.assertNotIn(temporary, await self.engine.async_requests())

    async def test_cancel_and_deactivate_are_idempotent(self) -> None:
        item = request("item", 50, (1, 1, 1))
        await self.engine.async_submit(item)

        first = await self.engine.async_deactivate("item")
        second = await self.engine.async_deactivate("item")
        cancelled = await self.engine.async_cancel("item")
        missing = await self.engine.async_cancel("item")

        self.assertEqual(first[0].previous, item)
        self.assertIsNone(first[0].current)
        self.assertEqual(second, ())
        self.assertEqual(cancelled, ())
        self.assertEqual(missing, ())

    async def test_restore_skips_expired_and_serializes_persistent_only(self) -> None:
        valid = request("valid", 50, (1, 2, 3), persistent=True)
        transient = request("transient", 60, (2, 3, 4))
        expired = request(
            "expired",
            100,
            (9, 9, 9),
            expires_at=BASE,
            persistent=True,
        )

        await self.engine.async_restore(
            [valid.to_dict(), transient.to_dict(), expired.to_dict()]
        )
        serialized = await self.engine.async_serialize(persistent_only=True)

        self.assertEqual([item["request_id"] for item in serialized], ["valid"])
        self.assertEqual(
            (await self.engine.async_winner("light.one")).request_id, "transient"
        )  # type: ignore[union-attr]

    async def test_target_change_releases_removed_target(self) -> None:
        original = request(
            "moving",
            50,
            (1, 2, 3),
            targets=frozenset({"light.one", "light.two"}),
        )
        moved = replace(
            original,
            targets=frozenset({"light.two"}),
            updated_at=BASE + timedelta(seconds=1),
        )
        await self.engine.async_submit(original)

        changes = await self.engine.async_submit(moved)

        self.assertEqual(
            [change.target for change in changes], ["light.one", "light.two"]
        )
        self.assertIsNone(changes[0].current)
        self.assertEqual(changes[1].current, moved)

    async def test_next_expiry_ignores_inactive_and_past_requests(self) -> None:
        early = request("early", 10, (1, 1, 1), expires_at=BASE + timedelta(seconds=5))
        late = request("late", 20, (2, 2, 2), expires_at=BASE + timedelta(seconds=10))
        await self.engine.async_submit(early)
        await self.engine.async_submit(late)
        await self.engine.async_deactivate("early")

        self.assertEqual(await self.engine.async_next_expiry(), late.expires_at)


if __name__ == "__main__":
    unittest.main()
