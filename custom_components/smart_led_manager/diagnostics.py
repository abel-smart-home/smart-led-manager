"""Diagnostics support for Smart LED Manager."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .coordinator import SmartLEDCoordinator
from .modules.configuration import mutable_json

# Event filters and request metadata can contain arbitrary external payloads.
_OPAQUE_KEYS = {"contextid", "eventdata", "metadata", "cookie", "privatekey", "apikey"}
_SECRET_PARTS = ("token", "password", "secret", "credential", "authorization")


def _sensitive_keys(value: object) -> set[str]:
    keys = set()
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = "".join(char for char in key.lower() if char.isalnum())
            if normalized in _OPAQUE_KEYS or any(
                part in normalized for part in _SECRET_PARTS
            ):
                keys.add(key)
            else:
                keys.update(_sensitive_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_sensitive_keys(child))
    return keys


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry[SmartLEDCoordinator]
) -> dict[str, Any]:
    """Return configuration and bounded runtime information without secrets."""
    runtime = (
        await entry.runtime_data.async_diagnostics()
        if entry.state is ConfigEntryState.LOADED
        else None
    )
    data = mutable_json(
        {
            "entry": {
                "version": entry.version,
                "minor_version": entry.minor_version,
                "state": entry.state.value,
                "data": entry.data,
                "options": entry.options,
            },
            "runtime": runtime,
        }
    )
    return async_redact_data(data, _sensitive_keys(data))
