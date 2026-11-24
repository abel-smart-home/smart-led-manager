"""Tests for event-driven state and numeric rules."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import Mock, patch

from homeassistant.core import State

from custom_components.smart_led_manager.core.engine import PriorityEngine
from custom_components.smart_led_manager.models import LightCommand, Request, utc_now
from custom_components.smart_led_manager.modules.rules import RuleManager


class _States:
    def __init__(self, values: dict[str, State]) -> None:
        self.values = values

    def get(self, entity_id: str) -> State | None:
        return self.values.get(entity_id)


class _Hass:
    def __init__(self, states: dict[str, State]) -> None:
        self.states = _States(states)

    def async_create_task(self, coroutine, name: str):
        return asyncio.create_task(coroutine, name=name)


class RuleManagerTests(unittest.IsolatedAsyncioTestCase):
    """Verify valid state conversion and sentinel handling."""

    async def asyncSetUp(self) -> None:
        self.submitted = []
        self.cancelled: list[str] = []

        async def submit(request) -> None:
            self.submitted.append(request)

        async def cancel(request_id: str) -> None:
            self.cancelled.append(request_id)

        self.submit = submit
        self.cancel = cancel

    async def test_state_rule_submits_and_releases(self) -> None:
        rule = {
            "id": "door",
            "type": "state",
            "name": "Door",
            "source": "binary_sensor.door",
            "operator": "equals",
            "state": "on",
            "targets": ["light.strip"],
            "priority": 70,
            "rgb_color": [255, 128, 0],
            "brightness": 180,
            "transition": 0,
        }
        hass = _Hass({"binary_sensor.door": State("binary_sensor.door", "on")})
        manager = RuleManager(
            hass,
            [rule],
            frozenset({"light.strip"}),
            self.submit,
            self.cancel,
        )

        await manager._async_evaluate_state(rule)
        hass.states.values["binary_sensor.door"] = State("binary_sensor.door", "off")
        await manager._async_evaluate_state(rule)

        self.assertEqual(self.submitted[0].request_id, "rule:door")
        self.assertEqual(self.submitted[0].command.color, (255, 128, 0))
        self.assertEqual(self.cancelled, ["rule:door"])

    async def test_numeric_rule_interpolates_and_rejects_unknown(self) -> None:
        rule = {
            "id": "temperature",
            "type": "numeric",
            "name": "Temperature",
            "source": "sensor.temperature",
            "targets": ["light.strip"],
            "priority": 40,
            "points": [
                {"value": 0, "rgb": [0, 0, 255]},
                {"value": 10, "rgb": [255, 0, 0]},
            ],
            "mode": "interpolate",
            "brightness": 255,
            "transition": 1,
            "minimum_change": 0,
            "minimum_interval": 0,
        }
        hass = _Hass({"sensor.temperature": State("sensor.temperature", "5")})
        manager = RuleManager(
            hass,
            [rule],
            frozenset({"light.strip"}),
            self.submit,
            self.cancel,
        )

        await manager._async_evaluate_numeric(rule)
        hass.states.values["sensor.temperature"] = State(
            "sensor.temperature", "unknown"
        )
        await manager._async_evaluate_numeric(rule)

        self.assertEqual(self.submitted[0].command.color, (128, 0, 128))
        self.assertEqual(self.cancelled, ["rule:temperature"])

    async def test_secondary_condition_is_reevaluated_and_unknown_not_is_safe(
        self,
    ) -> None:
        rule = {
            "id": "door_at_home",
            "type": "state",
            "name": "Door at home",
            "source": "binary_sensor.door",
            "operator": "equals",
            "state": "on",
            "targets": ["light.strip"],
            "conditions": {
                "type": "not",
                "condition": {
                    "type": "state",
                    "entity_id": "person.owner",
                    "state": "not_home",
                },
            },
            "rgb_color": [255, 128, 0],
        }
        hass = _Hass(
            {
                "binary_sensor.door": State("binary_sensor.door", "on"),
                "person.owner": State("person.owner", "unknown"),
            }
        )
        manager = RuleManager(
            hass,
            [rule],
            frozenset({"light.strip"}),
            self.submit,
            self.cancel,
        )

        await manager._async_evaluate(rule)
        hass.states.values["person.owner"] = State("person.owner", "home")
        await manager._async_evaluate(rule)

        self.assertEqual([request.request_id for request in self.submitted], ["rule:door_at_home"])
        self.assertEqual(self.cancelled, ["rule:door_at_home"])

    async def test_numeric_activation_hysteresis_is_independent_from_color(self) -> None:
        rule = {
            "id": "hot",
            "type": "numeric",
            "name": "Hot",
            "source": "sensor.temperature",
            "targets": ["light.strip"],
            "activation": {"operator": "above", "threshold": 28, "hysteresis": 2},
            "rgb_color": [255, 0, 0],
            "minimum_change": 0,
            "minimum_interval": 0,
        }
        hass = _Hass({"sensor.temperature": State("sensor.temperature", "28")})
        manager = RuleManager(
            hass,
            [rule],
            frozenset({"light.strip"}),
            self.submit,
            self.cancel,
        )

        await manager._async_evaluate(rule)
        hass.states.values["sensor.temperature"] = State("sensor.temperature", "29")
        await manager._async_evaluate(rule)
        hass.states.values["sensor.temperature"] = State("sensor.temperature", "27")
        await manager._async_evaluate(rule)
        hass.states.values["sensor.temperature"] = State("sensor.temperature", "25.9")
        await manager._async_evaluate(rule)

        self.assertEqual(len(self.submitted), 2)
        self.assertTrue(all(request.command.color == (255, 0, 0) for request in self.submitted))
        self.assertEqual(self.cancelled.count("rule:hot"), 2)

    async def test_minimum_dwell_rechecks_and_cancels_when_condition_breaks(self) -> None:
        rule = {
            "id": "door",
            "type": "state",
            "name": "Door",
            "source": "binary_sensor.door",
            "operator": "equals",
            "state": "on",
            "targets": ["light.strip"],
            "for_seconds": 30,
        }
        hass = _Hass({"binary_sensor.door": State("binary_sensor.door", "on")})
        callbacks = []

        def schedule(_hass, _delay, callback):
            callbacks.append(callback)
            return Mock()

        with patch(
            "custom_components.smart_led_manager.modules.rules.async_call_later",
            side_effect=schedule,
        ):
            manager = RuleManager(
                hass,
                [rule],
                frozenset({"light.strip"}),
                self.submit,
                self.cancel,
            )
            await manager._async_evaluate(rule)
            self.assertFalse(self.submitted)
            callbacks[0](utc_now())
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            self.assertEqual(len(self.submitted), 1)

            await manager._release(rule)
            await manager._async_evaluate(rule)
            hass.states.values["binary_sensor.door"] = State(
                "binary_sensor.door", "off"
            )
            await manager._async_evaluate(rule)
            self.assertEqual(manager._holds, {})

    async def test_repeated_event_renews_one_request_and_never_replays(self) -> None:
        rule = {
            "id": "button",
            "type": "event",
            "name": "Button",
            "trigger": {"platform": "event", "event_type": "demo"},
            "targets": ["light.strip"],
            "priority": 80,
            "rgb_color": [255, 128, 0],
            "animation": "blink",
            "period": 1,
            "duration": 8,
        }
        manager = RuleManager(
            _Hass({}),
            [rule],
            frozenset({"light.strip"}),
            self.submit,
            self.cancel,
        )

        await manager._async_event_fired(
            rule, {"trigger": {"description": "first"}}, None
        )
        first = self.submitted[-1]
        await manager._async_event_fired(
            rule, {"trigger": {"description": "second"}}, None
        )
        second = self.submitted[-1]

        self.assertEqual(first.request_id, second.request_id)
        self.assertGreater(second.expires_at, first.expires_at)
        self.assertEqual(second.command.animation.kind, "blink")
        self.assertEqual(len(manager._event_expiry), 1)

    async def test_shutdown_releases_listener_and_deferred_evaluation(self) -> None:
        rule = {
            "id": "door",
            "type": "state",
            "source": "binary_sensor.door",
            "operator": "equals",
            "state": "on",
            "targets": ["light.strip"],
        }
        hass = _Hass({"binary_sensor.door": State("binary_sensor.door", "on")})
        listener_unsubscribe = Mock()
        deferred_unsubscribe = Mock()
        with (
            patch(
                "custom_components.smart_led_manager.modules.rules."
                "async_track_state_change_event",
                return_value=listener_unsubscribe,
            ),
            patch(
                "custom_components.smart_led_manager.modules.rules.async_call_later",
                return_value=deferred_unsubscribe,
            ),
        ):
            manager = RuleManager(
                hass,
                [rule],
                frozenset({"light.strip"}),
                self.submit,
                self.cancel,
            )
            await manager.async_setup()
            manager._schedule_numeric({"id": "deferred"}, 60)

            await manager.async_shutdown()

        listener_unsubscribe.assert_called_once_with()
        deferred_unsubscribe.assert_called_once_with()
        self.assertIsNone(manager._unsubscribe)
        self.assertEqual(manager._pending, {})

    async def test_legacy_rule_defaults_enabled_and_disabled_rule_releases(
        self,
    ) -> None:
        legacy = {
            "id": "legacy",
            "type": "state",
            "source": "binary_sensor.door",
            "operator": "equals",
            "state": "on",
            "targets": ["light.strip"],
        }
        disabled = {**legacy, "id": "disabled", "enabled": False}
        hass = _Hass({"binary_sensor.door": State("binary_sensor.door", "on")})
        manager = RuleManager(
            hass,
            [legacy, disabled],
            frozenset({"light.strip"}),
            self.submit,
            self.cancel,
        )

        await manager._async_evaluate(legacy)
        await manager._async_evaluate(disabled)

        self.assertEqual(
            [request.request_id for request in self.submitted], ["rule:legacy"]
        )
        self.assertIn("rule:disabled", self.cancelled)

    async def test_shutdown_cancels_and_awaits_inflight_evaluations(self) -> None:
        hass = _Hass({})
        manager = RuleManager(
            hass,
            [],
            frozenset({"light.strip"}),
            self.submit,
            self.cancel,
        )
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def stale_evaluation() -> None:
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

        manager._create_task(stale_evaluation(), "stale_rule")
        await started.wait()

        await manager.async_shutdown()

        self.assertTrue(cancelled.is_set())
        self.assertEqual(manager._tasks, set())
        self.assertTrue(manager._stopped)

    async def test_event_task_failure_is_retrieved_and_logged(self) -> None:
        hass = _Hass({})

        async def failing_submit(_request) -> None:
            raise RuntimeError("submit failed")

        manager = RuleManager(
            hass,
            [],
            frozenset({"light.strip"}),
            failing_submit,
            self.cancel,
        )

        async def failing_evaluation() -> None:
            raise RuntimeError("evaluation failed")

        with patch(
            "custom_components.smart_led_manager.modules.rules._LOGGER.error"
        ) as logged:
            manager._create_task(failing_evaluation(), "failing_rule")
            await asyncio.sleep(0)
            await asyncio.sleep(0)

        self.assertEqual(manager._tasks, set())
        logged.assert_called_once()

    async def test_rule_with_any_unauthorized_target_is_rejected(self) -> None:
        rule = {
            "id": "unsafe",
            "type": "state",
            "source": "binary_sensor.door",
            "operator": "equals",
            "state": "on",
            "targets": ["light.strip", "light.not_managed"],
        }
        hass = _Hass({"binary_sensor.door": State("binary_sensor.door", "on")})
        manager = RuleManager(
            hass,
            [rule],
            frozenset({"light.strip"}),
            self.submit,
            self.cancel,
        )

        await manager._async_evaluate(rule)

        self.assertEqual(self.submitted, [])
        self.assertEqual(self.cancelled, ["rule:unsafe"])

    async def test_disabling_masked_rule_removes_only_its_current_intent(
        self,
    ) -> None:
        engine = PriorityEngine()

        async def submit(request) -> None:
            await engine.async_submit(request)

        async def cancel(request_id: str) -> None:
            await engine.async_cancel(request_id)

        rule = {
            "id": "door",
            "type": "state",
            "source": "binary_sensor.door",
            "operator": "equals",
            "state": "on",
            "targets": ["light.strip"],
            "priority": 40,
            "rgb_color": [0, 0, 255],
        }
        hass = _Hass({"binary_sensor.door": State("binary_sensor.door", "on")})
        manager = RuleManager(
            hass,
            [rule],
            frozenset({"light.strip"}),
            submit,
            cancel,
        )
        await manager._async_evaluate(rule)
        now = utc_now()
        blocker = Request(
            request_id="mode:blocker",
            source="test",
            name="Blocker",
            module="mode",
            targets=frozenset({"light.strip"}),
            priority=90,
            command=LightCommand(color=(255, 255, 255)),
            activated_at=now,
            updated_at=now,
        )
        await engine.async_submit(blocker)

        await manager._async_evaluate({**rule, "enabled": False})

        self.assertEqual(
            (await engine.async_winner("light.strip")).request_id, "mode:blocker"
        )
        await engine.async_cancel("mode:blocker")
        self.assertIsNone(await engine.async_winner("light.strip"))

    async def test_masked_edit_replaces_targets_and_delete_clears_current_intent(
        self,
    ) -> None:
        engine = PriorityEngine()

        async def submit(request) -> None:
            await engine.async_submit(request)

        async def cancel(request_id: str) -> None:
            await engine.async_cancel(request_id)

        hass = _Hass({"binary_sensor.door": State("binary_sensor.door", "on")})
        manager = RuleManager(
            hass,
            [],
            frozenset({"light.one", "light.two"}),
            submit,
            cancel,
        )
        old = {
            "id": "door",
            "type": "state",
            "name": "Door",
            "source": "binary_sensor.door",
            "operator": "equals",
            "state": "on",
            "targets": ["light.one"],
            "priority": 40,
            "rgb_color": [0, 0, 255],
        }
        await manager._async_evaluate(old)
        now = utc_now()
        blocker = Request(
            request_id="mode:blocker",
            source="test",
            name="Blocker",
            module="test",
            targets=frozenset({"light.one", "light.two"}),
            priority=90,
            command=LightCommand(color=(255, 255, 255)),
            activated_at=now,
            updated_at=now,
        )
        await engine.async_submit(blocker)
        updated = {
            **old,
            "source": "binary_sensor.door",
            "targets": ["light.two"],
            "priority": 60,
            "rgb_color": [255, 0, 0],
        }

        await manager._async_evaluate(updated)

        self.assertEqual(
            (await engine.async_winner("light.one")).request_id, "mode:blocker"
        )
        self.assertEqual(
            (await engine.async_winner("light.two")).request_id, "mode:blocker"
        )
        await engine.async_cancel(blocker.request_id)
        self.assertIsNone(await engine.async_winner("light.one"))
        recovered = await engine.async_winner("light.two")
        self.assertEqual(recovered.request_id, "rule:door")
        self.assertEqual(recovered.priority, 60)
        self.assertEqual(recovered.command.color, (255, 0, 0))

        await manager._release(updated)

        self.assertIsNone(await engine.async_winner("light.two"))


if __name__ == "__main__":
    unittest.main()
