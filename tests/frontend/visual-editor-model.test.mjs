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

test("panel renders a rule draft and uses WebSocket preview/save contracts", async () => {
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
  const Panel = registry.get("smart-led-manager-visual-editor");
  const editor = new Panel();
  const calls = [];
  editor._hass = {
    language: "es",
    callWS: async (message) => {
      calls.push(message);
      if (message.type.endsWith("/preview")) {
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
      return {
        revision: "new-revision",
        rule: { ...editor._selected.rule, mode: message.mode, points: message.points },
      };
    },
  };
  editor._panel = { config: { entry_id: "entry-1" } };
  editor._selected = {
    unit: "°C",
    rule: {
      id: "temperature",
      name: "Temperatura",
      source: "sensor.temperature",
      targets: ["light.strip"],
      priority: 40,
      brightness: 180,
      enabled: true,
      mode: "interpolate",
      points: deepClone(points),
    },
  };
  editor._original = { mode: "interpolate", points: deepClone(points) };
  editor._draft = { mode: "ranges", points: deepClone(points) };
  editor._simulatedValue = "22";
  editor._revision = "revision";

  await editor._requestPreview();
  assert.equal(calls[0].type, "smart_led_manager/rules/preview");
  assert.equal(calls[0].rule_id, "temperature");
  assert.equal(editor._preview.hex, "#008080");
  assert.match(editor.shadowRoot.innerHTML, /Temperatura/);
  assert.match(editor.shadowRoot.innerHTML, /RGB\(0, 128, 128\)/);

  await editor._save();
  assert.equal(calls[1].type, "smart_led_manager/rules/save");
  assert.equal(calls[1].revision, "revision");
  assert.equal(editor._revision, "new-revision");
  assert.equal(editor._original.mode, "ranges");
});
