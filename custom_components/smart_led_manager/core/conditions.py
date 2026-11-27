"""Pure condition, schedule, threshold, and hysteresis evaluation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, time, timedelta
from enum import StrEnum
from math import isfinite
from typing import Any

MAX_CONDITION_DEPTH = 5
MAX_CONDITION_NODES = 32
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class ConditionResult(StrEnum):
    """Tri-state result that prevents NOT from accepting unknown data."""

    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


class ConditionValidationError(ValueError):
    """Raised when a condition tree is unsafe or malformed."""


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise ConditionValidationError(f"{field} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError) as err:
        raise ConditionValidationError(f"{field} must be a finite number") from err
    if not isfinite(number):
        raise ConditionValidationError(f"{field} must be a finite number")
    return number


def _clock(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ConditionValidationError(f"{field} must use HH:MM")
    try:
        parsed = time.fromisoformat(value)
    except ValueError as err:
        raise ConditionValidationError(f"{field} must use HH:MM") from err
    if parsed.second or parsed.microsecond or parsed.tzinfo is not None:
        raise ConditionValidationError(f"{field} must use local HH:MM")
    return parsed.strftime("%H:%M")


def validate_condition_tree(value: object | None) -> dict[str, Any] | None:
    """Validate and normalize one optional nested condition tree."""

    if value in (None, {}):
        return None
    nodes = 0

    def _validate(raw: object, depth: int) -> dict[str, Any]:
        nonlocal nodes
        nodes += 1
        if depth > MAX_CONDITION_DEPTH:
            raise ConditionValidationError("condition nesting is too deep")
        if nodes > MAX_CONDITION_NODES:
            raise ConditionValidationError("condition tree has too many nodes")
        if not isinstance(raw, Mapping):
            raise ConditionValidationError("condition must be an object")
        kind = str(raw.get("type", ""))
        if kind in {"and", "or"}:
            children = raw.get("conditions")
            if not isinstance(children, list) or not 1 <= len(children) <= 16:
                raise ConditionValidationError(
                    f"{kind} requires between 1 and 16 conditions"
                )
            return {
                "type": kind,
                "conditions": [_validate(child, depth + 1) for child in children],
            }
        if kind == "not":
            if "condition" not in raw:
                raise ConditionValidationError("not requires one condition")
            return {"type": kind, "condition": _validate(raw["condition"], depth + 1)}
        if kind == "state":
            entity_id = raw.get("entity_id")
            if not isinstance(entity_id, str) or "." not in entity_id:
                raise ConditionValidationError("state condition needs an entity_id")
            operator = str(raw.get("operator", "equals"))
            if operator not in {"equals", "not_equals"}:
                raise ConditionValidationError("invalid state condition operator")
            expected = raw.get("state")
            if not isinstance(expected, str):
                raise ConditionValidationError("state condition needs a state")
            return {
                "type": kind,
                "entity_id": entity_id,
                "operator": operator,
                "state": expected,
            }
        if kind == "numeric":
            entity_id = raw.get("entity_id")
            if not isinstance(entity_id, str) or "." not in entity_id:
                raise ConditionValidationError("numeric condition needs an entity_id")
            comparison = validate_numeric_activation(raw)
            return {"type": kind, "entity_id": entity_id, **comparison}
        if kind == "time":
            after = _clock(raw.get("after", "00:00"), "after")
            before = _clock(raw.get("before", "00:00"), "before")
            weekdays = raw.get("weekdays", list(WEEKDAYS))
            if (
                not isinstance(weekdays, list)
                or not weekdays
                or any(day not in WEEKDAYS for day in weekdays)
            ):
                raise ConditionValidationError("invalid weekdays")
            return {
                "type": kind,
                "after": after,
                "before": before,
                "weekdays": list(dict.fromkeys(weekdays)),
            }
        raise ConditionValidationError(
            f"unsupported condition type: {kind or '<empty>'}"
        )

    return _validate(value, 1)


def condition_entity_ids(condition: Mapping[str, Any] | None) -> frozenset[str]:
    """Return every entity whose state can affect a tree."""

    if not condition:
        return frozenset()
    kind = condition.get("type")
    if kind in {"state", "numeric"}:
        return frozenset({str(condition["entity_id"])})
    if kind in {"and", "or"}:
        return frozenset().union(
            *(condition_entity_ids(child) for child in condition["conditions"])
        )
    if kind == "not":
        return condition_entity_ids(condition["condition"])
    return frozenset()


def condition_schedules(
    condition: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], ...]:
    """Return normalized time nodes for boundary scheduling."""

    if not condition:
        return ()
    kind = condition.get("type")
    if kind == "time":
        return (dict(condition),)
    if kind in {"and", "or"}:
        return tuple(
            schedule
            for child in condition["conditions"]
            for schedule in condition_schedules(child)
        )
    if kind == "not":
        return condition_schedules(condition["condition"])
    return ()


def evaluate_condition(
    condition: Mapping[str, Any] | None,
    state_getter: Callable[[str], object | None],
    now_local: datetime,
    *,
    numeric_history: dict[tuple[int, ...], bool] | None = None,
    path: tuple[int, ...] = (),
) -> ConditionResult:
    """Evaluate a normalized tree with explicit unknown propagation."""

    if condition is None:
        return ConditionResult.TRUE
    kind = condition["type"]
    if kind in {"state", "numeric"}:
        state = state_getter(str(condition["entity_id"]))
        value = getattr(state, "state", None)
        if value in (None, "unknown", "unavailable"):
            if numeric_history is not None:
                numeric_history.pop(path, None)
            return ConditionResult.UNKNOWN
        if kind == "state":
            matched = str(value) == condition["state"]
            if condition["operator"] == "not_equals":
                matched = not matched
        else:
            try:
                number = float(value)
            except (TypeError, ValueError):
                if numeric_history is not None:
                    numeric_history.pop(path, None)
                return ConditionResult.UNKNOWN
            if not isfinite(number):
                if numeric_history is not None:
                    numeric_history.pop(path, None)
                return ConditionResult.UNKNOWN
            matched = numeric_activation_matches(
                number,
                condition,
                previous=bool(numeric_history and numeric_history.get(path)),
            )
            if numeric_history is not None:
                numeric_history[path] = matched
        return ConditionResult.TRUE if matched else ConditionResult.FALSE
    if kind == "time":
        return (
            ConditionResult.TRUE
            if schedule_is_active(condition, now_local)
            else ConditionResult.FALSE
        )
    if kind == "not":
        result = evaluate_condition(
            condition["condition"],
            state_getter,
            now_local,
            numeric_history=numeric_history,
            path=(*path, 0),
        )
        if result is ConditionResult.UNKNOWN:
            return result
        return (
            ConditionResult.FALSE
            if result is ConditionResult.TRUE
            else ConditionResult.TRUE
        )
    results = [
        evaluate_condition(
            child,
            state_getter,
            now_local,
            numeric_history=numeric_history,
            path=(*path, index),
        )
        for index, child in enumerate(condition["conditions"])
    ]
    if kind == "and":
        if ConditionResult.FALSE in results:
            return ConditionResult.FALSE
        if ConditionResult.UNKNOWN in results:
            return ConditionResult.UNKNOWN
        return ConditionResult.TRUE
    if ConditionResult.TRUE in results:
        return ConditionResult.TRUE
    if ConditionResult.UNKNOWN in results:
        return ConditionResult.UNKNOWN
    return ConditionResult.FALSE


def evaluate_activation(
    condition: Mapping[str, Any] | None,
    schedule: Mapping[str, Any] | None,
    state_getter: Callable[[str], object | None],
    now_local: datetime,
    *,
    numeric_history: dict[tuple[int, ...], bool] | None = None,
) -> ConditionResult:
    """Combine a condition tree with the optional schedule used by a rule."""
    result = evaluate_condition(
        condition, state_getter, now_local, numeric_history=numeric_history
    )
    if (
        result is ConditionResult.TRUE
        and schedule is not None
        and not schedule_is_active(schedule, now_local)
    ):
        return ConditionResult.FALSE
    return result


def schedule_is_active(schedule: Mapping[str, Any], now_local: datetime) -> bool:
    """Evaluate a local schedule; crossing-midnight days refer to its start."""

    after = time.fromisoformat(str(schedule["after"]))
    before = time.fromisoformat(str(schedule["before"]))
    current = now_local.timetz().replace(tzinfo=None)
    days = set(schedule["weekdays"])
    if after < before:
        return WEEKDAYS[now_local.weekday()] in days and after <= current < before
    if after == before:
        return WEEKDAYS[now_local.weekday()] in days
    if current >= after:
        start_day = now_local.weekday()
    elif current < before:
        start_day = (now_local.weekday() - 1) % 7
    else:
        return False
    return WEEKDAYS[start_day] in days


def next_schedule_boundary(
    schedules: list[dict[str, Any]], now: datetime
) -> datetime | None:
    """Find the next UTC instant whose local clock can change a schedule."""
    if not schedules:
        return None
    candidates: set[datetime] = set()
    now_utc = now.astimezone(UTC)
    tz = now.tzinfo
    for offset in range(-1, 9):
        day = now.date() + timedelta(days=offset)
        for schedule in schedules:
            if WEEKDAYS[day.weekday()] not in schedule["weekdays"]:
                continue
            start = time.fromisoformat(schedule["after"])
            end = time.fromisoformat(schedule["before"])
            end_day = day + timedelta(days=start >= end)
            if start == end:  # Legacy equal endpoints describe a full local day.
                start = end = time.min
            for candidate in (
                datetime.combine(day, start),
                datetime.combine(end_day, end),
            ):
                for fold in (0, 1):
                    instant = candidate.replace(tzinfo=tz, fold=fold).astimezone(UTC)
                    if instant.astimezone(tz).replace(tzinfo=None) == candidate:
                        candidates.add(instant)

    # A skipped or repeated wall-clock interval can change truth at the
    # offset transition itself, even if no endpoint falls at that instant.
    if tz is not None:
        lower = now_utc.replace(microsecond=0)
        for _ in range(8):
            upper = lower + timedelta(days=1)
            offset_before = lower.astimezone(tz).utcoffset()
            if upper.astimezone(tz).utcoffset() != offset_before:
                left, right = lower, upper
                while (right - left).total_seconds() > 1:
                    middle = left + timedelta(
                        seconds=int((right - left).total_seconds()) // 2
                    )
                    if middle.astimezone(tz).utcoffset() == offset_before:
                        left = middle
                    else:
                        right = middle
                candidates.add(right)
            lower = upper
    return min(
        (candidate for candidate in candidates if candidate > now_utc), default=None
    )


def validate_numeric_activation(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one threshold/range activation policy."""

    operator = str(value.get("operator", "above"))
    if operator not in {"above", "below", "inside", "outside"}:
        raise ConditionValidationError("invalid numeric activation operator")
    hysteresis = _finite_number(value.get("hysteresis", 0), "hysteresis")
    if hysteresis < 0:
        raise ConditionValidationError("hysteresis cannot be negative")
    if operator in {"above", "below"}:
        return {
            "operator": operator,
            "threshold": _finite_number(value.get("threshold"), "threshold"),
            "hysteresis": hysteresis,
        }
    lower = _finite_number(value.get("lower"), "lower")
    upper = _finite_number(value.get("upper"), "upper")
    if lower >= upper:
        raise ConditionValidationError("lower must be less than upper")
    if hysteresis * 2 >= upper - lower:
        raise ConditionValidationError("range hysteresis is too large")
    return {
        "operator": operator,
        "lower": lower,
        "upper": upper,
        "hysteresis": hysteresis,
    }


def numeric_activation_matches(
    number: float, activation: Mapping[str, Any], *, previous: bool
) -> bool:
    """Evaluate thresholds with deterministic inclusive release boundaries."""

    operator = activation["operator"]
    hysteresis = float(activation.get("hysteresis", 0))
    if operator == "above":
        threshold = float(activation["threshold"])
        return number >= threshold - hysteresis if previous else number > threshold
    if operator == "below":
        threshold = float(activation["threshold"])
        return number <= threshold + hysteresis if previous else number < threshold
    lower = float(activation["lower"])
    upper = float(activation["upper"])
    if operator == "inside":
        return (
            lower - hysteresis <= number <= upper + hysteresis
            if previous
            else lower <= number <= upper
        )
    return (
        number < lower + hysteresis or number > upper - hysteresis
        if previous
        else number < lower or number > upper
    )
