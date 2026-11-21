"""Tests for numeric-state color mapping."""

from __future__ import annotations

import unittest

from custom_components.smart_led_manager.core.color import (
    ColorPoint,
    hex_to_rgb,
    interpolate_rgb,
    parse_numeric_state,
    rgb_to_hex,
)

POINTS = (
    ColorPoint(16, (0, 0, 255)),
    ColorPoint(20, (0, 255, 255)),
    ColorPoint(24, (0, 255, 0)),
)


class ColorTests(unittest.TestCase):
    """Verify parsing, clamping, ranges and gradual interpolation."""

    def test_unknown_and_unavailable_are_not_numbers(self) -> None:
        for value in ("unknown", "unavailable", "NaN", "inf", None, True, ""):
            with self.subTest(value=value):
                self.assertIsNone(parse_numeric_state(value))

    def test_numeric_strings_are_accepted(self) -> None:
        self.assertEqual(parse_numeric_state(" 21.5 "), 21.5)

    def test_interpolation_and_endpoint_clamping(self) -> None:
        self.assertEqual(interpolate_rgb(10, POINTS), (0, 0, 255))
        self.assertEqual(interpolate_rgb(18, POINTS), (0, 128, 255))
        self.assertEqual(interpolate_rgb(30, POINTS), (0, 255, 0))

    def test_range_mode_uses_lower_threshold(self) -> None:
        self.assertEqual(interpolate_rgb(19.99, POINTS, mode="ranges"), (0, 0, 255))
        self.assertEqual(interpolate_rgb(20, POINTS, mode="ranges"), (0, 255, 255))

    def test_duplicate_reference_value_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique"):
            interpolate_rgb(
                10,
                (ColorPoint(10, (0, 0, 0)), ColorPoint(10, (255, 255, 255))),
            )

    def test_hex_round_trip(self) -> None:
        self.assertEqual(hex_to_rgb("#0A14FF"), (10, 20, 255))
        self.assertEqual(rgb_to_hex((10, 20, 255)), "#0A14FF")
        with self.assertRaises(ValueError):
            hex_to_rgb("not-a-color")


if __name__ == "__main__":
    unittest.main()
