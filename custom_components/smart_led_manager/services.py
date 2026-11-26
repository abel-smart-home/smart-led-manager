"""Domain actions for Smart LED Manager."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import uuid4

import probatio
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from homeassistant.helpers.service import async_set_service_schema

from .const import (
    DOMAIN,
    MODULE_NOTIFICATION,
    MODULE_SCENE,
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
from .core.targets import UnauthorizedTargetError
from .models import (
    AnimationKind,
    AnimationSpec,
    LightCommand,
    Request,
    utc_now,
)
from .modules.modes import ModeValidationError

ATTR_REQUEST_ID = "request_id"
ATTR_NAME = "name"
ATTR_TARGETS = "targets"
ATTR_PRIORITY = "priority"
ATTR_RGB_COLOR = "rgb_color"
ATTR_BRIGHTNESS = "brightness"
ATTR_TRANSITION = "transition"
ATTR_DURATION = "duration"
ATTR_ALLOW_TURN_ON = "allow_turn_on"
ATTR_PERSISTENT = "persistent"
ATTR_ANIMATION = "animation"
ATTR_PERIOD = "period"
ATTR_ENABLED = "enabled"
ATTR_MODE_ID = "mode_id"
ATTR_ZONE_ID = "zone_id"
ATTR_NOTICE_ID = "notice_id"

_TARGET_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="light", multiple=True)
)
_RGB_SELECTOR = selector.ColorRGBSelector()
_PRIORITY = probatio.All(probatio.Coerce(int), probatio.Range(min=0, max=100))
_BRIGHTNESS = probatio.All(probatio.Coerce(int), probatio.Range(min=1, max=255))
_NON_NEGATIVE = probatio.All(probatio.Coerce(float), probatio.Range(min=0))
_POSITIVE = probatio.All(probatio.Coerce(float), probatio.Range(min=0.1))

_MISSING = object()


def _request_fields(
    *,
    priority_default: int = 50,
    transition_default: float = 0,
    require_color: bool = False,
    brightness_default: int | object = _MISSING,
    duration_default: float | object = _MISSING,
) -> dict[Any, Any]:
    """Build one request schema without duplicate optional markers.

    Optional markers for the same field but with different defaults are distinct
    dictionary keys. Building the mapping once ensures action-specific defaults
    replace the base values instead of competing with them during validation.
    """
    fields: dict[Any, Any] = {
        probatio.Optional(ATTR_REQUEST_ID): cv.string,
        probatio.Optional(ATTR_NAME): cv.string,
        probatio.Required(ATTR_TARGETS): _TARGET_SELECTOR,
        probatio.Optional(ATTR_PRIORITY, default=priority_default): _PRIORITY,
        (
            probatio.Required(ATTR_RGB_COLOR)
            if require_color
            else probatio.Optional(ATTR_RGB_COLOR)
        ): _RGB_SELECTOR,
        probatio.Optional(ATTR_TRANSITION, default=transition_default): _NON_NEGATIVE,
        probatio.Optional(ATTR_ALLOW_TURN_ON, default=True): cv.boolean,
        probatio.Optional(ATTR_PERSISTENT, default=False): cv.boolean,
    }
    brightness_marker = (
        probatio.Optional(ATTR_BRIGHTNESS)
        if brightness_default is _MISSING
        else probatio.Optional(ATTR_BRIGHTNESS, default=brightness_default)
    )
    duration_marker = (
        probatio.Optional(ATTR_DURATION)
        if duration_default is _MISSING
        else probatio.Optional(ATTR_DURATION, default=duration_default)
    )
    fields[brightness_marker] = _BRIGHTNESS
    fields[duration_marker] = _POSITIVE
    return fields


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration actions once for the domain."""

    async def _handle(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator(hass)
        service = call.service
        if service == SERVICE_RUN_NOTICE:
            try:
                return await coordinator.async_run_notice(call.data[ATTR_NOTICE_ID])
            except ModeValidationError as err:
                raise _service_mode_error(err) from err

        if service in {
            SERVICE_ACTIVATE_MODE,
            SERVICE_DEACTIVATE_MODE,
            SERVICE_SET_ZONE_MODE,
        }:
            try:
                if service == SERVICE_ACTIVATE_MODE:
                    mode_id = call.data[ATTR_MODE_ID]
                    await coordinator.async_activate_mode(mode_id)
                    return {ATTR_MODE_ID: mode_id, "active": True}
                if service == SERVICE_DEACTIVATE_MODE:
                    mode_id = call.data[ATTR_MODE_ID]
                    await coordinator.async_deactivate_mode(mode_id)
                    return {ATTR_MODE_ID: mode_id, "active": False}
                zone_id = call.data[ATTR_ZONE_ID]
                mode_id = call.data.get(ATTR_MODE_ID)
                await coordinator.async_set_zone_mode(zone_id, mode_id)
                return {ATTR_ZONE_ID: zone_id, ATTR_MODE_ID: mode_id}
            except ModeValidationError as err:
                raise _service_mode_error(err) from err

        if service in {SERVICE_DEACTIVATE, SERVICE_CANCEL}:
            request_id = call.data[ATTR_REQUEST_ID]
            try:
                if service == SERVICE_DEACTIVATE:
                    await coordinator.async_deactivate(request_id)
                else:
                    await coordinator.async_cancel(request_id)
            except ModeValidationError as err:
                raise _service_mode_error(err) from err
            return {ATTR_REQUEST_ID: request_id}

        if service == SERVICE_CLEAR_NOTIFICATIONS:
            targets = None
            if ATTR_TARGETS in call.data:
                targets = _resolve_targets(coordinator, call.data[ATTR_TARGETS])
            await coordinator.async_clear_notifications(targets)
            return {"cleared": True}

        if service == SERVICE_SET_MANUAL_OVERRIDE:
            targets = _resolve_targets(coordinator, call.data[ATTR_TARGETS])
            command = None
            if ATTR_RGB_COLOR in call.data or ATTR_BRIGHTNESS in call.data:
                command = _command(call.data)
            await coordinator.async_set_manual_override(
                targets,
                enabled=call.data[ATTR_ENABLED],
                command=command,
                priority=call.data[ATTR_PRIORITY],
            )
            return {"enabled": call.data[ATTR_ENABLED], "targets": sorted(targets)}

        targets = _resolve_targets(coordinator, call.data[ATTR_TARGETS])
        request_id = call.data.get(ATTR_REQUEST_ID) or _generated_id(service)
        now = utc_now()
        duration = call.data.get(ATTR_DURATION)
        expires = now + timedelta(seconds=duration) if duration else None
        module = {
            SERVICE_NOTIFY: MODULE_NOTIFICATION,
            SERVICE_SET_SCENE: MODULE_SCENE,
        }.get(service, "action")
        persistent = bool(call.data.get(ATTR_PERSISTENT, False))
        if service == SERVICE_SET_SCENE:
            persistent = True
        request = Request(
            request_id=request_id,
            source=f"action:{service}",
            name=call.data.get(ATTR_NAME) or request_id,
            module=module,
            targets=targets,
            priority=call.data[ATTR_PRIORITY],
            command=_command(call.data),
            activated_at=now,
            updated_at=now,
            expires_at=expires,
            allow_turn_on=call.data.get(ATTR_ALLOW_TURN_ON, True),
            persistent=persistent,
            metadata={"action": service},
        )
        try:
            await coordinator.async_submit(request)
        except ModeValidationError as err:
            raise _service_mode_error(err) from err
        return {ATTR_REQUEST_ID: request_id, "targets": sorted(targets)}

    hass.services.async_register(
        DOMAIN,
        SERVICE_ACTIVATE,
        _handle,
        schema=probatio.Schema(_request_fields()),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DEACTIVATE,
        _handle,
        schema=probatio.Schema({probatio.Required(ATTR_REQUEST_ID): cv.string}),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_NOTIFY,
        _handle,
        schema=probatio.Schema(
            {
                **_request_fields(
                    priority_default=70,
                    require_color=True,
                    brightness_default=255,
                    duration_default=5,
                ),
                probatio.Optional(ATTR_ANIMATION, default="fixed"): probatio.In(
                    {"fixed", "blink", "pulse"}
                ),
                probatio.Optional(ATTR_PERIOD, default=1): probatio.All(
                    probatio.Coerce(float), probatio.Range(min=0.5, max=60)
                ),
            }
        ),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCENE,
        _handle,
        schema=probatio.Schema(_request_fields(transition_default=1)),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RUN_NOTICE,
        _handle,
        schema=probatio.Schema({probatio.Required(ATTR_NOTICE_ID): cv.string}),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CANCEL,
        _handle,
        schema=probatio.Schema({probatio.Required(ATTR_REQUEST_ID): cv.string}),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_NOTIFICATIONS,
        _handle,
        schema=probatio.Schema({probatio.Optional(ATTR_TARGETS): _TARGET_SELECTOR}),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_MANUAL_OVERRIDE,
        _handle,
        schema=probatio.Schema(
            {
                probatio.Required(ATTR_ENABLED): cv.boolean,
                probatio.Required(ATTR_TARGETS): _TARGET_SELECTOR,
                probatio.Optional(ATTR_RGB_COLOR): _RGB_SELECTOR,
                probatio.Optional(ATTR_BRIGHTNESS): _BRIGHTNESS,
                probatio.Optional(ATTR_PRIORITY, default=60): _PRIORITY,
            }
        ),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ACTIVATE_MODE,
        _handle,
        schema=probatio.Schema({probatio.Required(ATTR_MODE_ID): cv.string}),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DEACTIVATE_MODE,
        _handle,
        schema=probatio.Schema({probatio.Required(ATTR_MODE_ID): cv.string}),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ZONE_MODE,
        _handle,
        schema=probatio.Schema(
            {
                probatio.Required(ATTR_ZONE_ID): cv.string,
                probatio.Optional(ATTR_MODE_ID): cv.string,
            }
        ),
        supports_response=SupportsResponse.OPTIONAL,
    )


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove actions if the integration has no loaded entries."""
    for service in (
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
    ):
        hass.services.async_remove(DOMAIN, service)


@callback
def async_update_notice_schema(
    hass: HomeAssistant, choices: list[dict[str, str]]
) -> None:
    """Publish the current notice choices through Home Assistant's service metadata."""
    async_set_service_schema(
        hass,
        DOMAIN,
        SERVICE_RUN_NOTICE,
        {
            "name": "Run saved notice",
            "description": "Play a saved Smart LED Manager light notice.",
            "fields": {
                ATTR_NOTICE_ID: {
                    "name": "Notice",
                    "description": "Pick the saved notice by name.",
                    "required": True,
                    "selector": {"select": {"options": choices, "mode": "dropdown"}},
                },
            },
        },
    )


def _coordinator(hass: HomeAssistant):
    entries = hass.data.get(DOMAIN, {}).get("entries", {})
    if not entries:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_configured",
        )
    return next(iter(entries.values()))


def _resolve_targets(coordinator, values: list[str]) -> frozenset[str]:
    try:
        return coordinator.targets.resolve(values)
    except UnauthorizedTargetError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="unmanaged_targets",
            translation_placeholders={"targets": ", ".join(sorted(err.targets))},
        ) from err
    except ValueError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="at_least_one_target",
        ) from err


def _command(data: dict[str, Any]) -> LightCommand:
    animation_name = data.get(ATTR_ANIMATION, "fixed")
    animation_kind = {
        "fixed": AnimationKind.NONE,
        "blink": AnimationKind.BLINK,
        "pulse": AnimationKind.PULSE,
    }[animation_name]
    color_data = data.get(ATTR_RGB_COLOR)
    color = tuple(color_data) if color_data is not None else None
    return LightCommand(
        turn_on=True,
        color=color,
        brightness=data.get(ATTR_BRIGHTNESS),
        transition=data.get(ATTR_TRANSITION),
        animation=AnimationSpec(
            kind=animation_kind,
            interval=float(data.get(ATTR_PERIOD, 1)),
        ),
    )


def _generated_id(service: str) -> str:
    return f"{service}:{uuid4().hex}"


def _service_mode_error(error: ModeValidationError) -> ServiceValidationError:
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key=error.key,
        translation_placeholders=error.placeholders,
    )
