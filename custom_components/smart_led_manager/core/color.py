"""Validated numeric-state and RGB interpolation helpers."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import pairwise
from typing import Any, Literal

from ..models import RGBColor, validate_rgb

ColorMode = Literal["interpolate", "ranges"]
ColorRelation = Literal["below", "point", "between", "above"]


@dataclass(frozen=True, slots=True, order=True)
class ColorPoint:
    """A numeric reference value and its associated RGB color."""

    value: float
    color: RGBColor

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not math.isfinite(self.value):
            raise ValueError("color point value must be a finite number")
        object.__setattr__(self, "color", validate_rgb(self.color))


@dataclass(frozen=True, slots=True)
class ColorEvaluation:
    """Exact color result plus the reference points that determined it."""

    color: RGBColor
    relation: ColorRelation
    lower: float
    upper: float
    ratio: float | None


def parse_numeric_state(value: object) -> float | None:
    """Parse a finite numeric state, rejecting HA sentinel states."""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped.lower() in {"unknown", "unavailable", "none"}:
            return None
        value = stripped
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _validated_points(
    points: list[ColorPoint] | tuple[ColorPoint, ...],
) -> tuple[ColorPoint, ...]:
    if not points:
        raise ValueError("at least one color point is required")
    ordered = tuple(sorted(points, key=lambda point: point.value))
    if any(left.value == right.value for left, right in pairwise(ordered)):
        raise ValueError("color point values must be unique")
    return ordered


def normalize_color_points(raw: object, *, minimum: int = 2) -> list[dict[str, Any]]:
    """Validate and sort the persisted ``value``/``rgb`` point format."""

    if not isinstance(raw, (list, tuple)):
        raise ValueError("color points must be a list")
    points: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValueError("color point must be an object")
        try:
            value = float(item["value"])
            color = validate_rgb(tuple(item["rgb"]))
        except (KeyError, TypeError, ValueError) as err:
            raise ValueError("invalid color point") from err
        if not math.isfinite(value):
            raise ValueError("color point value must be finite")
        points.append({"value": value, "rgb": list(color)})
    if len(points) < minimum:
        raise ValueError(f"at least {minimum} color points are required")
    points.sort(key=lambda point: point["value"])
    values = [point["value"] for point in points]
    if len(values) != len(set(values)):
        raise ValueError("color point values must be unique")
    return points


def evaluate_rgb(
    value: float,
    points: list[ColorPoint] | tuple[ColorPoint, ...],
    *,
    mode: ColorMode = "interpolate",
) -> ColorEvaluation:
    """Evaluate a color and report the exact point or interval used."""

    numeric = parse_numeric_state(value)
    if numeric is None:
        raise ValueError("value must be a finite number")
    if mode not in {"interpolate", "ranges"}:
        raise ValueError("mode must be 'interpolate' or 'ranges'")
    ordered = _validated_points(points)

    first = ordered[0]
    last = ordered[-1]
    if numeric < first.value:
        return ColorEvaluation(first.color, "below", first.value, first.value, None)
    if numeric == first.value:
        return ColorEvaluation(first.color, "point", first.value, first.value, None)
    if numeric > last.value:
        return ColorEvaluation(last.color, "above", last.value, last.value, None)
    if numeric == last.value:
        return ColorEvaluation(last.color, "point", last.value, last.value, None)

    for lower, upper in pairwise(ordered):
        if numeric == lower.value:
            return ColorEvaluation(lower.color, "point", lower.value, lower.value, None)
        if numeric < upper.value:
            ratio = (numeric - lower.value) / (upper.value - lower.value)
            if mode == "ranges":
                color = lower.color
            else:
                color = tuple(
                    round(start + (end - start) * ratio)
                    for start, end in zip(lower.color, upper.color, strict=True)
                )
            return ColorEvaluation(
                validate_rgb(color), "between", lower.value, upper.value, ratio
            )

    return ColorEvaluation(last.color, "point", last.value, last.value, None)


def interpolate_rgb(
    value: float,
    points: list[ColorPoint] | tuple[ColorPoint, ...],
    *,
    mode: ColorMode = "interpolate",
) -> RGBColor:
    """Map a numeric value to RGB using interpolation or lower-bound ranges.

    Values outside the configured domain are clamped to the closest endpoint.
    In ``ranges`` mode each point starts a range that continues until the next
    point, which makes threshold behavior explicit and deterministic.
    """

    return evaluate_rgb(value, points, mode=mode).color


def hex_to_rgb(value: str) -> RGBColor:
    """Convert a six-digit hexadecimal color into RGB."""

    normalized = value.strip().removeprefix("#")
    if len(normalized) != 6:
        raise ValueError("hex color must contain exactly six digits")
    try:
        return validate_rgb(
            tuple(int(normalized[index : index + 2], 16) for index in (0, 2, 4))
        )
    except ValueError as err:
        raise ValueError("hex color contains invalid digits") from err


def rgb_to_hex(color: RGBColor) -> str:
    """Convert RGB into an uppercase hexadecimal color."""

    return "#{:02X}{:02X}{:02X}".format(*validate_rgb(color))
