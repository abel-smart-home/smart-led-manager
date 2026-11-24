"""Event-driven state, numeric, and one-shot event rules."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, time, timedelta
from time import monotonic
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Context, Event, HomeAssistant, State, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
from homeassistant.helpers.event import (
    async_call_later,
    async_track_point_in_time,
    async_track_state_change_event,
)
from homeassistant.util import dt as dt_util

from ..const import RULE_TYPE_EVENT, RULE_TYPE_NUMERIC, RULE_TYPE_STATE
from ..core.color import ColorPoint, interpolate_rgb, parse_numeric_state
from ..core.conditions import (
    ConditionResult,
    ConditionValidationError,
    condition_entity_ids,
    condition_schedules,
    evaluate_condition,
    numeric_activation_matches,
    validate_condition_tree,
)
from ..models import (
    AnimationKind,
    AnimationSpec,
    LightCommand,
    Request,
    utc_now,
)
from .targeting import AdvancedTargetError, AdvancedTargetResolver

_LOGGER = logging.getLogger(__name__)

SubmitCallback = Callable[[Request], Awaitable[None]]
CancelCallback = Callable[[str], Awaitable[None]]


class RuleManager:
    """Translate Home Assistant changes and triggers into engine requests."""

    def __init__(
        self,
        hass: HomeAssistant,
        rules: list[dict[str, Any]],
        authorized_targets: frozenset[str],
        submit: SubmitCallback,
        cancel: CancelCallback,
        *,
        zones: list[Mapping[str, Any]] | None = None,
    ) -> None:
        self._hass = hass
        self._rules = {str(rule["id"]): rule for rule in rules if "id" in rule}
        self._authorized_targets = authorized_targets
        self._targets = AdvancedTargetResolver(
            hass, authorized_targets, zones or [], audit=False
        )
        self._submit = submit
        self._cancel = cancel
        self._unsubscribe: Callable[[], None] | None = None
        self._state_sources: frozenset[str] = frozenset()
        self._tracked_sources: frozenset[str] = frozenset()
        self._registry_unsubscribes: list[Callable[[], None]] = []
        self._trigger_unsubscribes: list[Callable[[], None]] = []
        self._schedule_unsubscribe: Callable[[], None] | None = None
        self._pending: dict[str, Callable[[], None]] = {}
        self._holds: dict[str, Callable[[], None]] = {}
        self._dwell_ready: set[str] = set()
        self._tasks: set[asyncio.Task[None]] = set()
        self._activated_at: dict[str, datetime] = {}
        self._last_numeric: dict[str, float] = {}
        self._last_numeric_update: dict[str, float] = {}
        self._numeric_activation: dict[str, bool] = {}
        self._resolved_targets: dict[str, frozenset[str]] = {}
        self._resolved_groups: dict[str, frozenset[str]] = {}
        self._event_expiry: dict[str, datetime] = {}
        self._evaluation_lock = asyncio.Lock()
        self._stopped = False

    async def async_setup(self) -> None:
        """Subscribe once, attach official triggers, and evaluate live rules."""

        self._stopped = False
        sources: set[str] = set()
        track_registries = False
        for rule in self._rules.values():
            if not _is_enabled(rule):
                continue
            selection = rule.get("target_selection")
            if isinstance(selection, Mapping):
                track_registries = track_registries or bool(
                    _string_items(selection.get("areas"))
                    or _string_items(selection.get("labels"))
                    or _string_items(selection.get("groups"))
                )
            if rule.get("type") == RULE_TYPE_EVENT:
                await self._async_setup_event_rule(rule)
                continue
            if source := rule.get("source"):
                sources.add(str(source))
            sources.update(self._condition_entities(rule))

        self._state_sources = frozenset(sources)
        self._refresh_state_subscription()
        if track_registries and hasattr(self._hass, "bus"):
            self._registry_unsubscribes = [
                self._hass.bus.async_listen(
                    er.EVENT_ENTITY_REGISTRY_UPDATED, self._async_registry_changed
                ),
                self._hass.bus.async_listen(
                    dr.EVENT_DEVICE_REGISTRY_UPDATED, self._async_registry_changed
                ),
                self._hass.bus.async_listen(
                    ar.EVENT_AREA_REGISTRY_UPDATED, self._async_registry_changed
                ),
                self._hass.bus.async_listen(
                    lr.EVENT_LABEL_REGISTRY_UPDATED, self._async_registry_changed
                ),
            ]
        self._schedule_next_boundary()
        for rule in self._rules.values():
            if rule.get("type") != RULE_TYPE_EVENT:
                await self._async_evaluate(rule)

    async def async_shutdown(self) -> None:
        """Unsubscribe and cancel every listener, timer, and evaluation."""

        self._stopped = True
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        for unsubscribe in self._registry_unsubscribes:
            unsubscribe()
        self._registry_unsubscribes.clear()
        for unsubscribe in self._trigger_unsubscribes:
            unsubscribe()
        self._trigger_unsubscribes.clear()
        if self._schedule_unsubscribe is not None:
            self._schedule_unsubscribe()
            self._schedule_unsubscribe = None
        for unsubscribe in (*self._pending.values(), *self._holds.values()):
            unsubscribe()
        self._pending.clear()
        self._holds.clear()
        self._dwell_ready.clear()
        tasks = tuple(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        self._event_expiry.clear()
        self._resolved_groups.clear()
        self._tracked_sources = frozenset()

    @callback
    def _refresh_state_subscription(self) -> None:
        tracked = set(self._state_sources)
        for rule_id, rule in self._rules.items():
            if _is_enabled(rule):
                dependencies = self._targets.group_dependencies(rule)
                self._resolved_groups[rule_id] = dependencies
                tracked.update(dependencies)
        if tracked == self._tracked_sources:
            return
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        self._tracked_sources = frozenset(tracked)
        if tracked:
            self._unsubscribe = async_track_state_change_event(
                self._hass, sorted(tracked), self._async_state_changed
            )

    async def _async_setup_event_rule(self, rule: Mapping[str, Any]) -> None:
        """Validate and attach one Home Assistant trigger without replay."""

        # Importing the trigger loader initializes HA trigger platforms. Keep it
        # lazy so the pure rule tests remain platform-independent on Windows.
        from homeassistant.helpers import trigger as trigger_helper

        try:
            trigger_config = await trigger_helper.async_validate_trigger_config(
                self._hass, [dict(rule["trigger"])]
            )

            async def _action(
                variables: dict[str, Any], context: Context | None = None
            ) -> None:
                await self._async_event_fired(rule, variables, context)

            rule_id = str(rule["id"])

            def _log(level: int, message: str, **kwargs: Any) -> None:
                _LOGGER.log(level, "Rule %s trigger: %s", rule_id, message, **kwargs)

            unsubscribe = await trigger_helper.async_initialize_triggers(
                self._hass,
                trigger_config,
                _action,
                "smart_led_manager",
                str(rule.get("name", rule_id)),
                _log,
            )
        except Exception:  # Home Assistant trigger platforms own validation errors
            _LOGGER.exception("Invalid trigger for rule %s", rule.get("id"))
            await self._release(rule)
            return
        if unsubscribe is not None:
            self._trigger_unsubscribes.append(unsubscribe)

    @callback
    def _async_state_changed(self, event: Event) -> None:
        entity_id = event.data.get("entity_id")
        if self._stopped or not isinstance(entity_id, str):
            return
        old = event.data.get("old_state")
        new = event.data.get("new_state")
        topology_changed = (
            old is None
            or new is None
            or old.attributes.get(ATTR_ENTITY_ID) != new.attributes.get(ATTR_ENTITY_ID)
        )
        if topology_changed:
            self._refresh_state_subscription()
        for rule in self._rules.values():
            if not _is_enabled(rule):
                continue
            if rule.get("type") == RULE_TYPE_EVENT:
                if topology_changed and entity_id in self._group_entities(rule):
                    self._create_task(
                        self._async_refresh_event_targets(rule),
                        f"smart_led_manager_event_targets_{rule['id']}",
                    )
                continue
            if (
                rule.get("source") == entity_id
                or entity_id in self._condition_entities(rule)
                or (topology_changed and entity_id in self._group_entities(rule))
            ):
                self._create_task(
                    self._async_evaluate(rule),
                    f"smart_led_manager_rule_{rule['id']}",
                )

    @callback
    def _async_registry_changed(self, _event: Event) -> None:
        if self._stopped:
            return
        self._create_task(
            self._async_dynamic_targets_changed(),
            "smart_led_manager_dynamic_targets",
        )

    async def _async_dynamic_targets_changed(self) -> None:
        """Re-resolve current intent after official registry updates."""

        self._refresh_state_subscription()
        for rule in self._rules.values():
            if not _is_enabled(rule):
                continue
            if rule.get("type") == RULE_TYPE_EVENT:
                await self._async_refresh_event_targets(rule)
            else:
                await self._async_evaluate(rule)

    def allows_target(self, request_id: str | None, target: str) -> bool:
        """Revalidate the winning rule at the physical dispatch boundary."""
        if request_id is None:
            return False
        if not request_id.startswith("rule:"):
            return True
        rule_id = request_id.removeprefix("rule:")
        rule = self._rules.get(rule_id)
        if rule is None:
            return True
        if self._stopped or not _is_enabled(rule):
            return False
        if rule.get("type") == RULE_TYPE_EVENT:
            expiry = self._event_expiry.get(rule_id)
            if expiry is None or expiry <= utc_now():
                return False
        try:
            return target in self._targets.resolve_rule(rule).targets
        except AdvancedTargetError:
            return False

    async def _async_evaluate(self, rule: Mapping[str, Any]) -> None:
        if self._stopped:
            return
        async with self._evaluation_lock:
            if self._stopped:
                return
            if not _is_enabled(rule):
                await self._release(rule)
                return
            try:
                resolved_result = self._targets.resolve_rule(rule)
            except AdvancedTargetError as err:
                _LOGGER.warning(
                    "Ignoring rule %s because targets are invalid (%s): %s",
                    rule.get("id"),
                    err.code,
                    err,
                )
                await self._release(rule)
                return
            rule_id = str(rule["id"])
            resolved = resolved_result.targets
            targets_changed = self._resolved_targets.get(rule_id) != resolved
            self._resolved_targets[rule_id] = resolved
            rule_type = rule.get("type")
            if rule_type == RULE_TYPE_STATE:
                await self._async_evaluate_state(
                    rule, targets=resolved, targets_changed=targets_changed
                )
            elif rule_type == RULE_TYPE_NUMERIC:
                await self._async_evaluate_numeric(
                    rule, targets=resolved, targets_changed=targets_changed
                )
            elif rule_type != RULE_TYPE_EVENT:
                _LOGGER.warning(
                    "Ignoring rule %s with unknown type %s", rule.get("id"), rule_type
                )
                await self._release(rule)

    async def _async_evaluate_state(
        self,
        rule: Mapping[str, Any],
        *,
        targets: frozenset[str] | None = None,
        targets_changed: bool = False,
    ) -> None:
        del targets_changed
        state = self._hass.states.get(str(rule["source"]))
        if state is None or state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            await self._release(rule)
            return
        expected = str(rule.get("state", ""))
        matched = state.state == expected
        if rule.get("operator", "equals") == "not_equals":
            matched = not matched
        if not matched or not self._extra_conditions_match(rule):
            await self._release(rule)
            return
        if not self._dwell_is_ready(rule):
            return
        resolved = targets or self._targets.resolve_rule(rule).targets
        await self._submit(
            self._request(rule, state, targets=resolved, request_id=_request_id(rule))
        )

    async def _async_evaluate_numeric(
        self,
        rule: Mapping[str, Any],
        *,
        targets: frozenset[str] | None = None,
        targets_changed: bool = False,
    ) -> None:
        rule_id = str(rule["id"])
        state = self._hass.states.get(str(rule["source"]))
        numeric = parse_numeric_state(state.state if state else None)
        if state is None or numeric is None:
            self._numeric_activation.pop(rule_id, None)
            self._last_numeric.pop(rule_id, None)
            await self._release(rule)
            return

        activation = rule.get("activation")
        if isinstance(activation, Mapping):
            active = numeric_activation_matches(
                numeric,
                activation,
                previous=self._numeric_activation.get(rule_id, False),
            )
            self._numeric_activation[rule_id] = active
            if not active:
                await self._release(rule)
                return
        if not self._extra_conditions_match(rule):
            await self._release(rule)
            return
        if not self._dwell_is_ready(rule):
            return

        last_value = self._last_numeric.get(rule_id)
        minimum_change = float(rule.get("minimum_change", 0))
        if (
            not targets_changed
            and rule_id in self._activated_at
            and last_value is not None
            and abs(numeric - last_value) < minimum_change
        ):
            return

        minimum_interval = max(0.0, float(rule.get("minimum_interval", 0)))
        elapsed = monotonic() - self._last_numeric_update.get(rule_id, 0.0)
        if not targets_changed and elapsed < minimum_interval:
            self._schedule_numeric(rule, minimum_interval - elapsed)
            return

        try:
            if rule.get("points"):
                points = tuple(
                    ColorPoint(float(point["value"]), tuple(point["rgb"]))
                    for point in rule.get("points", [])
                )
                mode = (
                    "ranges"
                    if rule.get("mode") in {"range", "ranges"}
                    else "interpolate"
                )
                color = interpolate_rgb(numeric, points, mode=mode)
            else:
                color = tuple(int(value) for value in rule["rgb_color"])
        except (KeyError, TypeError, ValueError):
            _LOGGER.exception("Invalid numeric rule %s", rule_id)
            await self._release(rule)
            return

        pending = self._pending.pop(rule_id, None)
        if pending is not None:
            pending()
        self._last_numeric[rule_id] = numeric
        self._last_numeric_update[rule_id] = monotonic()
        resolved = targets or self._targets.resolve_rule(rule).targets
        await self._submit(
            self._request(
                rule,
                state,
                targets=resolved,
                request_id=_request_id(rule),
                color=color,
                metadata={"numeric_value": numeric},
            )
        )

    async def _async_event_fired(
        self,
        rule: Mapping[str, Any],
        variables: Mapping[str, Any],
        context: Context | None,
    ) -> None:
        """Create or renew one bounded request for the current event only."""

        if self._stopped or not _is_enabled(rule):
            return
        async with self._evaluation_lock:
            if self._stopped or not self._extra_conditions_match(rule):
                return
            try:
                resolved = self._targets.resolve_rule(rule)
            except AdvancedTargetError as err:
                _LOGGER.warning(
                    "Discarding event for rule %s because targets are invalid (%s): %s",
                    rule.get("id"),
                    err.code,
                    err,
                )
                return
            rule_id = str(rule["id"])
            targets = resolved.targets
            now = utc_now()
            expires_at = now + timedelta(seconds=float(rule.get("duration", 5)))
            self._activated_at[rule_id] = now
            self._event_expiry[rule_id] = expires_at
            self._resolved_targets[rule_id] = targets
            trigger = variables.get("trigger")
            description = (
                trigger.get("description") if isinstance(trigger, Mapping) else None
            )
            await self._submit(
                self._request(
                    rule,
                    None,
                    targets=targets,
                    request_id=_request_id(rule),
                    expires_at=expires_at,
                    source=f"event:{rule.get('trigger', {}).get('platform', 'unknown')}",
                    metadata={
                        "trigger": str(description or "event"),
                        "context_id": context.id if context is not None else None,
                    },
                )
            )

    async def _async_refresh_event_targets(self, rule: Mapping[str, Any]) -> None:
        """Move an unexpired event request without renewing or replaying it."""

        async with self._evaluation_lock:
            await self._async_refresh_event_targets_locked(rule)

    async def _async_refresh_event_targets_locked(
        self, rule: Mapping[str, Any]
    ) -> None:
        """Refresh an event request while the rule evaluation lock is held."""

        rule_id = str(rule["id"])
        expires_at = self._event_expiry.get(rule_id)
        if expires_at is None:
            return
        if expires_at <= utc_now():
            self._event_expiry.pop(rule_id, None)
            self._activated_at.pop(rule_id, None)
            return
        try:
            resolved = self._targets.resolve_rule(rule)
        except AdvancedTargetError as err:
            _LOGGER.warning(
                "Cancelling active event rule %s after target change (%s): %s",
                rule_id,
                err.code,
                err,
            )
            await self._release(rule)
            return
        targets = resolved.targets
        if targets == self._resolved_targets.get(rule_id):
            return
        self._resolved_targets[rule_id] = targets
        await self._submit(
            self._request(
                rule,
                None,
                targets=targets,
                request_id=_request_id(rule),
                expires_at=expires_at,
                source=f"event:{rule.get('trigger', {}).get('platform', 'unknown')}",
                metadata={"trigger": "active event target refresh"},
            )
        )

    def _extra_conditions_match(self, rule: Mapping[str, Any]) -> bool:
        """Evaluate optional conditions and schedule as one logical AND."""

        try:
            condition = validate_condition_tree(rule.get("conditions"))
            raw_schedule = rule.get("schedule")
            schedule = (
                validate_condition_tree({"type": "time", **raw_schedule})
                if isinstance(raw_schedule, Mapping)
                else None
            )
        except (ConditionValidationError, TypeError):
            _LOGGER.exception("Invalid conditions in rule %s", rule.get("id"))
            return False
        now_local = dt_util.now()
        return all(
            evaluate_condition(item, self._hass.states.get, now_local)
            is ConditionResult.TRUE
            for item in (condition, schedule)
            if item is not None
        )

    def _dwell_is_ready(self, rule: Mapping[str, Any]) -> bool:
        """Apply minimum dwell to the final continuous-rule result."""

        rule_id = str(rule["id"])
        delay = max(0.0, float(rule.get("for_seconds", 0)))
        if delay == 0 or rule_id in self._activated_at:
            return True
        if rule_id in self._dwell_ready:
            self._dwell_ready.remove(rule_id)
            return True
        if rule_id in self._holds:
            return False

        @callback
        def _run(_now: datetime) -> None:
            self._holds.pop(rule_id, None)
            if self._stopped:
                return
            self._dwell_ready.add(rule_id)
            self._create_task(
                self._async_evaluate(rule),
                f"smart_led_manager_dwell_rule_{rule_id}",
            )

        self._holds[rule_id] = async_call_later(self._hass, delay, _run)
        return False

    def _schedule_numeric(self, rule: Mapping[str, Any], delay: float) -> None:
        rule_id = str(rule["id"])
        if rule_id in self._pending:
            return

        @callback
        def _run(_now: datetime) -> None:
            self._pending.pop(rule_id, None)
            if self._stopped:
                return
            self._create_task(
                self._async_evaluate(rule),
                f"smart_led_manager_deferred_rule_{rule_id}",
            )

        self._pending[rule_id] = async_call_later(self._hass, delay, _run)

    def _schedule_next_boundary(self) -> None:
        """Schedule the next effective local-time boundary without polling."""

        if self._schedule_unsubscribe is not None:
            self._schedule_unsubscribe()
            self._schedule_unsubscribe = None
        schedules = [
            schedule
            for rule in self._rules.values()
            if _is_enabled(rule) and rule.get("type") != RULE_TYPE_EVENT
            for schedule in self._rule_schedules(rule)
        ]
        if not schedules:
            return
        now = dt_util.now()
        candidates: list[datetime] = []
        for schedule in schedules:
            after = time.fromisoformat(str(schedule["after"]))
            before = time.fromisoformat(str(schedule["before"]))
            weekdays = set(schedule["weekdays"])
            for offset in range(9):
                start_date = now.date() + timedelta(days=offset)
                weekday = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")[
                    start_date.weekday()
                ]
                if weekday not in weekdays:
                    continue
                if after == before:
                    candidates.append(
                        datetime.combine(start_date, time.min, tzinfo=now.tzinfo)
                    )
                    candidates.append(
                        datetime.combine(
                            start_date + timedelta(days=1),
                            time.min,
                            tzinfo=now.tzinfo,
                        )
                    )
                    continue
                candidates.append(
                    datetime.combine(start_date, after, tzinfo=now.tzinfo)
                )
                end_date = (
                    start_date + timedelta(days=1) if after > before else start_date
                )
                candidates.append(datetime.combine(end_date, before, tzinfo=now.tzinfo))
        future = [candidate for candidate in candidates if candidate > now]
        if not future:
            return

        @callback
        def _run(_now: datetime) -> None:
            self._schedule_unsubscribe = None
            if self._stopped:
                return
            self._create_task(
                self._async_schedule_boundary(),
                "smart_led_manager_schedule_boundary",
            )

        self._schedule_unsubscribe = async_track_point_in_time(
            self._hass, _run, min(future)
        )

    async def _async_schedule_boundary(self) -> None:
        self._schedule_next_boundary()
        for rule in self._rules.values():
            if _is_enabled(rule) and rule.get("type") != RULE_TYPE_EVENT:
                await self._async_evaluate(rule)

    def _condition_entities(self, rule: Mapping[str, Any]) -> frozenset[str]:
        try:
            return condition_entity_ids(validate_condition_tree(rule.get("conditions")))
        except ConditionValidationError:
            return frozenset()

    def _rule_schedules(self, rule: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
        schedules: list[dict[str, Any]] = []
        try:
            schedules.extend(
                condition_schedules(validate_condition_tree(rule.get("conditions")))
            )
            if isinstance(rule.get("schedule"), Mapping):
                schedule = validate_condition_tree({"type": "time", **rule["schedule"]})
                if schedule is not None:
                    schedules.append(schedule)
        except ConditionValidationError:
            return ()
        return tuple(schedules)

    def _group_entities(self, rule: Mapping[str, Any]) -> frozenset[str]:
        selection = rule.get("target_selection")
        if not isinstance(selection, Mapping):
            return frozenset()
        roots = frozenset(_string_items(selection.get("groups")))
        return roots | self._resolved_groups.get(str(rule.get("id", "")), frozenset())

    def _create_task(self, coroutine: Awaitable[None], name: str) -> None:
        """Own one bounded evaluation task until completion or shutdown."""

        task = self._hass.async_create_task(coroutine, name)
        self._tasks.add(task)
        task.add_done_callback(self._task_done)

    @callback
    def _task_done(self, task: asyncio.Task[None]) -> None:
        """Retrieve task failures so rule events never leak exceptions."""

        self._tasks.discard(task)
        if task.cancelled():
            return
        if error := task.exception():
            _LOGGER.error("Rule evaluation failed", exc_info=error)

    def _request(
        self,
        rule: Mapping[str, Any],
        state: State | None,
        *,
        targets: frozenset[str],
        request_id: str,
        color: tuple[int, int, int] | None = None,
        expires_at: datetime | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Request:
        rule_id = str(rule["id"])
        now = utc_now()
        activated_at = self._activated_at.setdefault(rule_id, now)
        rgb = color or tuple(
            int(value) for value in rule.get("rgb_color", [255, 255, 255])
        )
        animation_name = str(rule.get("animation", "fixed"))
        animation = AnimationSpec(
            kind=(
                AnimationKind.NONE
                if animation_name == "fixed"
                else AnimationKind(animation_name)
            ),
            interval=float(rule.get("period", 1)),
        )
        return Request(
            request_id=request_id,
            source=source or str(rule.get("source", "rule")),
            name=str(rule.get("name", rule_id)),
            module="rule",
            targets=targets,
            priority=int(rule.get("priority", 40)),
            command=LightCommand(
                color=rgb,
                brightness=int(rule.get("brightness", 255)),
                transition=float(rule.get("transition", 0)),
                animation=animation,
            ),
            activated_at=activated_at,
            updated_at=now,
            expires_at=expires_at,
            metadata={
                "rule_id": rule_id,
                "source_state": state.state if state is not None else None,
                **(metadata or {}),
            },
        )

    async def _release(self, rule: Mapping[str, Any]) -> None:
        rule_id = str(rule["id"])
        for collection in (self._pending, self._holds):
            pending = collection.pop(rule_id, None)
            if pending is not None:
                pending()
        self._dwell_ready.discard(rule_id)
        self._activated_at.pop(rule_id, None)
        self._event_expiry.pop(rule_id, None)
        await self._cancel(_request_id(rule))


def _request_id(rule: Mapping[str, Any]) -> str:
    return f"rule:{rule['id']}"


def _is_enabled(rule: Mapping[str, Any]) -> bool:
    """Treat pre-alpha.3 rules without an enabled field as enabled."""

    return rule.get("enabled", True) is not False


def _string_items(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item)
