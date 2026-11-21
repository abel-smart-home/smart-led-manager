"""Linux CI tests against Home Assistant's integration runtime."""

from __future__ import annotations

import asyncio
import sys

import pytest
from homeassistant.components.light import (
    ATTR_SUPPORTED_COLOR_MODES,
    ColorMode,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import (
    ATTR_SUPPORTED_FEATURES,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
)
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant.common import MockConfigEntry

from custom_components.smart_led_manager.const import (
    CONF_LIGHTS,
    CONF_MANUAL_POLICY,
    CONF_MIN_COMMAND_INTERVAL,
    CONF_RULES,
    CONF_TIE_BREAKER,
    DOMAIN,
    SERVICE_CANCEL,
    SERVICE_NOTIFY,
)

pytestmark = [
    pytest.mark.skipif(
        sys.platform == "win32",
        reason="pytest-homeassistant requires Unix-only fcntl during collection",
    ),
    pytest.mark.usefixtures("enable_custom_integrations"),
]


async def test_config_flow_creates_allowlisted_entry(hass) -> None:
    """The UI flow creates the single entry with safe engine defaults."""
    hass.states.async_set(
        "light.strip",
        STATE_OFF,
        {
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.RGB],
            ATTR_SUPPORTED_FEATURES: 0,
        },
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_LIGHTS: ["light.strip"]},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_LIGHTS: ["light.strip"]}
    assert result["options"][CONF_RULES] == []
    assert result["options"][CONF_TIE_BREAKER] == "newest"
    assert result["options"][CONF_MANUAL_POLICY] == "service_only"
    assert result["options"][CONF_MIN_COMMAND_INTERVAL] > 0


async def test_setup_action_and_unload_lifecycle(hass) -> None:
    """Setup registers actions, applies intent, and unloads runtime tasks."""
    light_calls = []

    async def _record_light_call(call) -> None:
        light_calls.append(call)

    hass.services.async_register("light", SERVICE_TURN_ON, _record_light_call)
    hass.states.async_set(
        "light.strip",
        STATE_OFF,
        {
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.RGB],
            ATTR_SUPPORTED_FEATURES: 0,
        },
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={CONF_LIGHTS: ["light.strip"]},
        options={
            CONF_RULES: [],
            CONF_TIE_BREAKER: "newest",
            CONF_MIN_COMMAND_INTERVAL: 0,
            CONF_MANUAL_POLICY: "service_only",
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.services.has_service(DOMAIN, SERVICE_NOTIFY)
    assert entry.entry_id in hass.data[DOMAIN]["entries"]

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_NOTIFY,
        {
            "request_id": "notice:test",
            "targets": ["light.strip"],
            "rgb_color": [20, 40, 60],
            "animation": "fixed",
            "duration": 30,
        },
        blocking=True,
        return_response=True,
    )
    assert response["request_id"] == "notice:test"
    assert light_calls
    assert light_calls[-1].data["rgb_color"] == (20, 40, 60)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CANCEL,
        {"request_id": "notice:test"},
        blocking=True,
    )
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.entry_id not in hass.data[DOMAIN]["entries"]


async def test_unload_cancels_animation_listeners_and_late_commands(hass) -> None:
    """An active animation cannot outlive entry unload."""
    light_calls = []
    first_frame = asyncio.Event()

    async def _record_light_call(call) -> None:
        light_calls.append(call)
        first_frame.set()

    hass.services.async_register("light", SERVICE_TURN_ON, _record_light_call)
    hass.services.async_register("light", SERVICE_TURN_OFF, _record_light_call)
    hass.states.async_set(
        "light.strip",
        STATE_OFF,
        {
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.RGB],
            ATTR_SUPPORTED_FEATURES: 0,
        },
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{DOMAIN}-unload",
        data={CONF_LIGHTS: ["light.strip"]},
        options={
            CONF_RULES: [],
            CONF_TIE_BREAKER: "newest",
            CONF_MIN_COMMAND_INTERVAL: 0,
            CONF_MANUAL_POLICY: "service_only",
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = entry.runtime_data
    assert coordinator._unsub_lights is not None
    assert coordinator._listeners

    await hass.services.async_call(
        DOMAIN,
        SERVICE_NOTIFY,
        {
            "request_id": "notice:unload",
            "targets": ["light.strip"],
            "rgb_color": [255, 128, 0],
            "animation": "blink",
            "period": 0.5,
            "duration": 60,
        },
        blocking=True,
        return_response=True,
    )
    await asyncio.wait_for(first_frame.wait(), timeout=1)
    assert "light.strip" in coordinator.animations.active_targets
    assert coordinator.expiry.deadline is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    calls_after_unload = len(light_calls)
    await asyncio.sleep(0.3)

    assert len(light_calls) == calls_after_unload
    assert coordinator.animations.active_targets == frozenset()
    assert coordinator.controller.pending_targets == frozenset()
    assert coordinator.expiry.deadline is None
    assert coordinator._recovery_tasks == {}
    assert coordinator._unsub_lights is None
    assert coordinator._listeners == set()
    assert coordinator.status == "stopped"


async def test_options_flow_adds_and_deletes_graphical_rules(hass) -> None:
    """The native options UI owns state and numeric rule lifecycle."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={CONF_LIGHTS: ["light.strip"]},
        options={
            CONF_RULES: [],
            CONF_TIE_BREAKER: "newest",
            CONF_MIN_COMMAND_INTERVAL: 0.75,
            CONF_MANUAL_POLICY: "service_only",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert "add_state_rule" in result["menu_options"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_state_rule"}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": "Puerta abierta",
            "source": "binary_sensor.door",
            "operator": "equals",
            "state": "on",
            "targets": ["light.strip"],
            "priority": 65,
            "rgb_color": [255, 0, 0],
            "brightness": 200,
            "transition": 0,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    state_rule = result["data"][CONF_RULES][0]
    assert state_rule["type"] == "state"
    assert state_rule["targets"] == ["light.strip"]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_numeric_rule"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": "Temperatura",
            "source": "sensor.temperature",
            "targets": ["light.strip"],
            "priority": 40,
            "points": "18:0,0,255;28:255,0,0",
            "mode": "interpolate",
            "brightness": 180,
            "transition": 1,
            "minimum_change": 0.5,
            "minimum_interval": 5,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    rules = result["data"][CONF_RULES]
    assert len(rules) == 2
    assert rules[1]["type"] == "numeric"
    assert rules[1]["points"][0] == {"value": 18.0, "rgb": [0, 0, 255]}

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "delete_rule"}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"rule_id": state_rule["id"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert [rule["type"] for rule in result["data"][CONF_RULES]] == ["numeric"]
