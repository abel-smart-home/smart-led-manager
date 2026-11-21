"""Config flow for Smart LED Manager."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, override
from uuid import uuid4

import probatio
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_LIGHTS,
    CONF_MANUAL_POLICY,
    CONF_MIN_COMMAND_INTERVAL,
    CONF_RULES,
    CONF_TIE_BREAKER,
    DEFAULT_MANUAL_POLICY,
    DEFAULT_MIN_COMMAND_INTERVAL,
    DEFAULT_TIE_BREAKER,
    DOMAIN,
    NAME,
    RULE_TYPE_NUMERIC,
    RULE_TYPE_STATE,
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
    MINOR_VERSION = 1

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
                "settings",
                "add_state_rule",
                "add_numeric_rule",
                "delete_rule",
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
