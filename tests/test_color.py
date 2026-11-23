"""Tests for numeric-state color mapping."""

from __future__ import annotations

import unittest

from custom_components.smart_led_manager.core.color import (
    ColorPoint,
    evaluate_rgb,
    hex_to_rgb,
    interpolate_rgb,
    normalize_color_points,
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

    def test_evaluation_reports_exact_interval_and_clamping(self) -> None:
        below = evaluate_rgb(10, POINTS)
        between = evaluate_rgb(18, POINTS)
        exact = evaluate_rgb(20, POINTS)
        above = evaluate_rgb(30, POINTS)

        self.assertEqual((below.relation, below.lower, below.upper), ("below", 16, 16))
        self.assertEqual(between.color, (0, 128, 255))
        self.assertEqual(
            (between.relation, between.lower, between.upper, between.ratio),
            ("between", 16, 20, 0.5),
        )
        self.assertEqual((exact.relation, exact.lower), ("point", 20))
        self.assertEqual((above.relation, above.lower), ("above", 24))

    def test_persisted_points_are_validated_and_sorted(self) -> None:
        points = normalize_color_points(
            [
                {"value": 2, "rgb": [255, 255, 255]},
                {"value": -1, "rgb": [0, 0, 0]},
            ]
        )
        self.assertEqual([point["value"] for point in points], [-1.0, 2.0])
        with self.assertRaisesRegex(ValueError, "unique"):
            normalize_color_points(
                [
                    {"value": 1, "rgb": [0, 0, 0]},
                    {"value": 1, "rgb": [255, 255, 255]},
                ]
            )

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
