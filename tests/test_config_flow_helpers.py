"""Tests for config-flow data parsing."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, Mock

from homeassistant.data_entry_flow import FlowResultType

from custom_components.smart_led_manager.config_flow import (
    SmartLEDManagerConfigFlow,
    parse_color_points,
)
from custom_components.smart_led_manager.const import (
    CONF_LIGHTS,
    CONF_MODES,
    CONF_ZONES,
    DOMAIN,
)


class ConfigFlowHelperTests(unittest.TestCase):
    """Verify UI text is converted into validated structured data."""

    def test_color_points_are_sorted(self) -> None:
        self.assertEqual(
            parse_color_points("20:0,255,0;10:0,0,255"),
            [
                {"value": 10.0, "rgb": [0, 0, 255]},
                {"value": 20.0, "rgb": [0, 255, 0]},
            ],
        )

    def test_requires_unique_valid_points(self) -> None:
        for invalid in (
            "10:0,0,255",
            "10:0,0,255;10:255,0,0",
            "10:0,0,999;20:255,0,0",
            "not-a-point;20:255,0,0",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                parse_color_points(invalid)


class ConfigFlowTests(unittest.IsolatedAsyncioTestCase):
    """Cover alpha.1-compatible entry creation and alpha.2 empty defaults."""

    async def test_user_form_rejects_empty_allowlist(self) -> None:
        flow = SmartLEDManagerConfigFlow()

        form = await flow.async_step_user()
        invalid = await flow.async_step_user({CONF_LIGHTS: []})

        self.assertEqual(form["type"], FlowResultType.FORM)
        self.assertEqual(invalid["errors"][CONF_LIGHTS], "at_least_one_light")

    async def test_user_flow_creates_backward_compatible_empty_catalog(self) -> None:
        flow = SmartLEDManagerConfigFlow()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = Mock()

        result = await flow.async_step_user({CONF_LIGHTS: ["light.one", "light.one"]})

        self.assertEqual(result["type"], FlowResultType.CREATE_ENTRY)
        self.assertEqual(result["data"], {CONF_LIGHTS: ["light.one"]})
        self.assertEqual(result["options"][CONF_ZONES], [])
        self.assertEqual(result["options"][CONF_MODES], [])
        flow.async_set_unique_id.assert_awaited_once_with(DOMAIN)


if __name__ == "__main__":
    unittest.main()
