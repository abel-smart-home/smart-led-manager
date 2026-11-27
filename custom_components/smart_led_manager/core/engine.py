"""Concurrency-safe per-target priority engine."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import datetime
from typing import Any

from ..models import DecisionChange, Request, TieBreaker, ensure_utc, utc_now
from .priority import choose_winner, ranking_key

Clock = Callable[[], datetime]


class PriorityEngine:
    """Store requests and resolve one deterministic winner per target.

    Mutations are protected by one asyncio lock.  They return decision changes
    instead of invoking I/O while the lock is held; the Home Assistant layer can
    then cancel animations and apply commands without creating an engine
    re-entrancy deadlock.
    """

    def __init__(
        self,
        *,
        tie_breaker: TieBreaker = TieBreaker.NEWEST,
        clock: Clock = utc_now,
    ) -> None:
        self._tie_breaker = TieBreaker(tie_breaker)
        self._clock = clock
        self._requests: dict[str, Request] = {}
        self._lock = asyncio.Lock()

    @property
    def tie_breaker(self) -> TieBreaker:
        """Return the configured tie policy."""

        return self._tie_breaker

    async def async_set_tie_breaker(
        self, tie_breaker: TieBreaker
    ) -> tuple[DecisionChange, ...]:
        """Change tie policy and report every resulting target decision."""

        policy = TieBreaker(tie_breaker)
        async with self._lock:
            if policy is self._tie_breaker:
                return ()
            now = self._now()
            targets = self._all_targets()
            previous = self._winners(targets, now)
            self._tie_breaker = policy
            return self._changes(previous, targets, now, "tie_breaker")

    async def async_submit(self, request: Request) -> tuple[DecisionChange, ...]:
        """Create or replace a request atomically.

        Replacing a losing request still updates the stored request even when no
        decision changes are returned.  Its newest state is therefore applied if
        a higher-priority request later ends.
        """

        if not isinstance(request, Request):
            raise TypeError("request must be a Request")
        async with self._lock:
            now = self._now()
            old = self._requests.get(request.request_id)
            targets = set(request.targets)
            if old is not None:
                targets.update(old.targets)
            previous = self._winners(targets, now)
            self._requests[request.request_id] = request
            return self._changes(previous, targets, now, "submit")

    async def async_deactivate(
        self, request_id: str, *, updated_at: datetime | None = None
    ) -> tuple[DecisionChange, ...]:
        """Mark a request inactive while retaining it for history/storage."""

        async with self._lock:
            current = self._requests.get(request_id)
            if current is None or not current.active:
                return ()
            now = self._now()
            changed_at = ensure_utc(updated_at or now, field_name="updated_at")
            previous = self._winners_before_removal((current,), current.targets, now)
            self._requests[request_id] = replace(
                current, active=False, updated_at=changed_at
            )
            return self._changes(previous, current.targets, now, "deactivate")

    async def async_cancel(self, request_id: str) -> tuple[DecisionChange, ...]:
        """Remove one request and report affected targets."""

        async with self._lock:
            current = self._requests.get(request_id)
            if current is None:
                return ()
            now = self._now()
            previous = self._winners_before_removal((current,), current.targets, now)
            del self._requests[request_id]
            return self._changes(previous, current.targets, now, "cancel")

    async def async_cancel_matching(
        self, predicate: Callable[[Request], bool]
    ) -> tuple[DecisionChange, ...]:
        """Remove all requests accepted by ``predicate`` in one transaction."""

        async with self._lock:
            matching = [
                request for request in self._requests.values() if predicate(request)
            ]
            if not matching:
                return ()
            now = self._now()
            targets = {target for request in matching for target in request.targets}
            previous = self._winners_before_removal(matching, targets, now)
            for request in matching:
                del self._requests[request.request_id]
            return self._changes(previous, targets, now, "cancel_matching")

    async def async_replace_matching(
        self,
        predicate: Callable[[Request], bool],
        request: Request | None,
        *,
        reason: str = "replace_matching",
    ) -> tuple[DecisionChange, ...]:
        """Remove matching requests and optionally insert one in one transaction.

        The returned decisions compare the state before the complete replacement
        with its final state. Consumers therefore never observe an intermediate
        winner while a mutually exclusive intent is switched.
        """

        if request is not None and not isinstance(request, Request):
            raise TypeError("request must be a Request or None")
        async with self._lock:
            matching = [
                current for current in self._requests.values() if predicate(current)
            ]
            if not matching and request is None:
                return ()
            now = self._now()
            targets = {target for current in matching for target in current.targets}
            if request is not None:
                targets.update(request.targets)
            previous = self._winners_before_removal(matching, targets, now)
            for current in matching:
                del self._requests[current.request_id]
            if request is not None:
                self._requests[request.request_id] = request
            return self._changes(previous, targets, now, reason)

    async def async_expire(
        self, now: datetime | None = None
    ) -> tuple[DecisionChange, ...]:
        """Discard every request whose real-time expiry has elapsed."""

        reference = ensure_utc(now or self._clock(), field_name="now")
        async with self._lock:
            expired = [
                request
                for request in self._requests.values()
                if request.expires_at is not None and request.expires_at <= reference
            ]
            if not expired:
                return ()
            targets = {target for request in expired for target in request.targets}
            previous = self._winners_before_removal(expired, targets, reference)
            for request in expired:
                del self._requests[request.request_id]
            return self._changes(previous, targets, reference, "expire")

    async def async_restore(
        self, serialized: Iterable[dict[str, Any]], *, replace_existing: bool = False
    ) -> tuple[DecisionChange, ...]:
        """Restore valid serialized requests in one transaction.

        Expired records are deliberately discarded during recovery.  Duplicate
        identifiers in the input resolve deterministically to the last record.
        """

        restored: dict[str, Request] = {}
        for item in serialized:
            request = Request.from_dict(item)
            restored[request.request_id] = request

        async with self._lock:
            now = self._now()
            restored = {
                request_id: request
                for request_id, request in restored.items()
                if request.is_valid(now)
            }
            targets = self._all_targets()
            targets.update(
                target for request in restored.values() for target in request.targets
            )
            previous = self._winners(targets, now)
            if replace_existing:
                self._requests.clear()
            self._requests.update(restored)
            return self._changes(previous, targets, now, "restore")

    async def async_winner(
        self, target: str, *, now: datetime | None = None
    ) -> Request | None:
        """Return the current winner for one target."""

        async with self._lock:
            reference = ensure_utc(now or self._clock(), field_name="now")
            return choose_winner(
                self._requests.values(), target, self._tie_breaker, now=reference
            )

    async def async_requests(self) -> tuple[Request, ...]:
        """Return an immutable, identifier-sorted request snapshot."""

        async with self._lock:
            return tuple(self._requests[key] for key in sorted(self._requests))

    async def async_serialize(
        self, *, persistent_only: bool = False
    ) -> list[dict[str, Any]]:
        """Return JSON-compatible storage records."""

        async with self._lock:
            requests = self._requests.values()
            if persistent_only:
                requests = (
                    request
                    for request in requests
                    if request.persistent and request.active
                )
            return [
                request.to_dict()
                for request in sorted(requests, key=lambda item: item.request_id)
            ]

    async def async_next_expiry(self) -> datetime | None:
        """Return the earliest future expiry among active requests."""

        async with self._lock:
            now = self._now()
            expiries = [
                request.expires_at
                for request in self._requests.values()
                if request.active
                and request.expires_at is not None
                and request.expires_at > now
            ]
            return min(expiries, default=None)

    def _now(self) -> datetime:
        return ensure_utc(self._clock(), field_name="clock")

    def _all_targets(self) -> set[str]:
        return {
            target for request in self._requests.values() for target in request.targets
        }

    def _winners(
        self, targets: Iterable[str], now: datetime
    ) -> dict[str, Request | None]:
        return {
            target: choose_winner(
                self._requests.values(), target, self._tie_breaker, now=now
            )
            for target in targets
        }

    def _changes(
        self,
        previous: dict[str, Request | None],
        targets: Iterable[str],
        now: datetime,
        reason: str,
    ) -> tuple[DecisionChange, ...]:
        changes: list[DecisionChange] = []
        for target in sorted(set(targets)):
            current = choose_winner(
                self._requests.values(), target, self._tie_breaker, now=now
            )
            before = previous.get(target)
            if before != current:
                changes.append(
                    DecisionChange(
                        target=target,
                        previous=before,
                        current=current,
                        reason=reason,
                    )
                )
        return tuple(changes)

    def _winner_before_expiry(self, target: str, reference: datetime) -> Request | None:
        """Resolve the winner just before an exact expiry boundary."""

        candidates = [
            request
            for request in self._requests.values()
            if target in request.targets
            and request.active
            and (request.expires_at is None or request.expires_at >= reference)
        ]
        if not candidates:
            return None
        return min(
            candidates, key=lambda request: ranking_key(request, self._tie_breaker)
        )

    def _winners_before_removal(
        self,
        requests: Iterable[Request],
        targets: Iterable[str],
        reference: datetime,
    ) -> dict[str, Request | None]:
        """Resolve physical winners before intent is removed or disabled."""

        # A timer or terminal action can run after a wall-clock deadline.
        # Reconstruct each affected target at its earliest active expiry boundary,
        # not at the later processing time, so a still-visible expired winner is
        # included in the previous decision. Inactive records never define a
        # physical decision boundary.
        boundaries: dict[str, datetime] = {}
        for request in requests:
            expires_at = request.expires_at
            if not request.active or expires_at is None or expires_at > reference:
                continue
            for target in request.targets:
                boundary = boundaries.get(target)
                if boundary is None or expires_at < boundary:
                    boundaries[target] = expires_at

        previous: dict[str, Request | None] = {}
        for target in targets:
            boundary = boundaries.get(target)
            previous[target] = (
                self._winner_before_expiry(target, boundary)
                if boundary is not None
                else choose_winner(
                    self._requests.values(),
                    target,
                    self._tie_breaker,
                    now=reference,
                )
            )
        return previous
