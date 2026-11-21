"""Tests for versioned durable-request storage."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import AsyncMock, patch

from custom_components.smart_led_manager import async_remove_entry
from custom_components.smart_led_manager.const import (
    STORAGE_MINOR_VERSION,
    STORAGE_VERSION,
)
from custom_components.smart_led_manager.storage import SmartLEDStorage


class _MemoryStore:
    """Small Store double that persists data across wrapper instances."""

    records: ClassVar[dict[str, dict[str, object]]] = {}

    def __class_getitem__(cls, item):
        del item
        return cls

    def __init__(self, hass, version, key, *, minor_version) -> None:
        del hass, version, minor_version
        self.key = key

    async def async_load(self):
        return self.records.get(self.key)

    async def async_save(self, data) -> None:
        self.records[self.key] = data

    async def async_remove(self) -> None:
        self.records.pop(self.key, None)


class StorageTests(unittest.IsolatedAsyncioTestCase):
    """Verify defensive loading and storage lifecycle calls."""

    def setUp(self) -> None:
        self.store_patcher = patch("custom_components.smart_led_manager.storage.Store")
        store_type = self.store_patcher.start()
        self.addCleanup(self.store_patcher.stop)
        store_factory = store_type.__getitem__.return_value
        self.store = store_factory.return_value
        self.store.async_load = AsyncMock()
        self.store.async_save = AsyncMock()
        self.store.async_remove = AsyncMock()
        self.storage = SmartLEDStorage(object(), "entry-123")

        store_factory.assert_called_once_with(
            unittest.mock.ANY,
            STORAGE_VERSION,
            "smart_led_manager.entry-123",
            minor_version=STORAGE_MINOR_VERSION,
        )

    async def test_loads_only_mapping_items_from_request_list(self) -> None:
        """Malformed individual records do not poison valid stored requests."""
        valid = {"request_id": "rule:temperature"}
        self.store.async_load.return_value = {
            "requests": [valid, None, "bad", ["also bad"]]
        }

        self.assertEqual(await self.storage.async_load(), [valid])

    async def test_missing_or_malformed_payload_loads_as_empty(self) -> None:
        """A missing or incompatible store has a safe empty interpretation."""
        for payload in (None, [], {"requests": None}, {"requests": {}}):
            with self.subTest(payload=payload):
                self.store.async_load.return_value = payload
                self.assertEqual(await self.storage.async_load(), [])

    async def test_save_and_remove_delegate_to_home_assistant_store(self) -> None:
        """The wrapper preserves the versioned envelope and removal call."""
        requests = [{"request_id": "scene:evening"}]

        await self.storage.async_save(requests)
        await self.storage.async_remove()

        self.store.async_save.assert_awaited_once_with({"requests": requests})
        self.store.async_remove.assert_awaited_once_with()

    async def test_entry_removal_leaves_fresh_install_without_old_requests(
        self,
    ) -> None:
        _MemoryStore.records.clear()
        hass = object()
        entry = SimpleNamespace(entry_id="entry-reinstalled")
        old_request = {"request_id": "scene:old"}

        with patch("custom_components.smart_led_manager.storage.Store", _MemoryStore):
            installed = SmartLEDStorage(hass, entry.entry_id)
            await installed.async_save([old_request])
            self.assertEqual(await installed.async_load(), [old_request])

            await async_remove_entry(hass, entry)
            reinstalled = SmartLEDStorage(hass, entry.entry_id)

            self.assertEqual(await reinstalled.async_load(), [])


if __name__ == "__main__":
    unittest.main()
