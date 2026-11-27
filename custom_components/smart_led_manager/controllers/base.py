"""Shared controller result types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ApplyStatus(StrEnum):
    """Outcome of a physical light projection."""

    APPLIED = "applied"
    DEDUPLICATED = "deduplicated"
    ALREADY_MATCHED = "already_matched"
    OFFLINE = "offline"
    TURN_ON_BLOCKED = "turn_on_blocked"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class ApplyResult:
    """One controller operation result."""

    target: str
    status: ApplyStatus
    detail: str | None = None


class UnsupportedLightCommandError(ValueError):
    """Raised when a physical light cannot represent an intent."""
