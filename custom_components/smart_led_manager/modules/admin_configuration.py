"""Validate shared light, zone, and mode configuration changes."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar

from ..const import TARGET_AREAS, TARGET_LABELS
from .modes import ModeDefinition, ModeValidationError, ZoneDefinition
from .targeting import (
    TARGET_ENTITIES,
    TARGET_ZONES,
    AdvancedTargetError,
    AdvancedTargetResolver,
    is_aggregate_light,
    legacy_or_advanced_targets,
)


def validate_managed_lights(
    hass: HomeAssistant,
    current: Iterable[str],
    submitted: object,
    zones: list[Mapping[str, Any]],
    rules: list[Mapping[str, Any]],
) -> list[str]:
    """Reject edits that would invalidate configured destinations."""
    if not isinstance(submitted, list) or not submitted:
        raise ModeValidationError("at_least_one_light")
    if any(
        not isinstance(entity, str)
        or not entity.startswith("light.")
        or len(entity) <= len("light.")
        for entity in submitted
    ):
        raise ModeValidationError("target_not_managed")
    lights = list(dict.fromkeys(submitted))
    if any(is_aggregate_light(hass, light) for light in lights):
        raise ModeValidationError("group_not_authorized")
    removed = set(current).difference(lights)
    if not removed:
        return lights
    if any(removed.intersection(zone.get("targets", [])) for zone in zones):
        raise ModeValidationError("zones_use_removed_lights")
    before = AdvancedTargetResolver(hass, current, zones, audit=False)
    after = AdvancedTargetResolver(hass, lights, zones, audit=False)
    for rule in rules:
        try:
            selection = legacy_or_advanced_targets(rule)
        except AdvancedTargetError as err:
            raise ModeValidationError("invalid_rule") from err
        if removed.intersection(selection[TARGET_ENTITIES]) or removed.intersection(
            before.group_dependencies(rule)
        ):
            raise ModeValidationError("rules_use_removed_lights")
        if selection[TARGET_AREAS] or selection[TARGET_LABELS]:
            indirect = {
                TARGET_AREAS: selection[TARGET_AREAS],
                TARGET_LABELS: selection[TARGET_LABELS],
            }
            try:
                area_and_label_lights = before.resolve(indirect).targets
            except AdvancedTargetError:
                pass
            else:
                if removed.intersection(area_and_label_lights):
                    raise ModeValidationError("rules_use_removed_lights")
        try:
            before.resolve(selection)
        except AdvancedTargetError:
            continue
        try:
            after.resolve(selection)
        except AdvancedTargetError as err:
            raise ModeValidationError("rules_use_removed_lights") from err
    return lights


def validate_zone_removal(
    zone_id: str, modes: list[Mapping[str, Any]], rules: list[Mapping[str, Any]]
) -> None:
    """Protect references even when the associated rule is disabled."""
    if any(mode.get("zone_id") == zone_id for mode in modes):
        raise ModeValidationError("zone_has_modes")
    for rule in rules:
        selection = rule.get("target_selection")
        if isinstance(selection, Mapping) and zone_id in (
            selection.get(TARGET_ZONES) or []
        ):
            raise ModeValidationError("zone_has_rules")


def validate_zone(
    hass: HomeAssistant,
    zone: ZoneDefinition,
    lights: Iterable[str],
    zones: list[Mapping[str, Any]],
    modes: list[Mapping[str, Any]],
) -> None:
    """Validate a zone against the current catalog and HA area registry."""
    if not zone.targets.issubset(lights):
        raise ModeValidationError("target_not_managed")
    if any(is_aggregate_light(hass, light) for light in zone.targets):
        raise ModeValidationError("group_not_authorized")
    if (
        zone.area_id is not None
        and ar.async_get(hass).async_get_area(zone.area_id) is None
    ):
        raise ModeValidationError("area_not_found")
    for other in zones:
        if other["zone_id"] == zone.zone_id:
            continue
        if zone.targets.intersection(other.get("targets", [])):
            raise ModeValidationError("target_in_multiple_zones")
        if str(other.get("name", "")).casefold() == zone.name.casefold():
            raise ModeValidationError("duplicate_zone")
    if any(
        mode.get("zone_id") == zone.zone_id
        and not set(mode.get("targets", [])).issubset(zone.targets)
        for mode in modes
    ):
        raise ModeValidationError("mode_target_outside_zone")


def validate_mode(
    mode: ModeDefinition,
    zones: list[Mapping[str, Any]],
    modes: list[Mapping[str, Any]],
) -> None:
    """Validate the mode's zone membership and name."""
    zone = next((item for item in zones if item["zone_id"] == mode.zone_id), None)
    if zone is None:
        raise ModeValidationError("mode_zone_missing")
    if not mode.targets.issubset(zone.get("targets", [])):
        raise ModeValidationError("mode_target_outside_zone")
    if any(
        item["mode_id"] != mode.mode_id
        and item["zone_id"] == mode.zone_id
        and str(item.get("name", "")).casefold() == mode.name.casefold()
        for item in modes
    ):
        raise ModeValidationError("duplicate_mode_name")
