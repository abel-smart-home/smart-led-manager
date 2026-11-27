"""Pure data models used by Smart LED Manager.

This module intentionally has no Home Assistant imports.  The priority engine can
therefore be tested in isolation and reused by future physical-light adapters.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Self

RGBColor = tuple[int, int, int]


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""

    return datetime.now(UTC)


def ensure_utc(value: datetime, *, field_name: str = "datetime") -> datetime:
    """Validate an aware datetime and normalize it to UTC."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _parse_datetime(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be an ISO 8601 string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as err:
        raise ValueError(f"{field_name} is not a valid ISO 8601 datetime") from err
    return ensure_utc(parsed, field_name=field_name)


def validate_rgb(value: object) -> RGBColor:
    """Return a validated RGB tuple."""

    if (
        not isinstance(value, (list, tuple))
        or len(value) != 3
        or any(
            isinstance(channel, bool) or not isinstance(channel, int)
            for channel in value
        )
        or any(channel < 0 or channel > 255 for channel in value)
    ):
        raise ValueError("color must contain three integer channels between 0 and 255")
    return value[0], value[1], value[2]


class TieBreaker(StrEnum):
    """Policies used when two valid requests have the same priority."""

    NEWEST = "newest"
    OLDEST = "oldest"
    LEXICAL = "lexical"


class RestorationPolicy(StrEnum):
    """Behavior after a winning request stops."""

    NEXT_VALID = "next_valid"
    LEAVE_UNCHANGED = "leave_unchanged"


class TemporaryPolicy(StrEnum):
    """How the lifetime of an interrupted temporary request is measured."""

    REAL_TIME = "real_time"
    RESUME = "resume"


class AnimationKind(StrEnum):
    """Animation forms understood by the scheduler layer."""

    NONE = "none"
    BLINK = "blink"
    PULSE = "pulse"
    BREATHE = "breathe"
    ALTERNATE = "alternate"
    SEQUENCE = "sequence"


@dataclass(frozen=True, slots=True)
class AnimationSpec:
    """Declarative animation request.

    Timing and command-rate protection are implemented by the scheduler and
    controller, rather than by this data model.
    """

    kind: AnimationKind = AnimationKind.NONE
    colors: tuple[RGBColor, ...] = ()
    interval: float = 1.0
    repetitions: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", AnimationKind(self.kind))
        object.__setattr__(
            self, "colors", tuple(validate_rgb(color) for color in self.colors)
        )
        if self.interval < 0.1:
            raise ValueError("animation interval must be at least 0.1 seconds")
        if self.repetitions is not None and self.repetitions < 1:
            raise ValueError("animation repetitions must be positive")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the animation into JSON-compatible data."""

        return {
            "kind": self.kind.value,
            "colors": [list(color) for color in self.colors],
            "interval": self.interval,
            "repetitions": self.repetitions,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> Self:
        """Deserialize and validate an animation."""

        colors = value.get("colors", [])
        if not isinstance(colors, list):
            raise ValueError("animation colors must be a list")
        return cls(
            kind=AnimationKind(str(value.get("kind", AnimationKind.NONE.value))),
            colors=tuple(validate_rgb(color) for color in colors),
            interval=float(value.get("interval", 1.0)),
            repetitions=(
                int(value["repetitions"])
                if value.get("repetitions") is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class LightCommand:
    """Desired logical state, independent of a particular light platform."""

    turn_on: bool = True
    color: RGBColor | None = None
    brightness: int | None = None
    transition: float | None = None
    effect: str | None = None
    animation: AnimationSpec = field(default_factory=AnimationSpec)

    def __post_init__(self) -> None:
        if self.color is not None:
            object.__setattr__(self, "color", validate_rgb(self.color))
        if self.brightness is not None and (
            isinstance(self.brightness, bool)
            or not isinstance(self.brightness, int)
            or not 0 <= self.brightness <= 255
        ):
            raise ValueError("brightness must be between 0 and 255")
        if self.transition is not None and self.transition < 0:
            raise ValueError("transition cannot be negative")
        if self.effect is not None and not self.effect.strip():
            raise ValueError("effect cannot be blank")
        if not isinstance(self.animation, AnimationSpec):
            raise TypeError("animation must be an AnimationSpec")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the command into JSON-compatible data."""

        return {
            "turn_on": self.turn_on,
            "color": list(self.color) if self.color is not None else None,
            "brightness": self.brightness,
            "transition": self.transition,
            "effect": self.effect,
            "animation": self.animation.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> Self:
        """Deserialize and validate a light command."""

        color = value.get("color")
        animation = value.get("animation", {})
        if not isinstance(animation, Mapping):
            raise ValueError("animation must be an object")
        return cls(
            turn_on=bool(value.get("turn_on", True)),
            color=validate_rgb(color) if color is not None else None,
            brightness=(
                int(value["brightness"])
                if value.get("brightness") is not None
                else None
            ),
            transition=(
                float(value["transition"])
                if value.get("transition") is not None
                else None
            ),
            effect=str(value["effect"]) if value.get("effect") is not None else None,
            animation=AnimationSpec.from_dict(animation),
        )


@dataclass(frozen=True, slots=True)
class Request:
    """A priority request that can compete independently for multiple targets."""

    request_id: str
    source: str
    name: str
    module: str
    targets: frozenset[str]
    priority: int
    command: LightCommand
    active: bool = True
    activated_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    expires_at: datetime | None = None
    allow_turn_on: bool = True
    persistent: bool = False
    restoration_policy: RestorationPolicy = RestorationPolicy.NEXT_VALID
    temporary_policy: TemporaryPolicy = TemporaryPolicy.REAL_TIME
    metadata: Mapping[str, Any] = field(default_factory=dict, compare=True)

    def __post_init__(self) -> None:
        request_id = self.request_id.strip()
        if not request_id:
            raise ValueError("request_id cannot be blank")
        object.__setattr__(self, "request_id", request_id)

        for field_name in ("source", "name", "module"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} cannot be blank")
            object.__setattr__(self, field_name, value.strip())

        targets = frozenset(target.strip() for target in self.targets if target.strip())
        if not targets:
            raise ValueError("a request must contain at least one target")
        object.__setattr__(self, "targets", targets)

        if isinstance(self.priority, bool) or not 0 <= self.priority <= 100:
            raise ValueError("priority must be between 0 and 100")
        if not isinstance(self.command, LightCommand):
            raise TypeError("command must be a LightCommand")

        activated_at = ensure_utc(self.activated_at, field_name="activated_at")
        updated_at = ensure_utc(self.updated_at, field_name="updated_at")
        object.__setattr__(self, "activated_at", activated_at)
        object.__setattr__(self, "updated_at", updated_at)
        if updated_at < activated_at:
            raise ValueError("updated_at cannot precede activated_at")
        if self.expires_at is not None:
            object.__setattr__(
                self,
                "expires_at",
                ensure_utc(self.expires_at, field_name="expires_at"),
            )

        object.__setattr__(
            self, "restoration_policy", RestorationPolicy(self.restoration_policy)
        )
        object.__setattr__(
            self, "temporary_policy", TemporaryPolicy(self.temporary_policy)
        )

        try:
            # A JSON round trip both validates persistence safety and isolates the
            # frozen model from mutations to dictionaries supplied by callers.
            metadata_copy = json.loads(json.dumps(dict(self.metadata)))
        except (TypeError, ValueError) as err:
            raise ValueError("metadata must be JSON serializable") from err
        object.__setattr__(self, "metadata", MappingProxyType(metadata_copy))

    def is_valid(self, now: datetime | None = None) -> bool:
        """Return whether the request can currently compete for a target."""

        reference = ensure_utc(now or utc_now(), field_name="now")
        return self.active and (self.expires_at is None or self.expires_at > reference)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the request for Home Assistant storage."""

        return {
            "request_id": self.request_id,
            "source": self.source,
            "name": self.name,
            "module": self.module,
            "targets": sorted(self.targets),
            "priority": self.priority,
            "command": self.command.to_dict(),
            "active": self.active,
            "activated_at": self.activated_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "allow_turn_on": self.allow_turn_on,
            "persistent": self.persistent,
            "restoration_policy": self.restoration_policy.value,
            "temporary_policy": self.temporary_policy.value,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> Self:
        """Deserialize a request, rejecting incomplete or unsafe data."""

        required = {
            "request_id",
            "source",
            "name",
            "module",
            "targets",
            "priority",
            "command",
            "activated_at",
            "updated_at",
        }
        missing = required.difference(value)
        if missing:
            raise ValueError(f"request is missing fields: {', '.join(sorted(missing))}")
        targets = value["targets"]
        command = value["command"]
        metadata = value.get("metadata", {})
        if not isinstance(targets, list) or not all(
            isinstance(target, str) for target in targets
        ):
            raise ValueError("targets must be a list of strings")
        if not isinstance(command, Mapping):
            raise ValueError("command must be an object")
        if not isinstance(metadata, Mapping):
            raise ValueError("metadata must be an object")
        expires_at = value.get("expires_at")
        return cls(
            request_id=str(value["request_id"]),
            source=str(value["source"]),
            name=str(value["name"]),
            module=str(value["module"]),
            targets=frozenset(targets),
            priority=int(value["priority"]),
            command=LightCommand.from_dict(command),
            active=bool(value.get("active", True)),
            activated_at=_parse_datetime(
                value["activated_at"], field_name="activated_at"
            ),
            updated_at=_parse_datetime(value["updated_at"], field_name="updated_at"),
            expires_at=(
                _parse_datetime(expires_at, field_name="expires_at")
                if expires_at is not None
                else None
            ),
            allow_turn_on=bool(value.get("allow_turn_on", True)),
            persistent=bool(value.get("persistent", False)),
            restoration_policy=RestorationPolicy(
                str(value.get("restoration_policy", RestorationPolicy.NEXT_VALID.value))
            ),
            temporary_policy=TemporaryPolicy(
                str(value.get("temporary_policy", TemporaryPolicy.REAL_TIME.value))
            ),
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class DecisionChange:
    """A target whose effective winner changed after an engine mutation."""

    target: str
    previous: Request | None
    current: Request | None
    reason: str
