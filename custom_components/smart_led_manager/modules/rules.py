"""Event-driven state and numeric rules."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime
from time import monotonic
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from ..const import RULE_TYPE_NUMERIC, RULE_TYPE_STATE
from ..core.color import ColorPoint, interpolate_rgb, parse_numeric_state
from ..models import LightCommand, Request, utc_now

_LOGGER = logging.getLogger(__name__)

SubmitCallback = Callable[[Request], Awaitable[None]]
CancelCallback = Callable[[str], Awaitable[None]]


class RuleManager:
    """Translate Home Assistant state events into engine requests."""

    def __init__(
        self,
        hass: HomeAssistant,
        rules: list[dict[str, Any]],
        authorized_targets: frozenset[str],
        submit: SubmitCallback,
        cancel: CancelCallback,
    ) -> None:
        self._hass = hass
        self._rules = {str(rule["id"]): rule for rule in rules if "id" in rule}
        self._authorized_targets = authorized_targets
        self._submit = submit
        self._cancel = cancel
        self._unsubscribe: Callable[[], None] | None = None
        self._pending: dict[str, Callable[[], None]] = {}
        self._activated_at: dict[str, datetime] = {}
        self._last_numeric: dict[str, float] = {}
        self._last_numeric_update: dict[str, float] = {}

    async def async_setup(self) -> None:
        """Subscribe once and evaluate the current source states."""
        sources = {
            str(rule["source"]) for rule in self._rules.values() if rule.get("source")
        }
        if sources:
            self._unsubscribe = async_track_state_change_event(
                self._hass, sorted(sources), self._async_state_changed
            )
        for rule in self._rules.values():
            await self._async_evaluate(rule)

    async def async_shutdown(self) -> None:
        """Unsubscribe and cancel deferred rule evaluations."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        for unsubscribe in self._pending.values():
            unsubscribe()
        self._pending.clear()

    @callback
    def _async_state_changed(self, event: Event) -> None:
        entity_id = event.data.get("entity_id")
        for rule in self._rules.values():
            if rule.get("source") == entity_id:
                self._hass.async_create_task(
                    self._async_evaluate(rule),
                    f"smart_led_manager_rule_{rule['id']}",
                )

    async def _async_evaluate(self, rule: Mapping[str, Any]) -> None:
        if not frozenset(rule.get("targets", [])).intersection(
            self._authorized_targets
        ):
            _LOGGER.warning(
                "Ignoring rule %s because it has no authorized targets",
                rule.get("id"),
            )
            await self._release(rule)
            return
        rule_type = rule.get("type")
        if rule_type == RULE_TYPE_STATE:
            await self._async_evaluate_state(rule)
        elif rule_type == RULE_TYPE_NUMERIC:
            await self._async_evaluate_numeric(rule)
        else:
            _LOGGER.warning(
                "Ignoring rule %s with unknown type %s", rule.get("id"), rule_type
            )

    async def _async_evaluate_state(self, rule: Mapping[str, Any]) -> None:
        state = self._hass.states.get(str(rule["source"]))
        request_id = _request_id(rule)
        if state is None or state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            await self._release(rule)
            return
        expected = str(rule.get("state", ""))
        operator = rule.get("operator", "equals")
        matched = state.state == expected
        if operator == "not_equals":
            matched = not matched
        if not matched:
            await self._release(rule)
            return
        await self._submit(self._request(rule, state, request_id=request_id))

    async def _async_evaluate_numeric(self, rule: Mapping[str, Any]) -> None:
        rule_id = str(rule["id"])
        state = self._hass.states.get(str(rule["source"]))
        numeric = parse_numeric_state(state.state if state else None)
        if state is None or numeric is None:
            await self._release(rule)
            self._last_numeric.pop(rule_id, None)
            return

        last_value = self._last_numeric.get(rule_id)
        minimum_change = float(rule.get("minimum_change", 0))
        if last_value is not None and abs(numeric - last_value) < minimum_change:
            return

        minimum_interval = max(0.0, float(rule.get("minimum_interval", 0)))
        elapsed = monotonic() - self._last_numeric_update.get(rule_id, 0.0)
        if elapsed < minimum_interval:
            self._schedule_numeric(rule, minimum_interval - elapsed)
            return

        try:
            points = tuple(
                ColorPoint(float(point["value"]), tuple(point["rgb"]))
                for point in rule.get("points", [])
            )
            mode = (
                "ranges" if rule.get("mode") in {"range", "ranges"} else "interpolate"
            )
            color = interpolate_rgb(numeric, points, mode=mode)
        except (KeyError, TypeError, ValueError):
            _LOGGER.exception("Invalid numeric rule %s", rule_id)
            await self._release(rule)
            return

        self._pending.pop(rule_id, None)
        self._last_numeric[rule_id] = numeric
        self._last_numeric_update[rule_id] = monotonic()
        await self._submit(
            self._request(
                rule,
                state,
                request_id=_request_id(rule),
                color=color,
                metadata={"numeric_value": numeric},
            )
        )

    def _schedule_numeric(self, rule: Mapping[str, Any], delay: float) -> None:
        rule_id = str(rule["id"])
        if rule_id in self._pending:
            return

        @callback
        def _run(_now: datetime) -> None:
            self._pending.pop(rule_id, None)
            self._hass.async_create_task(
                self._async_evaluate(rule),
                f"smart_led_manager_deferred_rule_{rule_id}",
            )

        self._pending[rule_id] = async_call_later(self._hass, delay, _run)

    def _request(
        self,
        rule: Mapping[str, Any],
        state: State,
        *,
        request_id: str,
        color: tuple[int, int, int] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Request:
        rule_id = str(rule["id"])
        now = utc_now()
        activated_at = self._activated_at.setdefault(rule_id, now)
        targets = frozenset(rule.get("targets", [])).intersection(
            self._authorized_targets
        )
        if not targets:
            raise ValueError(f"rule {rule_id} has no authorized targets")
        rgb = color or tuple(
            int(value) for value in rule.get("rgb_color", [255, 255, 255])
        )
        return Request(
            request_id=request_id,
            source=str(rule["source"]),
            name=str(rule.get("name", rule_id)),
            module="rule",
            targets=targets,
            priority=int(rule.get("priority", 40)),
            command=LightCommand(
                color=rgb,
                brightness=int(rule.get("brightness", 255)),
                transition=float(rule.get("transition", 0)),
            ),
            activated_at=activated_at,
            updated_at=now,
            metadata={
                "rule_id": rule_id,
                "source_state": state.state,
                **(metadata or {}),
            },
        )

    async def _release(self, rule: Mapping[str, Any]) -> None:
        rule_id = str(rule["id"])
        pending = self._pending.pop(rule_id, None)
        if pending is not None:
            pending()
        self._activated_at.pop(rule_id, None)
        await self._cancel(_request_id(rule))


def _request_id(rule: Mapping[str, Any]) -> str:
    return f"rule:{rule['id']}"
