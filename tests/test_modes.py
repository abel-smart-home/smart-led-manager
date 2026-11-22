"""Regression tests for persistent zones and lighting modes."""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from custom_components.smart_led_manager.core.engine import PriorityEngine
from custom_components.smart_led_manager.models import LightCommand, Request, utc_now
from custom_components.smart_led_manager.modules.modes import (
    MODE_REQUEST_PREFIX,
    ModeManager,
    ModeValidationError,
)
from custom_components.smart_led_manager.select import (
    NO_MODE_OPTION,
    SmartLEDZoneModeSelect,
)
from custom_components.smart_led_manager.select import (
    async_setup_entry as async_setup_select_entry,
)
from custom_components.smart_led_manager.switch import SmartLEDModeSwitch
from custom_components.smart_led_manager.switch import (
    async_setup_entry as async_setup_switch_entry,
)


def _zone(
    zone_id: str = "living",
    name: str = "Sala",
    targets: list[str] | None = None,
) -> dict[str, object]:
    return {
        "zone_id": zone_id,
        "name": name,
        "targets": targets or ["light.one"],
    }


def _mode(
    mode_id: str,
    name: str,
    color: list[int],
    *,
    zone_id: str = "living",
    targets: list[str] | None = None,
    priority: int = 50,
    animation: str = "fixed",
    expose_switch: bool = False,
) -> dict[str, object]:
    return {
        "mode_id": mode_id,
        "zone_id": zone_id,
        "name": name,
        "targets": targets or ["light.one"],
        "priority": priority,
        "rgb_color": color,
        "brightness": 180,
        "transition": 1,
        "allow_turn_on": True,
        "animation": animation,
        "period": 1,
        "expose_switch": expose_switch,
    }


def _request(request_id: str, priority: int, color: tuple[int, int, int]) -> Request:
    now = utc_now()
    return Request(
        request_id=request_id,
        source="test",
        name=request_id,
        module="test",
        targets=frozenset({"light.one"}),
        priority=priority,
        command=LightCommand(color=color),
        activated_at=now,
        updated_at=now,
    )


class ModeManagerTests(unittest.IsolatedAsyncioTestCase):
    """Verify catalog invariants and engine-backed selection behavior."""

    def _manager(
        self,
        *,
        engine: PriorityEngine | None = None,
        zones: list[dict[str, object]] | None = None,
        modes: list[dict[str, object]] | None = None,
        authorized: frozenset[str] = frozenset({"light.one", "light.two"}),
    ) -> ModeManager:
        return ModeManager(
            engine or PriorityEngine(),
            zones or [_zone()],
            modes
            or [
                _mode("blue", "Azul", [0, 0, 255]),
                _mode("red", "Rojo", [255, 0, 0]),
            ],
            authorized,
        )

    def test_catalog_rejects_overlap_duplicates_and_outside_targets(self) -> None:
        invalid_catalogs = (
            (
                [
                    _zone(),
                    _zone("other", "Otra", ["light.one", "light.two"]),
                ],
                [],
            ),
            ([_zone(), _zone("other", "sala", ["light.two"])], []),
            ([_zone()], [_mode("bad", "Fuera", [1, 2, 3], targets=["light.two"])]),
            (
                [_zone()],
                [
                    _mode("one", "Igual", [1, 2, 3]),
                    _mode("two", "igual", [3, 2, 1]),
                ],
            ),
        )
        for zones, modes in invalid_catalogs:
            with (
                self.subTest(zones=zones, modes=modes),
                self.assertRaises(ModeValidationError),
            ):
                self._manager(zones=zones, modes=modes)

        with self.assertRaises(ModeValidationError):
            self._manager(zones=[_zone(targets=["light.unauthorized"])])

    async def test_activation_builds_one_persistent_canonical_request(self) -> None:
        engine = PriorityEngine()
        manager = self._manager(engine=engine)

        mutation = await manager.async_activate("blue")
        request = await engine.async_winner("light.one")

        self.assertTrue(mutation.changed)
        self.assertEqual(manager.selected_mode_id("living"), "blue")
        self.assertEqual(request.request_id, f"{MODE_REQUEST_PREFIX}blue")
        self.assertEqual(request.module, "mode")
        self.assertEqual(request.command.color, (0, 0, 255))
        self.assertTrue(request.persistent)
        self.assertIsNone(request.expires_at)
        self.assertEqual(request.metadata["zone_id"], "living")

    async def test_zone_replacement_is_atomic_and_never_exposes_lower_intent(
        self,
    ) -> None:
        engine = PriorityEngine()
        lower = _request("rule:lower", 10, (0, 255, 0))
        await engine.async_submit(lower)
        manager = self._manager(engine=engine)
        await manager.async_activate("blue")
        blue = await engine.async_winner("light.one")

        mutation = await manager.async_activate("red")

        self.assertEqual(len(mutation.changes), 1)
        self.assertEqual(mutation.changes[0].previous, blue)
        self.assertEqual(mutation.changes[0].current.command.color, (255, 0, 0))
        self.assertNotEqual(mutation.changes[0].current, lower)
        requests = await engine.async_requests()
        self.assertEqual(
            [request.request_id for request in requests if request.module == "mode"],
            [f"{MODE_REQUEST_PREFIX}red"],
        )

    async def test_reactivation_is_fully_idempotent(self) -> None:
        engine = PriorityEngine()
        manager = self._manager(engine=engine)
        await manager.async_activate("blue")
        before = await engine.async_requests()

        mutation = await manager.async_activate("blue")

        self.assertFalse(mutation.changed)
        self.assertEqual(mutation.changes, ())
        self.assertEqual(await engine.async_requests(), before)

    async def test_no_mode_releases_without_creating_an_off_command(self) -> None:
        engine = PriorityEngine()
        lower = _request("rule:lower", 10, (0, 255, 0))
        await engine.async_submit(lower)
        manager = self._manager(engine=engine)
        await manager.async_activate("blue")

        mutation = await manager.async_set_zone_mode("living", None)

        self.assertTrue(mutation.changed)
        self.assertIsNone(manager.selected_mode_id("living"))
        self.assertEqual(mutation.changes[0].current, lower)
        self.assertTrue(mutation.changes[0].current.command.turn_on)

    async def test_masked_switch_keeps_only_new_selection_for_later_recovery(
        self,
    ) -> None:
        engine = PriorityEngine()
        manager = self._manager(engine=engine)
        await manager.async_activate("blue")
        notice = _request("notice:high", 95, (255, 128, 0))
        await engine.async_submit(notice)

        mutation = await manager.async_activate("red")

        self.assertEqual(mutation.changes, ())
        self.assertEqual(manager.selected_mode_id("living"), "red")
        recovery = await engine.async_cancel(notice.request_id)
        self.assertEqual(recovery[0].current.request_id, f"{MODE_REQUEST_PREFIX}red")

    async def test_deactivation_during_notice_recovers_updated_lower_request(
        self,
    ) -> None:
        engine = PriorityEngine()
        lower = _request("rule:temperature", 40, (0, 0, 255))
        await engine.async_submit(lower)
        manager = self._manager(engine=engine)
        await manager.async_activate("blue")
        notice = _request("notice:high", 70, (255, 128, 0))
        await engine.async_submit(notice)
        updated_lower = replace(
            lower,
            command=LightCommand(color=(0, 255, 0)),
            updated_at=utc_now(),
        )
        await engine.async_submit(updated_lower)

        mutation = await manager.async_deactivate("blue")
        recovery = await engine.async_cancel(notice.request_id)

        self.assertEqual(mutation.changes, ())
        self.assertEqual(recovery[0].current, updated_lower)

    async def test_deactivating_unselected_mode_is_noop(self) -> None:
        manager = self._manager()
        await manager.async_activate("blue")

        mutation = await manager.async_deactivate("red")

        self.assertFalse(mutation.changed)
        self.assertTrue(manager.is_selected("blue"))

    async def test_reconcile_drops_orphans_duplicates_and_uses_definition_truth(
        self,
    ) -> None:
        source_engine = PriorityEngine()
        source = self._manager(engine=source_engine)
        await source.async_activate("blue")
        blue = (await source_engine.async_requests())[0]
        await source.async_activate("red")
        red = (await source_engine.async_requests())[0]
        red = replace(
            red,
            activated_at=blue.activated_at + timedelta(seconds=1),
            updated_at=blue.updated_at + timedelta(seconds=1),
            command=LightCommand(color=(1, 1, 1)),
        )
        orphan = replace(
            blue,
            request_id=f"{MODE_REQUEST_PREFIX}deleted",
            metadata={"managed": True, "mode_id": "deleted", "zone_id": "living"},
        )
        unrelated = _request("scene:kept", 5, (2, 3, 4))

        restored = self._manager()
        requests, changed = restored.reconcile_requests([blue, red, orphan, unrelated])

        self.assertTrue(changed)
        self.assertEqual(restored.selected_mode_id("living"), "red")
        mode_requests = [request for request in requests if request.module == "mode"]
        self.assertEqual(len(mode_requests), 1)
        self.assertEqual(mode_requests[0].command.color, (255, 0, 0))
        self.assertEqual(mode_requests[0].activated_at, red.activated_at)
        self.assertIn(unrelated, requests)

    async def test_multiple_zones_are_independent(self) -> None:
        engine = PriorityEngine()
        zones = [_zone(), _zone("kitchen", "Cocina", ["light.two"])]
        modes = [
            _mode("blue", "Azul", [0, 0, 255]),
            _mode(
                "warm",
                "Cálido",
                [255, 160, 40],
                zone_id="kitchen",
                targets=["light.two"],
            ),
        ]
        manager = self._manager(engine=engine, zones=zones, modes=modes)

        await manager.async_activate("blue")
        await manager.async_activate("warm")
        await manager.async_set_zone_mode("living", None)

        self.assertIsNone(await engine.async_winner("light.one"))
        self.assertEqual(
            (await engine.async_winner("light.two")).request_id,
            f"{MODE_REQUEST_PREFIX}warm",
        )

    async def test_snapshot_distinguishes_winner_masked_partial_and_no_mode(
        self,
    ) -> None:
        manager = self._manager(
            zones=[_zone(targets=["light.one", "light.two"])],
            modes=[
                _mode(
                    "blue",
                    "Azul",
                    [0, 0, 255],
                    targets=["light.one", "light.two"],
                )
            ],
        )
        self.assertEqual(manager.snapshot()["status"]["living"]["state"], "no_mode")
        await manager.async_activate("blue")
        request_id = manager.request_id("blue")

        masked = manager.snapshot({})["status"]["living"]
        partial = manager.snapshot({"light.one": request_id})["status"]["living"]
        winner = manager.snapshot({"light.one": request_id, "light.two": request_id})[
            "status"
        ]["living"]

        self.assertEqual(masked["state"], "masked")
        self.assertEqual(partial["state"], "partial")
        self.assertEqual(partial["masked_targets"], ["light.two"])
        self.assertEqual(winner["state"], "winner")

    async def test_empty_alpha1_catalog_preserves_other_persistent_requests(
        self,
    ) -> None:
        unrelated = replace(_request("scene:legacy", 40, (1, 2, 3)), persistent=True)
        manager = ModeManager(
            PriorityEngine(), [], [], frozenset({"light.one", "light.two"})
        )

        reconciled, changed = manager.reconcile_requests([unrelated])

        self.assertFalse(changed)
        self.assertEqual(reconciled, (unrelated,))

    def test_mode_definition_rejects_corrupt_and_reserved_values(self) -> None:
        invalid_modes = (
            {**_mode("one", "Sin modo", [1, 2, 3])},
            {**_mode("one", "Uno", [1, 2, 3]), "allow_turn_on": "yes"},
            {**_mode("one", "Uno", [1, 2, 3]), "priority": 50.5},
            {**_mode("one", "Uno", [1, 2, 3]), "brightness": 0},
            {**_mode("one", "Uno", [1, 2, 3]), "animation": "sequence"},
        )
        for mode in invalid_modes:
            with self.subTest(mode=mode), self.assertRaises(ModeValidationError):
                self._manager(modes=[mode])

    async def test_invalid_selection_and_internal_namespace_are_protected(self) -> None:
        manager = self._manager()
        with self.assertRaises(ModeValidationError):
            await manager.async_set_zone_mode("missing", None)
        with self.assertRaises(ModeValidationError):
            await manager.async_set_zone_mode("living", "missing")
        self.assertTrue(manager.is_internal_request_id(f"{MODE_REQUEST_PREFIX}blue"))


class ModeEntityTests(unittest.IsolatedAsyncioTestCase):
    """Verify stable select/switch entities delegate to the coordinator."""

    def _coordinator(self):
        manager = ModeManager(
            PriorityEngine(),
            [_zone()],
            [
                _mode("blue", "Azul", [0, 0, 255], expose_switch=True),
                _mode("red", "Rojo", [255, 0, 0]),
            ],
            frozenset({"light.one"}),
        )
        return SimpleNamespace(
            modes=manager,
            async_set_zone_mode=AsyncMock(),
            async_activate_mode=AsyncMock(),
            async_deactivate_mode=AsyncMock(),
            async_add_listener=Mock(return_value=Mock()),
        )

    async def test_zone_select_has_stable_identity_and_delegates(self) -> None:
        coordinator = self._coordinator()
        entry = SimpleNamespace(entry_id="entry-1")
        entity = SmartLEDZoneModeSelect(coordinator, entry, "living")

        self.assertEqual(entity.unique_id, "entry-1_zone_living_mode")
        self.assertEqual(entity.options, [NO_MODE_OPTION, "Azul", "Rojo"])
        self.assertEqual(entity.current_option, NO_MODE_OPTION)
        await entity.async_select_option("Rojo")
        await entity.async_select_option(NO_MODE_OPTION)

        self.assertEqual(
            coordinator.async_set_zone_mode.await_args_list[0].args,
            ("living", "red"),
        )
        self.assertEqual(
            coordinator.async_set_zone_mode.await_args_list[1].args,
            ("living", None),
        )
        with self.assertRaises(ValueError):
            await entity.async_select_option("Inexistente")

    async def test_mode_switch_delegates_without_owning_state(self) -> None:
        coordinator = self._coordinator()
        entry = SimpleNamespace(entry_id="entry-1")
        entity = SmartLEDModeSwitch(coordinator, entry, "blue")

        self.assertEqual(entity.unique_id, "entry-1_mode_blue")
        self.assertFalse(entity.is_on)
        await entity.async_turn_on()
        await entity.async_turn_off()

        coordinator.async_activate_mode.assert_awaited_once_with("blue")
        coordinator.async_deactivate_mode.assert_awaited_once_with("blue")

    async def test_platform_setup_creates_zone_and_only_opted_in_switches(self) -> None:
        coordinator = self._coordinator()
        entry = SimpleNamespace(entry_id="entry-1", runtime_data=coordinator)
        selects: list[SmartLEDZoneModeSelect] = []
        switches: list[SmartLEDModeSwitch] = []

        await async_setup_select_entry(None, entry, selects.extend)
        await async_setup_switch_entry(None, entry, switches.extend)

        self.assertEqual(
            [entity.unique_id for entity in selects], ["entry-1_zone_living_mode"]
        )
        self.assertEqual(
            [entity.unique_id for entity in switches], ["entry-1_mode_blue"]
        )


if __name__ == "__main__":
    unittest.main()
