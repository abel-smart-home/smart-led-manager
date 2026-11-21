"""Diagnostics support for Smart LED Manager."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .coordinator import SmartLEDCoordinator

_TO_REDACT = {"context_id", "access_token", "token", "password", "secret"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry[SmartLEDCoordinator]
) -> dict[str, Any]:
    """Return configuration and bounded runtime information without secrets."""
    return async_redact_data(
        {
            "entry": {
                "version": entry.version,
                "minor_version": entry.minor_version,
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            "runtime": await entry.runtime_data.async_diagnostics(),
        },
        _TO_REDACT,
    )
