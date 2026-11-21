"""Deterministic request ranking for Smart LED Manager."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from ..models import Request, TieBreaker, ensure_utc, utc_now


def ranking_key(request: Request, tie_breaker: TieBreaker) -> tuple[object, ...]:
    """Return a key where the smallest item is the winning request."""

    policy = TieBreaker(tie_breaker)
    timestamp = request.activated_at.timestamp()
    if policy is TieBreaker.NEWEST:
        return -request.priority, -timestamp, request.request_id
    if policy is TieBreaker.OLDEST:
        return -request.priority, timestamp, request.request_id
    return -request.priority, request.request_id, timestamp


def choose_winner(
    requests: Iterable[Request],
    target: str,
    tie_breaker: TieBreaker = TieBreaker.NEWEST,
    *,
    now: datetime | None = None,
) -> Request | None:
    """Choose the valid winning request for one target."""

    reference = ensure_utc(now or utc_now(), field_name="now")
    candidates = (
        request
        for request in requests
        if target in request.targets and request.is_valid(reference)
    )
    return min(
        candidates, key=lambda request: ranking_key(request, tie_breaker), default=None
    )
