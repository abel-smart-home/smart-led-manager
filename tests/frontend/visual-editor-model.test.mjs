import assert from "node:assert/strict";
import test from "node:test";

import {
  cssGradient,
  deepClone,
  draftChanged,
  gradientStopEntries,
  hexToRgb,
  nextPoint,
  pointPercent,
  removePoint,
  replacePoint,
  rgbToHex,
  sortPoints,
  validateDraft,
} from "../../custom_components/smart_led_manager/frontend/visual-editor-model.mjs";

const points = [
  { value: 20, rgb: [0, 255, 255] },
  { value: 24, rgb: [0, 255, 0] },
  { value: 36, rgb: [255, 0, 0] },
];

test("point creation, edit, deletion and sorting are deterministic", () => {
  assert.deepEqual(nextPoint(points), { value: 48, rgb: [255, 0, 0] });
  const edited = replacePoint(points, 2, { value: 10, rgb: [1, 2, 3] });
  assert.deepEqual(edited.map((point) => point.value), [10, 20, 24]);
  assert.deepEqual(edited[0].rgb, [1, 2, 3]);
  assert.deepEqual(removePoint(edited, 1).map((point) => point.value), [10, 24]);
  assert.deepEqual(sortPoints(points).map((point) => point.value), [20, 24, 36]);
  assert.throws(
    () => replacePoint(points, 0, { value: "", rgb: [1, 2, 3] }),
    /invalid numeric value/,
  );
});

test("validation rejects duplicate, non-finite and invalid RGB values", () => {
  assert.equal(validateDraft("interpolate", points), null);
  assert.equal(validateDraft("ranges", points.slice(0, 1)), "too_few_points");
  assert.equal(
    validateDraft("interpolate", [points[0], { ...points[1], value: 20 }]),
    "duplicate_value",
  );
  assert.equal(
    validateDraft("interpolate", [points[0], { ...points[1], value: Number.NaN }]),
    "invalid_value",
  );
  assert.equal(
    validateDraft("interpolate", [points[0], { ...points[1], rgb: [0, 0, 999] }]),
    "invalid_color",
  );
});

test("nonuniform positions and range stops use the real numeric domain", () => {
  assert.equal(pointPercent(20, points), 0);
  assert.equal(pointPercent(24, points), 25);
  assert.equal(pointPercent(36, points), 100);
  assert.deepEqual(
    gradientStopEntries(points, "interpolate").map((stop) => stop.offset),
    [0, 25, 100],
  );
  assert.deepEqual(
    gradientStopEntries(points, "ranges").map((stop) => stop.offset),
    [0, 25, 25, 100, 100],
  );
  assert.match(cssGradient(points, "interpolate"), /#00FF00 25%/);
});

test("draft comparison and cloning allow a true discard operation", () => {
  const original = { mode: "interpolate", points: deepClone(points) };
  const draft = deepClone(original);
  assert.equal(draftChanged(original, draft), false);
  draft.points[0].rgb = [9, 9, 9];
  assert.equal(draftChanged(original, draft), true);
  assert.deepEqual(original.points[0].rgb, [0, 255, 255]);
  assert.equal(draftChanged(original, deepClone(original)), false);
});

test("color picker conversion is reversible", () => {
  assert.equal(rgbToHex([10, 20, 255]), "#0A14FF");
  assert.deepEqual(hexToRgb("#0A14FF"), [10, 20, 255]);
  assert.throws(() => hexToRgb("invalid"), /invalid hex color/);
});

async function panelComponent() {
  if (globalThis.customElements?.get("smart-led-manager-visual-editor")) {
    return globalThis.customElements.get("smart-led-manager-visual-editor");
  }
  const registry = new Map();
  globalThis.HTMLElement = class {
    constructor() {
      this.isConnected = true;
    }

    attachShadow() {
      this.shadowRoot = {
        innerHTML: "",
        querySelectorAll: () => [],
        querySelector: () => null,
        getElementById: () => null,
      };
      return this.shadowRoot;
    }
  };
  globalThis.customElements = {
    define: (name, element) => registry.set(name, element),
    get: (name) => registry.get(name),
  };
  globalThis.window = {
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    confirm: () => true,
  };

  await import("../../custom_components/smart_led_manager/frontend/visual-editor-panel.mjs");
  return registry.get("smart-led-manager-visual-editor");
}

test("panel renders unified rules and uses preview/CRUD contracts", async () => {
  const Panel = await panelComponent();
  const editor = new Panel();
  const calls = [];
  let revision = "revision";
  let savedRule;
  let rejectSave = false;
  editor._hass = {
    language: "es",
    callWS: async (message) => {
      calls.push(message);
      if (message.type === "smart_led_manager/rules/preview") {
        return {
          results: [
            {
              value: 22,
              rgb: [0, 128, 128],
              hex: "#008080",
              relation: "between",
              lower: 20,
              upper: 24,
              ratio: 0.5,
            },
          ],
        };
      }
      if (message.type === "smart_led_manager/smart_rules/mutate") {
        if (rejectSave) throw { code: "conflict" };
        revision = "new-revision";
        savedRule = message.rule;
        return { revision, rule: savedRule };
      }
      if (message.type === "smart_led_manager/editor/status") {
        return { status: "ready", revision, applied_revision: revision };
      }
      return { revision, rules: savedRule ? [{ rule: savedRule }] : [], selections: {} };
    },
  };
  editor._panel = { config: { entry_id: "entry-1", version: "0.1.0-alpha.3" } };
  editor._render();
  assert.match(editor.shadowRoot.innerHTML, /Centro de administración/);
  assert.match(editor.shadowRoot.innerHTML, /0\.1\.0-alpha\.3/);
  assert.match(editor.shadowRoot.innerHTML, /\/config\/integrations\/integration\/smart_led_manager/);
  editor._selections = {
    managed_lights: [{ entity_id: "light.strip", name: "Tira del salón" }],
    zones: [], areas: [], labels: [], groups: [],
  };
  editor._selected = {
    unit: "°C",
    source: { entity_id: "sensor.temperature", name: "Temperatura del salón" },
    targets: [{ entity_id: "light.strip", name: "Tira del salón" }],
    rule: {
      id: "temperature",
      name: "Temperatura",
      source: "sensor.temperature",
      targets: ["light.strip"],
      priority: 40,
      brightness: 180,
      enabled: true,
      type: "numeric",
      target_selection: { entities: ["light.strip"], zones: [], areas: [], labels: [], groups: [], all_managed: false },
      mode: "interpolate",
      points: deepClone(points),
      rgb_color: [0, 128, 128],
    },
  };
  editor._draft = { ...deepClone(editor._selected.rule), mode: "ranges" };
  editor._original = { ...deepClone(editor._selected.rule), mode: "interpolate" };
  editor._simulateValue = "22";
  editor._revision = "revision";
  editor._runtimeStatus = "ready";

  await editor._previewNumeric();
  assert.equal(calls[0].type, "smart_led_manager/rules/preview");
  assert.equal(calls[0].rule_id, "temperature");
  assert.equal(editor._numericPreview.hex, "#008080");
  assert.match(editor.shadowRoot.innerHTML, /Temperatura/);
  assert.match(editor.shadowRoot.innerHTML, /Tira del salón/);
  assert.match(editor.shadowRoot.innerHTML, /RGB\(0, 128, 128\)/);
  assert.match(editor.shadowRoot.innerHTML, /Restaurar borrador/);
  assert.match(editor.shadowRoot.innerHTML, /Distribución numérica/);
  assert.match(editor.shadowRoot.innerHTML, /data-select-point="1"/);

  editor._restore();
  assert.equal(editor._draft.mode, "interpolate");
  editor._draft.mode = "ranges";

  await editor._save();
  assert.equal(calls[1].type, "smart_led_manager/smart_rules/mutate");
  assert.equal(calls[1].revision, "revision");
  assert.ok(calls[1].mutation_id);
  assert.equal(calls[2].type, "smart_led_manager/editor/status");
  assert.equal(editor._revision, "new-revision");
  assert.equal(editor._rules[0].rule.mode, "ranges");
  assert.equal(editor._draft, undefined);
  assert.equal(editor._view, "rules");
  assert.equal(editor._dirty(), false);
  assert.match(editor.shadowRoot.innerHTML, /Configuración guardada/);

  const callsBeforeEmptyPreview = calls.length;
  editor._selected = { rule: { id: "temperature" } };
  editor._draft = { type: "numeric", mode: "ranges", points: deepClone(points) };
  editor._simulateValue = "";
  await editor._previewNumeric();
  assert.equal(calls.length, callsBeforeEmptyPreview);
  assert.equal(editor._numericPreview, undefined);

  const pending = [];
  const callWS = editor._hass.callWS;
  editor._hass.callWS = (message) => new Promise((resolve) => pending.push({ message, resolve }));
  editor._simulateValue = "21";
  const firstPreview = editor._previewNumeric();
  editor._simulateValue = "22";
  const secondPreview = editor._previewNumeric();
  pending[1].resolve({ results: [{ hex: "#FF0000", rgb: [255, 0, 0], relation: "point", lower: 22, upper: 22 }] });
  await secondPreview;
  pending[0].resolve({ results: [{ hex: "#0000FF", rgb: [0, 0, 255], relation: "point", lower: 21, upper: 21 }] });
  await firstPreview;
  assert.equal(editor._numericPreview.hex, "#FF0000");

  editor._draft = { type: "numeric", name: "Conservar", mode: "ranges", points: deepClone(points) };
  editor._pointInput.set(0, "");
  assert.equal(editor._invalidNumeric(), true);
  assert.equal(editor._draft.points[0].value, 20);
  editor._pointInput.clear();
  editor._hass.callWS = callWS;
  rejectSave = true;
  await editor._save();
  assert.equal(editor._draft.name, "Conservar");
  assert.match(editor.shadowRoot.innerHTML, /sesión/);

  const stableEditor = new Panel();
  let rerenders = 0;
  stableEditor._render = () => { rerenders += 1; };
  stableEditor.hass = { language: "es" };
  stableEditor.hass = { language: "es", states: { changed: true } };
  assert.equal(rerenders, 1);
  stableEditor.hass = { language: "en" };
  assert.equal(rerenders, 2);

  const errorEditor = new Panel();
  errorEditor._hass = { language: "es" };
  errorEditor._panel = { config: { entry_id: "entry-1" } };
  errorEditor._view = "rules";
  errorEditor._error = "entry_not_loaded";
  errorEditor._render();
  assert.match(errorEditor.shadowRoot.innerHTML, /entry_not_loaded/);
  assert.doesNotMatch(errorEditor.shadowRoot.innerHTML, /Todavía no hay reglas/);

  editor._draft = { name: "Borrador" };
  editor._original = { name: "Original" };
  editor._goHome();
  assert.equal(editor._exitView, "home");
  assert.match(editor.shadowRoot.innerHTML, /Continuar editando/);
  editor._closeExit();
  assert.equal(editor._draft.name, "Borrador");
  editor._exitEditor("home");
  assert.equal(editor._selected, undefined);
  assert.equal(editor._view, "home");
});

test("an accepted save stays a draft until a status read confirms the applied revision", async () => {
  const Panel = await panelComponent();
  const editor = new Panel();
  let status = "failed";
  let appliedRevision = "before";
  let writes = 0;
  const rule = { id: "rule-1", type: "state", name: "Puerta" };
  editor._panel = { config: { entry_id: "lab" } };
  editor._view = "rules";
  editor._revision = "before";
  editor._runtimeStatus = "ready";
  editor._creating = true;
  editor._draft = { type: "state", name: "Puerta" };
  editor._hass = {
    language: "es",
    callWS: async ({ type }) => {
      if (type.endsWith("/mutate")) {
        writes++;
        return { revision: "accepted", rule };
      }
      if (type.endsWith("/status")) {
        return { status, entry_state: "setup_error", applied_revision: appliedRevision };
      }
      return { revision: "accepted", rules: [{ rule }] };
    },
  };
  await editor._save();
  assert.equal(editor._draft.name, "Puerta");
  assert.equal(editor._revision, "before");
  assert.match(editor.shadowRoot.innerHTML, /todavía no las aplica/);
  assert.doesNotMatch(editor.shadowRoot.innerHTML, /Configuración guardada/);
  await editor._save();
  assert.equal(writes, 1);

  status = "ready";
  appliedRevision = "accepted";
  await editor._load();
  assert.equal(editor._draft, undefined);
  assert.equal(editor._rules[0].rule.id, rule.id);
  assert.match(editor.shadowRoot.innerHTML, /Configuración guardada/);
});

test("an interrupted save is recovered by its receipt without resending a mutation", async () => {
  const Panel = await panelComponent();
  const editor = new Panel();
  let mutationId;
  let statusReads = 0;
  const rule = { id: "created-once", type: "state", name: "Presencia" };
  editor._panel = { config: { entry_id: "lab" } };
  editor._view = "rules";
  editor._revision = "before";
  editor._runtimeStatus = "ready";
  editor._creating = true;
  editor._draft = { type: "state", name: rule.name };
  editor._hass = {
    callWS: async (message) => {
      if (message.type.endsWith("/mutate")) {
        assert.equal(mutationId, undefined);
        mutationId = message.mutation_id;
        throw 3; // Home Assistant WebSocket client connection-lost error.
      }
      if (message.type.endsWith("/status")) {
        assert.equal(message.mutation_id, mutationId);
        statusReads++;
        return {
          status: statusReads === 1 ? "reloading" : "ready",
          mutation: { revision: "after", rule },
          applied_revision: statusReads === 1 ? null : "after",
        };
      }
      return { revision: "after", rules: [{ rule }] };
    },
  };
  await editor._save();
  assert.equal(statusReads, 2);
  assert.equal(editor._draft, undefined);
  assert.equal(editor._rules[0].rule.id, rule.id);
  assert.match(editor.shadowRoot.innerHTML, /Configuration saved/);
});

test("a reload between the status read and catalog read keeps the draft revision", async () => {
  const Panel = await panelComponent();
  const editor = new Panel();
  let reads = 0;
  editor._panel = { config: { entry_id: "lab" } };
  editor._view = "rules";
  editor._revision = "older";
  editor._draft = { type: "state", name: "Edit in progress" };
  editor._hass = {
    callWS: async ({ type }) => {
      if (type.endsWith("/status")) {
        reads++;
        return { status: "ready", applied_revision: reads === 1 ? "before" : "after" };
      }
      if (reads === 1) throw { code: "entry_not_loaded" };
      return { revision: "after", rules: [] };
    },
  };
  await editor._load();
  assert.equal(reads, 2);
  assert.equal(editor._runtimeStatus, "ready");
  assert.equal(editor._catalogRevision, "after");
  assert.equal(editor._revision, "older");
  assert.equal(editor._draft.name, "Edit in progress");
});
