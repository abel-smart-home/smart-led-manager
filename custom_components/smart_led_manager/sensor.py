"""Diagnostic engine sensor."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SmartLEDCoordinator
from .registry import central_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[SmartLEDCoordinator],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the one bounded diagnostic entity."""
    async_add_entities([SmartLEDManagerStatusSensor(entry.runtime_data, entry)])


class SmartLEDManagerStatusSensor(SensorEntity):
    """Expose a compact summary of the central engine."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "engine_status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:led-strip-variant"

    def __init__(self, coordinator: SmartLEDCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_engine_status"
        self._attr_device_info = central_device_info(entry.entry_id)

    @property
    def native_value(self) -> str:
        """Return translated engine status key."""
        return self._coordinator.status

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return bounded operational state."""
        return {
            "managed_lights": len(self._coordinator.targets.authorized),
            "request_count": self._coordinator.request_count,
            "active_targets": len(self._coordinator.animations.active_targets),
            "tie_breaker": self._coordinator.engine.tie_breaker.value,
            "minimum_command_interval": self._coordinator.controller.minimum_interval,
            "manual_policy": self._coordinator.manual_policy,
            "last_error": self._coordinator.last_error,
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator state changes."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._coordinator.async_add_listener(self._async_write_state)
        )

    @callback
    def _async_write_state(self) -> None:
        self.async_write_ha_state()
