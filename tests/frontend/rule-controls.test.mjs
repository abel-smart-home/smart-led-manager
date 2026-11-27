import assert from "node:assert/strict";
import test from "node:test";
import {
  CONTROL_TEXT,
  conditionControls,
  entityItems,
  newCondition,
  picker,
  scheduleControls,
  stateOptions,
  treeSize,
  triggerKind,
} from "../../custom_components/smart_led_manager/frontend/rule-controls.mjs";

const t = {
  ...CONTROL_TEXT.es, entity: "Entidad", remove: "Eliminar",
  type: "Tipo", state: "Estado", numeric: "Numérica", operator: "Operador",
  equals: "Igual", notEquals: "Distinto", expected: "Valor",
};

test("catalog retains temporarily unavailable numeric entities and filters button kinds", () => {
  const states = {
    "sensor.temp": { state: "unavailable", attributes: { friendly_name: "Temperatura", unit_of_measurement: "°C" } },
    "switch.test": { state: "on", attributes: {} },
    "input_button.test": { state: "2026-11-24", attributes: {} },
  };
  const registered = [{ entity_id: "number.late", name: "Temperatura ausente" }];
  const numeric = entityItems(states, registered, "numeric");
  assert.deepEqual(numeric.map((item) => item.entity_id), ["sensor.temp", "number.late"]);
  assert.deepEqual(stateOptions(numeric[0]), []);
  assert.deepEqual(entityItems(states, registered, "input_button").map((item) => item.entity_id), ["input_button.test"]);
  assert.match(picker("Origen", "source", numeric, "sensor.temp", t), /Temperatura \(unavailable · °C · sensor.temp\)/);
});

test("nested condition controls use the shared tree paths and time fields", () => {
  const tree = newCondition("and");
  tree.conditions.push(newCondition("not"), newCondition("time"));
  tree.conditions[2].after = "22:00";
  tree.conditions[2].before = "06:00";
  assert.equal(treeSize(tree), 5);
  const controls = conditionControls(tree, { t, entities: [], numeric: [] });
  assert.match(controls, /conditions\.conditions\.1\.condition\.entity_id/);
  assert.match(controls, /data-move-condition="conditions\.conditions\.2"/);
  assert.match(controls, /Cruza medianoche/);
  assert.doesNotMatch(controls, /textarea/);
  assert.equal((scheduleControls("schedule", tree.conditions[2], t).match(/checked/g) ?? []).length, 7);
});

test("trigger chooser preserves native variants it cannot faithfully edit", () => {
  assert.equal(triggerKind({ platform: "state", entity_id: "input_button.door" }), "input_button");
  assert.equal(triggerKind({ platform: "state", entity_id: "event.door" }), "event_entity");
  assert.equal(triggerKind({ platform: "event", event_type: "door", event_data: { status: "open" } }), "event_bus");
  assert.equal(triggerKind({ platform: "event", event_type: "door", event_data: { count: 1 } }), "advanced");
  assert.equal(triggerKind({ platform: "state", entity_id: "sensor.value", for: 30 }), "advanced");
  assert.equal(triggerKind({ platform: "device", domain: "demo", device_id: "test" }), "device");
});
