"""Shared JSON normalization and optimistic configuration revisions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


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
