# AGENTS.md — Smart LED Manager

These instructions apply to the whole repository and are permanent project policy.

## Source of truth and safe Git workflow

- The canonical repository is `https://github.com/abel-smart-home/smart-led-manager` and the default branch is `main`.
- Fetch and inspect the current remote state before development. Never replace newer repository code with an older local copy.
- Develop on a branch. Do not push ordinary development directly to `main`.
- Do not merge, create a tag, publish a release, or submit the Marketplace catalog entry without the owner's explicit approval.
- Preserve unrelated user changes. Never hide a failing check or claim a remote/physical action happened when it did not.

## Product invariants

- This is a fully local Home Assistant helper integration over existing `light` entities; it is not a physical LED driver.
- Only explicitly authorized lights may be controlled. Never default to every light in Home Assistant.
- The priority engine resolves every target independently. A lower request stays current while masked and becomes visible when higher requests end.
- Ranking is deterministic: priority first, then the configured tie policy, then a stable request identifier.
- Never restore a stale snapshot blindly. Re-evaluate the current request set and source states.
- All Home Assistant I/O is asynchronous and uses official APIs. Do not monkey-patch or intercept global services.
- Every command path must preserve per-device rate limiting, command deduplication, stale-work cancellation, and bounded retry behavior.
- `unknown` and `unavailable` are never valid numeric sensor values.
- Internal commands must not be misclassified as external manual control. Direct-change detection remains opt-in until its attribution is demonstrably reliable.
- Safety/security lighting is advisory only and is not a certified alarm, fire, or emergency system.

## Architecture boundaries

- Keep the decision core under `custom_components/smart_led_manager/core/` independent from Home Assistant so it can be tested as ordinary Python.
- Keep Home Assistant orchestration in `coordinator.py`, service/action registration in `services.py`, persistence in `storage.py`, and physical light calls in `controllers/`.
- A request describes intent; the RGB controller projects that intent onto the target's actual `supported_color_modes` and features.
- Scheduler/animation jobs are owned per target and must be cancelled before a new winner is applied.
- Addressable pixels and segments are future target/controller capabilities; do not leak assumptions about them into priority resolution.
- Do not create empty modules merely to mirror a proposed tree. Add a module only when it owns real behavior.

See [architecture](docs/architecture.md), [requirements](docs/requirements.md), and [roadmap](docs/roadmap.md) before changing behavior.

## Home Assistant and Marketplace conventions

- Target the supported Home Assistant/Python versions documented in `manifest.json`, `hacs.json`, `pyproject.toml`, and `docs/marketplace.md`; keep them synchronized.
- Configuration is UI-first through config/options flows. YAML must not be required for ordinary use.
- Custom-integration English fallback text lives in `translations/en.json`; ship matching Spanish text in `translations/es.json`.
- Register domain actions once from integration setup and describe them with selectors in `services.yaml` plus translations.
- Preserve `hacs.json`. Marketplace 2026.11 and HACS use the same repository metadata and validation action.
- Do not add dependencies already provided by Home Assistant. Keep manifest requirements empty unless a reviewed need exists.

## Quality gates

- Add focused tests with every behavior change. Test observable Home Assistant behavior where practical and keep exhaustive engine tests independent of HA.
- Minimum local/CI gates: Ruff, pytest with branch coverage, Hassfest, and HACS/Marketplace validation.
- Cover priorities, ties, masked updates, expiration, cancellation, unavailable devices, rate limiting, deduplication, persistence/migration, config flow, unload, and restart recovery.
- Prefer a controllable UTC clock in tests. Persist wall-clock UTC timestamps; use monotonic time only for in-process delays/rate limiting.
- Run `ruff check .` and `pytest --cov` before requesting review. Record any check that could not run and why.
- Unit tests and simulations do not count as HAOS, Zigbee, GLEDOPTO, Alexa, or Matter Hub validation. Physical results belong in the HAOS test record only when the owner performs them.

## Documentation, licenses, and releases

- Keep user-facing documentation in Spanish first, with UI strings in both Spanish and English.
- Update `CHANGELOG.md` and the roadmap for user-visible changes or deferred approved scope.
- Review `docs/community-audit.md` before borrowing from another project. Preserve required license and copyright notices and update `THIRD_PARTY_NOTICES.md`.
- The `0.1.0-alpha.1` manifest version, Python package form `0.1.0a1`, changelog, archive name, and eventual release tag must describe the same release.
- Never call a placeholder or untested path “implemented.” Mark incomplete work explicitly and state the path to the regular `0.1.0` release.
