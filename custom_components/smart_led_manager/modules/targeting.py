"""Home Assistant-aware, authorization-first advanced target resolution."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.const import ATTR_AREA_ID, ATTR_ENTITY_ID, ATTR_LABEL_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import label_registry as lr
from homeassistant.helpers.target import (
    TargetSelection,
    async_extract_referenced_entity_ids,
)

from ..const import (
    TARGET_ALL_MANAGED,
    TARGET_AREAS,
    TARGET_ENTITIES,
    TARGET_GROUPS,
    TARGET_LABELS,
    TARGET_ZONES,
)
from ..core.targets import TargetResolver, UnauthorizedTargetError


class AdvancedTargetError(ValueError):
    """A target definition cannot be expanded safely."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ResolvedTargets:
    """Safe physical targets plus informative indirect exclusions."""

    targets: frozenset[str]
    excluded: frozenset[str] = frozenset()
    groups: frozenset[str] = frozenset()


def normalize_target_definition(value: object) -> dict[str, Any]:
    """Normalize legacy target lists and advanced target dictionaries."""

    if isinstance(value, (list, tuple)):
        if not all(isinstance(item, str) and item for item in value):
            raise AdvancedTargetError("invalid_targets", "targets must be entity IDs")
        return {
            TARGET_ENTITIES: list(dict.fromkeys(value)),
            TARGET_ZONES: [],
            TARGET_AREAS: [],
            TARGET_LABELS: [],
            TARGET_GROUPS: [],
            TARGET_ALL_MANAGED: False,
        }
    if not isinstance(value, Mapping):
        raise AdvancedTargetError("invalid_targets", "target selection is invalid")
    normalized: dict[str, Any] = {}
    for key in (
        TARGET_ENTITIES,
        TARGET_ZONES,
        TARGET_AREAS,
        TARGET_LABELS,
        TARGET_GROUPS,
    ):
        items = value.get(key, [])
        if not isinstance(items, list) or not all(
            isinstance(item, str) and item for item in items
        ):
            raise AdvancedTargetError("invalid_targets", f"{key} must be a list")
        normalized[key] = list(dict.fromkeys(items))
    all_managed = value.get(TARGET_ALL_MANAGED, False)
    if not isinstance(all_managed, bool):
        raise AdvancedTargetError("invalid_targets", "all_managed must be boolean")
    normalized[TARGET_ALL_MANAGED] = all_managed
    if not all_managed and not any(
        normalized[key] for key in normalized if key != TARGET_ALL_MANAGED
    ):
        raise AdvancedTargetError("empty_targets", "at least one target is required")
    return normalized


def legacy_or_advanced_targets(rule: Mapping[str, Any]) -> dict[str, Any]:
    """Return the advanced selection, falling back to the legacy list."""

    return normalize_target_definition(
        rule.get("target_selection", rule.get("targets", []))
    )


class AdvancedTargetResolver:
    """Expand zones, registries, and transparent groups to authorized lights."""

    def __init__(
        self,
        hass: HomeAssistant,
        authorized: Iterable[str],
        zones: Iterable[Mapping[str, Any]],
    ) -> None:
        self._hass = hass
        self._explicit = TargetResolver(authorized)
        self._zones = {
            str(zone.get("zone_id")): frozenset(zone.get("targets", []))
            for zone in zones
            if zone.get("zone_id")
        }
        self._audit_authorized()

    @property
    def authorized(self) -> frozenset[str]:
        return self._explicit.authorized

    def _audit_authorized(self) -> None:
        states = getattr(self._hass, "states", None)
        if states is None:
            return
        for entity_id in self.authorized:
            state = states.get(entity_id)
            members = state.attributes.get(ATTR_ENTITY_ID) if state else None
            if isinstance(members, (list, tuple)):
                raise AdvancedTargetError(
                    "group_not_authorized",
                    f"managed target {entity_id} is a group, not a physical light",
                )

    def resolve_rule(self, rule: Mapping[str, Any]) -> ResolvedTargets:
        return self.resolve(legacy_or_advanced_targets(rule))

    def resolve(self, raw: object) -> ResolvedTargets:
        selection = normalize_target_definition(raw)
        resolved: set[str] = set()
        excluded: set[str] = set()
        groups: set[str] = set(selection[TARGET_GROUPS])

        explicit = selection[TARGET_ENTITIES]
        if explicit:
            try:
                resolved.update(self._explicit.resolve(explicit))
            except UnauthorizedTargetError as err:
                raise AdvancedTargetError("unauthorized_targets", str(err)) from err

        for zone_id in selection[TARGET_ZONES]:
            if zone_id not in self._zones:
                raise AdvancedTargetError("zone_not_found", f"zone {zone_id} not found")
            zone_targets = self._zones[zone_id]
            if not zone_targets or not zone_targets.issubset(self.authorized):
                raise AdvancedTargetError(
                    "invalid_zone_targets", f"zone {zone_id} is not safely authorized"
                )
            resolved.update(zone_targets)

        if selection[TARGET_AREAS]:
            area_reg = ar.async_get(self._hass)
            missing = set(selection[TARGET_AREAS]).difference(area_reg.areas)
            if missing:
                raise AdvancedTargetError(
                    "area_not_found", f"areas not found: {', '.join(sorted(missing))}"
                )
            area_entities = self._registry_entities(
                {ATTR_AREA_ID: selection[TARGET_AREAS]}
            )
            resolved.update(area_entities.intersection(self.authorized))
            excluded.update(area_entities.difference(self.authorized))

        if selection[TARGET_LABELS]:
            label_reg = lr.async_get(self._hass)
            missing = set(selection[TARGET_LABELS]).difference(label_reg.labels)
            if missing:
                raise AdvancedTargetError(
                    "label_not_found", f"labels not found: {', '.join(sorted(missing))}"
                )
            label_entities = self._registry_entities(
                {ATTR_LABEL_ID: selection[TARGET_LABELS]}
            )
            resolved.update(label_entities.intersection(self.authorized))
            excluded.update(label_entities.difference(self.authorized))

        for group_id in tuple(groups):
            resolved.update(self._expand_group(group_id, (), groups))

        if selection[TARGET_ALL_MANAGED]:
            resolved.update(self.authorized)
        if not resolved:
            raise AdvancedTargetError(
                "empty_targets", "target selection resolves to no managed lights"
            )
        return ResolvedTargets(
            targets=frozenset(resolved),
            excluded=frozenset(excluded),
            groups=frozenset(groups),
        )

    def _registry_entities(self, config: dict[str, Any]) -> set[str]:
        selected = async_extract_referenced_entity_ids(
            self._hass,
            TargetSelection(config),
            expand_group=False,
            primary_entities_only=True,
        )
        return {
            entity_id
            for entity_id in selected.referenced | selected.indirectly_referenced
            if entity_id.startswith("light.")
        }

    def _expand_group(
        self, entity_id: str, path: tuple[str, ...], known_groups: set[str]
    ) -> set[str]:
        if entity_id in path:
            cycle = " -> ".join((*path, entity_id))
            raise AdvancedTargetError("group_cycle", f"group cycle: {cycle}")
        state = self._hass.states.get(entity_id)
        members = state.attributes.get(ATTR_ENTITY_ID) if state else None
        if not isinstance(members, (list, tuple)) or not members:
            raise AdvancedTargetError(
                "opaque_group", f"group {entity_id} has no transparent membership"
            )
        resolved: set[str] = set()
        next_path = (*path, entity_id)
        for member in members:
            if not isinstance(member, str) or not member:
                raise AdvancedTargetError(
                    "opaque_group", f"group {entity_id} has invalid members"
                )
            member_state = self._hass.states.get(member)
            nested = (
                member_state.attributes.get(ATTR_ENTITY_ID) if member_state else None
            )
            if isinstance(nested, (list, tuple)):
                known_groups.add(member)
                resolved.update(self._expand_group(member, next_path, known_groups))
                continue
            if not member.startswith("light.") or member not in self.authorized:
                raise AdvancedTargetError(
                    "unsafe_group_member",
                    f"group {entity_id} contains unsafe member {member}",
                )
            resolved.add(member)
        return resolved
