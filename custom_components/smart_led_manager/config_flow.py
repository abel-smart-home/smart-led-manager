"""Config flow for Smart LED Manager."""

from __future__ import annotations

import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Any, override
from uuid import uuid4

import probatio
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_AREA_ID,
    CONF_LIGHTS,
    CONF_MANUAL_POLICY,
    CONF_MIN_COMMAND_INTERVAL,
    CONF_MODES,
    CONF_RULES,
    CONF_SHOW_SIDEBAR,
    CONF_TIE_BREAKER,
    CONF_ZONES,
    DEFAULT_MANUAL_POLICY,
    DEFAULT_MIN_COMMAND_INTERVAL,
    DEFAULT_SHOW_SIDEBAR,
    DEFAULT_TIE_BREAKER,
    DOMAIN,
    NAME,
    RULE_TYPE_EVENT,
    RULE_TYPE_NUMERIC,
    RULE_TYPE_STATE,
)
from .core.color import normalize_color_points
from .core.conditions import WEEKDAYS
from .modules.admin_configuration import (
    validate_managed_lights,
    validate_mode,
    validate_zone,
    validate_zone_removal,
)
from .modules.configuration import options_revision
from .modules.modes import ModeDefinition, ModeValidationError, ZoneDefinition
from .modules.native_rule_controls import (
    RuleStateSelector,
    native_condition_form,
    native_condition_tree,
    native_trigger,
    selector_clock,
)
from .modules.rule_schema import RuleValidationError, normalize_rule
from .modules.rule_templates import template_source_error
from .modules.targeting import (
    AdvancedTargetError,
    AdvancedTargetResolver,
    is_aggregate_light,
)

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
_NUMERIC_SOURCE_DOMAINS = ["counter", "input_number", "number", "sensor"]
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
    return normalize_color_points(raw, minimum=minimum)


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
            elif any(is_aggregate_light(self.hass, light) for light in lights):
                errors[CONF_LIGHTS] = "group_not_authorized"
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
        self._initial_revision: str | None = None

    def _capture_revision(self) -> None:
        revision = options_revision(self.config_entry.options)
        if self._initial_revision is None:
            self._initial_revision = revision

    def _options(self) -> dict[str, Any]:
        """Return a mutable copy of all current options."""
        self._capture_revision()
        return deepcopy(dict(self.config_entry.options))

    def _lights(self) -> list[str]:
        """Return currently managed lights."""
        self._capture_revision()
        return list(
            self.config_entry.options.get(
                CONF_LIGHTS, self.config_entry.data.get(CONF_LIGHTS, [])
            )
        )

    def _zones(self) -> list[dict[str, Any]]:
        """Return configured zone definitions."""
        self._capture_revision()
        return deepcopy(list(self.config_entry.options.get(CONF_ZONES, [])))

    def _modes(self) -> list[dict[str, Any]]:
        """Return configured mode definitions."""
        self._capture_revision()
        return deepcopy(list(self.config_entry.options.get(CONF_MODES, [])))

    def _rules(self) -> list[dict[str, Any]]:
        """Return configured rule definitions."""
        self._capture_revision()
        return deepcopy(list(self.config_entry.options.get(CONF_RULES, [])))

    def _create_options_entry(self, updates: dict[str, Any]) -> ConfigFlowResult:
        """Merge options so one flow step never discards unrelated settings."""
        if (
            self._initial_revision is not None
            and options_revision(self.config_entry.options) != self._initial_revision
        ):
            return self.async_abort(reason="configuration_changed")
        options = self._options()
        options.update(updates)
        result = self.async_create_entry(data=options)
        # A successful options entry terminates this flow. Clearing the token
        # also keeps direct unit-level reuse from treating a later operation as
        # the same stale form; a real new flow captures a fresh revision.
        self._initial_revision = None
        return result

    @override
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the native management menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "admin_center",
                "lights",
                "zones",
                "modes",
                "rules",
                "advanced",
            ],
        )

    async def async_step_admin_center(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure access to the local administration center."""
        if user_input is not None:
            return self._create_options_entry(
                {CONF_SHOW_SIDEBAR: bool(user_input[CONF_SHOW_SIDEBAR])}
            )
        return self.async_show_form(
            step_id="admin_center",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_SHOW_SIDEBAR,
                        default=self.config_entry.options.get(
                            CONF_SHOW_SIDEBAR, DEFAULT_SHOW_SIDEBAR
                        ),
                    ): selector.BooleanSelector()
                }
            ),
            description_placeholders={"path": "/smart-led-manager-editor"},
        )

    async def async_step_lights(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the physical lights this integration may control."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                lights = validate_managed_lights(
                    self.hass,
                    self._lights(),
                    user_input[CONF_LIGHTS],
                    self._zones(),
                    self._rules(),
                )
            except ModeValidationError as err:
                errors[CONF_LIGHTS] = err.key
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
                "open_visual_editor",
                "add_state_rule",
                "add_numeric_rule",
                "add_event_rule",
                "edit_rule",
                "duplicate_rule",
                "toggle_rule",
                "delete_rule",
            ],
        )

    async def async_step_open_visual_editor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer the supported internal route without private navigation APIs."""
        if user_input is not None:
            return await self.async_step_rules()
        return self.async_show_form(
            step_id="open_visual_editor",
            data_schema=probatio.Schema({}),
            description_placeholders={
                "path": "/smart-led-manager-editor",
            },
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
            try:
                validate_zone_removal(zone_id, self._modes(), self._rules())
            except ModeValidationError as err:
                errors["base"] = err.key
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
        validate_zone(self.hass, zone, self._lights(), self._zones(), self._modes())
        return zone

    def _validated_mode(
        self, user_input: dict[str, Any], mode_id: str
    ) -> ModeDefinition:
        mode = ModeDefinition.from_dict({**user_input, "mode_id": mode_id})
        validate_mode(mode, self._zones(), self._modes())
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

    async def async_step_add_event_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a one-shot rule backed by an official Home Assistant trigger."""

        self._rule_operation = "add"
        current = {
            "id": uuid4().hex,
            "type": RULE_TYPE_EVENT,
            "enabled": True,
            "trigger": {"platform": "event", "event_type": ""},
        }
        return await self._event_rule_form("add_event_rule", current, user_input)

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
        if rule.get("type") == RULE_TYPE_EVENT:
            return await self.async_step_edit_event_rule()
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
        if rule.get("type") == RULE_TYPE_EVENT:
            return await self.async_step_duplicate_event_rule()
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

    async def async_step_edit_event_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit an event rule while preserving its stable identifier."""

        current = self._editable_rule()
        if current is None:
            return self.async_abort(reason="rule_not_found")
        return await self._event_rule_form("edit_event_rule", current, user_input)

    async def async_step_duplicate_event_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create a disabled event-rule copy with a new identifier."""

        current = self._editable_rule()
        if current is None:
            return self.async_abort(reason="rule_not_found")
        return await self._event_rule_form("duplicate_event_rule", current, user_input)

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
            error = self._rule_targets_error(user_input)
            if error is not None:
                errors["targets"] = error
            else:
                try:
                    rule = self._prepare_rule_input(user_input, current)
                except RuleValidationError as err:
                    errors["base"] = err.code
                else:
                    if self._rule_operation == "duplicate":
                        rule["enabled"] = False
                    rule.update({"id": current["id"], "type": RULE_TYPE_STATE})
                    return self._save_rule(rule)
        return self.async_show_form(
            step_id=step_id,
            data_schema=self._state_rule_schema(
                current, include_enabled=self._rule_operation != "duplicate"
            ),
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
            error = self._rule_targets_error(user_input)
            if error is not None:
                errors["targets"] = error
            else:
                try:
                    submitted = self._prepare_rule_input(user_input, current)
                except RuleValidationError as err:
                    return self.async_show_form(
                        step_id=step_id,
                        data_schema=self._numeric_rule_schema(
                            current, include_enabled=self._rule_operation != "duplicate"
                        ),
                        errors={"base": err.code},
                    )
                if self._rule_operation == "duplicate":
                    submitted["enabled"] = False
                if submitted.get("mode") == "fixed":
                    submitted["mode"] = "interpolate"
                    return self._save_rule(
                        {**submitted, "id": current["id"], "type": RULE_TYPE_NUMERIC}
                    )
                self._numeric_rule_draft = {
                    **submitted,
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
            data_schema=self._numeric_rule_schema(
                current, include_enabled=self._rule_operation != "duplicate"
            ),
            errors=errors,
        )

    def _state_rule_schema(
        self, current: Mapping[str, Any], *, include_enabled: bool = True
    ) -> probatio.Schema:
        fields: dict[Any, Any] = {
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
            ): RuleStateSelector(
                selector.StateSelectorConfig(
                    hide_states=["unknown", "unavailable"],
                )
            ),
            probatio.Required(
                "targets", default=self._current_rule_entities(current)
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
        }
        if include_enabled:
            fields[
                probatio.Required("enabled", default=self._rule_enabled(current))
            ] = selector.BooleanSelector()
        self._add_advanced_rule_fields(fields, current)
        return probatio.Schema(fields)

    def _numeric_rule_schema(
        self, current: Mapping[str, Any], *, include_enabled: bool = True
    ) -> probatio.Schema:
        fields: dict[Any, Any] = {
            probatio.Required(
                "name", default=current.get("name", "")
            ): selector.TextSelector(),
            probatio.Required(
                "source", default=current.get("source", "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=_NUMERIC_SOURCE_DOMAINS)
            ),
            probatio.Required(
                "targets", default=self._current_rule_entities(current)
            ): _light_selector(entities=self._lights()),
            probatio.Required(
                "priority", default=current.get("priority", 40)
            ): _number_selector(0, 100),
            probatio.Required(
                "mode",
                default=(
                    "fixed"
                    if current.get("rgb_color") is not None
                    and not current.get("points")
                    else current.get("mode", "interpolate")
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["interpolate", "ranges", "fixed"],
                    translation_key="numeric_mode",
                )
            ),
            probatio.Optional(
                "rgb_color", default=current.get("rgb_color", [0, 0, 255])
            ): selector.ColorRGBSelector(),
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
        }
        if include_enabled:
            fields[
                probatio.Required("enabled", default=self._rule_enabled(current))
            ] = selector.BooleanSelector()
        activation = current.get("activation") or {}
        fields[
            probatio.Optional(
                "activation_operator", default=activation.get("operator", "none")
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=["none", "above", "below", "inside", "outside"],
                translation_key="activation_operator",
            )
        )
        for field in ("threshold", "lower", "upper", "hysteresis"):
            key = "activation_" + field
            marker = (
                probatio.Optional(key, default=activation[field])
                if field in activation
                else probatio.Optional(key)
            )
            fields[marker] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX, step="any"
                )
            )
        self._add_advanced_rule_fields(fields, current)
        return probatio.Schema(fields)

    async def _event_rule_form(
        self,
        step_id: str,
        current: dict[str, Any],
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            error = self._rule_targets_error(user_input)
            if error is not None:
                errors["targets"] = error
            else:
                try:
                    rule = self._prepare_rule_input(user_input, current)
                    if self._rule_operation == "duplicate":
                        rule["enabled"] = False
                    rule.update({"id": current["id"], "type": RULE_TYPE_EVENT})
                    normalized = self._validated_rule(rule)
                    from homeassistant.helpers import trigger as trigger_helper

                    await trigger_helper.async_validate_trigger_config(
                        self.hass, [dict(normalized["trigger"])]
                    )
                except (
                    RuleValidationError,
                    AdvancedTargetError,
                    ValueError,
                    probatio.Invalid,
                ):
                    errors["base"] = "invalid_rule"
                else:
                    return self._save_rule(normalized)
        return self.async_show_form(
            step_id=step_id,
            data_schema=self._event_rule_schema(
                current, include_enabled=self._rule_operation != "duplicate"
            ),
            errors=errors,
        )

    def _event_rule_schema(
        self, current: Mapping[str, Any], *, include_enabled: bool = True
    ) -> probatio.Schema:
        fields: dict[Any, Any] = {
            probatio.Required(
                "name", default=current.get("name", "")
            ): selector.TextSelector(),
            probatio.Required(
                "trigger",
                default=(
                    [current["trigger"]]
                    if current.get("trigger", {}).get("event_type", True)
                    else []
                ),
            ): selector.TriggerSelector(),
            probatio.Required(
                "targets", default=self._current_rule_entities(current)
            ): _light_selector(entities=self._lights()),
            probatio.Required(
                "priority", default=current.get("priority", 70)
            ): _number_selector(0, 100),
            probatio.Required(
                "rgb_color", default=current.get("rgb_color", [255, 128, 0])
            ): selector.ColorRGBSelector(),
            probatio.Required(
                "brightness", default=current.get("brightness", 255)
            ): _number_selector(1, 255),
            probatio.Required(
                "transition", default=current.get("transition", 0)
            ): _number_selector(0, 300, step=0.1),
            probatio.Required(
                "duration", default=current.get("duration", 5)
            ): _number_selector(0.1, 86400, step=0.1),
        }
        if include_enabled:
            fields[
                probatio.Required("enabled", default=self._rule_enabled(current))
            ] = selector.BooleanSelector()
        self._add_advanced_rule_fields(fields, current, include_dwell=False)
        return probatio.Schema(fields)

    def _add_advanced_rule_fields(
        self,
        fields: dict[Any, Any],
        current: Mapping[str, Any],
        *,
        include_dwell: bool = True,
    ) -> None:
        selection = current.get("target_selection")
        selection = selection if isinstance(selection, Mapping) else {}
        zone_options = self._zone_choices()
        fields[
            probatio.Optional("target_zones", default=list(selection.get("zones", [])))
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(options=zone_options, multiple=True)
        )
        fields[
            probatio.Optional("target_areas", default=list(selection.get("areas", [])))
        ] = selector.AreaSelector(selector.AreaSelectorConfig(multiple=True))
        fields[
            probatio.Optional(
                "target_labels", default=list(selection.get("labels", []))
            )
        ] = selector.LabelSelector(selector.LabelSelectorConfig(multiple=True))
        fields[
            probatio.Optional(
                "target_groups", default=list(selection.get("groups", []))
            )
        ] = _light_selector()
        fields[
            probatio.Required(
                "all_managed", default=bool(selection.get("all_managed", False))
            )
        ] = selector.BooleanSelector()
        try:
            conditions = native_condition_form(current.get("conditions"))
        except (RuleValidationError, KeyError, TypeError):
            fields[probatio.Optional("conditions_preserved", default=True)] = (
                selector.BooleanSelector(selector.BooleanSelectorConfig(read_only=True))
            )
        else:
            fields[probatio.Optional("conditions", default=conditions)] = (
                selector.ConditionSelector()
            )
        schedule = current.get("schedule") or {}
        fields[probatio.Optional("schedule_enabled", default=bool(schedule))] = (
            selector.BooleanSelector()
        )
        fields[
            probatio.Optional("schedule_after", default=schedule.get("after", "00:00"))
        ] = selector.TimeSelector()
        fields[
            probatio.Optional(
                "schedule_before", default=schedule.get("before", "00:00")
            )
        ] = selector.TimeSelector()
        fields[
            probatio.Optional(
                "schedule_days", default=schedule.get("weekdays", list(WEEKDAYS))
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=list(WEEKDAYS), multiple=True, translation_key="rule_weekdays"
            )
        )
        if include_dwell:
            fields[
                probatio.Optional(
                    "dwell", default={"seconds": current.get("for_seconds", 0)}
                )
            ] = selector.DurationSelector(
                selector.DurationSelectorConfig(enable_day=True)
            )
        fields[
            probatio.Required("animation", default=current.get("animation", "fixed"))
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=["fixed", "blink", "pulse"],
                translation_key="mode_animation",
            )
        )
        fields[probatio.Required("period", default=current.get("period", 1))] = (
            _number_selector(0.1, 3600, step=0.1)
        )

    def _prepare_rule_input(
        self, user_input: Mapping[str, Any], current: Mapping[str, Any]
    ) -> dict[str, Any]:
        rule = {
            key: current[key]
            for key in ("category", "source_unit", "release_seconds")
            if key in current
        }
        rule.update(user_input)
        rule.pop("conditions_preserved", None)
        conditions = rule.get("conditions")
        if isinstance(conditions, list):
            condition_tree = native_condition_tree(conditions)
            stored = current.get("conditions")
            if stored and condition_tree == native_condition_tree(
                native_condition_form(stored)
            ):
                condition_tree = stored
            rule["conditions"] = condition_tree
        elif "conditions" not in rule and current.get("conditions"):
            rule["conditions"] = current["conditions"]
        enabled = rule.pop("schedule_enabled", None)
        after = selector_clock(rule.pop("schedule_after", "00:00"))
        before = selector_clock(rule.pop("schedule_before", "00:00"))
        days = rule.pop("schedule_days", list(WEEKDAYS))
        if enabled is not None:
            rule["schedule"] = (
                {"after": after, "before": before, "weekdays": days}
                if enabled
                else None
            )
        elif "schedule" not in rule and current.get("schedule"):
            rule["schedule"] = current["schedule"]
        if (dwell := rule.pop("dwell", None)) is not None:
            factors = {
                "days": 86400,
                "hours": 3600,
                "minutes": 60,
                "seconds": 1,
                "milliseconds": 0.001,
            }
            rule["for_seconds"] = sum(
                float(dwell.get(key, 0)) * factor for key, factor in factors.items()
            )
        operator = rule.pop("activation_operator", None)
        activation = {
            key: rule.pop("activation_" + key)
            for key in ("threshold", "lower", "upper", "hysteresis")
            if "activation_" + key in rule
        }
        if operator is not None:
            rule["activation"] = (
                {"operator": operator, **activation} if operator != "none" else None
            )
        elif current.get("activation") and "activation" not in rule:
            rule["activation"] = current["activation"]
        if "trigger" in rule:
            rule["trigger"] = native_trigger(rule["trigger"])
        zones = list(rule.pop("target_zones", []))
        areas = list(rule.pop("target_areas", []))
        labels = list(rule.pop("target_labels", []))
        groups = list(rule.pop("target_groups", []))
        all_managed = bool(rule.pop("all_managed", False))
        if zones or areas or labels or groups or all_managed:
            rule["target_selection"] = {
                "entities": list(rule.pop("targets", [])),
                "zones": zones,
                "areas": areas,
                "labels": labels,
                "groups": groups,
                "all_managed": all_managed,
            }
        return rule

    @staticmethod
    def _current_rule_entities(current: Mapping[str, Any]) -> list[str]:
        selection = current.get("target_selection")
        if isinstance(selection, Mapping):
            entities = selection.get("entities", [])
            if isinstance(entities, list):
                return list(entities)
        return list(current.get("targets", []))

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
        try:
            saved = self._validated_rule(rule)
        except (RuleValidationError, AdvancedTargetError, ValueError) as err:
            return self.async_abort(reason=getattr(err, "code", "invalid_rule"))
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

    def _validated_rule(self, rule: Mapping[str, Any]) -> dict[str, Any]:
        normalized = normalize_rule(rule)
        if normalized.get("category") and (
            issue := template_source_error(
                self.hass.states.get(normalized["source"]), normalized
            )
        ):
            raise RuleValidationError(
                issue, "Review the source in the administration panel"
            )
        AdvancedTargetResolver(
            self.hass, self._lights(), self._zones(), audit=False
        ).resolve_rule(normalized)
        return normalized

    def _rule_targets_error(self, user_input: Mapping[str, Any]) -> str | None:
        targets = user_input.get("targets")
        has_indirect = any(
            user_input.get(key)
            for key in (
                "target_zones",
                "target_areas",
                "target_labels",
                "target_groups",
                "all_managed",
            )
        )
        if not targets and not has_indirect:
            return "at_least_one_target"
        if targets and not set(targets).issubset(self._lights()):
            return "target_not_managed"
        return None

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
