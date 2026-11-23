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
