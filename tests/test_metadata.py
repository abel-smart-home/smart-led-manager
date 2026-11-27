"""Manifest and translation catalog regression tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

INTEGRATION_ROOT = Path(__file__).parents[1] / "custom_components" / "smart_led_manager"


def _load_json(path: Path) -> dict[str, Any]:
    """Load a repository JSON object."""
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten_keys(value: dict[str, Any], prefix: str = "") -> set[str]:
    """Return every leaf translation key."""
    keys: set[str] = set()
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(child, dict):
            keys.update(_flatten_keys(child, path))
        else:
            keys.add(path)
    return keys


def test_manifest_classifies_manager_as_service() -> None:
    """The config entry belongs in Integrations, not Helpers."""
    manifest = _load_json(INTEGRATION_ROOT / "manifest.json")

    assert manifest["integration_type"] == "service"
    assert manifest["single_config_entry"] is True
    assert manifest["version"] == "0.1.0-alpha.3"


def test_latin_american_spanish_catalog_is_complete() -> None:
    """Both Spanish UI locales ship the complete options-flow catalog."""
    translations = INTEGRATION_ROOT / "translations"
    english = _load_json(translations / "en.json")
    spanish = _load_json(translations / "es.json")
    latin_american_spanish = _load_json(translations / "es-419.json")

    assert latin_american_spanish == spanish
    assert _flatten_keys(spanish) == _flatten_keys(english)
    assert (
        latin_american_spanish["options"]["step"]["init"]["title"]
        == "Administrar Smart LED Manager"
    )
    assert (
        latin_american_spanish["options"]["step"]["init"]["menu_options"]["modes"]
        == "Modos de iluminación"
    )
