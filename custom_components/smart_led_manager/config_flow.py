"""Config flow for Smart LED Manager."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, override
from uuid import uuid4

import probatio
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
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
            menu_options=["add_state_rule", "add_numeric_rule", "delete_rule"],
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
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input["targets"]:
                errors["targets"] = "at_least_one_target"
            elif not set(user_input["targets"]).issubset(self._lights()):
                errors["targets"] = "target_not_managed"
            else:
                rule = dict(user_input)
                rule.update({"id": uuid4().hex, "type": RULE_TYPE_STATE})
                rules = [*self._options().get(CONF_RULES, []), rule]
                return self._create_options_entry({CONF_RULES: rules})

        return self.async_show_form(
            step_id="add_state_rule",
            data_schema=probatio.Schema(
                {
                    probatio.Required("name"): selector.TextSelector(),
                    probatio.Required("source"): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=_STATE_SOURCE_DOMAINS)
                    ),
                    probatio.Required(
                        "operator", default="equals"
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["equals", "not_equals"],
                            translation_key="state_operator",
                        )
                    ),
                    probatio.Required("state"): selector.TextSelector(),
                    probatio.Required("targets"): _light_selector(
                        entities=self._lights()
                    ),
                    probatio.Required("priority", default=40): _number_selector(0, 100),
                    probatio.Required(
                        "rgb_color", default=[0, 0, 255]
                    ): selector.ColorRGBSelector(),
                    probatio.Required("brightness", default=255): _number_selector(
                        1, 255
                    ),
                    probatio.Required("transition", default=0): _number_selector(
                        0, 300, step=0.1
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_add_numeric_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a numeric sensor color rule."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                points = parse_color_points(user_input["points"])
            except ValueError:
                errors["points"] = "invalid_color_points"
            if not user_input["targets"]:
                errors["targets"] = "at_least_one_target"
            elif not set(user_input["targets"]).issubset(self._lights()):
                errors["targets"] = "target_not_managed"
            if not errors:
                rule = dict(user_input)
                rule["points"] = points
                rule.update({"id": uuid4().hex, "type": RULE_TYPE_NUMERIC})
                rules = [*self._options().get(CONF_RULES, []), rule]
                return self._create_options_entry({CONF_RULES: rules})

        return self.async_show_form(
            step_id="add_numeric_rule",
            data_schema=probatio.Schema(
                {
                    probatio.Required("name"): selector.TextSelector(),
                    probatio.Required("source"): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=_NUMERIC_SOURCE_DOMAINS)
                    ),
                    probatio.Required("targets"): _light_selector(
                        entities=self._lights()
                    ),
                    probatio.Required("priority", default=40): _number_selector(0, 100),
                    probatio.Required(
                        "points",
                        default="16:0,0,255;20:0,255,255;24:0,255,0;28:255,255,0;32:255,128,0;36:255,0,0",
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(multiline=True)
                    ),
                    probatio.Required(
                        "mode", default="interpolate"
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["interpolate", "ranges"],
                            translation_key="numeric_mode",
                        )
                    ),
                    probatio.Required("brightness", default=255): _number_selector(
                        1, 255
                    ),
                    probatio.Required("transition", default=1): _number_selector(
                        0, 300, step=0.1
                    ),
                    probatio.Required("minimum_change", default=0.1): _number_selector(
                        0, 100000, step="any"
                    ),
                    probatio.Required("minimum_interval", default=5): _number_selector(
                        0, 3600, step=0.5
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_delete_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Delete one configured rule."""
        rules = list(self._options().get(CONF_RULES, []))
        if not rules:
            return self.async_abort(reason="no_rules")
        if user_input is not None:
            selected = user_input["rule_id"]
            return self._create_options_entry(
                {CONF_RULES: [rule for rule in rules if rule["id"] != selected]}
            )

        choices = [
            {"value": rule["id"], "label": rule.get("name", rule["id"])}
            for rule in rules
        ]
        return self.async_show_form(
            step_id="delete_rule",
            data_schema=probatio.Schema(
                {
                    probatio.Required("rule_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=choices)
                    )
                }
            ),
        )
