"""Tests for authorization-first target resolution."""

from __future__ import annotations

import unittest

from custom_components.smart_led_manager.core.targets import (
    TargetResolver,
    UnauthorizedTargetError,
)


class TargetResolverTests(unittest.TestCase):
    """Verify allow-list and deduplication semantics."""

    def test_resolves_explicit_targets_without_duplicates(self) -> None:
        resolver = TargetResolver(["light.one", "light.two"])

        result = resolver.resolve(["light.one", "light.one"])

        self.assertEqual(result, frozenset({"light.one"}))

    def test_rejects_unmanaged_target(self) -> None:
        resolver = TargetResolver(["light.one"])

        with self.assertRaises(UnauthorizedTargetError) as context:
            resolver.resolve(["light.outside"])

        self.assertEqual(context.exception.targets, frozenset({"light.outside"}))

    def test_all_managed_is_explicit(self) -> None:
        resolver = TargetResolver(["light.one", "light.two"])

        self.assertEqual(
            resolver.resolve(None, all_managed=True),
            frozenset({"light.one", "light.two"}),
        )
        with self.assertRaises(ValueError):
            resolver.resolve(None)


if __name__ == "__main__":
    unittest.main()
