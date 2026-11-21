"""Capability-aware, rate-limited Home Assistant light controller."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from time import monotonic

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_EFFECT_LIST,
    ATTR_RGB_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    ATTR_TRANSITION,
    ColorMode,
    LightEntityFeature,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Context, HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError

from ..models import LightCommand
from .base import ApplyResult, ApplyStatus, UnsupportedLightCommandError

_LOGGER = logging.getLogger(__name__)

_COLOR_MODES = {
    ColorMode.HS,
    ColorMode.RGB,
    ColorMode.RGBW,
    ColorMode.RGBWW,
    ColorMode.XY,
}


@dataclass(frozen=True, slots=True)
class _Desired:
    command: LightCommand
    allow_turn_on: bool
    generation: int


class RGBLightController:
    """Project logical commands onto existing Home Assistant lights.

    A target owns one worker. New desired states replace its pending state, so a
    backlog cannot replay obsolete animation frames after a higher priority wins.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        minimum_interval: float = 0.75,
        global_minimum_interval: float = 0.05,
        max_parallel_commands: int = 4,
        max_recovery_attempts: int = 3,
        retry_base_delay: float = 1.0,
        retry_max_delay: float = 4.0,
    ) -> None:
        self._hass = hass
        self._minimum_interval = max(0.1, float(minimum_interval))
        self._global_minimum_interval = max(0.0, float(global_minimum_interval))
        self._parallel = asyncio.Semaphore(max_parallel_commands)
        self._global_lock = asyncio.Lock()
        self._max_recovery_attempts = max(1, int(max_recovery_attempts))
        self._retry_base_delay = max(0.0, float(retry_base_delay))
        self._retry_max_delay = max(self._retry_base_delay, float(retry_max_delay))
        self._desired: dict[str, _Desired] = {}
        self._workers: dict[str, asyncio.Task[ApplyResult]] = {}
        self._recovery_generation: dict[str, int] = {}
        self._last_sent: dict[str, float] = {}
        self._last_global_sent = 0.0
        self._last_signature: dict[str, tuple[object, ...]] = {}
        self._force_send: set[str] = set()
        self._contexts: dict[str, float] = {}
        self._generation = 0
        self._stopping = False

    @property
    def minimum_interval(self) -> float:
        """Return the per-target rate limit in seconds."""
        return self._minimum_interval

    @property
    def pending_targets(self) -> frozenset[str]:
        """Return targets with desired state waiting or retained offline."""
        return frozenset(self._desired)

    def update_minimum_interval(self, value: float) -> None:
        """Change the interval for future commands."""
        self._minimum_interval = max(0.1, float(value))

    async def async_apply(
        self,
        target: str,
        command: LightCommand,
        *,
        allow_turn_on: bool = True,
    ) -> ApplyResult:
        """Set the latest desired command and wait for its target worker."""
        if self._stopping:
            return ApplyResult(target, ApplyStatus.SUPERSEDED, "controller stopping")
        self._generation += 1
        desired = _Desired(command, allow_turn_on, self._generation)
        self._desired[target] = desired

        return await self._async_wait_for_worker(target, desired)

    async def async_retry(self, target: str) -> ApplyResult | None:
        """Retry the retained current intent without creating a new generation."""
        desired = self._desired.get(target)
        if desired is None:
            return None
        self._recovery_generation[target] = desired.generation
        return await self._async_wait_for_worker(target, desired)

    async def _async_wait_for_worker(
        self, target: str, desired: _Desired
    ) -> ApplyResult:
        """Start or share the one worker that owns a target's latest intent."""

        worker = self._workers.get(target)
        if worker is None or worker.done():
            worker = asyncio.create_task(
                self._async_worker(target), name=f"smart_led_manager_command_{target}"
            )
            self._workers[target] = worker
            worker.add_done_callback(
                lambda completed, target=target: self._discard_worker(target, completed)
            )

        try:
            result = await asyncio.shield(worker)
        except asyncio.CancelledError:
            # ``async_cancel`` deliberately cancels stale shared work. Report
            # that outcome to a still-running caller, while preserving normal
            # task cancellation when the caller itself is being cancelled.
            if self._desired.get(target) is not desired:
                return ApplyResult(target, ApplyStatus.SUPERSEDED)
            raise
        if self._desired.get(target) is not desired:
            return ApplyResult(target, ApplyStatus.SUPERSEDED)
        return result

    async def async_cancel(self, target: str) -> None:
        """Cancel pending work and discard retained intent for one target.

        Animation callbacks await workers through ``asyncio.shield`` so that a
        caller cancellation cannot accidentally corrupt shared work. A priority
        decision change is different: the old work is now stale and must be
        cancelled explicitly before the new winner is scheduled.
        """
        self._desired.pop(target, None)
        self._recovery_generation.pop(target, None)
        worker = self._workers.pop(target, None)
        if worker is None:
            return
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)

    def invalidate_applied_state(self, target: str) -> None:
        """Force the next desired state to be compared and sent again."""
        self._last_signature.pop(target, None)
        self._force_send.add(target)

    def is_own_context(self, context: Context | None) -> bool:
        """Return whether a state change belongs to a recent controller call."""
        cutoff = monotonic() - max(10.0, self._minimum_interval * 4)
        self._contexts = {
            context_id: timestamp
            for context_id, timestamp in self._contexts.items()
            if timestamp >= cutoff
        }
        if context is None:
            return False
        return context.id in self._contexts or context.parent_id in self._contexts

    async def async_shutdown(self) -> None:
        """Cancel pending rate-limit work and release controller state."""
        self._stopping = True
        tasks = tuple(self._workers.values())
        self._workers.clear()
        self._desired.clear()
        self._recovery_generation.clear()
        self._force_send.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _async_worker(self, target: str) -> ApplyResult:
        try:
            return await self._async_worker_loop(target)
        finally:
            self._recovery_generation.pop(target, None)

    async def _async_worker_loop(self, target: str) -> ApplyResult:
        retry_desired: _Desired | None = None
        failed_attempts = 0
        while True:
            desired = self._desired[target]
            if desired is not retry_desired:
                retry_desired = desired
                failed_attempts = 0
            elapsed = monotonic() - self._last_sent.get(target, 0.0)
            if (delay := self._minimum_interval - elapsed) > 0:
                await asyncio.sleep(delay)
            if self._desired.get(target) is not desired:
                continue

            state = self._hass.states.get(target)
            if state is None or state.state in {STATE_UNAVAILABLE, STATE_UNKNOWN}:
                return ApplyResult(target, ApplyStatus.OFFLINE)
            if (
                desired.command.turn_on
                and state.state == STATE_OFF
                and not desired.allow_turn_on
            ):
                return ApplyResult(target, ApplyStatus.TURN_ON_BLOCKED)

            service, data, signature = self._build_service_call(target, state, desired)
            force_send = target in self._force_send
            if not force_send and self._last_signature.get(target) == signature:
                return ApplyResult(target, ApplyStatus.DEDUPLICATED)
            if not force_send and _state_matches(state, desired.command):
                self._last_signature[target] = signature
                return ApplyResult(target, ApplyStatus.ALREADY_MATCHED)

            try:
                async with self._parallel, self._global_lock:
                    global_elapsed = monotonic() - self._last_global_sent
                    if (
                        global_delay := self._global_minimum_interval - global_elapsed
                    ) > 0:
                        await asyncio.sleep(global_delay)
                    if self._desired.get(target) is not desired:
                        continue
                    context = Context()
                    self._contexts[context.id] = monotonic()
                    await self._hass.services.async_call(
                        "light",
                        service,
                        data,
                        blocking=True,
                        context=context,
                    )
                    sent = monotonic()
                    self._last_global_sent = sent
                    self._last_sent[target] = sent
                    self._last_signature[target] = signature
                    self._force_send.discard(target)
            except (HomeAssistantError, TimeoutError) as err:
                if self._desired.get(target) is not desired:
                    continue
                failed_attempts += 1
                attempt_limit = (
                    self._max_recovery_attempts
                    if self._recovery_generation.get(target) == desired.generation
                    else 1
                )
                if failed_attempts >= attempt_limit:
                    attempt_label = "attempt" if failed_attempts == 1 else "attempts"
                    detail = (
                        f"send failed after {failed_attempts} {attempt_label}: "
                        f"{type(err).__name__}: {err}"
                    )
                    _LOGGER.warning("Light command for %s %s", target, detail)
                    return ApplyResult(target, ApplyStatus.OFFLINE, detail)
                retry_delay = min(
                    self._retry_base_delay * (2 ** (failed_attempts - 1)),
                    self._retry_max_delay,
                )
                _LOGGER.warning(
                    "Light command for %s failed on attempt %d/%d: %s; "
                    "retrying current intent in %.2f seconds",
                    target,
                    failed_attempts,
                    attempt_limit,
                    err,
                    retry_delay,
                )
                await asyncio.sleep(retry_delay)
                continue

            if self._desired.get(target) is desired:
                return ApplyResult(target, ApplyStatus.APPLIED)

    def _build_service_call(
        self, target: str, state: State, desired: _Desired
    ) -> tuple[str, dict[str, object], tuple[object, ...]]:
        command = desired.command
        if not command.turn_on:
            data: dict[str, object] = {ATTR_ENTITY_ID: target}
            if _supports(state, LightEntityFeature.TRANSITION) and command.transition:
                data[ATTR_TRANSITION] = command.transition
            return "turn_off", data, (False, data.get(ATTR_TRANSITION))

        data = {ATTR_ENTITY_ID: target}
        if command.color is not None:
            supported_modes = _supported_color_modes(state)
            if not supported_modes.intersection(_COLOR_MODES):
                raise UnsupportedLightCommandError(
                    f"{target} cannot represent an RGB color; modes={sorted(supported_modes)}"
                )
            data[ATTR_RGB_COLOR] = command.color
        if command.brightness is not None:
            data[ATTR_BRIGHTNESS] = command.brightness
        if command.transition is not None and _supports(
            state, LightEntityFeature.TRANSITION
        ):
            data[ATTR_TRANSITION] = command.transition
        if command.effect is not None:
            effects = state.attributes.get(ATTR_EFFECT_LIST, [])
            if (
                not _supports(state, LightEntityFeature.EFFECT)
                or command.effect not in effects
            ):
                raise UnsupportedLightCommandError(
                    f"{target} does not expose native effect {command.effect!r}"
                )
            data[ATTR_EFFECT] = command.effect

        signature = (
            True,
            data.get(ATTR_RGB_COLOR),
            data.get(ATTR_BRIGHTNESS),
            data.get(ATTR_TRANSITION),
            data.get(ATTR_EFFECT),
        )
        return "turn_on", data, signature

    def _discard_worker(
        self, target: str, completed: asyncio.Task[ApplyResult]
    ) -> None:
        if self._workers.get(target) is completed:
            self._workers.pop(target, None)
        if not completed.cancelled() and (error := completed.exception()) is not None:
            _LOGGER.debug("Light command for %s failed: %s", target, error)


def _supported_color_modes(state: State) -> set[str | ColorMode]:
    modes = state.attributes.get(ATTR_SUPPORTED_COLOR_MODES, [])
    if not isinstance(modes, (list, set, tuple)):
        return set()
    return set(modes)


def _supports(state: State, feature: LightEntityFeature) -> bool:
    features = int(state.attributes.get(ATTR_SUPPORTED_FEATURES, 0))
    return bool(features & feature)


def _state_matches(state: State, command: LightCommand) -> bool:
    """Compare stable attributes and avoid needless traffic."""
    if not command.turn_on:
        return state.state == STATE_OFF
    if state.state != STATE_ON:
        return False
    attributes: Mapping[str, object] = state.attributes
    if (
        command.brightness is not None
        and attributes.get(ATTR_BRIGHTNESS) != command.brightness
    ):
        return False
    if command.effect is not None and attributes.get(ATTR_EFFECT) != command.effect:
        return False
    if command.color is not None:
        actual = attributes.get(ATTR_RGB_COLOR)
        if not isinstance(actual, (list, tuple)) or len(actual) != 3:
            return False
        if any(
            abs(int(actual[index]) - command.color[index]) > 2 for index in range(3)
        ):
            return False
    return True
