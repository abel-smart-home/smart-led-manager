"""Versioned persistence for durable priority requests."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_MINOR_VERSION, STORAGE_VERSION


class SmartLEDStorage:
    """Persist only requests explicitly marked durable."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store[dict[str, Any]](
            hass,
            STORAGE_VERSION,
            STORAGE_KEY.format(entry_id=entry_id),
            minor_version=STORAGE_MINOR_VERSION,
        )

    async def async_load(self) -> list[dict[str, Any]]:
        """Load serialized requests, treating a missing store as empty."""
        data = await self._store.async_load()
        if not isinstance(data, dict):
            return []
        requests = data.get("requests", [])
        if not isinstance(requests, list):
            return []
        return [item for item in requests if isinstance(item, dict)]

    async def async_save(self, requests: list[dict[str, Any]]) -> None:
        """Atomically save the current durable request set."""
        await self._store.async_save({"requests": requests})

    async def async_remove(self) -> None:
        """Remove storage when the config entry is deleted."""
        await self._store.async_remove()
