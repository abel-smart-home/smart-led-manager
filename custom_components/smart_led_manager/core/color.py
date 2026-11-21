"""Validated numeric-state and RGB interpolation helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise
from typing import Literal

from ..models import RGBColor, validate_rgb

ColorMode = Literal["interpolate", "ranges"]


@dataclass(frozen=True, slots=True, order=True)
class ColorPoint:
    """A numeric reference value and its associated RGB color."""

    value: float
    color: RGBColor

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not math.isfinite(self.value):
            raise ValueError("color point value must be a finite number")
        object.__setattr__(self, "color", validate_rgb(self.color))


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

    numeric = parse_numeric_state(value)
    if numeric is None:
        raise ValueError("value must be a finite number")
    if mode not in {"interpolate", "ranges"}:
        raise ValueError("mode must be 'interpolate' or 'ranges'")
    ordered = _validated_points(points)

    if numeric <= ordered[0].value:
        return ordered[0].color
    if numeric >= ordered[-1].value:
        return ordered[-1].color

    for lower, upper in pairwise(ordered):
        if numeric < upper.value:
            if mode == "ranges":
                return lower.color
            ratio = (numeric - lower.value) / (upper.value - lower.value)
            return tuple(
                round(start + (end - start) * ratio)
                for start, end in zip(lower.color, upper.color, strict=True)
            )  # type: ignore[return-value]

    # Endpoint checks above make this unreachable, but retaining a safe result
    # protects future changes to the loop conditions.
    return ordered[-1].color


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
