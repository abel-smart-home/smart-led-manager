"""Shared JSON normalization and optimistic configuration revisions."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any

from ..const import (
    CONF_MANUAL_POLICY,
    CONF_MIN_COMMAND_INTERVAL,
    CONF_SHOW_SIDEBAR,
    CONF_TIE_BREAKER,
    DEFAULT_MANUAL_POLICY,
    DEFAULT_MIN_COMMAND_INTERVAL,
    DEFAULT_SHOW_SIDEBAR,
    DEFAULT_TIE_BREAKER,
)
from ..models import TieBreaker

ENGINE_DEFAULTS = {
    CONF_TIE_BREAKER: DEFAULT_TIE_BREAKER,
    CONF_MANUAL_POLICY: DEFAULT_MANUAL_POLICY,
    CONF_MIN_COMMAND_INTERVAL: DEFAULT_MIN_COMMAND_INTERVAL,
}
PREFERENCE_DEFAULTS = {CONF_SHOW_SIDEBAR: DEFAULT_SHOW_SIDEBAR, **ENGINE_DEFAULTS}
MANUAL_POLICIES = ("service_only", "respect", "temporary")
MIN_COMMAND_INTERVAL = 0.1
MAX_COMMAND_INTERVAL = 10
COMMAND_INTERVAL_STEP = 0.05


class PreferenceError(ValueError):
    """An invalid configuration preference from either editor."""


def read_preferences(options: Mapping[str, Any]) -> dict[str, Any]:
    """Read persisted values and use defaults for absent keys only."""
    return {
        key: options.get(key, default) for key, default in PREFERENCE_DEFAULTS.items()
    }


def validate_preferences(kind: str, values: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one form without allowing it to update any other options."""
    if kind == "general":
        visible = values.get(CONF_SHOW_SIDEBAR)
        if type(visible) is not bool:
            raise PreferenceError("invalid_sidebar_preference")
        return {CONF_SHOW_SIDEBAR: visible}
    tie = values.get(CONF_TIE_BREAKER)
    manual = values.get(CONF_MANUAL_POLICY)
    if tie not in tuple(TieBreaker) or manual not in MANUAL_POLICIES:
        raise PreferenceError("invalid_engine_preference")
    interval = values.get(CONF_MIN_COMMAND_INTERVAL)
    if (
        type(interval) not in (int, float)
        or not MIN_COMMAND_INTERVAL <= interval <= MAX_COMMAND_INTERVAL
        or not math.isclose(
            interval * 20, round(interval * 20), rel_tol=0, abs_tol=1e-9
        )
    ):
        raise PreferenceError("invalid_command_interval")
    return {
        CONF_TIE_BREAKER: tie,
        CONF_MANUAL_POLICY: manual,
        CONF_MIN_COMMAND_INTERVAL: round(interval, 2),
    }


def mutable_json(value: object) -> Any:
    """Return a mutable JSON-compatible copy, including mapping proxies."""

    if isinstance(value, Mapping):
        return {key: mutable_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [mutable_json(item) for item in value]
    return value


def options_revision(options: object) -> str:
    """Return a deterministic optimistic-concurrency token."""

    encoded = json.dumps(
        mutable_json(options),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
