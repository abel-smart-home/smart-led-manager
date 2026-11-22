"""Per-zone mode selectors."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import SmartLEDCoordinator

NO_MODE_OPTION = "none"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[SmartLEDCoordinator],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one selector for every configured zone."""
    async_add_entities(
        [
            SmartLEDZoneModeSelect(entry.runtime_data, entry, zone.zone_id)
            for zone in entry.runtime_data.modes.zones
        ]
    )


class SmartLEDZoneModeSelect(SelectEntity):
    """Select the one active persistent mode for a zone."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:palette-outline"

    def __init__(
        self,
        coordinator: SmartLEDCoordinator,
        entry: ConfigEntry,
        zone_id: str,
    ) -> None:
        self._coordinator = coordinator
        self._zone_id = zone_id
        zone = coordinator.modes.zone(zone_id)
        self._attr_translation_key = "zone_mode"
        self._attr_translation_placeholders = {"zone": zone.name}
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone_id}_mode"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Smart LED Manager",
            "manufacturer": "abel-smart-home",
            "model": "Priority engine",
        }

    @property
    def options(self) -> list[str]:
        """Return mode display names plus the explicit release choice."""
        return [
            NO_MODE_OPTION,
            *[
                mode.name
                for mode in self._coordinator.modes.modes_for_zone(self._zone_id)
            ],
        ]

    @property
    def current_option(self) -> str:
        """Return the current mode display name."""
        mode_id = self._coordinator.modes.selected_mode_id(self._zone_id)
        return (
            self._coordinator.modes.mode(mode_id).name
            if mode_id is not None
            else NO_MODE_OPTION
        )

    async def async_select_option(self, option: str) -> None:
        """Atomically select the requested mode or release the zone."""
        if option == NO_MODE_OPTION:
            await self._coordinator.async_set_zone_mode(self._zone_id, None)
            return
        for mode in self._coordinator.modes.modes_for_zone(self._zone_id):
            if mode.name == option:
                await self._coordinator.async_set_zone_mode(self._zone_id, mode.mode_id)
                return
        raise ValueError(f"Unknown mode option: {option}")

    async def async_added_to_hass(self) -> None:
        """Subscribe to mode and engine state changes."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._coordinator.async_add_listener(self._async_write_state)
        )

    @callback
    def _async_write_state(self) -> None:
        self.async_write_ha_state()
