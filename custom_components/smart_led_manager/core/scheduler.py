"""Cancellable expiry and animation scheduling."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import replace
from datetime import datetime

from ..models import (
    AnimationKind,
    AnimationSpec,
    LightCommand,
    Request,
    ensure_utc,
    utc_now,
)

_LOGGER = logging.getLogger(__name__)

AsyncCallback = Callable[[], Awaitable[None]]
FrameCallback = Callable[[LightCommand], Awaitable[None]]


class DeadlineScheduler:
    """Own one cancellable wall-clock deadline."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._deadline: datetime | None = None

    @property
    def deadline(self) -> datetime | None:
        """Return the scheduled UTC deadline."""
        return self._deadline

    def schedule(self, deadline: datetime | None, callback: AsyncCallback) -> None:
        """Replace the current deadline without leaving duplicate timers."""
        self.cancel()
        if deadline is None:
            return
        self._deadline = ensure_utc(deadline, field_name="deadline")
        self._task = asyncio.create_task(
            self._run(self._deadline, callback), name="smart_led_manager_expiry"
        )

    def cancel(self) -> None:
        """Cancel the current deadline."""
        self._deadline = None
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def async_shutdown(self) -> None:
        """Cancel and await the scheduler task."""
        task = self._task
        self.cancel()
        if task is not None:
            await _await_cancelled(task)

    async def _run(self, deadline: datetime, callback: AsyncCallback) -> None:
        try:
            while True:
                delay = (deadline - utc_now()).total_seconds()
                if delay <= 0:
                    break
                await asyncio.sleep(delay)
            # Release ownership before the callback. The callback is allowed to
            # schedule the next engine deadline and must not cancel itself.
            if self._task is asyncio.current_task():
                self._task = None
                self._deadline = None
            await callback()
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover - defensive integration boundary
            _LOGGER.exception("Expiry callback failed")
        finally:
            if self._task is asyncio.current_task():
                self._task = None
                self._deadline = None


class AnimationScheduler:
    """Own at most one software animation task per physical target."""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[None]] = {}

    @property
    def active_targets(self) -> frozenset[str]:
        """Return targets with an active software animation."""
        return frozenset(self._tasks)

    async def async_apply(
        self,
        target: str,
        request: Request | None,
        callback: FrameCallback,
    ) -> None:
        """Cancel an old animation and apply a winner or empty decision."""
        await self.async_cancel(target)
        if request is None:
            return

        animation = request.command.animation
        if animation.kind is AnimationKind.NONE:
            await callback(request.command)
            return

        task = asyncio.create_task(
            self._run(target, request.command, callback),
            name=f"smart_led_manager_animation_{target}",
        )
        self._tasks[target] = task
        task.add_done_callback(
            lambda completed, target=target: self._discard(target, completed)
        )

    async def async_cancel(self, target: str) -> None:
        """Cancel and await one target animation."""
        task = self._tasks.pop(target, None)
        if task is not None:
            task.cancel()
            await _await_cancelled(task)

    async def async_shutdown(self) -> None:
        """Cancel every active animation."""
        tasks = tuple(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _discard(self, target: str, completed: asyncio.Task[None]) -> None:
        if self._tasks.get(target) is completed:
            self._tasks.pop(target, None)
        if not completed.cancelled() and (error := completed.exception()) is not None:
            _LOGGER.error("Animation for %s failed: %s", target, error, exc_info=error)

    async def _run(
        self, target: str, command: LightCommand, callback: FrameCallback
    ) -> None:
        animation = command.animation
        base = replace(command, animation=AnimationSpec())
        frames = _animation_frames(base, animation)
        if not frames:
            await callback(base)
            return

        repetitions = animation.repetitions
        completed = 0
        frame_delay = max(0.1, animation.interval / len(frames))
        while repetitions is None or completed < repetitions:
            for frame in frames:
                await callback(frame)
                await asyncio.sleep(frame_delay)
            completed += 1

        # A finite animation settles on the request's declared steady state.
        await callback(base)
        _LOGGER.debug("Completed animation for %s", target)


def _animation_frames(
    base: LightCommand, animation: AnimationSpec
) -> tuple[LightCommand, ...]:
    """Build one deterministic animation cycle."""
    if animation.kind is AnimationKind.BLINK:
        return base, LightCommand(turn_on=False)

    if animation.kind in {AnimationKind.PULSE, AnimationKind.BREATHE}:
        peak = base.brightness if base.brightness is not None else 255
        levels = (
            max(1, round(peak * 0.2)),
            max(1, round(peak * 0.6)),
            peak,
            max(1, round(peak * 0.6)),
        )
        return tuple(replace(base, brightness=level) for level in levels)

    if animation.kind in {AnimationKind.ALTERNATE, AnimationKind.SEQUENCE}:
        colors = animation.colors or ((base.color,) if base.color is not None else ())
        return tuple(replace(base, color=color) for color in colors)

    return (base,)


async def _await_cancelled(task: asyncio.Task[None]) -> None:
    with suppress(asyncio.CancelledError):
        await task
