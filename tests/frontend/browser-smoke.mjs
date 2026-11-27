// Optional DOM regression. Run with a Chromium or Edge executable as argument.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdir, mkdtemp, readFile, realpath, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { once } from "node:events";
import { tmpdir } from "node:os";
import { basename, dirname, join } from "node:path";

const browser = process.argv[2];
if (!browser) throw new Error("Pass the path to a Chromium or Edge executable.");
const captures = process.argv[3];

const fixture = `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{font-family:system-ui,sans-serif;--primary-background-color:#f8f8f8;--card-background-color:#fff;--primary-text-color:#111;--secondary-text-color:#626262;--divider-color:#ddd;--secondary-background-color:#ececec;--input-fill-color:#fff;--primary-color:#008eaa;--text-primary-color:#fff;--success-color:#246c47;--error-color:#a92836}
:root[data-theme=dark]{color-scheme:dark;--primary-background-color:#161616;--card-background-color:#202020;--primary-text-color:#f2f2f2;--secondary-text-color:#b8b8b8;--divider-color:#444;--secondary-background-color:#252525;--input-fill-color:#343434;--primary-color:#009fc1;--text-primary-color:#080808;--success-color:#68c895;--error-color:#f48188}
body{margin:0;background:var(--primary-background-color);color:var(--primary-text-color)}output{position:absolute;clip-path:inset(50%)}
</style><output id="result">PENDING</output>
<smart-led-manager-visual-editor></smart-led-manager-visual-editor>
<script type="module">
import "/frontend/visual-editor-panel.mjs";
const result = document.querySelector("#result");
const editor = document.querySelector("smart-led-manager-visual-editor");
const root = editor.shadowRoot;
const pick = (selector) => root.querySelector(selector);
const change = (selector, value, event = "change") => {
  const field = pick(selector);
  field.value = value;
  field.dispatchEvent(new Event(event, { bubbles: true }));
};
const check = (condition, message) => { if (!condition) throw new Error(message); };
const waitFor = async (condition, message) => {
  for (let attempts = 0; attempts < 120; attempts++) {
    if (condition()) return;
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
  throw new Error(message);
};
let rule, revision = "start", applied = "start", runtime = "ready", receipt;
let conflict = false, failReload = false, loseResponse = false, mutations = 0;
const sensors = {
  temperature: ["sensor.temperature", "Temperatura Oficina", "°C", "23"],
  humidity: ["sensor.humidity", "Humedad Oficina", "%", "55"],
  power: ["sensor.power", "Potencia Sala", "W", "220"],
  energy: ["sensor.energy", "Energía acumulada Sala", "kWh", "8"],
  security: ["binary_sensor.front_door", "Puerta de entrada", null, "on"],
  presence: ["binary_sensor.living_motion", "Movimiento Sala", null, "on"],
};
const selections = {
  managed_lights: [{ entity_id: "light.a", name: "Luz Oficina" }],
  zones: [{id:"living",name:"Sala"}],
  template_sources: Object.fromEntries(Object.entries(sensors).map(([category, [id]]) => [id, category])),
};
const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
const connection = new EventTarget();
connection.subscribeEvents = async () => () => {}; // Deliberately drop lifecycle events.
const baseMode = { animation: "fixed", period: 1, brightness: 128, priority: 50, transition: null, allow_turn_on: true, expose_switch: false };
const demo = {
  managed: ["light.office", "light.living"], available: ["light.office", "light.living"],
  lights: [{entity_id:"light.office",name:"Luz Oficina"},{entity_id:"light.living",name:"Luz Sala"},{entity_id:"light.kitchen",name:"Luz Cocina"}],
  areas: [{id:"office",name:"Oficina"},{id:"living",name:"Sala"},{id:"kitchen",name:"Cocina"}],
  zones: [{zone_id:"office",name:"Oficina",area_id:"office",targets:["light.office"]},{zone_id:"living",name:"Sala",area_id:"living",targets:["light.living"]}],
  modes: [{...baseMode,mode_id:"cinema",zone_id:"living",name:"Cine",targets:["light.living"],rgb_color:[102,51,255],brightness:64},
          {...baseMode,mode_id:"reading",zone_id:"living",name:"Lectura",targets:["light.living"],rgb_color:[255,204,128],brightness:204}],
  status:{},
  engine_defaults: {tie_breaker:"newest",manual_policy:"service_only",min_command_interval:0.75},
  preferences: {show_sidebar:true,tie_breaker:"oldest",manual_policy:"temporary",min_command_interval:0.5},
};
let admin = structuredClone(demo);
let modeCalls = 0;
editor.panel = { config: { entry_id: "lab" } };
editor.hass = {
  language: "es",
  states: { "input_boolean.door": { state: "on", attributes: { friendly_name: "Puerta" } },
    ...Object.fromEntries(Object.entries(sensors).map(([category, [id, label, unit, state]]) =>
      [id, {state, attributes:{friendly_name:label, unit_of_measurement:unit, device_class:category}}])),
  },
  connection,
  callWS: async (message) => {
    if (message.type.endsWith("/status")) return {
      status: runtime, revision, applied_revision: applied,
      entry_state: runtime === "failed" ? "setup_error" : "loaded",
      mutation: receipt?.id === message.mutation_id ? receipt : null,
    };
    if (message.type.endsWith("/admin/get")) return { revision, admin: structuredClone(admin) };
    if (message.type.endsWith("/admin/diagnostics")) return {
      runtime:{version:"0.1.0-alpha.3", status:"active", managed_targets:admin.managed, winners:{"light.living":"sample"},
        requests:[{request_id:"sample",name:"Cine",priority:60}],
        request_decisions:{sample:{winning_targets:["light.living"],masked_targets:[]}},
        animation_targets:[],pending_controller_targets:[],history:[],last_error:null,
        mode_catalog:{modes:admin.modes,selected:{living:"cinema"}}},
      entry:{options:{zones:admin.zones,rules:[{enabled:true},{type:"notice",enabled:true}]}},
    };
    if (message.type.endsWith("/preview_activation")) return { result: "true" };
    if (message.type.endsWith("/preview")) return { results: [{
      hex:"#800080", rgb:[128,0,128], lower:message.points[0].value, upper:message.points.at(-1).value,
    }] };
    if (message.type.endsWith("/get")) return { revision, selections, rules: rule ? [{ rule, targets: [] }] : [] };
    if (message.type.endsWith("/admin/mode")) {
      modeCalls++;
      admin.status.living = { selected_mode_id: message.active ? message.mode_id : null, state: "winner" };
      return { status: admin.status };
    }
    if (message.type.endsWith("/admin/mutate")) {
      if (message.kind === "lights") {
        if (!message.item.targets.includes("light.office")) throw {code:"zones_use_removed_lights"};
        admin.managed = message.item.targets;
      } else if (message.kind === "zone" && message.operation === "update") {
        admin.zones = admin.zones.map((zone) => zone.zone_id === message.item_id ? message.item : zone);
      } else if (["general", "priorities"].includes(message.kind) && message.operation === "save") {
        Object.assign(admin.preferences, message.item);
      } else throw new Error("Unexpected admin mutation");
      revision = applied = "r" + (++mutations);
      return { revision, item: message.item };
    }
    if (!message.type.endsWith("/mutate")) throw new Error(message.type);
    mutations++;
    if (conflict) throw { code: "conflict" };
    rule = { ...message.rule, id: "one" };
    revision = "r" + mutations;
    runtime = failReload ? "failed" : "reloading";
    receipt = { id: message.mutation_id, revision, rule };
    if (loseResponse) {
      connection.dispatchEvent(new Event("disconnected"));
      throw { error: { code: 3 } };
    }
    return receipt;
  },
};
try {
  pick("[data-rules]").click();
  pick('[data-smart-category="smartRules"]').click();
  await waitFor(() => pick("[data-create]") && !pick("[data-create]").disabled, "Catalog did not become ready");
  pick("[data-create]").click();
  const input = pick('[data-path="name"]');
  input.focus();
  change('[data-path="name"]', "Puerta temporal", "input");
  check(root.activeElement === input, "Typing replaced the focused input");
  change('[data-path="source"]', "input_boolean.door");
  pick("[data-add-root]").click();
  change('[data-path="conditions.type"]', "not");
  change('[data-path="conditions.condition.entity_id"]', "input_boolean.door");
  change('[data-path="conditions.condition.state"]', "off", "input");
  pick("[data-schedule-enabled]").click();
  change('[data-path="schedule.after"]', "22:00");
  change('[data-path="schedule.before"]', "06:00");
  const save = pick("[data-save]");
  save.click();
  save.click();
  await tick();
  check(mutations === 1, "A double click produced two writes");
  check(pick("[data-save]")?.disabled && !pick(".notice"), "An accepted revision was presented as applied");
  check(rule.conditions.condition.entity_id === "input_boolean.door", "Condition selector did not serialize");
  check(rule.schedule.after === "22:00", "Time selector did not serialize");
  runtime = "ready";
  applied = revision;
  await waitFor(() => pick('[data-edit="one"]') && pick(".notice"), "Lost ready event blocked the editor");
  pick('[data-edit="one"]').click();
  change('[data-path="priority"]', "", "input");
  change('[data-path="priority"]', "64", "input");
  pick("[data-back]").click();
  check(pick("[data-exit-dialog]").open && root.activeElement === pick("[data-exit-continue]"), "Exit dialog did not open with safe focus");
  pick("[data-exit-continue]").click();
  check(pick('[data-path="priority"]').value === "64", "Continue editing dropped the draft");
  pick("[data-back]").click();
  pick("[data-exit-discard]").click();
  check(pick('[data-edit="one"]') && rule.priority === 40 && mutations === 1, "Discard mutated the rule");
  pick('[data-edit="one"]').click();
  change('[data-path="priority"]', "64", "input");
  failReload = true;
  pick("[data-discard]").click();
  pick("[data-exit-save]").click();
  await waitFor(() => root.textContent.includes("todavía no las aplica"), "Failed reload was not reported");
  check(pick('[data-path="priority"]').value === "64" && !pick(".notice"), "Save and exit lost the draft on failed reload");
  check(rule.priority === 64 && mutations === 2, "Update was not accepted once");
  change('[data-path="priority"]', "65", "input");
  runtime = "ready";
  applied = revision;
  pick("[data-reload]").click();
  await waitFor(() => pick("[data-save]") && !pick("[data-save]").disabled && pick(".notice"), "Editor did not recover after checking status");
  check(pick('[data-path="priority"]').value === "65", "Late confirmation overwrote a newer draft");
  failReload = false;
  conflict = true;
  change('[data-path="priority"]', "66", "input");
  pick("[data-save]").click();
  await tick();
  check(pick('[data-path="priority"]').value === "66" && pick('[role="alert"]'), "Conflict dropped the draft");
  conflict = false;
  loseResponse = true;
  pick("[data-back]").click();
  pick("[data-exit-save]").click();
  await waitFor(() => root.textContent.includes("Se perdió la conexión"), "Lost connection was not shown");
  check(pick('[data-path="priority"]').value === "66", "Disconnect lost the draft");
  runtime = "ready";
  applied = revision;
  const sent = mutations;
  connection.dispatchEvent(new Event("ready"));
  await waitFor(() => pick('[data-edit="one"]') && pick(".notice"), "Reconnect did not recover the receipt");
  check(mutations === sent && rule.priority === 66, "Reconnect resent or lost the mutation");
  loseResponse = false;
  pick("[data-smart-menu]").click();
  pick("[data-home]").click();
  check(root.querySelectorAll(".slm-tile").length === 5, "Expected exactly five home cards");
  pick('[data-admin-view="lights"]').click();
  await waitFor(() => pick("[data-admin-search]"), "Lights did not load");
  change("[data-admin-search]", "Cocina", "input");
  check([...root.querySelectorAll("[data-choice-label]")].filter((label) => !label.hidden).length === 1, "Integrated search did not filter lights");
  change("[data-admin-search]", "", "input");
  pick('[data-admin-target="light.office"]').click();
  pick("[data-save]").click();
  await waitFor(() => pick('[role="alert"]') && pick("[data-save]") && !pick("[data-save]").disabled, "Dependency failure was not retained");
  check(!pick('[data-admin-target="light.office"]').checked, "Dependency failure dropped draft");
  pick("[data-back]").click();
  pick("[data-exit-discard]").click();
  pick('[data-admin-view="zones"]').click();
  await waitFor(() => pick('[data-admin-edit="office"]') && !pick('[data-admin-edit="office"]').disabled, "Zones did not load");
  pick('[data-admin-edit="office"]').click();
  change('[data-path="name"]', "Estudio", "input");
  pick("[data-save]").click();
  await waitFor(() => pick('[data-admin-edit="office"]')?.textContent.includes("Estudio"), "Zone rename did not preserve its ID");
  pick("[data-home]").click();
  pick('[data-admin-view="modes"]').click();
  await waitFor(() => pick('[data-mode-active="cinema"]') && !pick('[data-mode-active="cinema"]').disabled, "Modes did not load");
  pick('[data-mode-active="cinema"]').click();
  await waitFor(() => pick('[data-mode-active="cinema"]')?.dataset.on === "true", "Mode selection was not shown");
  pick('[data-mode-active="reading"]').click();
  await waitFor(() => pick('[data-mode-active="reading"]')?.dataset.on === "true", "Other mode did not replace selection");
  check(pick('[data-mode-active="cinema"]').dataset.on === "false", "Modes were not exclusive");
  pick('[data-admin-edit="reading"]').click();
  change('[data-path="animation"]', "pulse");
  pick("[data-preview-effect]").click();
  check(modeCalls === 2 && pick(".slm-strip.slm-pulse"), "Preview was not local or did not start");
  pick("[data-back]").click();
  pick("[data-exit-discard]").click();
  check(location.pathname === "/smart-led-manager-editor", "The panel left its route");
  const openTemplate = async (category) => {
    editor._openView("home");
    pick("[data-rules]").click();
    if (["power","energy"].includes(category)) pick('[data-smart-category="energyMenu"]').click();
    pick('[data-smart-category="' + category + '"]').click();
    await waitFor(() => pick(".template-editor"), "Template did not open: " + category);
  };
  const fillTemplate = (category) => {
    const source = pick(".template-source");
    source.open = true;
    change('[data-path="name"]', sensors[category][1], "input");
    change('[data-path="source"]', sensors[category][0]);
    change('[data-add-choice="target_selection.zones"]', "living");
    if (["security","presence"].includes(category)) change('[data-path="state"]', "on");
  };
  const sampleTemplate = async (category) => {
    fillTemplate(category);
    if (["security","presence"].includes(category)) {
      change("[data-color]", category === "security" ? "#ff3737" : "#ffcc80");
      change("[data-template-brightness]", category === "security" ? "70" : "50", "input");
      change('[data-path="animation"]', category === "security" ? "blink" : "fixed");
      change('[data-path="release_seconds"]', category === "security" ? "8" : "0", "input");
      change("[data-state-simulation]", "on");
    } else {
      const values = {temperature:[16,36],humidity:[20,80],power:[0,3000],energy:[0,8]}[category];
      change('[data-point-value="0"]', String(values[0]), "input");
      change('[data-point-value="1"]', String(values[1]), "input");
      change("[data-simulate]", String((values[0] + values[1]) / 2), "input");
      pick("[data-preview-numeric]").click();
      await waitFor(() => pick(".template-strip[data-preview-result]"), "Sample numeric preview did not render");
    }
  };
  await openTemplate("security");
  fillTemplate("security");
  const beforeSimulation = mutations;
  change('[data-state-simulation]', "on");
  check(pick(".template-strip span").style.getPropertyValue("--preview-intensity") === "1", "State simulation did not light the preview");
  change('[data-state-simulation]', "unavailable");
  check(pick(".template-strip span").style.getPropertyValue("--preview-intensity") === "0", "Unavailable simulation kept the preview active");
  check(mutations === beforeSimulation, "State simulation wrote to the catalog");
  pick('[data-admin-expanded="template-advanced"]').open = true;
  change('[data-path="release_seconds"]', "20", "input");
  pick("[data-full-editor]").click();
  check(pick('[data-path="release_seconds"]').value === "20", "Advanced editor dropped the delay");
  await openTemplate("power");
  check(pick('[data-path="source"] option[value="sensor.power"]') &&
    !pick('[data-path="source"] option[value="sensor.energy"]'), "Energy leaked into the power selector");
  fillTemplate("power");
  check(root.textContent.includes("Unidad del sensor W"), "Power template did not bind the real unit");
  change('[data-point-value="1"]', "3000", "input");
  change('[data-simulate]', "50", "input");
  pick("[data-preview-numeric]").click();
  await waitFor(() => pick(".template-strip[data-preview-result]"), "Numeric simulation did not render");
  check(pick("svg.axis").textContent.includes("3000 (W)"), "Numeric graph did not use the edited points");
  pick("[data-save]").click();
  await tick();
  check(rule.category === "power" && rule.source_unit === "W", "Template save lost its source unit");
  runtime = "ready"; applied = revision;
  await waitFor(() => pick(".notice") && pick("[data-edit]"), "Template save did not return to the common catalog");
  const openPlan = async (category) => {
    editor._openView("home");
    pick("[data-rules]").click();
    pick('[data-smart-category="' + category + '"]').click();
    if (category === "notifications") {
      await waitFor(() => pick("[data-create]:enabled"), "Notice catalog did not open");
      pick("[data-create]").click();
    }
    await waitFor(() => pick(".plan-editor"), "C.2.4 form did not open");
  };
  await openPlan("notifications");
  const beforeNotice = mutations;
  pick("[data-simulate-notice]").click();
  check(pick(".template-strip span").style.getPropertyValue("--preview-intensity") === "0.8", "Notice did not simulate locally");
  check(mutations === beforeNotice && !pick('[data-run-notice]'), "Unsaved notice can send real commands");
  pick("[data-simulate-notice]").click();
  await openPlan("scheduleTemplate");
  check(!pick('[data-path="source"]'), "Independent schedule requires a fake source");
  change('[data-path="name"]', "Luz nocturna", "input");
  change('[data-add-choice="target_selection.zones"]', "living");
  change('[data-path="schedule.before"]', "19:00");
  check(pick("[data-save]").disabled, "Equal schedule endpoints were accepted");
  change('[data-path="schedule.before"]', "06:00");
  pick("[data-simulate-plan]").click();
  await waitFor(() => root.textContent.includes("Solicitaría la iluminación"), "Schedule preview did not render");
  await openPlan("advancedTemplate");
  change('[data-path="conditions.conditions.0.entity_id"]', "input_boolean.door");
  change('[data-path="conditions.conditions.0.state"]', "on", "input");
  change('[data-path="conditions.type"]', "or");
  check(pick('[data-path="conditions.conditions.0.entity_id"]').value === "input_boolean.door", "Changing all/any dropped the conditions");
  editor._openView("home");
  pick('[data-admin-view="settings"]').click();
  pick('[data-settings-view="priorities"]').click();
  await waitFor(() => pick('[data-save]:enabled'), "Priorities did not load");
  check(pick('[data-path="tie_breaker"]').value === "oldest", "Saved policy was replaced by the default");
  check(!pick('[data-admin-expanded="network"]').open, "Network protection expanded by default");
  pick('[data-admin-expanded="network"]').open = true;
  change('[data-path="min_command_interval"]', "0.53", "input");
  check(pick('[data-save]').disabled && !pick('[data-interval-error]').hidden, "Off-step interval was accepted");
  pick('[data-reset-preferences]').click();
  check(pick('[data-path="tie_breaker"]').value === "newest" && admin.preferences.tie_breaker === "oldest", "Reset changed persistence");
  pick('[data-discard]').click();
  pick('[data-exit-discard]').click();
  pick('[data-settings-view="general"]').click();
  await waitFor(() => pick('[data-save]:enabled'), "General did not load");
  pick('[data-admin-boolean="show_sidebar"]').click();
  pick('[data-save]').click();
  await waitFor(() => pick('.notice') && pick('[data-settings-view="general"]'), "Preferences did not confirm the applied revision");
  check(!admin.preferences.show_sidebar && admin.preferences.tie_breaker === "oldest", "General overwrote engine preferences");
  const beforeRecovery = mutations;
  pick('[data-settings-view="recovery"]').click();
  pick('[data-recovery-step="lost"]').click();
  check(pick('.slm-recovery-preview').textContent.includes('desconectada'), "Disconnect simulation did not update");
  pick('[data-recovery-step="restored"]').click();
  check(pick('.slm-recovery-preview').textContent.includes('Lectura vigente'), "Recovery simulation did not update");
  pick('[data-recovery-step="available"]').click();
  check(pick('.slm-recovery-preview').textContent.includes('Cine de ejemplo') && mutations === beforeRecovery, "Recovery simulation modified the configuration");
  pick('[data-back]').click();
  pick('[data-settings-view="diagnostics"]').click();
  await waitFor(() => pick('[data-refresh-diagnostics]:enabled') && pick('.slm-diagnostic-list'), "Diagnostics did not show data");
  check(pick('.slm-diagnostic-list').textContent.includes('Cine') && pick('.slm-diagnostic-list').textContent.includes('60'), "Diagnostics lost the request identity or priority");
  editor._openView("home");
  window.captureAdmin = async (name, theme) => {
    document.documentElement.dataset.theme = theme;
    admin = structuredClone(demo);
    editor._openView("home");
    const view = { "edit-zone":"zones", "create-zone":"zones", "draft-exit":"zones",
      "create-mode":"modes", "edit-mode":"modes", "active-mode":"modes" }[name] ?? name;
    if (name === "active-mode") admin.status.living = {selected_mode_id:"cinema", state:"winner"};
    if (name === "smart" || name === "automation-list") {
      pick("[data-rules]").click();
      if (name === "automation-list") {
        pick('[data-smart-category="smartRules"]').click();
        await waitFor(() => pick("[data-create]") && !pick("[data-create]").disabled, "Rule list did not load");
      }
    } else if (["notice", "schedule", "advanced"].includes(name)) {
      await openPlan({notice:"notifications",schedule:"scheduleTemplate",advanced:"advancedTemplate"}[name]);
      change('[data-path="name"]', {notice:"Límite de energía",schedule:"Iluminación nocturna",advanced:"Iluminar si hay presencia"}[name], "input");
      change('[data-add-choice="target_selection.zones"]', "living");
      if (name === "notice") {
        change('[data-path="animation"]', "pulse");
        pick("[data-simulate-notice]").click();
      } else {
        if (name === "advanced") {
          change('[data-path="conditions.conditions.0.entity_id"]', "input_boolean.door");
          change('[data-path="conditions.conditions.0.state"]', "on", "input");
          pick("[data-schedule-enabled]").click();
          change('[data-path="schedule.after"]', "19:00");
          change('[data-path="schedule.before"]', "23:00");
        } else {
          change('[data-path="schedule.after"]', "22:00");
          change('[data-path="schedule.before"]', "06:00");
        }
        pick("[data-simulate-plan]").click();
        await waitFor(() => root.textContent.includes("Solicitaría la iluminación"), "Draft preview did not render");
      }
    } else if (Object.hasOwn(sensors, name)) {
      await openTemplate(name);
      await sampleTemplate(name);
    } else if (name !== "home") {
      pick('[data-admin-view="' + view + '"]').click();
      if (view !== "settings") await waitFor(() => !editor._loading && editor._admin, "Administration did not load");
      if (name === "edit-zone") pick('[data-admin-edit="office"]').click();
      if (name === "draft-exit") {
        pick('[data-admin-edit="office"]').click();
        change('[data-path="name"]', "Estudio", "input");
        pick("[data-back]").click();
      }
      if (name.startsWith("create-")) pick("[data-admin-create]").click();
      if (name === "edit-mode") pick('[data-admin-edit="cinema"]').click();
      if (name === "create-mode") change('[data-path="zone_id"]', "living");
    }
    window.scrollTo(0, 0);
    const width = document.documentElement.scrollWidth;
    return { width, clientWidth: document.documentElement.clientWidth, viewport: innerWidth, heading: pick("h1")?.textContent };
  };
  result.textContent = "BROWSER_SMOKE_PASSED";
} catch (error) {
  result.textContent = "FAILED: " + (error?.stack ?? error);
}
</script>`;

const server = createServer(async (request, response) => {
  const name = /^\/frontend\/(visual-editor-panel|visual-editor-model|rule-controls|admin-views|smart-views|plan-views|settings-views)\.mjs$/.exec(request.url);
  if (name) {
    const file = new URL(`../../custom_components/smart_led_manager/frontend/${name[1]}.mjs`, import.meta.url);
    response.setHeader("Content-Type", "text/javascript");
    response.end(await readFile(file));
  } else if (request.url === "/smart-led-manager-editor") {
    response.setHeader("Content-Type", "text/html;charset=utf-8");
    response.end(fixture);
  } else {
    response.writeHead(404).end();
  }
});
server.listen(0, "127.0.0.1");
await once(server, "listening");
const temp = await realpath(tmpdir());
const profile = await mkdtemp(join(temp, "smart-led-browser-"));
const child = spawn(browser, [
  "--headless=new", "--disable-gpu", "--disable-extensions", "--no-first-run",
  `--user-data-dir=${profile}`, "--remote-debugging-port=0",
  `http://127.0.0.1:${server.address().port}/smart-led-manager-editor`,
], { windowsHide: true, stdio: ["ignore", "ignore", "ignore"] });
const exited = once(child, "close");
let socket;

async function until(callback) {
  for (let attempts = 0; attempts < 120; attempts++) {
    const result = await callback();
    if (result) return result;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("Browser timed out.");
}

try {
  const port = await until(async () => {
    try {
      return (await readFile(join(profile, "DevToolsActivePort"), "utf8")).split(/\r?\n/)[0];
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
      return null;
    }
  });
  const page = await until(async () => {
    const response = await fetch(`http://127.0.0.1:${port}/json/list`);
    const targets = await response.json();
    return targets.find((target) => target.url.endsWith("/smart-led-manager-editor"));
  });
  socket = new WebSocket(page.webSocketDebuggerUrl);
  await once(socket, "open");
  let sequence = 0;
  const send = async (method, params = {}) => {
    const id = ++sequence;
    return new Promise((resolve, reject) => {
      const receive = ({ data }) => {
        const message = JSON.parse(data);
        if (message.id !== id) return;
        socket.removeEventListener("message", receive);
        if (message.error) reject(new Error(message.error.message));
        else resolve(message.result);
      };
      socket.addEventListener("message", receive);
      socket.send(JSON.stringify({ id, method, params }));
    });
  };
  const result = await until(async () => {
    const value = await send("Runtime.evaluate", {
      expression: "document.querySelector('#result')?.textContent",
      returnByValue: true,
    });
    const state = value.result.value;
    return state === "PENDING" ? null : state;
  });
  assert.equal(result, "BROWSER_SMOKE_PASSED");
  if (captures) {
    await mkdir(captures, { recursive: true });
    const c23 = basename(captures) === "c23-evidence";
    const c24 = basename(captures) === "c24-evidence";
    const sets = c24 ? [
      {name:"desktop",theme:"light",width:1280,height:900,views:["notice","schedule","advanced"]},
      {name:"mobile",theme:"dark",width:390,height:844,views:["notice","schedule","advanced"]},
    ] : c23 ? [
      { name: "desktop", theme: "light", width: 1280, height: 900, views: ["home","smart","automation-list","temperature","humidity","power","energy","security","presence"] },
      { name: "mobile", theme: "dark", width: 390, height: 844, views: ["home","smart","temperature","energy","security","presence"] },
    ] : [
      { name: "desktop", theme: "light", width: 1280, height: 900, views: ["home", "lights", "zones", "create-zone", "edit-zone", "draft-exit", "modes", "active-mode", "create-mode", "edit-mode", "smart", "settings"] },
      { name: "mobile", theme: "dark", width: 390, height: 844, views: ["home", "lights", "edit-zone", "modes", "create-mode"] },
    ];
    for (const { name, theme, width, height, views } of sets) {
      await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
      for (const view of views) {
        const prepared = await send("Runtime.evaluate", {
          expression: "window.captureAdmin(" + JSON.stringify(view) + "," + JSON.stringify(theme) + ")",
          awaitPromise: true, returnByValue: true,
        });
        assert.equal(prepared.exceptionDetails, undefined);
        assert.equal(prepared.result.value.viewport, width);
        assert.ok(prepared.result.value.width <= prepared.result.value.clientWidth, "Horizontal overflow in " + view);
        assert.ok(prepared.result.value.heading);
        const saved = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
        await writeFile(join(captures, name + "-" + view + ".png"), Buffer.from(saved.data, "base64"));
        if (c24 || view === "create-mode" || c23 && ["temperature","humidity","power","energy","security","presence"].includes(view)) {
          const { cssContentSize } = await send("Page.getLayoutMetrics");
          const full = await send("Page.captureScreenshot", {
            format: "png", fromSurface: true, captureBeyondViewport: true,
            clip: { x: 0, y: 0, width, height: Math.ceil(cssContentSize.height), scale: 1 },
          });
          await writeFile(join(captures, name + "-" + view + "-full.png"), Buffer.from(full.data, "base64"));
        }
      }
    }
  }
} finally {
  if (socket?.readyState === WebSocket.OPEN) {
    const disconnected = once(socket, "close");
    socket.send(JSON.stringify({ id: 1_000_000, method: "Browser.close" }));
    let timer;
    await Promise.race([
      disconnected,
      new Promise((resolve) => { timer = setTimeout(resolve, 3000); }),
    ]);
    clearTimeout(timer);
  }
  socket?.close();
  if (child.exitCode === null) child.kill();
  await exited;
  server.close();
  const resolved = await realpath(profile);
  if (dirname(resolved) === temp && basename(resolved).startsWith("smart-led-browser-")) {
    await rm(resolved, { recursive: true, force: true, maxRetries: 4 });
  }
}
process.stdout.write("Browser smoke test passed.\n");
