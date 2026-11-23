"""Persistent zone and lighting-mode orchestration.

Definitions are configuration, while the active selection is represented by one
ordinary persistent priority request per zone.  Keeping that boundary explicit
lets modes participate in the same deterministic engine as every other intent.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..const import CONF_AREA_ID, MODULE_MODE
from ..core.engine import PriorityEngine
from ..models import (
    AnimationKind,
    AnimationSpec,
    DecisionChange,
    LightCommand,
    Request,
    utc_now,
)

MODE_REQUEST_PREFIX = "smart_led_manager:mode:"


class ModeValidationError(ValueError):
    """Describe a catalog or selection error with a translatable key."""

    def __init__(self, key: str, **placeholders: str) -> None:
        super().__init__(key)
        self.key = key
        self.placeholders = placeholders


@dataclass(frozen=True, slots=True)
class ZoneDefinition:
    """A named, non-overlapping group of authorized physical lights."""

    zone_id: str
    name: str
    targets: frozenset[str]
    area_id: str | None = None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ZoneDefinition:
        """Parse a stored options-flow zone definition."""
        zone_id = _required_text(value.get("zone_id"), "invalid_zone")
        name = _required_text(value.get("name"), "invalid_zone")
        targets = _targets(value.get("targets"), "zone_without_targets")
        area_id = _optional_text(value.get(CONF_AREA_ID), "invalid_zone")
        return cls(zone_id=zone_id, name=name, targets=targets, area_id=area_id)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-compatible options data."""
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "targets": sorted(self.targets),
            CONF_AREA_ID: self.area_id,
        }


@dataclass(frozen=True, slots=True)
class ModeDefinition:
    """Editable mode definition with an immutable identifier."""

    mode_id: str
    zone_id: str
    name: str
    targets: frozenset[str]
    priority: int = 50
    rgb_color: tuple[int, int, int] | None = None
    brightness: int | None = None
    transition: float | None = None
    allow_turn_on: bool = True
    animation: AnimationKind = AnimationKind.NONE
    period: float = 1.0
    expose_switch: bool = False

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ModeDefinition:
        """Parse and validate one stored mode definition."""
        mode_id = _required_text(value.get("mode_id"), "invalid_mode")
        zone_id = _required_text(value.get("zone_id"), "invalid_mode")
        name = _required_text(value.get("name"), "invalid_mode")
        if name.casefold() in {"none", "sin modo", "no mode"}:
            raise ModeValidationError("reserved_mode_name")
        targets = _targets(value.get("targets"), "mode_without_targets")

        priority_value = value.get("priority", 50)
        if (
            isinstance(priority_value, bool)
            or not isinstance(priority_value, (int, float))
            or int(priority_value) != priority_value
            or not 0 <= priority_value <= 100
        ):
            raise ModeValidationError("invalid_mode")
        priority = int(priority_value)

        color_value = value.get("rgb_color")
        color: tuple[int, int, int] | None = None
        if color_value is not None:
            if (
                not isinstance(color_value, (list, tuple))
                or len(color_value) != 3
                or any(
                    isinstance(channel, bool) or not isinstance(channel, int)
                    for channel in color_value
                )
                or any(channel < 0 or channel > 255 for channel in color_value)
            ):
                raise ModeValidationError("invalid_mode")
            color = color_value[0], color_value[1], color_value[2]

        brightness_value = value.get("brightness")
        brightness: int | None = None
        if brightness_value is not None:
            if (
                isinstance(brightness_value, bool)
                or not isinstance(brightness_value, (int, float))
                or int(brightness_value) != brightness_value
                or not 1 <= brightness_value <= 255
            ):
                raise ModeValidationError("invalid_mode")
            brightness = int(brightness_value)

        transition = value.get("transition")
        if transition is not None:
            if (
                isinstance(transition, bool)
                or not isinstance(transition, (int, float))
                or transition < 0
            ):
                raise ModeValidationError("invalid_mode")
            transition = float(transition)

        animation_value = str(value.get("animation", "fixed"))
        animation = {
            "fixed": AnimationKind.NONE,
            AnimationKind.NONE.value: AnimationKind.NONE,
            AnimationKind.BLINK.value: AnimationKind.BLINK,
            AnimationKind.PULSE.value: AnimationKind.PULSE,
        }.get(animation_value)
        if animation is None:
            raise ModeValidationError("invalid_mode")

        period = value.get("period", 1.0)
        if (
            isinstance(period, bool)
            or not isinstance(period, (int, float))
            or not 0.5 <= float(period) <= 60
        ):
            raise ModeValidationError("invalid_mode")

        allow_turn_on = value.get("allow_turn_on", True)
        expose_switch = value.get("expose_switch", False)
        if not isinstance(allow_turn_on, bool) or not isinstance(expose_switch, bool):
            raise ModeValidationError("invalid_mode")

        return cls(
            mode_id=mode_id,
            zone_id=zone_id,
            name=name,
            targets=targets,
            priority=priority,
            rgb_color=color,
            brightness=brightness,
            transition=transition,
            allow_turn_on=allow_turn_on,
            animation=animation,
            period=float(period),
            expose_switch=expose_switch,
        )

    @property
    def command(self) -> LightCommand:
        """Project this definition into an engine command."""
        return LightCommand(
            turn_on=True,
            color=self.rgb_color,
            brightness=self.brightness,
            transition=self.transition,
            animation=AnimationSpec(kind=self.animation, interval=self.period),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-compatible options data."""
        return {
            "mode_id": self.mode_id,
            "zone_id": self.zone_id,
            "name": self.name,
            "targets": sorted(self.targets),
            "priority": self.priority,
            "rgb_color": list(self.rgb_color) if self.rgb_color is not None else None,
            "brightness": self.brightness,
            "transition": self.transition,
            "allow_turn_on": self.allow_turn_on,
            "animation": (
                "fixed"
                if self.animation is AnimationKind.NONE
                else self.animation.value
            ),
            "period": self.period,
            "expose_switch": self.expose_switch,
        }


@dataclass(frozen=True, slots=True)
class ModeMutation:
    """Result of one atomic zone-selection transaction."""

    changes: tuple[DecisionChange, ...]
    changed: bool


class ModeManager:
    """Validate definitions and own one active mode request per zone."""

    def __init__(
        self,
        engine: PriorityEngine,
        zones: Iterable[Mapping[str, Any]],
        modes: Iterable[Mapping[str, Any]],
        authorized_targets: frozenset[str],
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._engine = engine
        self._clock = clock
        self._zones: dict[str, ZoneDefinition] = {}
        self._modes: dict[str, ModeDefinition] = {}
        self._selected: dict[str, str] = {}

        occupied: dict[str, str] = {}
        zone_names: set[str] = set()
        for raw_zone in zones:
            zone = ZoneDefinition.from_dict(raw_zone)
            if zone.zone_id in self._zones or zone.name.casefold() in zone_names:
                raise ModeValidationError("duplicate_zone")
            unauthorized = zone.targets.difference(authorized_targets)
            if unauthorized:
                raise ModeValidationError(
                    "target_not_managed", targets=", ".join(sorted(unauthorized))
                )
            overlap = zone.targets.intersection(occupied)
            if overlap:
                raise ModeValidationError(
                    "target_in_multiple_zones", targets=", ".join(sorted(overlap))
                )
            self._zones[zone.zone_id] = zone
            zone_names.add(zone.name.casefold())
            occupied.update(dict.fromkeys(zone.targets, zone.zone_id))

        mode_names: dict[str, set[str]] = {}
        for raw_mode in modes:
            mode = ModeDefinition.from_dict(raw_mode)
            zone = self._zones.get(mode.zone_id)
            if zone is None:
                raise ModeValidationError("mode_zone_missing")
            if mode.mode_id in self._modes:
                raise ModeValidationError("duplicate_mode")
            if not mode.targets.issubset(zone.targets):
                raise ModeValidationError("mode_target_outside_zone")
            names = mode_names.setdefault(mode.zone_id, set())
            if mode.name.casefold() in names:
                raise ModeValidationError("duplicate_mode_name")
            names.add(mode.name.casefold())
            self._modes[mode.mode_id] = mode

    @property
    def zones(self) -> tuple[ZoneDefinition, ...]:
        """Return definitions in stable configuration order."""
        return tuple(self._zones.values())

    @property
    def modes(self) -> tuple[ModeDefinition, ...]:
        """Return definitions in stable configuration order."""
        return tuple(self._modes.values())

    def zone(self, zone_id: str) -> ZoneDefinition:
        """Return one zone or raise a user-facing validation error."""
        try:
            return self._zones[zone_id]
        except KeyError as err:
            raise ModeValidationError("zone_not_found", zone_id=zone_id) from err

    def mode(self, mode_id: str) -> ModeDefinition:
        """Return one mode or raise a user-facing validation error."""
        try:
            return self._modes[mode_id]
        except KeyError as err:
            raise ModeValidationError("mode_not_found", mode_id=mode_id) from err

    def modes_for_zone(self, zone_id: str) -> tuple[ModeDefinition, ...]:
        """Return the modes belonging to one zone."""
        self.zone(zone_id)
        return tuple(mode for mode in self._modes.values() if mode.zone_id == zone_id)

    def selected_mode_id(self, zone_id: str) -> str | None:
        """Return the selected mode identifier for a zone."""
        self.zone(zone_id)
        return self._selected.get(zone_id)

    def is_selected(self, mode_id: str) -> bool:
        """Return whether one mode is its zone's active selection."""
        mode = self.mode(mode_id)
        return self._selected.get(mode.zone_id) == mode_id

    @staticmethod
    def request_id(mode_id: str) -> str:
        """Return the protected deterministic engine identifier for a mode."""
        return f"{MODE_REQUEST_PREFIX}{mode_id}"

    @staticmethod
    def is_internal_request_id(request_id: str) -> bool:
        """Return whether an identifier belongs to the managed mode namespace."""
        return request_id.startswith(MODE_REQUEST_PREFIX)

    @classmethod
    def is_internal_request(cls, request: Request) -> bool:
        """Return whether a request claims the protected mode namespace."""
        return request.module == MODULE_MODE or cls.is_internal_request_id(
            request.request_id
        )

    def reconcile_requests(
        self, requests: Iterable[Request]
    ) -> tuple[tuple[Request, ...], bool]:
        """Drop orphan/duplicate mode intent and rebuild it from definitions."""
        original = tuple(requests)
        retained = [
            request for request in original if not self.is_internal_request(request)
        ]
        candidates: dict[str, list[tuple[ModeDefinition, Request]]] = {}

        for request in original:
            if not self.is_internal_request(request):
                continue
            if not self.is_internal_request_id(request.request_id):
                continue
            mode_id = request.request_id.removeprefix(MODE_REQUEST_PREFIX)
            mode = self._modes.get(mode_id)
            if mode is None or request.module != MODULE_MODE:
                continue
            candidates.setdefault(mode.zone_id, []).append((mode, request))

        self._selected.clear()
        for zone_id, zone_candidates in candidates.items():
            mode, request = max(
                zone_candidates,
                key=lambda item: (
                    item[1].activated_at,
                    item[1].updated_at,
                    item[1].request_id,
                ),
            )
            retained.append(
                self._build_request(
                    mode,
                    activated_at=request.activated_at,
                    updated_at=request.updated_at,
                )
            )
            self._selected[zone_id] = mode.mode_id

        reconciled = tuple(sorted(retained, key=lambda request: request.request_id))
        original_sorted = tuple(
            sorted(original, key=lambda request: request.request_id)
        )
        changed = [item.to_dict() for item in reconciled] != [
            item.to_dict() for item in original_sorted
        ]
        return reconciled, changed

    async def async_activate(self, mode_id: str) -> ModeMutation:
        """Select a mode, replacing its zone's prior selection atomically."""
        mode = self.mode(mode_id)
        return await self.async_set_zone_mode(mode.zone_id, mode_id)

    async def async_deactivate(self, mode_id: str) -> ModeMutation:
        """Clear a mode only when it is currently selected."""
        mode = self.mode(mode_id)
        if self._selected.get(mode.zone_id) != mode_id:
            return ModeMutation((), False)
        return await self.async_set_zone_mode(mode.zone_id, None)

    async def async_set_zone_mode(
        self, zone_id: str, mode_id: str | None
    ) -> ModeMutation:
        """Atomically replace or clear the managed mode request for one zone."""
        self.zone(zone_id)
        selected = self._selected.get(zone_id)
        mode: ModeDefinition | None = None
        if mode_id is not None:
            mode = self.mode(mode_id)
            if mode.zone_id != zone_id:
                raise ModeValidationError("mode_not_in_zone")

        existing = tuple(
            request
            for request in await self._engine.async_requests()
            if self._request_belongs_to_zone(request, zone_id)
        )
        if selected == mode_id:
            if mode is None and not existing:
                return ModeMutation((), False)
            if mode is not None and len(existing) == 1:
                canonical = self._build_request(
                    mode,
                    activated_at=existing[0].activated_at,
                    updated_at=existing[0].updated_at,
                )
                if existing[0] == canonical:
                    return ModeMutation((), False)

        now = self._clock()
        request = (
            self._build_request(mode, activated_at=now, updated_at=now)
            if mode
            else None
        )
        changes = await self._engine.async_replace_matching(
            lambda item: self._request_belongs_to_zone(item, zone_id),
            request,
            reason="mode_selection",
        )
        if mode is None:
            self._selected.pop(zone_id, None)
        else:
            self._selected[zone_id] = mode.mode_id
        return ModeMutation(changes, True)

    def snapshot(self, winners: Mapping[str, str] | None = None) -> dict[str, Any]:
        """Return bounded catalog, selection, and per-zone intent diagnostics."""
        winner_ids = winners or {}
        zone_status: dict[str, dict[str, Any]] = {}
        for zone in self.zones:
            selected = self._selected.get(zone.zone_id)
            winning_targets: list[str] = []
            masked_targets: list[str] = []
            if selected is not None:
                request_id = self.request_id(selected)
                mode = self._modes[selected]
                winning_targets = sorted(
                    target
                    for target in mode.targets
                    if winner_ids.get(target) == request_id
                )
                masked_targets = sorted(mode.targets.difference(winning_targets))
            state = "no_mode"
            if selected is not None:
                if not winning_targets:
                    state = "masked"
                elif masked_targets:
                    state = "partial"
                else:
                    state = "winner"
            zone_status[zone.zone_id] = {
                "selected_mode_id": selected,
                "state": state,
                "winning_targets": winning_targets,
                "masked_targets": masked_targets,
            }
        return {
            "zones": [zone.to_dict() for zone in self.zones],
            "modes": [mode.to_dict() for mode in self.modes],
            "selected": dict(sorted(self._selected.items())),
            "status": zone_status,
        }

    def _request_belongs_to_zone(self, request: Request, zone_id: str) -> bool:
        if not self.is_internal_request_id(request.request_id):
            return False
        mode_id = request.request_id.removeprefix(MODE_REQUEST_PREFIX)
        mode = self._modes.get(mode_id)
        return (
            request.module == MODULE_MODE
            and mode is not None
            and mode.zone_id == zone_id
        )

    def _build_request(
        self,
        mode: ModeDefinition,
        *,
        activated_at: datetime,
        updated_at: datetime,
    ) -> Request:
        return Request(
            request_id=self.request_id(mode.mode_id),
            source=f"mode:{mode.mode_id}",
            name=mode.name,
            module=MODULE_MODE,
            targets=mode.targets,
            priority=mode.priority,
            command=mode.command,
            activated_at=activated_at,
            updated_at=updated_at,
            allow_turn_on=mode.allow_turn_on,
            persistent=True,
            metadata={
                "managed": True,
                "mode_id": mode.mode_id,
                "zone_id": mode.zone_id,
            },
        )


def _required_text(value: object, error_key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModeValidationError(error_key)
    return value.strip()


def _optional_text(value: object, error_key: str) -> str | None:
    if value is None or value == "":
        return None
    return _required_text(value, error_key)


def _targets(value: object, error_key: str) -> frozenset[str]:
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ModeValidationError(error_key)
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ModeValidationError(error_key)
    targets = frozenset(item.strip() for item in value)
    if not targets:
        raise ModeValidationError(error_key)
    return targets
