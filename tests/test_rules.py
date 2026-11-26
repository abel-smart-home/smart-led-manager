"""Tests for event-driven state and numeric rules."""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from homeassistant.core import Event, State

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


class _Bus:
    def __init__(self) -> None:
        self.listeners = []

    def async_listen(self, event_type, callback):
        unsubscribe = Mock()
        self.listeners.append((event_type, callback, unsubscribe))
        return unsubscribe


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

    async def test_state_release_wait_restarts_after_recovery_and_ends_on_unknown(
        self,
    ) -> None:
        entity = "binary_sensor.door"
        rule = {
            "id": "door",
            "type": "state",
            "source": entity,
            "state": "on",
            "targets": ["light.strip"],
            "release_seconds": 12,
        }
        hass = _Hass({entity: State(entity, "on")})
        manager = RuleManager(
            hass, [rule], frozenset({"light.strip"}), self.submit, self.cancel
        )
        timers = []

        def schedule(_hass, delay, callback):
            unsubscribe = Mock()
            timers.append((delay, callback, unsubscribe))
            return unsubscribe

        async def update(value):
            hass.states.values[entity] = State(entity, value)
            await manager._async_evaluate(rule)

        with patch(
            "custom_components.smart_led_manager.modules.rules.async_call_later",
            side_effect=schedule,
        ):
            await update("on")
            await update("off")
            await update("off")
            self.assertEqual([timer[0] for timer in timers], [12])
            self.assertFalse(self.cancelled)
            await update("on")
            timers[0][2].assert_called_once()
            await update("off")
            self.assertEqual(len(timers), 2)
            timers[-1][1](utc_now())
            await asyncio.sleep(0)
            self.assertEqual(self.cancelled, ["rule:door"])
            await update("on")
            await update("off")
            await update("unavailable")
            timers[-1][2].assert_called_once()
            self.assertEqual(self.cancelled, ["rule:door", "rule:door"])

    async def test_rule_releases_when_calibrated_unit_changes_and_recovers(
        self,
    ) -> None:
        entity = "sensor.demo"
        rule = {
            "id": "power",
            "type": "numeric",
            "source": entity,
            "source_unit": "W",
            "rgb_color": [255, 0, 0],
            "targets": ["light.strip"],
        }
        hass = _Hass({entity: State(entity, "8", {"unit_of_measurement": "W"})})
        manager = RuleManager(
            hass, [rule], frozenset({"light.strip"}), self.submit, self.cancel
        )
        await manager._async_evaluate(rule)
        hass.states.values[entity] = State(entity, "8", {"unit_of_measurement": "kW"})
        await manager._async_evaluate(rule)
        self.assertEqual(len(self.submitted), 1)
        self.assertEqual(self.cancelled, ["rule:power"])
        hass.states.values[entity] = State(entity, "8", {"unit_of_measurement": "W"})
        await manager._async_evaluate(rule)
        self.assertEqual(len(self.submitted), 2)

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

        self.assertEqual(
            [request.request_id for request in self.submitted], ["rule:door_at_home"]
        )
        self.assertEqual(self.cancelled, ["rule:door_at_home"])

    async def test_numeric_activation_hysteresis_is_independent_from_color(
        self,
    ) -> None:
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
        self.assertTrue(
            all(request.command.color == (255, 0, 0) for request in self.submitted)
        )
        self.assertEqual(self.cancelled.count("rule:hot"), 2)

    async def test_minimum_dwell_rechecks_and_cancels_when_condition_breaks(
        self,
    ) -> None:
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

    async def test_active_event_moves_to_current_group_members_without_extending_lifetime(
        self,
    ) -> None:
        root, first, second = "light.root", "light.first", "light.second"
        states = {
            root: State(root, "on", {"entity_id": [first]}),
            first: State(first, "off"),
            second: State(second, "off"),
        }
        rule = {
            "id": "dynamic-event",
            "type": "event",
            "duration": 8,
            "trigger": {"platform": "event", "event_type": "demo"},
            "target_selection": {"groups": [root]},
        }
        manager = RuleManager(
            _Hass(states), [rule], frozenset({first, second}), self.submit, self.cancel
        )
        await manager._async_refresh_event_targets(rule)
        assert not self.submitted
        await manager._async_event_fired(rule, {}, None)
        assert manager.allows_target("rule:dynamic-event", first)
        original = self.submitted[-1]
        states[root] = State(root, "on", {"entity_id": [second]})
        assert not manager.allows_target("rule:dynamic-event", first)
        await manager._async_refresh_event_targets(rule)
        moved = self.submitted[-1]
        assert moved.request_id == original.request_id
        assert moved.targets == frozenset({second})
        assert moved.expires_at == original.expires_at
        await manager._async_refresh_event_targets(rule)
        assert len(self.submitted) == 2
        states.pop(second)
        await manager._async_refresh_event_targets(rule)
        assert self.cancelled[-1] == original.request_id
        states[second] = State(second, "off")
        await manager._async_refresh_event_targets(rule)
        assert len(self.submitted) == 2

        assert original.expires_at is not None
        with patch(
            "custom_components.smart_led_manager.modules.rules.utc_now",
            return_value=original.expires_at,
        ):
            await manager._async_event_fired(rule, {}, None)
        last_expiry = self.submitted[-1].expires_at
        with patch(
            "custom_components.smart_led_manager.modules.rules.utc_now",
            return_value=last_expiry,
        ):
            assert not manager.allows_target("rule:dynamic-event", second)
            await manager._async_refresh_event_targets(rule)
        assert len(self.submitted) == 3
        assert not manager._event_expiry

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

    async def test_dynamic_targets_track_nested_groups_and_all_registries(self) -> None:
        rule = {
            "id": "dynamic",
            "type": "state",
            "source": "binary_sensor.door",
            "operator": "equals",
            "state": "on",
            "target_selection": {
                "entities": [],
                "zones": [],
                "areas": [],
                "labels": ["accent"],
                "groups": ["light.group_a"],
                "all_managed": False,
            },
        }
        hass = _Hass(
            {
                "binary_sensor.door": State("binary_sensor.door", "on"),
                "light.group_a": State(
                    "light.group_a", "on", {"entity_id": ["light.group_b"]}
                ),
                "light.group_b": State(
                    "light.group_b", "on", {"entity_id": ["light.strip"]}
                ),
            }
        )
        hass.bus = _Bus()
        listener_unsubscribe = Mock()
        manager = RuleManager(
            hass,
            [rule],
            frozenset({"light.strip"}),
            self.submit,
            self.cancel,
        )
        with (
            patch(
                "custom_components.smart_led_manager.modules.rules."
                "async_track_state_change_event",
                return_value=listener_unsubscribe,
            ) as track_states,
            patch(
                "custom_components.smart_led_manager.modules.targeting.lr.async_get",
                return_value=Mock(labels={"accent": object()}),
            ),
            patch.object(
                manager._targets, "_registry_entities", return_value={"light.strip"}
            ),
        ):
            await manager.async_setup()

        tracked = set(track_states.call_args.args[1])
        self.assertEqual(
            tracked,
            {"binary_sensor.door", "light.group_a", "light.group_b", "light.strip"},
        )
        self.assertEqual(len(hass.bus.listeners), 4)

        await manager.async_shutdown()
        listener_unsubscribe.assert_called_once_with()
        for _event_type, _callback, unsubscribe in hass.bus.listeners:
            unsubscribe.assert_called_once_with()

    async def test_late_nested_members_recover_and_removed_members_are_unsubscribed(
        self,
    ) -> None:
        root, nested, leaf = "light.root", "light.nested", "light.strip"
        states = {
            root: State(root, "on", {"entity_id": []}),
            "binary_sensor.door": State("binary_sensor.door", "on"),
        }
        hass = _Hass(states)
        rule = {
            "id": "groups",
            "type": "state",
            "source": "binary_sensor.door",
            "state": "on",
            "target_selection": {"groups": [root]},
        }
        manager = RuleManager(hass, [rule], frozenset({leaf}), self.submit, self.cancel)
        listeners = []

        def track(_hass, entities, _listener):
            unsubscribe = Mock()
            listeners.append((set(entities), unsubscribe))
            return unsubscribe

        async def change(entity_id: str, state: State) -> None:
            old = states.get(entity_id)
            states[entity_id] = state
            manager._async_state_changed(
                Event(
                    "state_changed",
                    {"entity_id": entity_id, "old_state": old, "new_state": state},
                )
            )
            await asyncio.sleep(0)

        with patch(
            "custom_components.smart_led_manager.modules.rules.async_track_state_change_event",
            track,
        ):
            await manager.async_setup()
            assert listeners[-1][0] == {root, "binary_sensor.door"}
            await change(root, State(root, "on", {"entity_id": [nested]}))
            assert listeners[-1][0] == {root, nested, "binary_sensor.door"}
            assert not self.submitted
            assert not manager.allows_target("rule:groups", leaf)
            await change(nested, State(nested, "on", {"entity_id": [leaf]}))
            assert listeners[-1][0] == {root, nested, leaf, "binary_sensor.door"}
            assert not self.submitted
            await change(leaf, State(leaf, "unavailable"))
            assert self.submitted[-1].targets == frozenset({leaf})
            assert manager.allows_target("rule:groups", leaf)
            await change(root, State(root, "on", {"entity_id": [leaf]}))
            assert listeners[-1][0] == {root, leaf, "binary_sensor.door"}
            await manager.async_shutdown()
        for _entities, unsubscribe in listeners:
            unsubscribe.assert_called_once_with()

    async def test_overnight_schedule_closes_on_restart_without_source_event(
        self,
    ) -> None:
        zone = ZoneInfo("America/Tijuana")
        now = datetime(2026, 11, 24, 1, tzinfo=zone)
        hass = _Hass({"binary_sensor.door": State("binary_sensor.door", "on")})
        rule = {
            "id": "night",
            "type": "state",
            "source": "binary_sensor.door",
            "state": "on",
            "targets": ["light.strip"],
            "conditions": {"type": "time", "after": "00:00", "before": "00:00"},
            "schedule": {"after": "22:00", "before": "06:00", "weekdays": ["mon"]},
        }
        manager = RuleManager(
            hass, [rule], frozenset({"light.strip"}), self.submit, self.cancel
        )
        with (
            patch(
                "custom_components.smart_led_manager.modules.rules.dt_util.now",
                side_effect=lambda: now,
            ),
            patch(
                "custom_components.smart_led_manager.modules.rules.async_track_state_change_event"
            ),
            patch(
                "custom_components.smart_led_manager.modules.rules.async_track_point_in_time"
            ) as track,
        ):
            await manager.async_setup()
            assert self.submitted[-1].request_id == "rule:night"
            boundary = track.call_args.args[2]
            assert boundary == datetime(2026, 11, 24, 6, tzinfo=zone)
            now = boundary
            track.call_args.args[1](now)
            await asyncio.sleep(0)
            assert self.cancelled[-1] == "rule:night"
            assert track.call_args.args[2] > boundary
            await manager.async_shutdown()
        track.return_value.assert_called_once_with()

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
