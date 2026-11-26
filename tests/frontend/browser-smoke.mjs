// Optional DOM regression. Run with a Chromium or Edge executable as argument.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, realpath, rm } from "node:fs/promises";
import { createServer } from "node:http";
import { once } from "node:events";
import { tmpdir } from "node:os";
import { basename, dirname, join } from "node:path";

const browser = process.argv[2];
if (!browser) throw new Error("Pass the path to a Chromium or Edge executable.");

const fixture = `<!doctype html><meta charset="utf-8"><output id="result">PENDING</output>
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
const selections = { managed_lights: [{ entity_id: "light.a", name: "Demo A" }] };
const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
const connection = new EventTarget();
connection.subscribeEvents = async () => () => {}; // Deliberately drop lifecycle events.
editor.panel = { config: { entry_id: "lab" } };
editor.hass = {
  language: "es",
  states: { "input_boolean.door": { state: "on", attributes: { friendly_name: "Puerta" } } },
  connection,
  callWS: async (message) => {
    if (message.type.endsWith("/status")) return {
      status: runtime, revision, applied_revision: applied,
      entry_state: runtime === "failed" ? "setup_error" : "loaded",
      mutation: receipt?.id === message.mutation_id ? receipt : null,
    };
    if (message.type.endsWith("/get")) return { revision, selections, rules: rule ? [{ rule, targets: [] }] : [] };
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
  check(location.pathname === "/smart-led-manager-editor", "The panel left its route");
  result.textContent = "BROWSER_SMOKE_PASSED";
} catch (error) {
  result.textContent = "FAILED: " + (error?.stack ?? error);
}
</script>`;

const server = createServer(async (request, response) => {
  const name = /^\/frontend\/(visual-editor-panel|visual-editor-model|rule-controls)\.mjs$/.exec(request.url);
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
