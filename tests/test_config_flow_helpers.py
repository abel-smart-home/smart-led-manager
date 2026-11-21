"""Tests for config-flow data parsing."""

from __future__ import annotations

import unittest

from custom_components.smart_led_manager.config_flow import parse_color_points


class ConfigFlowHelperTests(unittest.TestCase):
    """Verify UI text is converted into validated structured data."""

    def test_color_points_are_sorted(self) -> None:
        self.assertEqual(
            parse_color_points("20:0,255,0;10:0,0,255"),
            [
                {"value": 10.0, "rgb": [0, 0, 255]},
                {"value": 20.0, "rgb": [0, 255, 0]},
            ],
        )

    def test_requires_unique_valid_points(self) -> None:
        for invalid in (
            "10:0,0,255",
            "10:0,0,255;10:255,0,0",
            "10:0,0,999;20:255,0,0",
            "not-a-point;20:255,0,0",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                parse_color_points(invalid)


if __name__ == "__main__":
    unittest.main()
