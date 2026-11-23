"""Owned Home Assistant device and entity registry lifecycle."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, NAME
from .modules.modes import ModeManager, ZoneDefinition

_LOGGER = logging.getLogger(__name__)

_MANUFACTURER = "abel-smart-home"
_CENTRAL_MODEL = "Priority engine"
_ZONE_MODEL = "Lighting zone"


def central_device_identifier(entry_id: str) -> tuple[str, str]:
    """Return the stable identifier for the integration's central device."""
    return DOMAIN, entry_id


def zone_device_identifier(entry_id: str, zone_id: str) -> tuple[str, str]:
    """Return the stable identifier for one virtual zone device."""
    return DOMAIN, f"{entry_id}:zone:{zone_id}"


def zone_select_unique_id(entry_id: str, zone_id: str) -> str:
    """Return the alpha.2-compatible selector unique ID."""
    return f"{entry_id}_zone_{zone_id}_mode"


def mode_switch_unique_id(entry_id: str, mode_id: str) -> str:
    """Return the alpha.2-compatible mode-switch unique ID."""
    return f"{entry_id}_mode_{mode_id}"


def central_device_info(entry_id: str) -> dr.DeviceInfo:
    """Describe the central manager device without changing its identifier."""
    return dr.DeviceInfo(
        identifiers={central_device_identifier(entry_id)},
        name=NAME,
        manufacturer=_MANUFACTURER,
        model=_CENTRAL_MODEL,
    )


def zone_device_info(entry_id: str, zone: ZoneDefinition) -> dr.DeviceInfo:
    """Describe one stable virtual zone device."""
    return dr.DeviceInfo(
        identifiers={zone_device_identifier(entry_id, zone.zone_id)},
        name=zone.name,
        manufacturer=_MANUFACTURER,
        model=_ZONE_MODEL,
    )


@callback
def async_reconcile_registries(
    hass: HomeAssistant,
    entry: ConfigEntry,
    modes: ModeManager,
    *,
    cleanup: bool = True,
) -> None:
    """Create zone devices and remove only permanently deleted owned records."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    zones = {zone.zone_id: zone for zone in modes.zones}

    if cleanup:
        _async_remove_deleted_entities(entity_registry, entry.entry_id, modes)
        _async_remove_deleted_zone_devices(
            device_registry,
            entity_registry,
            entry.entry_id,
            frozenset(zones),
        )

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={central_device_identifier(entry.entry_id)},
        name=NAME,
        manufacturer=_MANUFACTURER,
        model=_CENTRAL_MODEL,
    )
    area_registry = ar.async_get(hass)
    for zone in zones.values():
        device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={zone_device_identifier(entry.entry_id, zone.zone_id)},
            name=zone.name,
            manufacturer=_MANUFACTURER,
            model=_ZONE_MODEL,
        )
        area_id = zone.area_id
        if area_id is not None and area_registry.async_get_area(area_id) is None:
            _LOGGER.warning(
                "Zone %s references missing area %s; leaving its device unassigned",
                zone.zone_id,
                area_id,
            )
            area_id = None
        if device.area_id != area_id:
            device_registry.async_update_device(device.id, area_id=area_id)


@callback
def _async_remove_deleted_entities(
    registry: er.EntityRegistry,
    entry_id: str,
    modes: ModeManager,
) -> None:
    """Remove active registry rows only after their definitions are gone."""
    expected_selects = {
        zone_select_unique_id(entry_id, zone.zone_id) for zone in modes.zones
    }
    retained_switches = {
        mode_switch_unique_id(entry_id, mode.mode_id) for mode in modes.modes
    }
    select_prefix = f"{entry_id}_zone_"
    switch_prefix = f"{entry_id}_mode_"

    for entity in tuple(er.async_entries_for_config_entry(registry, entry_id)):
        if entity.platform != DOMAIN:
            continue
        remove = (
            entity.domain == Platform.SELECT
            and entity.unique_id.startswith(select_prefix)
            and entity.unique_id.endswith("_mode")
            and entity.unique_id not in expected_selects
        ) or (
            entity.domain == Platform.SWITCH
            and entity.unique_id.startswith(switch_prefix)
            and entity.unique_id not in retained_switches
        )
        if remove:
            _LOGGER.info(
                "Removing registry entry %s for a deleted Smart LED definition",
                entity.entity_id,
            )
            registry.async_remove(entity.entity_id)


@callback
def _async_remove_deleted_zone_devices(
    registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    entry_id: str,
    zone_ids: frozenset[str],
) -> None:
    """Remove only this entry's virtual devices for zones no longer defined."""
    identifier_prefix = f"{entry_id}:zone:"
    for device in tuple(dr.async_entries_for_config_entry(registry, entry_id)):
        owned_zone_ids = {
            identifier.removeprefix(identifier_prefix)
            for domain, identifier in device.identifiers
            if domain == DOMAIN and identifier.startswith(identifier_prefix)
        }
        if not owned_zone_ids or not owned_zone_ids.isdisjoint(zone_ids):
            continue
        remaining_entities = tuple(
            entity.entity_id
            for entity in er.async_entries_for_device(
                entity_registry, device.id, include_disabled_entities=True
            )
        )
        if remaining_entities:
            _LOGGER.warning(
                "Keeping virtual device %s for deleted zone because entities still "
                "reference it: %s",
                device.id,
                ", ".join(remaining_entities),
            )
        else:
            _LOGGER.info("Removing virtual device for deleted zone %s", device.id)
            registry.async_remove_device(device.id)
