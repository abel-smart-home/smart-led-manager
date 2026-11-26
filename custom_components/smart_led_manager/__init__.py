"""Smart LED Manager integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from copy import deepcopy

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CONF_AREA_ID, CONF_ZONES, DOMAIN, PLATFORMS
from .coordinator import SmartLEDCoordinator, SmartLEDManagerConfigEntry
from .registry import async_reconcile_registries
from .services import async_setup_services, async_update_notice_schema
from .storage import SmartLEDStorage
from .visual_editor import (
    async_clear_visual_editor_state,
    async_finish_visual_editor_unload,
    async_register_visual_editor_panel,
    async_reload_visual_editor_entry,
    async_remove_visual_editor_panel,
    async_setup_visual_editor,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration-level actions."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data.setdefault("entries", {})
    if not domain_data.get("services_registered"):
        async_setup_services(hass)
        domain_data["services_registered"] = True
    await async_setup_visual_editor(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: SmartLEDManagerConfigEntry
) -> bool:
    """Set up one config entry."""
    coordinator = SmartLEDCoordinator(hass, entry)
    await coordinator.async_initialize()
    async_reconcile_registries(
        hass,
        entry,
        coordinator.modes,
        cleanup=coordinator.catalog_valid,
    )
    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {}).setdefault("entries", {})[entry.entry_id] = (
        coordinator
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_visual_editor_panel(hass, entry)
    async_update_notice_schema(hass, coordinator.notice_choices())
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: SmartLEDManagerConfigEntry
) -> bool:
    """Unload an entry and all of its tasks/listeners."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.async_shutdown()
    entries = hass.data.get(DOMAIN, {}).get("entries", {})
    entries.pop(entry.entry_id, None)
    if not entries:
        async_update_notice_schema(hass, [])
    async_finish_visual_editor_unload(hass, entry)
    return True


async def async_remove_entry(
    hass: HomeAssistant, entry: SmartLEDManagerConfigEntry
) -> None:
    """Remove retained storage after the entry has unloaded."""
    storage = SmartLEDStorage(hass, entry.entry_id)
    await storage.async_remove()
    async_clear_visual_editor_state(hass, entry.entry_id)
    async_remove_visual_editor_panel(hass)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Add optional zone areas without changing stable zone or entity IDs."""
    if entry.version != 1:
        _LOGGER.error("Unsupported Smart LED Manager config version %s", entry.version)
        return False
    if entry.minor_version < 2:
        options = deepcopy(dict(entry.options))
        zones: list[object] = []
        for raw_zone in options.get(CONF_ZONES, []):
            if isinstance(raw_zone, Mapping):
                zone = dict(raw_zone)
                zone.setdefault(CONF_AREA_ID, None)
                zones.append(zone)
            else:
                zones.append(raw_zone)
        options[CONF_ZONES] = zones
        hass.config_entries.async_update_entry(
            entry,
            options=options,
            version=1,
            minor_version=2,
        )
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: SmartLEDManagerConfigEntry
) -> None:
    """Reload atomically after an options-flow change."""
    await async_reload_visual_editor_entry(hass, entry)
