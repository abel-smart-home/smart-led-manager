"""Tests for Smart LED Manager domain actions."""

from __future__ import annotations

import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

from homeassistant.core import ServiceCall
from homeassistant.exceptions import ServiceValidationError

from custom_components.smart_led_manager.const import (
    DOMAIN,
    MODULE_NOTIFICATION,
    SERVICE_ACTIVATE,
    SERVICE_ACTIVATE_MODE,
    SERVICE_CANCEL,
    SERVICE_CLEAR_NOTIFICATIONS,
    SERVICE_DEACTIVATE,
    SERVICE_DEACTIVATE_MODE,
    SERVICE_NOTIFY,
    SERVICE_RUN_NOTICE,
    SERVICE_SET_MANUAL_OVERRIDE,
    SERVICE_SET_SCENE,
    SERVICE_SET_ZONE_MODE,
)
from custom_components.smart_led_manager.core.engine import PriorityEngine
from custom_components.smart_led_manager.core.targets import TargetResolver
from custom_components.smart_led_manager.models import (
    AnimationKind,
    LightCommand,
    Request,
    utc_now,
)
from custom_components.smart_led_manager.modules.modes import ModeValidationError
from custom_components.smart_led_manager.services import (
    async_setup_services,
    async_unload_services,
)


class _ServiceRegistry:
    def __init__(self) -> None:
        self.registrations: dict[str, SimpleNamespace] = {}
        self.removed: list[tuple[str, str]] = []

    def async_register(
        self,
        domain: str,
        service: str,
        handler,
        *,
        schema,
        supports_response,
    ) -> None:
        assert domain == DOMAIN
        self.registrations[service] = SimpleNamespace(
            handler=handler,
            schema=schema,
            supports_response=supports_response,
        )

    def async_remove(self, domain: str, service: str) -> None:
        self.removed.append((domain, service))
        self.registrations.pop(service, None)


class _Hass:
    def __init__(self, coordinator=None) -> None:
        self.services = _ServiceRegistry()
        entries = {} if coordinator is None else {"entry-1": coordinator}
        self.data = {DOMAIN: {"entries": entries}}


def _coordinator():
    return SimpleNamespace(
        targets=TargetResolver(["light.strip"]),
        async_submit=AsyncMock(),
        async_deactivate=AsyncMock(),
        async_cancel=AsyncMock(),
        async_clear_notifications=AsyncMock(),
        async_set_manual_override=AsyncMock(),
        async_activate_mode=AsyncMock(),
        async_deactivate_mode=AsyncMock(),
        async_set_zone_mode=AsyncMock(),
    )


async def _call(hass: _Hass, service: str, data: dict[str, object]):
    registration = hass.services.registrations[service]
    validated = registration.schema(data)
    call = ServiceCall(hass, DOMAIN, service, validated, return_response=True)
    return await registration.handler(call)


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    """Exercise registration, defaults, authorization, and lifecycle."""

    async def test_notification_builds_priority_request_with_defaults(self) -> None:
        coordinator = _coordinator()
        hass = _Hass(coordinator)
        async_setup_services(hass)

        response = await _call(
            hass,
            SERVICE_NOTIFY,
            {
                "request_id": "notice:doorbell",
                "targets": ["light.strip"],
                "rgb_color": [10, 20, 30],
                "animation": "blink",
            },
        )

        request = coordinator.async_submit.await_args.args[0]
        self.assertEqual(response["request_id"], "notice:doorbell")
        self.assertEqual(response["targets"], ["light.strip"])
        self.assertEqual(request.module, MODULE_NOTIFICATION)
        self.assertEqual(request.targets, frozenset({"light.strip"}))
        self.assertEqual(request.priority, 70)
        self.assertEqual(request.command.color, (10, 20, 30))
        self.assertEqual(request.command.brightness, 255)
        self.assertEqual(request.command.animation.kind, AnimationKind.BLINK)
        self.assertIsNotNone(request.expires_at)
        self.assertFalse(request.persistent)

    async def test_temporary_notification_recovers_lower_request_when_late(
        self,
    ) -> None:
        now = utc_now()
        clock = SimpleNamespace(value=now)
        engine = PriorityEngine(clock=lambda: clock.value)
        lower = Request(
            request_id="scene:ambient",
            source="test",
            name="Ambient",
            module="scene",
            targets=frozenset({"light.strip"}),
            priority=20,
            command=LightCommand(color=(1, 2, 3), brightness=90),
            activated_at=now,
            updated_at=now,
        )
        await engine.async_submit(lower)
        coordinator = _coordinator()
        coordinator.async_submit = AsyncMock(side_effect=engine.async_submit)
        hass = _Hass(coordinator)
        async_setup_services(hass)

        await _call(
            hass,
            SERVICE_NOTIFY,
            {
                "request_id": "notice:doorbell",
                "targets": ["light.strip"],
                "rgb_color": [255, 0, 0],
                "duration": 1,
                "animation": "blink",
            },
        )
        notification = coordinator.async_submit.await_args.args[0]
        self.assertEqual(notification.module, MODULE_NOTIFICATION)
        self.assertIsNotNone(notification.expires_at)
        clock.value = notification.expires_at + timedelta(seconds=1)

        changes = await engine.async_expire()

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].previous, notification)
        self.assertEqual(changes[0].current, lower)
        self.assertEqual(await engine.async_winner("light.strip"), lower)

    async def test_rejects_target_outside_explicit_allowlist(self) -> None:
        coordinator = _coordinator()
        hass = _Hass(coordinator)
        async_setup_services(hass)

        with self.assertRaises(ServiceValidationError):
            await _call(
                hass,
                SERVICE_ACTIVATE,
                {"targets": ["light.not_authorized"], "priority": 10},
            )

        coordinator.async_submit.assert_not_awaited()

    async def test_control_actions_delegate_to_coordinator(self) -> None:
        coordinator = _coordinator()
        hass = _Hass(coordinator)
        async_setup_services(hass)

        self.assertEqual(
            await _call(
                hass,
                SERVICE_DEACTIVATE,
                {"request_id": "scene:evening"},
            ),
            {"request_id": "scene:evening"},
        )
        self.assertEqual(
            await _call(
                hass,
                SERVICE_CANCEL,
                {"request_id": "scene:evening"},
            ),
            {"request_id": "scene:evening"},
        )
        await _call(
            hass,
            SERVICE_CLEAR_NOTIFICATIONS,
            {"targets": ["light.strip"]},
        )
        manual_response = await _call(
            hass,
            SERVICE_SET_MANUAL_OVERRIDE,
            {
                "enabled": True,
                "targets": ["light.strip"],
                "rgb_color": [1, 2, 3],
                "brightness": 42,
            },
        )

        coordinator.async_deactivate.assert_awaited_once_with("scene:evening")
        coordinator.async_cancel.assert_awaited_once_with("scene:evening")
        coordinator.async_clear_notifications.assert_awaited_once_with(
            frozenset({"light.strip"})
        )
        manual_call = coordinator.async_set_manual_override.await_args
        self.assertEqual(manual_call.args[0], frozenset({"light.strip"}))
        self.assertTrue(manual_call.kwargs["enabled"])
        self.assertEqual(manual_call.kwargs["priority"], 60)
        self.assertEqual(manual_call.kwargs["command"].color, (1, 2, 3))
        self.assertEqual(manual_response["targets"], ["light.strip"])

    async def test_scene_is_persistent_and_registration_can_be_unloaded(self) -> None:
        coordinator = _coordinator()
        hass = _Hass(coordinator)
        async_setup_services(hass)

        expected = {
            SERVICE_ACTIVATE,
            SERVICE_DEACTIVATE,
            SERVICE_NOTIFY,
            SERVICE_RUN_NOTICE,
            SERVICE_SET_SCENE,
            SERVICE_CANCEL,
            SERVICE_CLEAR_NOTIFICATIONS,
            SERVICE_SET_MANUAL_OVERRIDE,
            SERVICE_ACTIVATE_MODE,
            SERVICE_DEACTIVATE_MODE,
            SERVICE_SET_ZONE_MODE,
        }
        self.assertEqual(set(hass.services.registrations), expected)

        await _call(
            hass,
            SERVICE_SET_SCENE,
            {
                "request_id": "scene:movie",
                "targets": ["light.strip"],
                "brightness": 100,
            },
        )
        request = coordinator.async_submit.await_args.args[0]
        self.assertTrue(request.persistent)

        async_unload_services(hass)
        self.assertEqual(hass.services.registrations, {})
        self.assertEqual(
            {service for domain, service in hass.services.removed if domain == DOMAIN},
            expected,
        )

    async def test_mode_actions_delegate_by_stable_identifiers(self) -> None:
        coordinator = _coordinator()
        hass = _Hass(coordinator)
        async_setup_services(hass)

        self.assertEqual(
            await _call(hass, SERVICE_ACTIVATE_MODE, {"mode_id": "blue"}),
            {"mode_id": "blue", "active": True},
        )
        self.assertEqual(
            await _call(hass, SERVICE_DEACTIVATE_MODE, {"mode_id": "blue"}),
            {"mode_id": "blue", "active": False},
        )
        self.assertEqual(
            await _call(
                hass,
                SERVICE_SET_ZONE_MODE,
                {"zone_id": "living", "mode_id": "red"},
            ),
            {"zone_id": "living", "mode_id": "red"},
        )
        self.assertEqual(
            await _call(hass, SERVICE_SET_ZONE_MODE, {"zone_id": "living"}),
            {"zone_id": "living", "mode_id": None},
        )

        coordinator.async_activate_mode.assert_awaited_once_with("blue")
        coordinator.async_deactivate_mode.assert_awaited_once_with("blue")
        self.assertEqual(
            coordinator.async_set_zone_mode.await_args_list[0].args,
            ("living", "red"),
        )
        self.assertEqual(
            coordinator.async_set_zone_mode.await_args_list[1].args,
            ("living", None),
        )

    async def test_protected_mode_namespace_returns_service_validation_error(
        self,
    ) -> None:
        coordinator = _coordinator()
        coordinator.async_submit.side_effect = ModeValidationError(
            "managed_mode_request"
        )
        hass = _Hass(coordinator)
        async_setup_services(hass)

        with self.assertRaises(ServiceValidationError):
            await _call(
                hass,
                SERVICE_ACTIVATE,
                {
                    "request_id": "smart_led_manager:mode:blue",
                    "targets": ["light.strip"],
                },
            )

    async def test_reports_action_use_before_configuration(self) -> None:
        hass = _Hass()
        async_setup_services(hass)

        with self.assertRaises(ServiceValidationError):
            await _call(
                hass,
                SERVICE_ACTIVATE,
                {"targets": ["light.strip"]},
            )


if __name__ == "__main__":
    unittest.main()
