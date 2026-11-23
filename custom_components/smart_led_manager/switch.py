"""Optional per-mode switches for dashboards, Matter, and voice bridges."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SmartLEDCoordinator
from .registry import mode_switch_unique_id, zone_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[SmartLEDCoordinator],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create switches only for modes explicitly exposed by the owner."""
    async_add_entities(
        [
            SmartLEDModeSwitch(entry.runtime_data, entry, mode.mode_id)
            for mode in entry.runtime_data.modes.modes
            if mode.expose_switch
        ]
    )


class SmartLEDModeSwitch(SwitchEntity):
    """Activate or release one configured mode."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:lightbulb-group-outline"

    def __init__(
        self,
        coordinator: SmartLEDCoordinator,
        entry: ConfigEntry,
        mode_id: str,
    ) -> None:
        self._coordinator = coordinator
        self._mode_id = mode_id
        mode = coordinator.modes.mode(mode_id)
        zone = coordinator.modes.zone(mode.zone_id)
        self._attr_name = mode.name
        self._attr_unique_id = mode_switch_unique_id(entry.entry_id, mode_id)
        self._attr_device_info = zone_device_info(entry.entry_id, zone)

    @property
    def is_on(self) -> bool:
        """Return whether this mode is the selected one in its zone."""
        return self._coordinator.modes.is_selected(self._mode_id)

    async def async_turn_on(self, **kwargs) -> None:
        """Activate this mode through the central coordinator."""
        await self._coordinator.async_activate_mode(self._mode_id)

    async def async_turn_off(self, **kwargs) -> None:
        """Release this mode if it is still selected."""
        await self._coordinator.async_deactivate_mode(self._mode_id)

    async def async_added_to_hass(self) -> None:
        """Subscribe to mode and engine state changes."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._coordinator.async_add_listener(self._async_write_state)
        )

    @callback
    def _async_write_state(self) -> None:
        self.async_write_ha_state()
