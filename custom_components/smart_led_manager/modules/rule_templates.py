"""Describe Home Assistant sources supported by the visual rule templates."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import State

NUMERIC_TEMPLATES = {
    "temperature": {"°C", "°F", "K"},
    "humidity": {"%"},
    "power": {"mW", "W", "kW", "MW", "GW", "TW", "BTU/h"},
    "energy": {
        "Wh",
        "kWh",
        "MWh",
        "GWh",
        "TWh",
        "J",
        "kJ",
        "MJ",
        "GJ",
        "cal",
        "kcal",
        "Mcal",
    },
}
STATE_TEMPLATES = {"security", "presence"}
SECURITY_CLASSES = {
    "door",
    "garage_door",
    "window",
    "opening",
    "lock",
    "safety",
    "tamper",
    "smoke",
    "gas",
    "carbon_monoxide",
    "moisture",
}
PRESENCE_CLASSES = {"motion", "occupancy", "presence", "moving"}


def source_template(state: State) -> str | None:
    """Classify by the published device class and exact unit, without conversion."""
    domain = state.entity_id.split(".", 1)[0]
    device_class = state.attributes.get(ATTR_DEVICE_CLASS)
    unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
    if (
        domain == "sensor"
        and isinstance(device_class, str)
        and isinstance(unit, str)
        and unit in NUMERIC_TEMPLATES.get(device_class, ())
    ):
        return device_class
    if domain in {"alarm_control_panel", "lock"}:
        return "security"
    if domain in {"person", "device_tracker"}:
        return "presence"
    if domain == "binary_sensor" and isinstance(device_class, str):
        if device_class in SECURITY_CLASSES:
            return "security"
        if device_class in PRESENCE_CLASSES:
            return "presence"
    return None


def template_source_error(state: State | None, rule: Mapping[str, Any]) -> str | None:
    """Validate a normalized template against live Home Assistant metadata."""
    if not rule.get("category"):
        return None
    if state is None or source_template(state) != rule["category"]:
        return "incompatible_template_source"
    if "source_unit" in rule and rule["source_unit"] != state.attributes.get(
        ATTR_UNIT_OF_MEASUREMENT
    ):
        return "rule_unit_changed"
    expected = rule.get("state")
    if rule["category"] in STATE_TEMPLATES and (
        expected in ("", "unknown", "unavailable")
        or (
            state.entity_id.startswith("binary_sensor.")
            and expected not in ("on", "off")
        )
    ):
        return "invalid_template_state"
    return None
