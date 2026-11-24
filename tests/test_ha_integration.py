"""Linux CI tests against Home Assistant's integration runtime."""

from __future__ import annotations

import asyncio
import sys

import pytest
from homeassistant.components import frontend
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
    STATE_ON,
)
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.translation import async_get_translations
from pytest_homeassistant.common import MockConfigEntry

from custom_components.smart_led_manager.const import (
    CONF_AREA_ID,
    CONF_LIGHTS,
    CONF_MANUAL_POLICY,
    CONF_MIN_COMMAND_INTERVAL,
    CONF_MODES,
    CONF_RULES,
    CONF_TIE_BREAKER,
    CONF_ZONES,
    DOMAIN,
    SERVICE_CANCEL,
    SERVICE_NOTIFY,
)
from custom_components.smart_led_manager.registry import (
    central_device_identifier,
    mode_switch_unique_id,
    zone_device_identifier,
    zone_select_unique_id,
)
from custom_components.smart_led_manager.visual_editor import PANEL_PATH

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
    assert result["options"][CONF_ZONES] == []
    assert result["options"][CONF_MODES] == []
    assert result["options"][CONF_TIE_BREAKER] == "newest"
    assert result["options"][CONF_MANUAL_POLICY] == "service_only"
    assert result["options"][CONF_MIN_COMMAND_INTERVAL] > 0


@pytest.mark.parametrize("language", ["es", "es-419"])
async def test_spanish_options_flow_translations_load(hass, language: str) -> None:
    """Home Assistant loads both supported Spanish catalogs without fallback."""
    translations = await async_get_translations(
        hass,
        language,
        "options",
        {DOMAIN},
    )

    prefix = f"component.{DOMAIN}.options.step.init"
    assert translations[f"{prefix}.title"] == "Administrar Smart LED Manager"
    assert translations[f"{prefix}.menu_options.lights"] == "Luces administradas"
    assert translations[f"{prefix}.menu_options.modes"] == "Modos de iluminación"


async def test_saving_options_keeps_registered_panel_across_real_entry_reload(
    hass,
) -> None:
    """Exercise the Core ConfigEntry update listener and real panel registry."""
    panels = hass.data.setdefault(frontend.DATA_PANELS, {})
    hass.states.async_set("light.strip", STATE_OFF)
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_LIGHTS: ["light.strip"]}, minor_version=2
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert panels[PANEL_PATH].require_admin
    first_panel = panels[PANEL_PATH]
    first_runtime = entry.runtime_data
    updates = []
    remove_listener = hass.bus.async_listen(
        frontend.EVENT_PANELS_UPDATED, lambda _: updates.append(PANEL_PATH in panels)
    )
    try:
        assert hass.config_entries.async_update_entry(
            entry, options={CONF_RULES: [], CONF_TIE_BREAKER: "oldest"}
        )
        await hass.async_block_till_done()
        assert entry.runtime_data is not first_runtime
        assert panels[PANEL_PATH] is first_panel
        assert False not in updates
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert PANEL_PATH not in panels
    finally:
        remove_listener()


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
    assert "rules" in result["menu_options"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "rules"}
    )
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
            "enabled": True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    state_rule = result["data"][CONF_RULES][0]
    assert state_rule["type"] == "state"
    assert state_rule["targets"] == ["light.strip"]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "rules"}
    )
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
            "mode": "interpolate",
            "brightness": 180,
            "transition": 1,
            "minimum_change": 0.5,
            "minimum_interval": 5,
            "enabled": True,
        },
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "numeric_points"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "save_numeric_rule"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    rules = result["data"][CONF_RULES]
    assert len(rules) == 2
    assert rules[1]["type"] == "numeric"
    assert rules[1]["points"][0] == {"value": 16.0, "rgb": [0, 0, 255]}

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "rules"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "delete_rule"}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"rule_id": state_rule["id"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert [rule["type"] for rule in result["data"][CONF_RULES]] == ["numeric"]


async def test_rule_edit_and_delete_reload_rebuilds_only_current_intent(hass) -> None:
    """Reload waits for the old catalog and reconstructs only saved rules."""
    light_calls = []

    async def _record_light_call(call) -> None:
        light_calls.append(call)

    hass.services.async_register("light", SERVICE_TURN_ON, _record_light_call)
    for entity_id in ("light.one", "light.two"):
        hass.states.async_set(
            entity_id,
            STATE_OFF,
            {
                ATTR_SUPPORTED_COLOR_MODES: [ColorMode.RGB],
                ATTR_SUPPORTED_FEATURES: 0,
            },
        )
    hass.states.async_set("binary_sensor.door", STATE_ON)
    original = {
        "id": "door",
        "type": "state",
        "name": "Puerta",
        "source": "binary_sensor.door",
        "operator": "equals",
        "state": STATE_ON,
        "targets": ["light.one"],
        "priority": 40,
        "rgb_color": [0, 0, 255],
        "brightness": 200,
        "transition": 0,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{DOMAIN}-rule-reload",
        data={CONF_LIGHTS: ["light.one", "light.two"]},
        options={
            CONF_RULES: [original],
            CONF_TIE_BREAKER: "newest",
            CONF_MIN_COMMAND_INTERVAL: 0,
            CONF_MANUAL_POLICY: "service_only",
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    old_runtime = entry.runtime_data
    assert (
        await old_runtime.engine.async_winner("light.one")
    ).request_id == "rule:door"

    edited = {
        **original,
        "targets": ["light.two"],
        "priority": 70,
        "rgb_color": [255, 0, 0],
    }
    hass.config_entries.async_update_entry(
        entry,
        options={**dict(entry.options), CONF_RULES: [edited]},
    )
    await hass.async_block_till_done()
    current_runtime = entry.runtime_data

    assert current_runtime is not old_runtime
    assert old_runtime.status == "stopped"
    assert old_runtime.rules._tasks == set()
    assert await current_runtime.engine.async_winner("light.one") is None
    winner = await current_runtime.engine.async_winner("light.two")
    assert winner.request_id == "rule:door"
    assert winner.priority == 70
    assert winner.command.color == (255, 0, 0)
    assert light_calls[-1].data["rgb_color"] == (255, 0, 0)

    hass.config_entries.async_update_entry(
        entry,
        options={**dict(entry.options), CONF_RULES: []},
    )
    await hass.async_block_till_done()

    assert await entry.runtime_data.engine.async_requests() == ()


async def test_options_flow_creates_zone_and_mode_definitions(hass) -> None:
    """Zones and modes are created through native, validated option forms."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{DOMAIN}-modes",
        data={CONF_LIGHTS: ["light.one", "light.two"]},
        options={
            CONF_RULES: [],
            CONF_ZONES: [],
            CONF_MODES: [],
            CONF_TIE_BREAKER: "newest",
            CONF_MIN_COMMAND_INTERVAL: 0.75,
            CONF_MANUAL_POLICY: "service_only",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "zones"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_zone"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"name": "Sala", "targets": ["light.one", "light.two"]},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    zone = result["data"][CONF_ZONES][0]
    assert zone["name"] == "Sala"
    assert zone["targets"] == ["light.one", "light.two"]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "modes"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_mode"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "zone_id": zone["zone_id"],
            "name": "Lectura",
            "targets": ["light.one"],
            "priority": 50,
            "rgb_color": [255, 180, 80],
            "brightness": 160,
            "transition": 1,
            "allow_turn_on": True,
            "animation": "fixed",
            "period": 1,
            "expose_switch": True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    mode = result["data"][CONF_MODES][0]
    assert mode["zone_id"] == zone["zone_id"]
    assert mode["name"] == "Lectura"
    assert mode["rgb_color"] == [255, 180, 80]
    assert mode["expose_switch"] is True


async def test_alpha2_entities_migrate_to_stable_zone_devices(hass) -> None:
    """Existing entity IDs and custom names survive their device reassociation."""
    hass.states.async_set(
        "light.one",
        STATE_OFF,
        {
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.RGB],
            ATTR_SUPPORTED_FEATURES: 0,
        },
    )
    area = ar.async_get(hass).async_create("Sala")
    zone = {
        "zone_id": "living",
        "name": "Sala",
        "targets": ["light.one"],
        CONF_AREA_ID: area.id,
    }
    mode = {
        "mode_id": "cinema",
        "zone_id": "living",
        "name": "Cine",
        "targets": ["light.one"],
        "priority": 50,
        "rgb_color": [0, 0, 255],
        "brightness": 180,
        "transition": 1,
        "allow_turn_on": True,
        "animation": "fixed",
        "period": 1,
        "expose_switch": True,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{DOMAIN}-alpha2-migration",
        minor_version=1,
        data={CONF_LIGHTS: ["light.one"]},
        options={
            CONF_RULES: [],
            CONF_ZONES: [zone],
            CONF_MODES: [mode],
            CONF_TIE_BREAKER: "newest",
            CONF_MIN_COMMAND_INTERVAL: 0,
            CONF_MANUAL_POLICY: "service_only",
        },
    )
    entry.add_to_hass(hass)
    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    central = devices.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={central_device_identifier(entry.entry_id)},
        name="Smart LED Manager",
    )
    old_select = entities.async_get_or_create(
        "select",
        DOMAIN,
        zone_select_unique_id(entry.entry_id, "living"),
        config_entry=entry,
        device_id=central.id,
        original_name="Modo de Sala",
    )
    old_switch = entities.async_get_or_create(
        "switch",
        DOMAIN,
        mode_switch_unique_id(entry.entry_id, "cinema"),
        config_entry=entry,
        device_id=central.id,
        original_name="Cine",
    )
    entities.async_update_entity(old_switch.entity_id, name="Cine personalizado")

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    migrated_select = entities.async_get(old_select.entity_id)
    migrated_switch = entities.async_get(old_switch.entity_id)
    zone_device = devices.async_get_device_by_identifier(
        zone_device_identifier(entry.entry_id, "living"), entry.entry_id
    )
    central_device = devices.async_get_device_by_identifier(
        central_device_identifier(entry.entry_id), entry.entry_id
    )
    assert zone_device is not None
    assert central_device is not None
    assert zone_device.name == "Sala"
    assert zone_device.area_id == area.id
    assert migrated_select is not None
    assert migrated_switch is not None
    assert migrated_select.entity_id == old_select.entity_id
    assert migrated_switch.entity_id == old_switch.entity_id
    assert migrated_select.device_id == zone_device.id
    assert migrated_switch.device_id == zone_device.id
    assert migrated_switch.name == "Cine personalizado"
    assert (
        entities.async_get_entity_id(
            "sensor", DOMAIN, f"{entry.entry_id}_engine_status"
        )
        is not None
    )
    sensor_id = entities.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_engine_status"
    )
    assert entities.async_get(sensor_id).device_id == central_device.id
    assert (
        len(
            [
                item
                for item in er.async_entries_for_config_entry(entities, entry.entry_id)
                if item.unique_id == old_select.unique_id
            ]
        )
        == 1
    )
