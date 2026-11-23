"""Config flow for Smart LED Manager."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Any, override
from uuid import uuid4

import probatio
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import selector

from .const import (
    CONF_AREA_ID,
    CONF_LIGHTS,
    CONF_MANUAL_POLICY,
    CONF_MIN_COMMAND_INTERVAL,
    CONF_MODES,
    CONF_RULES,
    CONF_TIE_BREAKER,
    CONF_ZONES,
    DEFAULT_MANUAL_POLICY,
    DEFAULT_MIN_COMMAND_INTERVAL,
    DEFAULT_TIE_BREAKER,
    DOMAIN,
    NAME,
    RULE_TYPE_NUMERIC,
    RULE_TYPE_STATE,
)
from .modules.modes import ModeDefinition, ModeValidationError, ZoneDefinition

_STATE_SOURCE_DOMAINS = [
    "alarm_control_panel",
    "binary_sensor",
    "climate",
    "device_tracker",
    "input_boolean",
    "input_number",
    "input_select",
    "person",
    "sensor",
    "sun",
    "switch",
]
_NUMERIC_SOURCE_DOMAINS = ["input_number", "number", "sensor"]
_POINT_RE = re.compile(
    r"^\s*(-?(?:\d+(?:\.\d*)?|\.\d+))\s*:\s*"
    r"(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*$"
)
_DEFAULT_COLOR_POINTS = [
    {"value": 16.0, "rgb": [0, 0, 255]},
    {"value": 20.0, "rgb": [0, 255, 255]},
    {"value": 24.0, "rgb": [0, 255, 0]},
    {"value": 28.0, "rgb": [255, 255, 0]},
    {"value": 32.0, "rgb": [255, 128, 0]},
    {"value": 36.0, "rgb": [255, 0, 0]},
]


def _light_selector(*, entities: list[str] | None = None) -> selector.EntitySelector:
    """Return a multiple light selector, optionally limited to managed lights."""
    config: dict[str, Any] = {"multiple": True}
    if entities is None:
        config["domain"] = "light"
    else:
        config["include_entities"] = entities
    return selector.EntitySelector(selector.EntitySelectorConfig(**config))


def _number_selector(
    minimum: float,
    maximum: float,
    *,
    step: float | str = 1,
) -> selector.NumberSelector:
    """Return a boxed number selector."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=step,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def parse_color_points(raw: str) -> list[dict[str, Any]]:
    """Parse ``value:r,g,b`` reference points separated by semicolons."""
    points: list[dict[str, Any]] = []
    for item in raw.split(";"):
        match = _POINT_RE.match(item)
        if match is None:
            raise ValueError("invalid color point")
        value = float(match.group(1))
        rgb = [int(match.group(index)) for index in (2, 3, 4)]
        if any(channel > 255 for channel in rgb):
            raise ValueError("RGB channel out of range")
        points.append({"value": value, "rgb": rgb})
    if len(points) < 2:
        raise ValueError("at least two color points are required")
    values = [point["value"] for point in points]
    if len(values) != len(set(values)):
        raise ValueError("duplicate color point")
    return sorted(points, key=lambda point: point["value"])


def validate_color_points(raw: object, *, minimum: int = 2) -> list[dict[str, Any]]:
    """Validate the persisted visual point format and return it sorted."""
    if not isinstance(raw, (list, tuple)):
        raise ValueError("color points must be a list")
    points = [_validate_color_point(point) for point in raw]
    if len(points) < minimum:
        raise ValueError(f"at least {minimum} color points are required")
    values = [point["value"] for point in points]
    if len(values) != len(set(values)):
        raise ValueError("duplicate color point")
    return sorted(points, key=lambda point: point["value"])


def _validate_color_point(raw: object) -> dict[str, Any]:
    """Validate one finite numeric value and one RGB triplet."""
    if not isinstance(raw, Mapping):
        raise ValueError("color point must be an object")
    try:
        value = float(raw["value"])
        rgb = list(raw["rgb"])
    except (KeyError, TypeError, ValueError) as err:
        raise ValueError("invalid color point") from err
    if not math.isfinite(value):
        raise ValueError("color point value must be finite")
    if len(rgb) != 3 or any(
        isinstance(channel, bool)
        or not isinstance(channel, int)
        or not 0 <= channel <= 255
        for channel in rgb
    ):
        raise ValueError("RGB channel out of range")
    return {"value": value, "rgb": rgb}


class SmartLEDManagerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure Smart LED Manager."""

    VERSION = 1
    MINOR_VERSION = 2

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry) -> SmartLEDManagerOptionsFlow:
        """Create the options flow."""
        return SmartLEDManagerOptionsFlow()

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the single integration entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            lights = list(dict.fromkeys(user_input[CONF_LIGHTS]))
            if not lights:
                errors[CONF_LIGHTS] = "at_least_one_light"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=NAME,
                    data={CONF_LIGHTS: lights},
                    options={
                        CONF_RULES: [],
                        CONF_ZONES: [],
                        CONF_MODES: [],
                        CONF_TIE_BREAKER: DEFAULT_TIE_BREAKER,
                        CONF_MIN_COMMAND_INTERVAL: DEFAULT_MIN_COMMAND_INTERVAL,
                        CONF_MANUAL_POLICY: DEFAULT_MANUAL_POLICY,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=probatio.Schema(
                {probatio.Required(CONF_LIGHTS): _light_selector()}
            ),
            errors=errors,
        )


class SmartLEDManagerOptionsFlow(OptionsFlow):
    """Manage strips, rules, and engine settings."""

    def __init__(self) -> None:
        super().__init__()
        self._selected_rule_id: str | None = None
        self._rule_operation = "add"
        self._numeric_rule_draft: dict[str, Any] | None = None
        self._selected_point_index: int | None = None

    def _options(self) -> dict[str, Any]:
        """Return a mutable copy of all current options."""
        return deepcopy(dict(self.config_entry.options))

    def _lights(self) -> list[str]:
        """Return currently managed lights."""
        return list(
            self.config_entry.options.get(
                CONF_LIGHTS, self.config_entry.data.get(CONF_LIGHTS, [])
            )
        )

    def _zones(self) -> list[dict[str, Any]]:
        """Return configured zone definitions."""
        return deepcopy(list(self.config_entry.options.get(CONF_ZONES, [])))

    def _modes(self) -> list[dict[str, Any]]:
        """Return configured mode definitions."""
        return deepcopy(list(self.config_entry.options.get(CONF_MODES, [])))

    def _rules(self) -> list[dict[str, Any]]:
        """Return configured rule definitions."""
        return deepcopy(list(self.config_entry.options.get(CONF_RULES, [])))

    def _create_options_entry(self, updates: dict[str, Any]) -> ConfigFlowResult:
        """Merge options so one flow step never discards unrelated settings."""
        options = self._options()
        options.update(updates)
        return self.async_create_entry(data=options)

    @override
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the native management menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "lights",
                "zones",
                "modes",
                "rules",
                "advanced",
            ],
        )

    async def async_step_lights(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the physical lights this integration may control."""
        errors: dict[str, str] = {}
        if user_input is not None:
            lights = list(dict.fromkeys(user_input[CONF_LIGHTS]))
            if not lights:
                errors[CONF_LIGHTS] = "at_least_one_light"
            elif any(
                not set(zone.get("targets", [])).issubset(lights)
                for zone in self._zones()
            ):
                errors[CONF_LIGHTS] = "zones_use_removed_lights"
            else:
                return self._create_options_entry({CONF_LIGHTS: lights})

        return self.async_show_form(
            step_id="lights",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_LIGHTS, default=self._lights()
                    ): _light_selector()
                }
            ),
            errors=errors,
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure deterministic ranking and command protection."""
        if user_input is not None:
            return self._create_options_entry(user_input)
        options = self._options()
        return self.async_show_form(
            step_id="settings",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_TIE_BREAKER,
                        default=options.get(CONF_TIE_BREAKER, DEFAULT_TIE_BREAKER),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["newest", "oldest", "lexical"],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="tie_breaker",
                        )
                    ),
                    probatio.Required(
                        CONF_MIN_COMMAND_INTERVAL,
                        default=options.get(
                            CONF_MIN_COMMAND_INTERVAL, DEFAULT_MIN_COMMAND_INTERVAL
                        ),
                    ): _number_selector(0.1, 10, step=0.05),
                    probatio.Required(
                        CONF_MANUAL_POLICY,
                        default=options.get(CONF_MANUAL_POLICY, DEFAULT_MANUAL_POLICY),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["service_only", "respect", "temporary"],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="manual_policy",
                        )
                    ),
                }
            ),
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Expose advanced engine settings under the top-level menu."""
        if user_input is not None:
            return self._create_options_entry(user_input)
        options = self._options()
        return self.async_show_form(
            step_id="advanced",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_TIE_BREAKER,
                        default=options.get(CONF_TIE_BREAKER, DEFAULT_TIE_BREAKER),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["newest", "oldest", "lexical"],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="tie_breaker",
                        )
                    ),
                    probatio.Required(
                        CONF_MIN_COMMAND_INTERVAL,
                        default=options.get(
                            CONF_MIN_COMMAND_INTERVAL, DEFAULT_MIN_COMMAND_INTERVAL
                        ),
                    ): _number_selector(0.1, 10, step=0.05),
                    probatio.Required(
                        CONF_MANUAL_POLICY,
                        default=options.get(CONF_MANUAL_POLICY, DEFAULT_MANUAL_POLICY),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["service_only", "respect", "temporary"],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="manual_policy",
                        )
                    ),
                }
            ),
        )

    async def async_step_rules(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show smart-rule lifecycle actions."""
        return self.async_show_menu(
            step_id="rules",
            menu_options=[
                "add_state_rule",
                "add_numeric_rule",
                "edit_rule",
                "duplicate_rule",
                "toggle_rule",
                "delete_rule",
            ],
        )

    async def async_step_zones(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show zone lifecycle actions."""
        return self.async_show_menu(
            step_id="zones",
            menu_options=["add_zone", "edit_zone", "delete_zone"],
        )

    async def async_step_add_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create a non-overlapping zone."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                zone = self._validated_zone(user_input, uuid4().hex)
            except ModeValidationError as err:
                errors["base"] = err.key
            else:
                return self._create_options_entry(
                    {CONF_ZONES: [*self._zones(), zone.to_dict()]}
                )
        return self.async_show_form(
            step_id="add_zone",
            data_schema=self._zone_schema(),
            errors=errors,
        )

    async def async_step_edit_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose a zone whose editable fields will be changed."""
        zones = self._zones()
        if not zones:
            return self.async_abort(reason="no_zones")
        if user_input is not None:
            self._editing_zone_id = str(user_input["zone_id"])
            return await self.async_step_edit_zone_form()
        return self.async_show_form(
            step_id="edit_zone",
            data_schema=probatio.Schema(
                {
                    probatio.Required("zone_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=self._zone_choices())
                    )
                }
            ),
        )

    async def async_step_edit_zone_form(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit a zone while preserving its immutable identifier."""
        zone_id = self._editing_zone_id
        current = next(zone for zone in self._zones() if zone["zone_id"] == zone_id)
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                zone = self._validated_zone(user_input, zone_id)
            except ModeValidationError as err:
                errors["base"] = err.key
            else:
                zones = [
                    zone.to_dict() if item["zone_id"] == zone_id else item
                    for item in self._zones()
                ]
                return self._create_options_entry({CONF_ZONES: zones})
        return self.async_show_form(
            step_id="edit_zone_form",
            data_schema=self._zone_schema(current),
            errors=errors,
        )

    async def async_step_delete_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Delete an empty zone after its modes have been removed."""
        zones = self._zones()
        if not zones:
            return self.async_abort(reason="no_zones")
        errors: dict[str, str] = {}
        if user_input is not None:
            zone_id = str(user_input["zone_id"])
            if any(mode.get("zone_id") == zone_id for mode in self._modes()):
                errors["base"] = "zone_has_modes"
            else:
                return self._create_options_entry(
                    {CONF_ZONES: [zone for zone in zones if zone["zone_id"] != zone_id]}
                )
        return self.async_show_form(
            step_id="delete_zone",
            data_schema=probatio.Schema(
                {
                    probatio.Required("zone_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=self._zone_choices())
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_modes(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show mode lifecycle actions."""
        return self.async_show_menu(
            step_id="modes",
            menu_options=["add_mode", "edit_mode", "delete_mode"],
        )

    async def async_step_add_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create a persistent mode definition."""
        if not self._zones():
            return self.async_abort(reason="no_zones")
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                mode = self._validated_mode(user_input, uuid4().hex)
            except ModeValidationError as err:
                errors["base"] = err.key
            else:
                return self._create_options_entry(
                    {CONF_MODES: [*self._modes(), mode.to_dict()]}
                )
        return self.async_show_form(
            step_id="add_mode",
            data_schema=self._mode_schema(),
            errors=errors,
        )

    async def async_step_edit_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose a mode whose editable definition will be changed."""
        modes = self._modes()
        if not modes:
            return self.async_abort(reason="no_modes")
        if user_input is not None:
            self._editing_mode_id = str(user_input["mode_id"])
            return await self.async_step_edit_mode_form()
        return self.async_show_form(
            step_id="edit_mode",
            data_schema=probatio.Schema(
                {
                    probatio.Required("mode_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=self._mode_choices())
                    )
                }
            ),
        )

    async def async_step_edit_mode_form(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit a mode while preserving its immutable identifier."""
        mode_id = self._editing_mode_id
        current = next(mode for mode in self._modes() if mode["mode_id"] == mode_id)
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                mode = self._validated_mode(user_input, mode_id)
            except ModeValidationError as err:
                errors["base"] = err.key
            else:
                modes = [
                    mode.to_dict() if item["mode_id"] == mode_id else item
                    for item in self._modes()
                ]
                return self._create_options_entry({CONF_MODES: modes})
        return self.async_show_form(
            step_id="edit_mode_form",
            data_schema=self._mode_schema(current),
            errors=errors,
        )

    async def async_step_delete_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Delete a definition; startup reconciliation removes active intent."""
        modes = self._modes()
        if not modes:
            return self.async_abort(reason="no_modes")
        if user_input is not None:
            mode_id = str(user_input["mode_id"])
            return self._create_options_entry(
                {CONF_MODES: [mode for mode in modes if mode["mode_id"] != mode_id]}
            )
        return self.async_show_form(
            step_id="delete_mode",
            data_schema=probatio.Schema(
                {
                    probatio.Required("mode_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=self._mode_choices())
                    )
                }
            ),
        )

    def _zone_schema(self, current: dict[str, Any] | None = None) -> probatio.Schema:
        current = current or {}
        area_marker = (
            probatio.Optional(CONF_AREA_ID, default=current[CONF_AREA_ID])
            if current.get(CONF_AREA_ID)
            else probatio.Optional(CONF_AREA_ID)
        )
        return probatio.Schema(
            {
                probatio.Required(
                    "name", default=current.get("name", "")
                ): selector.TextSelector(),
                probatio.Required(
                    "targets", default=current.get("targets", [])
                ): _light_selector(entities=self._lights()),
                area_marker: selector.AreaSelector(),
            }
        )

    def _mode_schema(self, current: dict[str, Any] | None = None) -> probatio.Schema:
        current = current or {}
        color_marker = (
            probatio.Optional("rgb_color", default=current["rgb_color"])
            if current.get("rgb_color") is not None
            else probatio.Optional("rgb_color")
        )
        brightness_marker = (
            probatio.Optional("brightness", default=current["brightness"])
            if current.get("brightness") is not None
            else probatio.Optional("brightness")
        )
        transition_marker = (
            probatio.Optional("transition", default=current["transition"])
            if current.get("transition") is not None
            else probatio.Optional("transition")
        )
        return probatio.Schema(
            {
                probatio.Required(
                    "zone_id",
                    default=current.get("zone_id", self._zones()[0]["zone_id"]),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=self._zone_choices())
                ),
                probatio.Required(
                    "name", default=current.get("name", "")
                ): selector.TextSelector(),
                probatio.Required(
                    "targets", default=current.get("targets", [])
                ): _light_selector(entities=self._lights()),
                probatio.Required(
                    "priority", default=current.get("priority", 50)
                ): _number_selector(0, 100),
                color_marker: selector.ColorRGBSelector(),
                brightness_marker: _number_selector(1, 255),
                transition_marker: _number_selector(0, 300, step=0.1),
                probatio.Required(
                    "allow_turn_on", default=current.get("allow_turn_on", True)
                ): selector.BooleanSelector(),
                probatio.Required(
                    "animation", default=current.get("animation", "fixed")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["fixed", "blink", "pulse"],
                        translation_key="mode_animation",
                    )
                ),
                probatio.Required(
                    "period", default=current.get("period", 1.0)
                ): _number_selector(0.5, 60, step=0.1),
                probatio.Required(
                    "expose_switch", default=current.get("expose_switch", False)
                ): selector.BooleanSelector(),
            }
        )

    def _validated_zone(
        self, user_input: dict[str, Any], zone_id: str
    ) -> ZoneDefinition:
        zone = ZoneDefinition.from_dict({**user_input, "zone_id": zone_id})
        if not zone.targets.issubset(self._lights()):
            raise ModeValidationError("target_not_managed")
        if (
            zone.area_id is not None
            and ar.async_get(self.hass).async_get_area(zone.area_id) is None
        ):
            raise ModeValidationError("area_not_found")
        for other in self._zones():
            if other["zone_id"] != zone_id and zone.targets.intersection(
                other.get("targets", [])
            ):
                raise ModeValidationError("target_in_multiple_zones")
            if (
                other["zone_id"] != zone_id
                and str(other.get("name", "")).casefold() == zone.name.casefold()
            ):
                raise ModeValidationError("duplicate_zone")
        if any(
            mode.get("zone_id") == zone_id
            and not set(mode.get("targets", [])).issubset(zone.targets)
            for mode in self._modes()
        ):
            raise ModeValidationError("mode_target_outside_zone")
        return zone

    def _validated_mode(
        self, user_input: dict[str, Any], mode_id: str
    ) -> ModeDefinition:
        mode = ModeDefinition.from_dict({**user_input, "mode_id": mode_id})
        zones = {zone["zone_id"]: zone for zone in self._zones()}
        zone = zones.get(mode.zone_id)
        if zone is None:
            raise ModeValidationError("mode_zone_missing")
        if not mode.targets.issubset(zone.get("targets", [])):
            raise ModeValidationError("mode_target_outside_zone")
        if any(
            item["mode_id"] != mode_id
            and item.get("zone_id") == mode.zone_id
            and str(item.get("name", "")).casefold() == mode.name.casefold()
            for item in self._modes()
        ):
            raise ModeValidationError("duplicate_mode_name")
        return mode

    def _zone_choices(self) -> list[dict[str, str]]:
        return [
            {"value": zone["zone_id"], "label": zone["name"]} for zone in self._zones()
        ]

    def _mode_choices(self) -> list[dict[str, str]]:
        zones = {zone["zone_id"]: zone["name"] for zone in self._zones()}
        return [
            {
                "value": mode["mode_id"],
                "label": f"{zones.get(mode['zone_id'], mode['zone_id'])}: {mode['name']}",
            }
            for mode in self._modes()
        ]

    async def async_step_add_state_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a persistent state rule."""
        self._rule_operation = "add"
        current = {
            "id": uuid4().hex,
            "type": RULE_TYPE_STATE,
            "enabled": True,
        }
        return self._state_rule_form("add_state_rule", current, user_input)

    async def async_step_add_numeric_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a numeric sensor color rule."""
        self._rule_operation = "add"
        current = {
            "id": uuid4().hex,
            "type": RULE_TYPE_NUMERIC,
            "enabled": True,
            "points": deepcopy(_DEFAULT_COLOR_POINTS),
        }
        return self._numeric_rule_form("add_numeric_rule", current, user_input)

    async def async_step_edit_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select an existing rule to edit without changing its identifier."""
        rules = self._rules()
        if not rules:
            return self.async_abort(reason="no_rules")
        if user_input is None:
            return self._rule_selection_form("edit_rule", rules)
        self._selected_rule_id = str(user_input["rule_id"])
        self._rule_operation = "edit"
        rule = self._selected_rule(rules)
        if rule is None:
            return self.async_abort(reason="rule_not_found")
        if rule.get("type") == RULE_TYPE_STATE:
            return await self.async_step_edit_state_rule()
        if rule.get("type") == RULE_TYPE_NUMERIC:
            return await self.async_step_edit_numeric_rule()
        return self.async_abort(reason="invalid_rule")

    async def async_step_duplicate_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select a rule to copy into a new, initially disabled definition."""
        rules = self._rules()
        if not rules:
            return self.async_abort(reason="no_rules")
        if user_input is None:
            return self._rule_selection_form("duplicate_rule", rules)
        self._selected_rule_id = str(user_input["rule_id"])
        self._rule_operation = "duplicate"
        rule = self._selected_rule(rules)
        if rule is None:
            return self.async_abort(reason="rule_not_found")
        if rule.get("type") == RULE_TYPE_STATE:
            return await self.async_step_duplicate_state_rule()
        if rule.get("type") == RULE_TYPE_NUMERIC:
            return await self.async_step_duplicate_numeric_rule()
        return self.async_abort(reason="invalid_rule")

    async def async_step_toggle_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Enable or disable a rule while preserving its stable identifier."""
        rules = self._rules()
        if not rules:
            return self.async_abort(reason="no_rules")
        if user_input is None:
            return self._rule_selection_form("toggle_rule", rules)
        selected = str(user_input["rule_id"])
        found = False
        updated: list[dict[str, Any]] = []
        for rule in rules:
            if str(rule.get("id")) == selected:
                found = True
                rule["enabled"] = not self._rule_enabled(rule)
            updated.append(rule)
        if not found:
            return self.async_abort(reason="rule_not_found")
        return self._create_options_entry({CONF_RULES: updated})

    async def async_step_edit_state_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit one state rule and preserve its stable identifier."""
        current = self._editable_rule()
        if current is None:
            return self.async_abort(reason="rule_not_found")
        return self._state_rule_form("edit_state_rule", current, user_input)

    async def async_step_duplicate_state_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create a disabled state-rule draft from an existing definition."""
        current = self._editable_rule()
        if current is None:
            return self.async_abort(reason="rule_not_found")
        return self._state_rule_form("duplicate_state_rule", current, user_input)

    async def async_step_edit_numeric_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit numeric metadata before opening its visual point editor."""
        current = self._editable_rule()
        if current is None:
            return self.async_abort(reason="rule_not_found")
        return self._numeric_rule_form("edit_numeric_rule", current, user_input)

    async def async_step_duplicate_numeric_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create a disabled numeric-rule draft from an existing definition."""
        current = self._editable_rule()
        if current is None:
            return self.async_abort(reason="rule_not_found")
        return self._numeric_rule_form("duplicate_numeric_rule", current, user_input)

    async def async_step_numeric_points(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the native multi-step editor for one numeric rule's points."""
        del user_input
        draft = self._numeric_rule_draft
        if draft is None:
            return self.async_abort(reason="rule_not_found")
        menu_options = ["add_numeric_point"]
        if draft["points"]:
            menu_options.extend(["edit_numeric_point", "delete_numeric_point"])
        menu_options.extend(["save_numeric_rule", "cancel_numeric_rule"])
        return self.async_show_menu(
            step_id="numeric_points",
            menu_options=menu_options,
            description_placeholders={
                "points": self._numeric_points_summary(draft),
                "unit": self._numeric_unit(str(draft["source"])) or "—",
            },
        )

    async def async_step_add_numeric_point(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add one finite value and RGB color to the draft."""
        draft = self._numeric_rule_draft
        if draft is None:
            return self.async_abort(reason="rule_not_found")
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                points = validate_color_points(
                    [*draft["points"], user_input], minimum=1
                )
            except ValueError:
                errors["base"] = "invalid_or_duplicate_color_point"
            else:
                draft["points"] = points
                return await self.async_step_numeric_points()

        return self.async_show_form(
            step_id="add_numeric_point",
            data_schema=self._numeric_point_schema(draft),
            errors=errors,
        )

    async def async_step_edit_numeric_point(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select a color point to edit."""
        draft = self._numeric_rule_draft
        if draft is None:
            return self.async_abort(reason="rule_not_found")
        if user_input is not None:
            self._selected_point_index = int(user_input["point_index"])
            return await self.async_step_edit_numeric_point_form()
        return self._numeric_point_selection_form("edit_numeric_point", draft)

    async def async_step_edit_numeric_point_form(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update one point without saving the rule yet."""
        draft = self._numeric_rule_draft
        index = self._selected_point_index
        if draft is None or index is None or index >= len(draft["points"]):
            return self.async_abort(reason="rule_not_found")
        current = draft["points"][index]
        errors: dict[str, str] = {}
        if user_input is not None:
            points = [
                user_input if item_index == index else point
                for item_index, point in enumerate(draft["points"])
            ]
            try:
                draft["points"] = validate_color_points(points, minimum=1)
            except ValueError:
                errors["base"] = "invalid_or_duplicate_color_point"
            else:
                self._selected_point_index = None
                return await self.async_step_numeric_points()
        return self.async_show_form(
            step_id="edit_numeric_point_form",
            data_schema=self._numeric_point_schema(draft, current=current),
            errors=errors,
        )

    async def async_step_delete_numeric_point(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove one point from the draft without applying the rule."""
        draft = self._numeric_rule_draft
        if draft is None:
            return self.async_abort(reason="rule_not_found")
        if user_input is not None:
            index = int(user_input["point_index"])
            if 0 <= index < len(draft["points"]):
                draft["points"].pop(index)
            return await self.async_step_numeric_points()
        return self._numeric_point_selection_form("delete_numeric_point", draft)

    async def async_step_save_numeric_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate and atomically persist the completed numeric rule."""
        draft = self._numeric_rule_draft
        if draft is None:
            return self.async_abort(reason="rule_not_found")
        try:
            draft["points"] = validate_color_points(draft["points"])
        except ValueError:
            if user_input is not None:
                return await self.async_step_numeric_points()
            return self.async_show_form(
                step_id="save_numeric_rule",
                data_schema=probatio.Schema({}),
                errors={"base": "at_least_two_color_points"},
            )
        return self._save_rule(draft)

    async def async_step_cancel_numeric_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Discard all in-flow numeric edits without changing options."""
        del user_input
        self._numeric_rule_draft = None
        self._selected_point_index = None
        return await self.async_step_rules()

    async def async_step_delete_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Delete one configured rule."""
        rules = self._rules()
        if not rules:
            return self.async_abort(reason="no_rules")
        if user_input is not None:
            selected = str(user_input["rule_id"])
            if not any(str(rule.get("id")) == selected for rule in rules):
                return self.async_abort(reason="rule_not_found")
            return self._create_options_entry(
                {
                    CONF_RULES: [
                        rule for rule in rules if str(rule.get("id")) != selected
                    ]
                }
            )

        return self._rule_selection_form("delete_rule", rules)

    def _state_rule_form(
        self,
        step_id: str,
        current: dict[str, Any],
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            error = self._targets_error(user_input.get("targets"))
            if error is not None:
                errors["targets"] = error
            else:
                rule = dict(user_input)
                rule.update({"id": current["id"], "type": RULE_TYPE_STATE})
                return self._save_rule(rule)
        return self.async_show_form(
            step_id=step_id,
            data_schema=self._state_rule_schema(current),
            errors=errors,
        )

    def _numeric_rule_form(
        self,
        step_id: str,
        current: dict[str, Any],
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        try:
            points = validate_color_points(current.get("points", _DEFAULT_COLOR_POINTS))
        except ValueError:
            return self.async_abort(reason="invalid_rule")
        if user_input is not None:
            error = self._targets_error(user_input.get("targets"))
            if error is not None:
                errors["targets"] = error
            else:
                self._numeric_rule_draft = {
                    **user_input,
                    "id": current["id"],
                    "type": RULE_TYPE_NUMERIC,
                    "points": points,
                }
                return self.async_show_menu(
                    step_id="numeric_points",
                    menu_options=[
                        "add_numeric_point",
                        "edit_numeric_point",
                        "delete_numeric_point",
                        "save_numeric_rule",
                        "cancel_numeric_rule",
                    ],
                    description_placeholders={
                        "points": self._numeric_points_summary(
                            self._numeric_rule_draft
                        ),
                        "unit": self._numeric_unit(str(user_input["source"])) or "—",
                    },
                )
        return self.async_show_form(
            step_id=step_id,
            data_schema=self._numeric_rule_schema(current),
            errors=errors,
        )

    def _state_rule_schema(self, current: Mapping[str, Any]) -> probatio.Schema:
        return probatio.Schema(
            {
                probatio.Required(
                    "name", default=current.get("name", "")
                ): selector.TextSelector(),
                probatio.Required(
                    "source", default=current.get("source", "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=_STATE_SOURCE_DOMAINS)
                ),
                probatio.Required(
                    "operator", default=current.get("operator", "equals")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["equals", "not_equals"],
                        translation_key="state_operator",
                    )
                ),
                probatio.Required(
                    "state", default=current.get("state", "")
                ): selector.TextSelector(),
                probatio.Required(
                    "targets", default=list(current.get("targets", []))
                ): _light_selector(entities=self._lights()),
                probatio.Required(
                    "priority", default=current.get("priority", 40)
                ): _number_selector(0, 100),
                probatio.Required(
                    "rgb_color", default=current.get("rgb_color", [0, 0, 255])
                ): selector.ColorRGBSelector(),
                probatio.Required(
                    "brightness", default=current.get("brightness", 255)
                ): _number_selector(1, 255),
                probatio.Required(
                    "transition", default=current.get("transition", 0)
                ): _number_selector(0, 300, step=0.1),
                probatio.Required(
                    "enabled", default=self._rule_enabled(current)
                ): selector.BooleanSelector(),
            }
        )

    def _numeric_rule_schema(self, current: Mapping[str, Any]) -> probatio.Schema:
        return probatio.Schema(
            {
                probatio.Required(
                    "name", default=current.get("name", "")
                ): selector.TextSelector(),
                probatio.Required(
                    "source", default=current.get("source", "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=_NUMERIC_SOURCE_DOMAINS)
                ),
                probatio.Required(
                    "targets", default=list(current.get("targets", []))
                ): _light_selector(entities=self._lights()),
                probatio.Required(
                    "priority", default=current.get("priority", 40)
                ): _number_selector(0, 100),
                probatio.Required(
                    "mode", default=current.get("mode", "interpolate")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["interpolate", "ranges"],
                        translation_key="numeric_mode",
                    )
                ),
                probatio.Required(
                    "brightness", default=current.get("brightness", 255)
                ): _number_selector(1, 255),
                probatio.Required(
                    "transition", default=current.get("transition", 1)
                ): _number_selector(0, 300, step=0.1),
                probatio.Required(
                    "minimum_change", default=current.get("minimum_change", 0.1)
                ): _number_selector(0, 100000, step="any"),
                probatio.Required(
                    "minimum_interval", default=current.get("minimum_interval", 5)
                ): _number_selector(0, 3600, step=0.5),
                probatio.Required(
                    "enabled", default=self._rule_enabled(current)
                ): selector.BooleanSelector(),
            }
        )

    def _numeric_point_schema(
        self,
        draft: Mapping[str, Any],
        *,
        current: Mapping[str, Any] | None = None,
    ) -> probatio.Schema:
        current = current or {"value": 0, "rgb": [0, 0, 255]}
        config: dict[str, Any] = {
            "step": "any",
            "mode": selector.NumberSelectorMode.BOX,
        }
        if unit := self._numeric_unit(str(draft["source"])):
            config["unit_of_measurement"] = unit
        return probatio.Schema(
            {
                probatio.Required(
                    "value", default=current["value"]
                ): selector.NumberSelector(selector.NumberSelectorConfig(**config)),
                probatio.Required(
                    "rgb", default=current["rgb"]
                ): selector.ColorRGBSelector(),
            }
        )

    def _rule_selection_form(
        self, step_id: str, rules: list[dict[str, Any]]
    ) -> ConfigFlowResult:
        choices = [
            {"value": rule["id"], "label": rule.get("name", rule["id"])}
            for rule in rules
        ]
        return self.async_show_form(
            step_id=step_id,
            data_schema=probatio.Schema(
                {
                    probatio.Required("rule_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=choices)
                    )
                }
            ),
        )

    def _numeric_point_selection_form(
        self, step_id: str, draft: Mapping[str, Any]
    ) -> ConfigFlowResult:
        choices = [
            {
                "value": str(index),
                "label": self._format_numeric_point(point, draft),
            }
            for index, point in enumerate(draft["points"])
        ]
        return self.async_show_form(
            step_id=step_id,
            data_schema=probatio.Schema(
                {
                    probatio.Required("point_index"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=choices)
                    )
                }
            ),
        )

    def _editable_rule(self) -> dict[str, Any] | None:
        rule = self._selected_rule(self._rules())
        if rule is None:
            return None
        rule.setdefault("enabled", True)
        if self._rule_operation == "duplicate":
            rule["id"] = uuid4().hex
            rule["name"] = f"{rule.get('name', 'Rule')} (2)"
            rule["enabled"] = False
        return rule

    def _selected_rule(self, rules: list[dict[str, Any]]) -> dict[str, Any] | None:
        return next(
            (rule for rule in rules if str(rule.get("id")) == self._selected_rule_id),
            None,
        )

    def _save_rule(self, rule: Mapping[str, Any]) -> ConfigFlowResult:
        saved = deepcopy(dict(rule))
        rules = self._rules()
        for index, current in enumerate(rules):
            if str(current.get("id")) == str(saved["id"]):
                rules[index] = saved
                break
        else:
            rules.append(saved)
        self._numeric_rule_draft = None
        self._selected_point_index = None
        return self._create_options_entry({CONF_RULES: rules})

    def _targets_error(self, targets: object) -> str | None:
        if not targets:
            return "at_least_one_target"
        if not set(targets).issubset(self._lights()):
            return "target_not_managed"
        return None

    def _numeric_unit(self, source: str) -> str | None:
        states = getattr(self.hass, "states", None)
        state = states.get(source) if states is not None else None
        if state is None:
            return None
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        return unit if isinstance(unit, str) and unit else None

    def _numeric_points_summary(self, draft: Mapping[str, Any]) -> str:
        return (
            "\n".join(
                self._format_numeric_point(point, draft) for point in draft["points"]
            )
            or "—"
        )

    def _format_numeric_point(
        self, point: Mapping[str, Any], draft: Mapping[str, Any]
    ) -> str:
        unit = self._numeric_unit(str(draft["source"]))
        suffix = f" {unit}" if unit else ""
        rgb = ",".join(str(channel) for channel in point["rgb"])
        return f"{point['value']:g}{suffix} — RGB({rgb})"

    @staticmethod
    def _rule_enabled(rule: Mapping[str, Any]) -> bool:
        return rule.get("enabled", True) is not False
