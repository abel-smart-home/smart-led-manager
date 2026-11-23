"""Home Assistant orchestration for Smart LED Manager."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Callable
from dataclasses import replace
from datetime import timedelta
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_RGB_COLOR
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_LIGHTS,
    CONF_MANUAL_POLICY,
    CONF_MIN_COMMAND_INTERVAL,
    CONF_MODES,
    CONF_RULES,
    CONF_TIE_BREAKER,
    CONF_ZONES,
    DEFAULT_MANUAL_POLICY,
    DEFAULT_MIN_COMMAND_INTERVAL,
    DEFAULT_TIE_BREAKER,
    EVENT_REQUEST_CHANGED,
    MAX_ACTIVITY_ITEMS,
    MODULE_MANUAL,
)
from .controllers.base import ApplyStatus, UnsupportedLightCommandError
from .controllers.rgb import RGBLightController
from .core.engine import PriorityEngine
from .core.scheduler import AnimationScheduler, DeadlineScheduler
from .core.targets import TargetResolver
from .models import (
    AnimationSpec,
    DecisionChange,
    LightCommand,
    Request,
    TieBreaker,
    utc_now,
)
from .modules.modes import ModeManager, ModeValidationError
from .modules.rules import RuleManager
from .storage import SmartLEDStorage

_LOGGER = logging.getLogger(__name__)

_FAILED_SEND_RECOVERY_DELAY = 5.0

CoordinatorListener = Callable[[], None]


class SmartLEDCoordinator:
    """Own the engine, physical controller, subscriptions, and persistence."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        options = dict(entry.options)
        lights = options.get(CONF_LIGHTS, entry.data.get(CONF_LIGHTS, []))
        self.targets = TargetResolver(lights)
        self.engine = PriorityEngine(
            tie_breaker=TieBreaker(options.get(CONF_TIE_BREAKER, DEFAULT_TIE_BREAKER))
        )
        self.controller = RGBLightController(
            hass,
            minimum_interval=float(
                options.get(CONF_MIN_COMMAND_INTERVAL, DEFAULT_MIN_COMMAND_INTERVAL)
            ),
        )
        self.animations = AnimationScheduler()
        self.expiry = DeadlineScheduler()
        self.storage = SmartLEDStorage(hass, entry.entry_id)
        catalog_error: str | None = None
        self.catalog_valid = True
        try:
            self.modes = ModeManager(
                self.engine,
                list(options.get(CONF_ZONES, [])),
                list(options.get(CONF_MODES, [])),
                self.targets.authorized,
            )
        except ModeValidationError as err:
            self.catalog_valid = False
            catalog_error = f"Invalid mode catalog ignored: {err.key}"
            _LOGGER.error("%s", catalog_error)
            self.modes = ModeManager(self.engine, [], [], self.targets.authorized)
        self.rules = RuleManager(
            hass,
            list(options.get(CONF_RULES, [])),
            self.targets.authorized,
            self.async_submit,
            self.async_cancel,
        )
        self.manual_policy = str(options.get(CONF_MANUAL_POLICY, DEFAULT_MANUAL_POLICY))
        self.history: deque[dict[str, Any]] = deque(maxlen=MAX_ACTIVITY_ITEMS)
        self.last_error: str | None = catalog_error
        self.status = "idle"
        self.request_count = 0
        self._winners: dict[str, str] = {}
        self._listeners: set[CoordinatorListener] = set()
        self._unsub_lights: Callable[[], None] | None = None
        self._manual_activated: dict[str, Any] = {}
        self._persisted_request_ids: set[str] = set()
        self._recovery_tasks: dict[str, asyncio.Task[None]] = {}
        self._failed_send_recovery_delay = _FAILED_SEND_RECOVERY_DELAY
        self._mutation_lock = asyncio.Lock()
        self._started = False

    async def async_initialize(self) -> None:
        """Restore durable intent and start event-driven processing."""
        stored = await self.storage.async_load()
        changes: tuple[DecisionChange, ...] = ()
        storage_changed = False
        if stored:
            authorized: list[Request] = []
            rejected = 0
            for item in stored:
                try:
                    request = Request.from_dict(item)
                    self.targets.resolve(request.targets)
                except (TypeError, ValueError) as err:
                    rejected += 1
                    if item.get(
                        "module"
                    ) == "mode" or ModeManager.is_internal_request_id(
                        str(item.get("request_id", ""))
                    ):
                        storage_changed = True
                    _LOGGER.warning(
                        "Ignoring unauthorized or invalid stored request %s: %s",
                        item.get("request_id", "<unknown>"),
                        err,
                    )
                    continue
                authorized.append(request)
            if rejected:
                self.last_error = (
                    f"Ignored {rejected} invalid or unauthorized stored request(s)"
                )
            try:
                reconciled, modes_changed = self.modes.reconcile_requests(authorized)
                storage_changed = storage_changed or modes_changed
                changes = await self.engine.async_restore(
                    request.to_dict() for request in reconciled
                )
            except (TypeError, ValueError):
                storage_changed = True
                self.last_error = "Stored requests were invalid and were ignored"
                _LOGGER.exception("Unable to restore Smart LED Manager requests")
        self._persisted_request_ids = {
            str(item["request_id"])
            for item in await self.engine.async_serialize(persistent_only=True)
        }
        if storage_changed:
            await self._async_save()

        self._unsub_lights = async_track_state_change_event(
            self.hass,
            sorted(self.targets.authorized),
            self._async_light_state_changed,
        )
        self._started = True
        await self._async_apply_changes(changes)
        await self.rules.async_setup()
        await self._async_refresh_metadata()
        await self._async_schedule_expiry()
        self._notify_listeners()

    async def async_submit(self, request: Request) -> None:
        """Authorize, submit, apply, persist, and reschedule a request."""
        if ModeManager.is_internal_request(request):
            raise ModeValidationError("managed_mode_request")
        resolved = self.targets.resolve(request.targets)
        if resolved != request.targets:
            request = replace(request, targets=resolved)
        async with self._mutation_lock:
            save = (
                request.persistent or request.request_id in self._persisted_request_ids
            )
            changes = await self.engine.async_submit(request)
            await self._async_apply_changes(changes)
            await self._async_after_mutation(save=save)

    async def async_deactivate(self, request_id: str) -> None:
        """Deactivate a request without deleting its record."""
        if ModeManager.is_internal_request_id(request_id):
            raise ModeValidationError("managed_mode_request")
        async with self._mutation_lock:
            save = request_id in self._persisted_request_ids
            changes = await self.engine.async_deactivate(request_id)
            self._forget_manual_activation(request_id)
            await self._async_apply_changes(changes)
            await self._async_after_mutation(save=save)

    async def async_cancel(self, request_id: str) -> None:
        """Delete a request and expose the next valid winner."""
        if ModeManager.is_internal_request_id(request_id):
            raise ModeValidationError("managed_mode_request")
        async with self._mutation_lock:
            save = request_id in self._persisted_request_ids
            changes = await self.engine.async_cancel(request_id)
            self._forget_manual_activation(request_id)
            await self._async_apply_changes(changes)
            await self._async_after_mutation(save=save)

    async def async_activate_mode(self, mode_id: str) -> None:
        """Select one configured mode through the protected mode manager."""
        mode = self.modes.mode(mode_id)
        await self.async_set_zone_mode(mode.zone_id, mode_id)

    async def async_deactivate_mode(self, mode_id: str) -> None:
        """Clear one configured mode if it is currently selected."""
        async with self._mutation_lock:
            mutation = await self.modes.async_deactivate(mode_id)
            if not mutation.changed:
                return
            await self._async_apply_changes(mutation.changes)
            await self._async_after_mutation(save=True)

    async def async_set_zone_mode(self, zone_id: str, mode_id: str | None) -> None:
        """Atomically replace a zone's selected mode, or select no mode."""
        async with self._mutation_lock:
            mutation = await self.modes.async_set_zone_mode(zone_id, mode_id)
            if not mutation.changed:
                return
            await self._async_apply_changes(mutation.changes)
            await self._async_after_mutation(save=True)

    async def async_clear_notifications(
        self, targets: frozenset[str] | None = None
    ) -> None:
        """Cancel notification requests, optionally intersecting targets."""
        async with self._mutation_lock:
            persistent_ids = self._persisted_request_ids.copy()
            save = False

            def _matches(request: Request) -> bool:
                nonlocal save
                matched = request.module == "notification" and (
                    targets is None or bool(request.targets.intersection(targets))
                )
                if matched and request.request_id in persistent_ids:
                    save = True
                return matched

            changes = await self.engine.async_cancel_matching(_matches)
            await self._async_apply_changes(changes)
            await self._async_after_mutation(save=save)

    async def async_set_manual_override(
        self,
        targets: frozenset[str],
        *,
        enabled: bool,
        command: LightCommand | None = None,
        priority: int = 60,
    ) -> None:
        """Create or remove stable manual requests for selected targets."""
        targets = self.targets.resolve(targets)
        for target in sorted(targets):
            request_id = f"manual:{target}"
            if not enabled:
                await self.async_cancel(request_id)
                await self.async_cancel(f"manual:detected:{target}")
                continue
            state = self.hass.states.get(target)
            effective = command or _command_from_state(state)
            now = utc_now()
            await self.async_submit(
                Request(
                    request_id=request_id,
                    source="manual_action",
                    name=f"Manual override {target}",
                    module=MODULE_MANUAL,
                    targets=frozenset({target}),
                    priority=priority,
                    command=effective,
                    activated_at=now,
                    updated_at=now,
                    persistent=True,
                )
            )

    @callback
    def async_add_listener(self, listener: CoordinatorListener) -> Callable[[], None]:
        """Register an entity/runtime listener."""
        self._listeners.add(listener)

        @callback
        def _remove() -> None:
            self._listeners.discard(listener)

        return _remove

    async def async_diagnostics(self) -> dict[str, Any]:
        """Return bounded, non-secret runtime diagnostics."""
        requests = await self.engine.async_requests()
        return {
            "status": self.status,
            "managed_targets": sorted(self.targets.authorized),
            "tie_breaker": self.engine.tie_breaker.value,
            "minimum_command_interval": self.controller.minimum_interval,
            "manual_policy": self.manual_policy,
            "request_count": len(requests),
            "requests": [request.to_dict() for request in requests],
            "mode_catalog": self.modes.snapshot(self._winners),
            "winners": dict(sorted(self._winners.items())),
            "animation_targets": sorted(self.animations.active_targets),
            "pending_controller_targets": sorted(self.controller.pending_targets),
            "last_error": self.last_error,
            "history": list(self.history),
        }

    async def async_shutdown(self) -> None:
        """Release every listener and task without blind physical restoration."""
        self._started = False
        await self.rules.async_shutdown()
        if self._unsub_lights is not None:
            self._unsub_lights()
            self._unsub_lights = None
        await self.expiry.async_shutdown()
        await self._async_cancel_recoveries()
        await self.animations.async_shutdown()
        await self.controller.async_shutdown()
        await self._async_save()
        self.status = "stopped"
        self._notify_listeners()

    async def async_remove_storage(self) -> None:
        """Delete retained data when Home Assistant removes the entry."""
        await self.storage.async_remove()

    async def _async_after_mutation(self, *, save: bool) -> None:
        await self._async_refresh_metadata()
        if save:
            await self._async_save()
        await self._async_schedule_expiry()
        self._notify_listeners()

    async def _async_refresh_metadata(self) -> None:
        requests = await self.engine.async_requests()
        self.request_count = len(requests)
        self.status = "active" if self._winners else "idle"

    async def _async_save(self) -> None:
        serialized = await self.engine.async_serialize(persistent_only=True)
        await self.storage.async_save(serialized)
        self._persisted_request_ids = {str(item["request_id"]) for item in serialized}

    async def _async_schedule_expiry(self) -> None:
        self.expiry.schedule(await self.engine.async_next_expiry(), self._async_expire)

    async def _async_expire(self) -> None:
        async with self._mutation_lock:
            changes = await self.engine.async_expire()
            requests = await self.engine.async_requests()
            request_ids = {request.request_id for request in requests}
            for target in tuple(self._manual_activated):
                if f"manual:detected:{target}" not in request_ids:
                    self._manual_activated.pop(target, None)
            persistent_ids = {
                request.request_id
                for request in requests
                if request.persistent and request.active
            }
            await self._async_apply_changes(changes)
            await self._async_after_mutation(
                save=persistent_ids != self._persisted_request_ids
            )

    async def _async_apply_changes(self, changes: tuple[DecisionChange, ...]) -> None:
        if not changes:
            return
        await asyncio.gather(*(self._async_apply_change(change) for change in changes))

    async def _async_apply_change(self, change: DecisionChange) -> None:
        await self._async_cancel_recovery(change.target)
        await self.animations.async_cancel(change.target)
        await self.controller.async_cancel(change.target)
        current = change.current
        if current is None:
            self._winners.pop(change.target, None)
            status = "released"
        else:
            self._winners[change.target] = current.request_id

            async def _apply_frame(command: LightCommand) -> None:
                try:
                    result = await self.controller.async_apply(
                        change.target,
                        command,
                        allow_turn_on=current.allow_turn_on,
                    )
                except (HomeAssistantError, TimeoutError) as err:
                    self.controller.invalidate_applied_state(change.target)
                    self.last_error = (
                        f"{change.target}: send failed: {type(err).__name__}: {err}"
                    )
                    self.status = "error"
                    _LOGGER.warning(
                        "Unable to apply current intent to %s: %s; "
                        "intent retained and recovery scheduled",
                        change.target,
                        err,
                    )
                    self._schedule_recovery(
                        change.target,
                        "send_failure",
                        delay=self._failed_send_recovery_delay,
                    )
                    return
                except (UnsupportedLightCommandError, ValueError) as err:
                    self.last_error = f"{change.target}: {err}"
                    self.status = "error"
                    _LOGGER.error("Unable to apply %s: %s", change.target, err)
                    return
                if result.status is ApplyStatus.OFFLINE:
                    if result.detail is not None:
                        self.last_error = f"{change.target}: {result.detail}"
                        self.status = "error"
                        _LOGGER.warning(
                            "Unable to apply current intent to %s: %s; intent retained",
                            change.target,
                            result.detail,
                        )
                        self._schedule_recovery(
                            change.target,
                            "send_failure",
                            delay=self._failed_send_recovery_delay,
                        )
                    else:
                        _LOGGER.info(
                            "Managed light %s is unavailable; intent retained",
                            change.target,
                        )

            await self.animations.async_apply(change.target, current, _apply_frame)
            status = current.request_id

        event = {
            "timestamp": utc_now().isoformat(),
            "target": change.target,
            "previous": change.previous.request_id if change.previous else None,
            "current": current.request_id if current else None,
            "reason": change.reason,
            "result": status,
        }
        self.history.append(event)
        self.hass.bus.async_fire(EVENT_REQUEST_CHANGED, event)

    @callback
    def _async_light_state_changed(self, event: Event) -> None:
        if not self._started:
            return
        target = event.data.get("entity_id")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if target not in self.targets.authorized or new_state is None:
            return
        if new_state.state not in {STATE_UNAVAILABLE, STATE_UNKNOWN} and (
            old_state is None or old_state.state in {STATE_UNAVAILABLE, STATE_UNKNOWN}
        ):
            self.controller.invalidate_applied_state(target)
            self._schedule_recovery(target, "resync")
            return
        if new_state.state in {STATE_UNAVAILABLE, STATE_UNKNOWN}:
            return
        if self.controller.is_own_context(event.context):
            return
        if self.manual_policy == "service_only":
            self.controller.invalidate_applied_state(target)
            self._schedule_recovery(target, "reassert")
            return
        self.hass.async_create_task(
            self._async_detect_manual(target, new_state),
            f"smart_led_manager_manual_{target}",
        )

    @callback
    def _schedule_recovery(
        self, target: str, operation: str, *, delay: float = 0.0
    ) -> None:
        """Own one safe recovery task per target."""
        existing = self._recovery_tasks.get(target)
        if existing is not None and not existing.done():
            _LOGGER.debug(
                "Recovery for %s is already active; ignoring duplicate %s event",
                target,
                operation,
            )
            return
        task = self.hass.async_create_task(
            self._async_retry_target(target, operation, delay=delay),
            f"smart_led_manager_{operation}_{target}",
        )
        self._recovery_tasks[target] = task
        _LOGGER.info(
            "Scheduled %s recovery for %s in %.2f seconds",
            operation,
            target,
            delay,
        )
        task.add_done_callback(
            lambda completed, target=target: self._discard_recovery_task(
                target, completed
            )
        )

    async def _async_retry_target(
        self, target: str, operation: str, *, delay: float = 0.0
    ) -> None:
        """Retry retained intent and contain every recovery-task failure."""
        try:
            if delay > 0:
                await asyncio.sleep(delay)
            result = await self.controller.async_retry(target)
        except asyncio.CancelledError:
            raise
        except Exception as err:
            self._record_recovery_error(
                target,
                operation,
                f"{type(err).__name__}: {err}",
            )
            _LOGGER.exception(
                "Unexpected %s recovery failure for %s", operation, target
            )
            return

        if result is None or result.status is ApplyStatus.SUPERSEDED:
            return
        if result.status is ApplyStatus.OFFLINE:
            if result.detail is None:
                _LOGGER.info(
                    "Managed light %s became unavailable during %s; "
                    "current intent remains retained",
                    target,
                    operation,
                )
                return
            self._record_recovery_error(target, operation, result.detail)
            _LOGGER.warning(
                "%s recovery for %s exhausted its bounded attempts: %s",
                operation.capitalize(),
                target,
                result.detail,
            )
            return

        error_prefixes = (
            f"{target}: recovery failed",
            f"{target}: send failed",
        )
        if self.last_error is not None and self.last_error.startswith(error_prefixes):
            self.last_error = None
            self.status = "active" if self._winners else "idle"
            self._notify_listeners()
        _LOGGER.info(
            "%s recovery for %s completed with %s",
            operation.capitalize(),
            target,
            result.status,
        )

    def _record_recovery_error(self, target: str, operation: str, detail: str) -> None:
        """Expose a contained recovery failure through runtime diagnostics."""
        self.last_error = f"{target}: recovery failed during {operation}: {detail}"
        self.status = "error"
        self._notify_listeners()

    async def _async_cancel_recovery(self, target: str) -> None:
        """Cancel and await one target's recovery task."""
        task = self._recovery_tasks.pop(target, None)
        if task is None:
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def _async_cancel_recoveries(self) -> None:
        """Cancel and await all recovery tasks during unload."""
        tasks = tuple(self._recovery_tasks.values())
        self._recovery_tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _discard_recovery_task(
        self, target: str, completed: asyncio.Task[None]
    ) -> None:
        """Release task ownership and retrieve defensive-boundary failures."""
        if self._recovery_tasks.get(target) is completed:
            self._recovery_tasks.pop(target, None)
        if not completed.cancelled() and (error := completed.exception()) is not None:
            _LOGGER.error(
                "Recovery task for %s failed unexpectedly: %s",
                target,
                error,
                exc_info=error,
            )

    async def _async_detect_manual(self, target: str, state) -> None:
        now = utc_now()
        activated = self._manual_activated.setdefault(target, now)
        expires = (
            now + timedelta(minutes=15) if self.manual_policy == "temporary" else None
        )
        await self.async_submit(
            Request(
                request_id=f"manual:detected:{target}",
                source="physical_state_change",
                name=f"Detected manual control {target}",
                module=MODULE_MANUAL,
                targets=frozenset({target}),
                priority=60,
                command=_command_from_state(state),
                activated_at=activated,
                updated_at=now,
                expires_at=expires,
                persistent=self.manual_policy == "respect",
                metadata={"attribution": "state_context"},
            )
        )

    @callback
    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    def _forget_manual_activation(self, request_id: str) -> None:
        """Forget tie age after a detected manual request ends."""
        prefix = "manual:detected:"
        if request_id.startswith(prefix):
            self._manual_activated.pop(request_id.removeprefix(prefix), None)


type SmartLEDManagerConfigEntry = ConfigEntry[SmartLEDCoordinator]


def _command_from_state(state) -> LightCommand:
    if state is None or state.state == STATE_OFF:
        return LightCommand(turn_on=False)
    rgb = state.attributes.get(ATTR_RGB_COLOR)
    color = (
        tuple(int(channel) for channel in rgb)
        if isinstance(rgb, (list, tuple)) and len(rgb) == 3
        else None
    )
    brightness = state.attributes.get(ATTR_BRIGHTNESS)
    return LightCommand(
        turn_on=True,
        color=color,
        brightness=int(brightness) if isinstance(brightness, (int, float)) else None,
        animation=AnimationSpec(),
    )
