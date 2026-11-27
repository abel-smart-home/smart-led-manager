"""Regression tests for owned device and entity registry reconciliation."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from custom_components.smart_led_manager.const import DOMAIN
from custom_components.smart_led_manager.core.engine import PriorityEngine
from custom_components.smart_led_manager.modules.modes import ModeManager
from custom_components.smart_led_manager.registry import (
    async_reconcile_registries,
    central_device_identifier,
    mode_switch_unique_id,
    zone_device_identifier,
    zone_select_unique_id,
)


def _zone(
    zone_id: str,
    name: str,
    target: str,
    area_id: str | None = None,
) -> dict[str, object]:
    return {
        "zone_id": zone_id,
        "name": name,
        "targets": [target],
        "area_id": area_id,
    }


def _mode(
    mode_id: str,
    zone_id: str,
    target: str,
    *,
    expose_switch: bool,
) -> dict[str, object]:
    return {
        "mode_id": mode_id,
        "zone_id": zone_id,
        "name": mode_id.title(),
        "targets": [target],
        "priority": 50,
        "rgb_color": [1, 2, 3],
        "brightness": 180,
        "transition": 0,
        "allow_turn_on": True,
        "animation": "fixed",
        "period": 1,
        "expose_switch": expose_switch,
    }


class _EntityRegistry:
    def __init__(self, entries: list[SimpleNamespace]) -> None:
        self.entries = entries
        self.removed: list[str] = []

    def async_remove(self, entity_id: str) -> None:
        self.removed.append(entity_id)
        self.entries = [entry for entry in self.entries if entry.entity_id != entity_id]


class _DeviceRegistry:
    def __init__(self, devices: list[SimpleNamespace] | None = None) -> None:
        self.devices = devices or []
        self.removed: list[str] = []
        self.updated: list[tuple[str, str | None]] = []

    def async_get_or_create(self, *, config_entry_id: str, identifiers, **values):
        device = next(
            (
                candidate
                for candidate in self.devices
                if candidate.identifiers.intersection(identifiers)
            ),
            None,
        )
        if device is None:
            device = SimpleNamespace(
                id=f"device-{len(self.devices) + 1}",
                identifiers=set(identifiers),
                config_entries={config_entry_id},
                area_id=None,
                **values,
            )
            self.devices.append(device)
        else:
            for key, value in values.items():
                setattr(device, key, value)
        return device

    def async_update_device(self, device_id: str, *, area_id: str | None):
        device = next(item for item in self.devices if item.id == device_id)
        device.area_id = area_id
        self.updated.append((device_id, area_id))
        return device

    def async_remove_device(self, device_id: str) -> None:
        self.removed.append(device_id)
        self.devices = [device for device in self.devices if device.id != device_id]


def _entity(
    entity_id: str,
    domain: str,
    unique_id: str,
    *,
    platform: str = DOMAIN,
    device_id: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        entity_id=entity_id,
        domain=domain,
        platform=platform,
        unique_id=unique_id,
        device_id=device_id,
    )


class RegistryReconciliationTests(unittest.TestCase):
    """Verify exact ownership, stable identifiers, and selective cleanup."""

    def _manager(self) -> ModeManager:
        return ModeManager(
            PriorityEngine(),
            [
                _zone("living", "Sala nueva", "light.one", "living_room"),
                _zone("office", "Oficina", "light.two"),
            ],
            [
                _mode("cinema", "living", "light.one", expose_switch=True),
                _mode("reading", "living", "light.one", expose_switch=False),
            ],
            frozenset({"light.one", "light.two"}),
        )

    def test_reconcile_creates_zone_devices_and_removes_only_deleted_owned_rows(
        self,
    ) -> None:
        entry = SimpleNamespace(entry_id="entry-1")
        stale_device = SimpleNamespace(
            id="device-stale",
            identifiers={zone_device_identifier("entry-1", "deleted")},
            config_entries={"entry-1"},
            area_id=None,
            name="Borrada",
        )
        referenced_stale = SimpleNamespace(
            id="device-referenced",
            identifiers={zone_device_identifier("entry-1", "referenced")},
            config_entries={"entry-1"},
            area_id=None,
            name="Referenciada",
        )
        old_living = SimpleNamespace(
            id="device-living",
            identifiers={zone_device_identifier("entry-1", "living")},
            config_entries={"entry-1"},
            area_id="old_area",
            name="Sala vieja",
        )
        devices = _DeviceRegistry([stale_device, referenced_stale, old_living])
        entities = _EntityRegistry(
            [
                _entity(
                    "select.sala_modo",
                    "select",
                    zone_select_unique_id("entry-1", "living"),
                ),
                _entity(
                    "switch.cinema",
                    "switch",
                    mode_switch_unique_id("entry-1", "cinema"),
                ),
                _entity(
                    "switch.reading",
                    "switch",
                    mode_switch_unique_id("entry-1", "reading"),
                ),
                _entity(
                    "switch.deleted",
                    "switch",
                    mode_switch_unique_id("entry-1", "deleted"),
                ),
                _entity(
                    "select.deleted",
                    "select",
                    zone_select_unique_id("entry-1", "deleted"),
                ),
                _entity(
                    "switch.foreign",
                    "switch",
                    mode_switch_unique_id("entry-1", "foreign"),
                    platform="other_integration",
                ),
                _entity(
                    "sensor.reference",
                    "sensor",
                    "foreign-reference",
                    platform="other_integration",
                    device_id="device-referenced",
                ),
            ]
        )
        areas = SimpleNamespace(
            async_get_area=lambda area_id: (
                SimpleNamespace(id=area_id) if area_id == "living_room" else None
            )
        )

        with (
            patch(
                "custom_components.smart_led_manager.registry.er.async_get",
                return_value=entities,
            ),
            patch(
                "custom_components.smart_led_manager.registry.dr.async_get",
                return_value=devices,
            ),
            patch(
                "custom_components.smart_led_manager.registry.ar.async_get",
                return_value=areas,
            ),
            patch(
                "custom_components.smart_led_manager.registry.er.async_entries_for_config_entry",
                side_effect=lambda registry, _entry_id: list(registry.entries),
            ),
            patch(
                "custom_components.smart_led_manager.registry.er.async_entries_for_device",
                side_effect=lambda registry, device_id, **_kwargs: [
                    entity
                    for entity in registry.entries
                    if entity.device_id == device_id
                ],
            ),
            patch(
                "custom_components.smart_led_manager.registry.dr.async_entries_for_config_entry",
                side_effect=lambda registry, _entry_id: list(registry.devices),
            ),
        ):
            async_reconcile_registries(None, entry, self._manager())

        self.assertEqual(set(entities.removed), {"switch.deleted", "select.deleted"})
        self.assertNotIn("switch.reading", entities.removed)
        self.assertNotIn("switch.foreign", entities.removed)
        self.assertIn("device-stale", devices.removed)
        self.assertNotIn("device-referenced", devices.removed)
        identifiers = {
            identifier
            for device in devices.devices
            for identifier in device.identifiers
        }
        self.assertIn(central_device_identifier("entry-1"), identifiers)
        self.assertIn(zone_device_identifier("entry-1", "living"), identifiers)
        self.assertIn(zone_device_identifier("entry-1", "office"), identifiers)
        self.assertEqual(old_living.name, "Sala nueva")
        self.assertEqual(old_living.area_id, "living_room")

    def test_invalid_catalog_mode_skips_cleanup(self) -> None:
        entry = SimpleNamespace(entry_id="entry-1")
        entities = _EntityRegistry(
            [
                _entity(
                    "switch.retained",
                    "switch",
                    mode_switch_unique_id("entry-1", "retained"),
                )
            ]
        )
        devices = _DeviceRegistry()
        manager = ModeManager(PriorityEngine(), [], [], frozenset({"light.one"}))

        with (
            patch(
                "custom_components.smart_led_manager.registry.er.async_get",
                return_value=entities,
            ),
            patch(
                "custom_components.smart_led_manager.registry.dr.async_get",
                return_value=devices,
            ),
            patch(
                "custom_components.smart_led_manager.registry.ar.async_get",
                return_value=SimpleNamespace(async_get_area=lambda _area_id: None),
            ),
        ):
            async_reconcile_registries(None, entry, manager, cleanup=False)

        self.assertEqual(entities.removed, [])


if __name__ == "__main__":
    unittest.main()
