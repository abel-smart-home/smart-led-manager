"""Tests for event-driven state and numeric rules."""

from __future__ import annotations

import unittest

from homeassistant.core import State

from custom_components.smart_led_manager.modules.rules import RuleManager


class _States:
    def __init__(self, values: dict[str, State]) -> None:
        self.values = values

    def get(self, entity_id: str) -> State | None:
        return self.values.get(entity_id)


class _Hass:
    def __init__(self, states: dict[str, State]) -> None:
        self.states = _States(states)


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


if __name__ == "__main__":
    unittest.main()
