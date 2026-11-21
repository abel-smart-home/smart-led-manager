"""Tests for persistent, Home Assistant-independent models."""

from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime, timedelta

from custom_components.smart_led_manager.models import (
    AnimationKind,
    AnimationSpec,
    LightCommand,
    Request,
)

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


def make_request(**overrides: object) -> Request:
    """Create a valid request for model tests."""

    values: dict[str, object] = {
        "request_id": "request-1",
        "source": "test",
        "name": "Test request",
        "module": "state",
        "targets": frozenset({"light.desk"}),
        "priority": 50,
        "command": LightCommand(color=(1, 2, 3), brightness=100),
        "activated_at": NOW,
        "updated_at": NOW,
        "persistent": True,
    }
    values.update(overrides)
    return Request(**values)  # type: ignore[arg-type]


class ModelTests(unittest.TestCase):
    """Validate bounds, time semantics, and storage round trips."""

    def test_request_round_trip_is_json_safe(self) -> None:
        request = make_request(
            expires_at=NOW + timedelta(minutes=5),
            command=LightCommand(
                color=(10, 20, 30),
                brightness=200,
                transition=1.5,
                animation=AnimationSpec(
                    kind=AnimationKind.ALTERNATE,
                    colors=((10, 20, 30), (40, 50, 60)),
                    interval=0.5,
                    repetitions=3,
                ),
            ),
            metadata={"room": "office", "nested": {"enabled": True}},
        )

        serialized = json.loads(json.dumps(request.to_dict()))

        self.assertEqual(Request.from_dict(serialized), request)

    def test_request_rejects_naive_timestamps(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            make_request(activated_at=datetime(2026, 1, 1), updated_at=NOW)

    def test_request_rejects_invalid_priority_and_targets(self) -> None:
        with self.assertRaisesRegex(ValueError, "priority"):
            make_request(priority=101)
        with self.assertRaisesRegex(ValueError, "target"):
            make_request(targets=frozenset())

    def test_command_rejects_invalid_channels_and_brightness(self) -> None:
        with self.assertRaisesRegex(ValueError, "color"):
            LightCommand(color=(0, 20, 999))
        with self.assertRaisesRegex(ValueError, "brightness"):
            LightCommand(brightness=-1)

    def test_expiration_boundary_is_not_valid(self) -> None:
        request = make_request(expires_at=NOW + timedelta(seconds=10))

        self.assertTrue(request.is_valid(NOW + timedelta(seconds=9)))
        self.assertFalse(request.is_valid(NOW + timedelta(seconds=10)))

    def test_metadata_is_detached_from_caller(self) -> None:
        metadata = {"nested": {"value": 1}}
        request = make_request(metadata=metadata)

        metadata["nested"]["value"] = 2

        self.assertEqual(request.metadata["nested"]["value"], 1)  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()
