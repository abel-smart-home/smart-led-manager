"""Linux CI tests against Home Assistant's integration runtime."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import timedelta
from unittest.mock import patch

import probatio
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
    STATE_UNAVAILABLE,
)
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service import async_set_service_schema
from homeassistant.helpers.translation import async_get_translations
from homeassistant.setup import async_setup_component
from pytest_homeassistant.common import MockConfigEntry

from custom_components.smart_led_manager.const import (
    CONF_AREA_ID,
    CONF_LIGHTS,
    CONF_MANUAL_POLICY,
    CONF_MIN_COMMAND_INTERVAL,
    CONF_MODES,
    CONF_RULES,
    CONF_SHOW_SIDEBAR,
    CONF_TIE_BREAKER,
    CONF_ZONES,
    DOMAIN,
    SERVICE_CANCEL,
    SERVICE_NOTIFY,
    SERVICE_RUN_NOTICE,
)
from custom_components.smart_led_manager.coordinator import SmartLEDCoordinator
from custom_components.smart_led_manager.models import LightCommand, Request, utc_now
from custom_components.smart_led_manager.modules.configuration import options_revision
from custom_components.smart_led_manager.modules.rules import RuleManager
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
        applied_runtime = entry.runtime_data
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.runtime_data is not applied_runtime
        assert panels[PANEL_PATH] is first_panel
        assert False not in updates
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert PANEL_PATH not in panels
    finally:
        remove_listener()


@pytest.mark.parametrize("setup_succeeds", [True, False])
async def test_editor_confirms_runtime_revision_after_real_reload(
    hass, hass_ws_client, setup_succeeds
) -> None:
    """Read acknowledgements over the actual HA transport during a reload."""
    panels = hass.data.setdefault(frontend.DATA_PANELS, {})
    hass.states.async_set("light.strip", STATE_OFF)
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_LIGHTS: ["light.strip"]}, minor_version=2
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    client = await hass_ws_client()
    panel = panels[PANEL_PATH]
    accepted = asyncio.Event()
    resume = asyncio.Event()
    initialize = SmartLEDCoordinator.async_initialize

    async def initialize_later(coordinator) -> None:
        accepted.set()
        await resume.wait()
        if not setup_succeeds:
            raise RuntimeError("Test setup failure after options were accepted")
        await initialize(coordinator)

    async def command(msg_id, command_type, **data):
        await client.send_json(
            {
                "id": msg_id,
                "type": f"{DOMAIN}/{command_type}",
                "entry_id": entry.entry_id,
                **data,
            }
        )
        return await client.receive_json()

    old_revision = options_revision(entry.options)
    with patch.object(SmartLEDCoordinator, "async_initialize", initialize_later):
        try:
            response = await command(
                1,
                "smart_rules/mutate",
                operation="create",
                mutation_id="stable-request",
                revision=old_revision,
                rule={
                    "type": "state",
                    "name": "Test",
                    "source": "input_boolean.test",
                    "state": "on",
                    "targets": ["light.strip"],
                    "enabled": False,
                },
            )
            assert response["success"]
            new_revision = response["result"]["revision"]
            assert new_revision != old_revision
            await asyncio.wait_for(accepted.wait(), timeout=5)
            assert panels[PANEL_PATH] is panel
            pending = await command(2, "editor/status", mutation_id="stable-request")
            assert pending["result"]["status"] == "reloading"
            assert pending["result"]["revision"] == new_revision
            assert pending["result"]["applied_revision"] != new_revision
            assert (
                pending["result"]["mutation"]["rule"]["id"]
                == response["result"]["rule"]["id"]
            )
            denied = await command(
                3, "smart_rules/mutate", operation="delete", revision=new_revision
            )
            assert denied["error"]["code"] == "entry_not_loaded"
        finally:
            resume.set()
            await hass.async_block_till_done()

    settled = await command(4, "editor/status", mutation_id="stable-request")
    assert settled["result"]["revision"] == new_revision
    assert settled["result"]["status"] == ("ready" if setup_succeeds else "failed")
    assert settled["result"]["applied_revision"] == (
        new_revision if setup_succeeds else None
    )
    assert len(entry.options[CONF_RULES]) == 1
    assert panels[PANEL_PATH] is panel
    await client.close()


async def test_notice_definition_updates_action_schema_and_renews_one_request(
    hass, hass_ws_client
) -> None:
    hass.states.async_set(
        "light.strip", STATE_OFF, {ATTR_SUPPORTED_COLOR_MODES: ["rgb"]}
    )
    # Both actions are test doubles. Supply their metadata so get_services
    # does not import unrelated integration dependencies for real light actions.
    for service in (SERVICE_TURN_ON, SERVICE_TURN_OFF):
        hass.services.async_register("light", service, lambda _call: None)
        async_set_service_schema(hass, "light", service, {})
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_LIGHTS: ["light.strip"]}, minor_version=2
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    client = await hass_ws_client()

    async def options(message_id):
        await client.send_json({"id": message_id, "type": "get_services"})
        response = await client.receive_json()
        assert response["success"], response
        return response["result"][DOMAIN][SERVICE_RUN_NOTICE]["fields"]["notice_id"][
            "selector"
        ]["select"]["options"]

    async def mutate(message_id, operation, **data):
        await client.send_json(
            {
                "id": message_id,
                "type": f"{DOMAIN}/smart_rules/mutate",
                "entry_id": entry.entry_id,
                "revision": options_revision(entry.options),
                "operation": operation,
                **data,
            }
        )
        response = await client.receive_json()
        assert response["success"], response
        await hass.async_block_till_done()
        return response["result"]["rule"]

    async def run(notice_id):
        return await hass.services.async_call(
            DOMAIN,
            SERVICE_RUN_NOTICE,
            {"notice_id": notice_id},
            blocking=True,
            return_response=True,
        )

    assert await options(1) == []
    rule = await mutate(
        2,
        "create",
        rule={
            "type": "notice",
            "name": "Door",
            "targets": ["light.strip"],
            "duration": 15,
            "priority": 70,
            "rgb_color": [255, 80, 0],
        },
    )
    notice_id = rule["id"]
    assert await options(3) == [{"label": "Door", "value": notice_id}]
    now = utc_now()
    with patch(
        "custom_components.smart_led_manager.coordinator.utc_now", return_value=now
    ):
        request = await run(notice_id)
    runtime = entry.runtime_data
    with patch(
        "custom_components.smart_led_manager.coordinator.utc_now",
        return_value=now + timedelta(seconds=2),
    ):
        assert await run(notice_id) == request
    (pending,) = await runtime.engine.async_requests()
    assert pending.expires_at == now + timedelta(seconds=17)
    assert not pending.persistent
    await hass.services.async_call(
        DOMAIN,
        SERVICE_NOTIFY,
        {
            "request_id": "ceiling",
            "targets": ["light.strip"],
            "rgb_color": [0, 0, 255],
            "priority": 100,
            "duration": 60,
        },
        blocking=True,
    )
    assert (await runtime.engine.async_winner("light.strip")).request_id == "ceiling"
    await runtime.engine.async_expire(now + timedelta(seconds=18))
    await runtime.async_cancel("ceiling")
    assert await runtime.engine.async_winner("light.strip") is None
    await mutate(4, "update", rule_id=notice_id, rule={**rule, "name": "Renamed"})
    assert await options(5) == [{"label": "Renamed", "value": notice_id}]
    assert await entry.runtime_data.engine.async_requests() == ()
    assert await run(notice_id) == request
    await mutate(6, "delete", rule_id=notice_id)
    assert await options(7) == []
    assert await entry.runtime_data.engine.async_requests() == ()
    with pytest.raises(ServiceValidationError) as rejected:
        await run(notice_id)
    assert rejected.value.translation_key == "notice_not_found"
    await client.close()


async def test_panel_and_native_preferences_share_revision_and_live_ranking(
    hass, hass_ws_client
) -> None:
    """Apply preferences on both surfaces and read the real engine decisions."""
    panels = hass.data.setdefault(frontend.DATA_PANELS, {})
    for light in ("light.strip", "light.side"):
        hass.states.async_set(light, STATE_UNAVAILABLE)
    rules = [
        {
            "id": "saved-notice",
            "type": "notice",
            "name": "Aviso guardado",
            "targets": ["light.strip"],
            "duration": 3,
        }
    ]
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_LIGHTS: ["light.strip", "light.side"]},
        options={
            CONF_RULES: rules,
            CONF_SHOW_SIDEBAR: False,
            CONF_TIE_BREAKER: "oldest",
            CONF_MANUAL_POLICY: "respect",
            CONF_MIN_COMMAND_INTERVAL: 0.45,
            "apiToken": "sensitive-value-from-options",
        },
        minor_version=2,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    client = await hass_ws_client()
    message_id = 0

    async def command(command_type, **values):
        nonlocal message_id
        message_id += 1
        await client.send_json(
            {
                "id": message_id,
                "type": f"{DOMAIN}/{command_type}",
                "entry_id": entry.entry_id,
                **values,
            }
        )
        return await client.receive_json()

    async def read(command_type):
        response = await command(command_type)
        assert response["success"], response
        return response["result"]

    async def save(kind, item, revision):
        return await command(
            "admin/mutate", kind=kind, operation="save", item=item, revision=revision
        )

    initial = await read("admin/get")
    assert initial["admin"]["preferences"] == {
        CONF_SHOW_SIDEBAR: False,
        CONF_TIE_BREAKER: "oldest",
        CONF_MANUAL_POLICY: "respect",
        CONF_MIN_COMMAND_INTERVAL: 0.45,
    }
    assert panels[PANEL_PATH].sidebar_title is None
    now = utc_now() - timedelta(seconds=10)
    for index, (request_id, targets, priority) in enumerate(
        [
            ("z-early", ["light.strip"], 80),
            ("a-middle", ["light.strip", "light.side"], 80),
            ("y-late", ["light.strip"], 80),
            ("0-low", ["light.strip"], 40),
        ]
    ):
        activated = now + timedelta(seconds=index)
        await entry.runtime_data.async_submit(
            Request(
                request_id=request_id,
                source="test",
                module="scene",
                name=request_id,
                targets=frozenset(targets),
                priority=priority,
                persistent=True,
                command=LightCommand(color=(255, 120, 0)),
                activated_at=activated,
                updated_at=activated,
                metadata={"arbitrary": "sensitive-from-metadata"},
            )
        )
    entry.runtime_data._record_recovery_error(
        "light.side", "test", "sensitive-error-message"
    )
    diagnostics = await read("admin/diagnostics")
    runtime = diagnostics["runtime"]
    assert runtime["winners"] == {"light.strip": "z-early", "light.side": "a-middle"}
    assert runtime["request_decisions"]["a-middle"] == {
        "winning_targets": ["light.side"],
        "masked_targets": ["light.strip"],
    }
    assert runtime["request_decisions"]["0-low"]["masked_targets"] == ["light.strip"]
    assert runtime["last_error"] == {"kind": "recovery_failed", "target": "light.side"}
    assert runtime["history"]
    assert "sensitive-" not in json.dumps(diagnostics)
    assert diagnostics["entry"]["options"]["apiToken"] == "**REDACTED**"

    flow = await hass.config_entries.options.async_init(entry.entry_id)
    native = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"next_step_id": "advanced"}
    )
    assert native["step_id"] == "advanced"
    desired = {
        CONF_TIE_BREAKER: "newest",
        CONF_MANUAL_POLICY: "temporary",
        CONF_MIN_COMMAND_INTERVAL: 1.05,
    }
    invalid = await save(
        "priorities", {**desired, CONF_MIN_COMMAND_INTERVAL: 1.04}, initial["revision"]
    )
    assert invalid["error"]["code"] == "invalid_command_interval"
    changed = await save("priorities", {**desired, CONF_RULES: []}, initial["revision"])
    assert changed["success"], changed
    await hass.async_block_till_done()
    assert entry.runtime_data.options_revision == changed["result"]["revision"]
    assert entry.options[CONF_RULES] == rules
    assert not entry.options[CONF_SHOW_SIDEBAR]
    assert (await read("admin/diagnostics"))["runtime"]["winners"][
        "light.strip"
    ] == "y-late"
    stale_native = await hass.config_entries.options.async_configure(
        flow["flow_id"], desired
    )
    assert stale_native["reason"] == "configuration_changed"
    stale_panel = await save("general", {CONF_SHOW_SIDEBAR: True}, initial["revision"])
    assert stale_panel["error"]["code"] == "conflict"

    native_flow = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        native_flow["flow_id"], {"next_step_id": "advanced"}
    )
    invalid_native = await hass.config_entries.options.async_configure(
        native_flow["flow_id"], {**desired, CONF_MIN_COMMAND_INTERVAL: 1.06}
    )
    assert invalid_native["errors"]["base"] == "invalid_command_interval"
    saved_native = await hass.config_entries.options.async_configure(
        native_flow["flow_id"], {**desired, CONF_TIE_BREAKER: "lexical"}
    )
    assert saved_native["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    current = await read("admin/get")
    assert current["admin"]["preferences"][CONF_TIE_BREAKER] == "lexical"
    assert (await read("admin/diagnostics"))["runtime"]["winners"][
        "light.strip"
    ] == "a-middle"
    general = await save(
        "general",
        {CONF_SHOW_SIDEBAR: True, CONF_TIE_BREAKER: "newest"},
        current["revision"],
    )
    assert general["success"], general
    await hass.async_block_till_done()
    assert panels[PANEL_PATH].sidebar_title == "Smart LED Manager"
    assert entry.options[CONF_TIE_BREAKER] == "lexical"
    assert entry.options[CONF_RULES] == rules
    await client.close()


async def test_template_unit_is_validated_and_persisted_through_the_existing_catalog(
    hass, hass_ws_client
) -> None:
    hass.states.async_set(
        "light.strip", STATE_OFF, {ATTR_SUPPORTED_COLOR_MODES: ["rgb"]}
    )
    hass.states.async_set(
        "sensor.draw", "100", {"device_class": "power", "unit_of_measurement": "W"}
    )
    hass.states.async_set(
        "sensor.total", "2", {"device_class": "energy", "unit_of_measurement": "kWh"}
    )
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_LIGHTS: ["light.strip"]}, minor_version=2
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    client = await hass_ws_client()
    request = {"entry_id": entry.entry_id, "type": f"{DOMAIN}/smart_rules/get"}
    await client.send_json({**request, "id": 1})
    catalog = (await client.receive_json())["result"]
    assert catalog["selections"]["template_sources"] == {
        "sensor.draw": "power",
        "sensor.total": "energy",
    }
    rule = {
        "name": "Power",
        "type": "numeric",
        "category": "power",
        "source": "sensor.draw",
        "source_unit": "kW",
        "enabled": False,
        "targets": ["light.strip"],
        "points": [
            {"value": 0, "rgb": [0, 0, 255]},
            {"value": 400, "rgb": [255, 0, 0]},
        ],
        "activation": {"operator": "above", "threshold": 10, "hysteresis": 2},
    }
    mutate = {
        **request,
        "type": f"{DOMAIN}/smart_rules/mutate",
        "operation": "create",
        "revision": catalog["revision"],
    }
    await client.send_json({**mutate, "id": 2, "rule": rule})
    assert (await client.receive_json())["error"]["code"] == "rule_unit_changed"
    assert not entry.options.get(CONF_RULES)
    rule["source_unit"] = "W"
    await client.send_json({**mutate, "id": 3, "rule": rule})
    saved = (await client.receive_json())["result"]
    await hass.async_block_till_done()
    assert entry.runtime_data.options_revision == saved["revision"]
    await client.send_json({**request, "id": 4})
    (persisted,) = (await client.receive_json())["result"]["rules"]
    assert persisted["category"] == "power"
    assert persisted["rule"]["id"] == saved["rule"]["id"]
    assert persisted["rule"]["source_unit"] == "W"
    assert persisted["rule"]["activation"]["hysteresis"] == 2
    await client.close()


async def test_admin_center_reuses_config_entry_and_exclusive_mode_engine(
    hass, hass_ws_client
) -> None:
    """Drive the new panel's WebSocket contracts against a real HA runtime."""
    for entity in ("light.strip", "light.desk"):
        hass.states.async_set(entity, STATE_OFF, {ATTR_SUPPORTED_COLOR_MODES: ["rgb"]})
    hass.states.async_set("light.group", STATE_OFF, {"entity_id": ["light.strip"]})
    sent = []

    async def record(call):
        entities = call.data["entity_id"]
        sent.extend([entities] if isinstance(entities, str) else entities)

    hass.services.async_register("light", SERVICE_TURN_ON, record)
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_LIGHTS: ["light.strip"]}, minor_version=2
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    client = await hass_ws_client()
    area = ar.async_get(hass).async_create("Office")
    msg_id = 0

    async def cmd(command, **data):
        nonlocal msg_id
        msg_id += 1
        await client.send_json(
            {
                "id": msg_id,
                "type": f"{DOMAIN}/admin/{command}",
                "entry_id": entry.entry_id,
                **data,
            }
        )
        return await client.receive_json()

    async def mutate(kind, operation, **data):
        result = await cmd(
            "mutate",
            kind=kind,
            operation=operation,
            revision=options_revision(entry.options),
            **data,
        )
        assert result["success"], result
        await hass.async_block_till_done()
        assert entry.runtime_data.options_revision == result["result"]["revision"]
        return result["result"]["item"]

    original = (await cmd("get"))["result"]["admin"]
    assert original["managed"] == ["light.strip"]
    assert {light["entity_id"] for light in original["lights"]} == {
        "light.strip",
        "light.desk",
    }
    group = await cmd(
        "mutate",
        kind="lights",
        operation="save",
        revision=options_revision(entry.options),
        item={"targets": ["light.group"]},
    )
    assert group["error"]["code"] == "group_not_authorized"
    await mutate("lights", "save", item={"targets": ["light.strip", "light.desk"]})

    zone = await mutate(
        "zone",
        "create",
        item={"name": "Office", "targets": ["light.strip"], "area_id": area.id},
    )
    zone_id = zone["zone_id"]
    first = await mutate(
        "mode",
        "create",
        item={
            "name": "Cinema",
            "zone_id": zone_id,
            "targets": ["light.strip"],
            "rgb_color": [40, 20, 255],
            "expose_switch": True,
        },
    )
    second = await mutate(
        "mode",
        "create",
        item={
            "name": "Reading",
            "zone_id": zone_id,
            "targets": ["light.strip"],
            "rgb_color": [255, 204, 128],
        },
    )
    registry = er.async_get(hass)
    unique_id = mode_switch_unique_id(entry.entry_id, first["mode_id"])
    switch_id = registry.async_get_entity_id("switch", DOMAIN, unique_id)
    assert switch_id
    changed = await mutate("zone", "update", item_id=zone_id, item={"name": "Studio"})
    assert changed["zone_id"] == zone_id and changed["area_id"] == area.id
    assert registry.async_get_entity_id("switch", DOMAIN, unique_id) == switch_id

    denied = await cmd(
        "mutate",
        kind="zone",
        operation="delete",
        revision=options_revision(entry.options),
        item_id=zone_id,
    )
    assert denied["error"]["code"] == "zone_has_modes"
    stale = await cmd(
        "mutate",
        kind="zone",
        operation="update",
        revision=options_revision({}),
        item_id=zone_id,
        item={"name": "Old"},
    )
    assert stale["error"]["code"] == "conflict"

    for mode in (first, second):
        result = await cmd(
            "mode",
            revision=options_revision(entry.options),
            mode_id=mode["mode_id"],
            active=True,
        )
        assert (
            result["result"]["status"][zone_id]["selected_mode_id"] == mode["mode_id"]
        )
    assert set(sent) == {"light.strip"}
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    persisted = (await cmd("get"))["result"]["admin"]
    assert persisted["status"][zone_id]["selected_mode_id"] == second["mode_id"]
    assert registry.async_get_entity_id("switch", DOMAIN, unique_id) == switch_id

    cleared = await cmd(
        "mode",
        revision=options_revision(entry.options),
        mode_id=second["mode_id"],
        active=False,
    )
    assert cleared["result"]["status"][zone_id]["selected_mode_id"] is None
    for mode in (first, second):
        await mutate("mode", "delete", item_id=mode["mode_id"])
    await mutate("zone", "delete", item_id=zone_id)
    assert (await cmd("get"))["result"]["admin"]["zones"] == []
    await client.close()


async def test_official_bus_button_and_event_entity_triggers_do_not_replay(
    hass,
) -> None:
    assert await async_setup_component(hass, "homeassistant", {})
    events = []

    async def submit(request):
        events.append(request)

    async def cancel(_):
        pass

    guard = {"type": "state", "entity_id": "input_boolean.permission", "state": "on"}
    triggers = {
        "bus": {"platform": "event", "event_type": "slm_test_c1"},
        "button": {"platform": "state", "entity_id": "input_button.lab", "to": None},
        "event": {"platform": "state", "entity_id": "event.lab", "to": None},
    }
    rules = [
        {
            "id": name,
            "name": name,
            "type": "event",
            "trigger": trigger,
            "targets": ["light.strip"],
            "duration": 8,
            "conditions": guard,
        }
        for name, trigger in triggers.items()
    ]
    states = hass.states
    states.async_set("input_boolean.permission", "off")
    states.async_set("input_button.lab", "2026-11-24T14:00:00+00:00")
    states.async_set("event.lab", "2026-11-24T14:00:00+00:00")
    manager = RuleManager(hass, rules, frozenset({"light.strip"}), submit, cancel)
    try:
        await manager.async_setup()
        hass.bus.async_fire("slm_test_c1")
        await hass.async_block_till_done()
        assert not events
        states.async_set("input_boolean.permission", "on")
        await hass.async_block_till_done()
        assert not events
        states.async_set("input_button.lab", "2026-11-24T14:00:01+00:00")
        states.async_set("event.lab", "2026-11-24T14:00:01+00:00")
        hass.bus.async_fire("slm_test_c1")
        await hass.async_block_till_done()
        assert {item.request_id for item in events} == {
            "rule:bus",
            "rule:button",
            "rule:event",
        }
        states.async_set(
            "event.lab", "2026-11-24T14:00:01+00:00", {"metadata": "changed"}
        )
        await hass.async_block_till_done()
        assert len(events) == 3
    finally:
        await manager.async_shutdown()
    hass.bus.async_fire("slm_test_c1")
    states.async_set("input_button.lab", "2026-11-24T14:00:02+00:00")
    await hass.async_block_till_done()
    assert len(events) == 3


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
    fields = probatio.to_field_list(
        result["data_schema"], custom_serializer=cv.custom_serializer
    )
    state = next(field for field in fields if field["name"] == "state")
    assert state["context"] == {"filter_entity": "source"}
    assert (
        "condition"
        in next(field for field in fields if field["name"] == "conditions")["selector"]
    )
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
            "conditions": [
                {
                    "condition": "state",
                    "entity_id": "input_boolean.presence",
                    "state": "on",
                }
            ],
            "schedule_enabled": True,
            "schedule_after": "22:00:00",
            "schedule_before": "06:00:00",
            "schedule_days": ["mon"],
            "dwell": {"seconds": 30},
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    state_rule = result["data"][CONF_RULES][0]
    assert state_rule["type"] == "state"
    assert state_rule["targets"] == ["light.strip"]
    assert state_rule["conditions"]["entity_id"] == "input_boolean.presence"
    assert state_rule["schedule"]["after"] == "22:00"
    assert state_rule["for_seconds"] == 30

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
