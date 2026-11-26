// Capture the installed panel, including the native Home Assistant shell.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { once } from "node:events";
import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

const origin = "http://127.0.0.1:8123";
const client = origin + "/";
const username = "visual-test";
const password = randomUUID();
const [chrome, output] = process.argv.slice(2);
assert.ok(chrome && output, "Pass the browser executable and an output directory");
const sources = {
  temperature: ["sensor.office_temperature", "Temperatura Oficina", "temperature", "°C", "23"],
  humidity: ["sensor.office_humidity", "Humedad Oficina", "humidity", "%", "55"],
  power: ["sensor.living_power", "Potencia Sala", "power", "W", "220"],
  energy: ["sensor.living_energy", "Energía acumulada Sala", "energy", "kWh", "8"],
  security: ["binary_sensor.front_door", "Puerta de entrada", "door", null, "on"],
  presence: ["binary_sensor.living_motion", "Movimiento Sala", "motion", null, "on"],
};

async function waitFor(check, label, seconds = 20) {
  const end = Date.now() + seconds * 1000;
  while (Date.now() < end) {
    const result = await check();
    if (result) return result;
    await delay(160);
  }
  throw Error("Timed out waiting for " + label);
}

let access;
async function api(path, data) {
  const form = data instanceof URLSearchParams;
  const response = await fetch(origin + path, {
    method: data ? "POST" : "GET",
    headers: {
      ...(data && !form && { "Content-Type": "application/json" }),
      ...(access && { Authorization: "Bearer " + access }),
    },
    body: data && (form ? data : JSON.stringify(data)),
  });
  assert.ok(response.ok, path + " returned HTTP " + response.status);
  return response.json();
}

await waitFor(async () => {
  try { return (await fetch(origin + "/api/onboarding")).ok; }
  catch { return false; }
}, "Home Assistant", 180);
const { auth_code } = await api("/api/onboarding/users", {
  client_id: client, name: "Validación visual", username, password, language: "es",
});
const auth = await api("/auth/token", new URLSearchParams({
  grant_type: "authorization_code", client_id: client, code: auth_code,
}));
access = auth.access_token;
const light = "light.office";
await api("/api/states/" + light, {
  state: "off", attributes: { friendly_name: "Luz Oficina", supported_color_modes: ["rgb"] },
});
for (const [id, name, deviceClass, unit, state] of Object.values(sources)) {
  await api("/api/states/" + id, {
    state, attributes: { friendly_name: name, device_class: deviceClass, ...(unit && { unit_of_measurement: unit }) },
  });
}
const flow = await api("/api/config/config_entries/flow", { handler: "smart_led_manager" });
const entry = await api("/api/config/config_entries/flow/" + flow.flow_id, { lights: [light] });
assert.equal(entry.type, "create_entry");

const profile = await mkdtemp(join(tmpdir(), "slm-ha-browser-"));
const browser = spawn(chrome, [
  "--headless=new", "--disable-gpu", "--disable-extensions", "--no-first-run",
  "--lang=es", "--no-sandbox", "--remote-debugging-port=0", "--user-data-dir=" + profile, "about:blank",
], { stdio: "ignore" });
const exited = once(browser, "close");
let socket;
try {
  const port = await waitFor(async () => {
    try { return (await readFile(join(profile, "DevToolsActivePort"), "utf8")).split(/\r?\n/)[0]; }
    catch (error) { if (error.code !== "ENOENT") throw error; }
  }, "Chromium");
  const pages = await (await fetch("http://127.0.0.1:" + port + "/json/list")).json();
  socket = new WebSocket(pages.find((item) => item.type === "page").webSocketDebuggerUrl);
  await once(socket, "open");
  let id = 0;
  function send(method, params = {}) {
    const request = ++id;
    return new Promise((resolve, reject) => {
      const receive = ({ data }) => {
        const reply = JSON.parse(data);
        if (reply.id !== request) return;
        socket.removeEventListener("message", receive);
        if (reply.error) reject(Error(method + ": " + reply.error.message));
        else resolve(reply.result);
      };
      socket.addEventListener("message", receive);
      socket.send(JSON.stringify({ id: request, method, params }));
    });
  }
  async function run(expression) {
    const response = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    assert.ok(!response.exceptionDetails, "Chromium could not operate the panel");
    return response.result.value;
  }
  const sentCommands = new Map();
  socket.addEventListener("message", ({ data }) => {
    const event = JSON.parse(data);
    if (event.method === "Network.webSocketFrameSent" || event.method === "Network.webSocketFrameReceived") {
      try {
        const payload = JSON.parse(event.params.response.payloadData);
        if (event.method.endsWith("Sent") && payload.id) sentCommands.set(payload.id, payload.type);
        if (payload.success === false) console.log("WebSocket", sentCommands.get(payload.id), payload.error?.code);
      } catch { /* Non-JSON control frame. */ }
    }
    if (event.method === "Runtime.exceptionThrown") {
      console.log("Browser", event.params.exceptionDetails.text, event.params.exceptionDetails.exception?.className);
    }
    if (event.method === "Network.responseReceived" && event.params.response.status >= 400) {
      console.log("HTTP", event.params.response.status, new URL(event.params.response.url).pathname);
    }
  });
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Network.enable");
  await send("Network.setExtraHTTPHeaders", { headers: { "Accept-Language": "es-ES,es;q=0.9" } });
  await send("Page.addScriptToEvaluateOnNewDocument", { source: `
    if (location.origin === ${JSON.stringify(origin)}) {
      localStorage.setItem("selectedLanguage", JSON.stringify("es"));
    }
    function panel(root = document) {
      const direct = root.querySelector("smart-led-manager-visual-editor");
      if (direct) return direct;
      for (const node of root.querySelectorAll("*")) {
        if (node.shadowRoot) {
          const nested = panel(node.shadowRoot);
          if (nested) return nested;
        }
      }
    }
    window.pick = (selector) => panel()?.shadowRoot?.querySelector(selector);
    window.click = (selector) => pick(selector).click();
    window.change = (selector, value, event) => {
      const field = pick(selector);
      field.value = value;
      field.dispatchEvent(new Event(event, {bubbles: true}));
    };
  ` });
  const panelUrl = origin + "/smart-led-manager-editor";
  await send("Page.navigate", { url: panelUrl });
  await waitFor(() => run("location.pathname === '/auth/authorize'"), "the Home Assistant sign-in");
  const query = new URLSearchParams(await run("location.search"));
  const redirect = new URL(query.get("redirect_uri"));
  assert.equal(redirect.origin, origin);
  assert.equal(query.get("client_id"), client);
  const loginArgs = Object.fromEntries(["client_id", "redirect_uri", "code_challenge", "code_challenge_method", "response_type"]
    .filter((key) => query.has(key)).map((key) => [key, query.get(key)]));
  const login = await api("/auth/login_flow", { ...loginArgs, handler: ["homeassistant", null] });
  const completed = await api("/auth/login_flow/" + login.flow_id, { client_id: client, username, password });
  assert.equal(completed.type, "create_entry");
  redirect.searchParams.set("code", completed.result);
  redirect.searchParams.set("state", query.get("state"));
  redirect.searchParams.set("storeToken", "true");
  await send("Page.navigate", { url: redirect.href });
  await waitFor(() => run("typeof pick === 'function' && !!pick('.slm-tile')"), "the initial authenticated panel", 50);
  await mkdir(output, { recursive: true });
  const sets = [
    ["desktop", "light", 1280, 900, ["home", "smart", "smartRules", ...Object.keys(sources)]],
    ["mobile", "dark", 390, 844, ["home", "smart", "temperature", "energy", "security", "presence"]],
  ];
  for (const [device, theme, width, height, views] of sets) {
    await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
    await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: theme }] });
    for (const view of views) {
      await send("Page.navigate", { url: panelUrl });
      try {
        await waitFor(() => run("typeof pick === 'function' && !!pick('.slm-tile')"), "the installed panel", 40);
      } catch (error) {
        console.log(await run(`({path: location.pathname, ready: document.readyState,
          tags: Array.from(document.body.children, (element) => element.tagName),
          panelRegistered: !!customElements.get('smart-led-manager-visual-editor')})`));
        throw error;
      }
      if (view !== "home") await run("click('[data-rules]')");
      if (view === "smartRules") {
        await run("click('[data-smart-category=smartRules]')");
        await waitFor(() => run("!!pick('[data-create]:enabled')"), "the shared catalog");
      }
      if (Object.hasOwn(sources, view)) {
        if (["power", "energy"].includes(view)) await run("click('[data-smart-category=energyMenu]')");
        await run("click('[data-smart-category=" + view + "]')");
        await waitFor(() => run("!!pick('.template-editor')"), view);
        const [entity, name] = sources[view];
        await run(`pick(".template-source").open = true;
          change('[data-path="name"]', ${JSON.stringify(name)}, 'input');
          change('[data-path="source"]', ${JSON.stringify(entity)}, 'change');
          change('[data-add-choice="target_selection.entities"]', "${light}", 'change');`);
        if (["security", "presence"].includes(view)) await run("change('[data-path=state]', 'on', 'change')");
        assert.ok(await run("!!pick('[data-save]:enabled')"), "Invalid draft for " + view);
      }
      await run("document.fonts.ready.then(() => true)");
      await delay(700); // Allow the native startup overlay to finish fading.
      const screenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
      await writeFile(join(output, device + "-" + view + ".png"), Buffer.from(screenshot.data, "base64"));
      console.log(device, view, await run("pick('h1').textContent"));
      if (view === "home") {
        const layout = await run(`({
          columns: getComputedStyle(pick(".slm-grid")).gridTemplateColumns.split(" ").length,
          width: pick(".slm-home").getBoundingClientRect().width,
          targets: [...pick(".slm-grid").children].map((button) => button.getBoundingClientRect().height),
        })`);
        assert.equal(layout.columns, device === "desktop" ? 2 : 1);
        assert.ok(layout.width <= 1000 && layout.targets.length === 5 && layout.targets.every((size) => size >= 44));
        await send("Page.bringToFront");
        assert.ok(await run(`(() => {
          const tile = pick("[data-rules]");
          tile.focus();
          return tile.matches(":focus");
        })()`), "The smart lighting tile did not accept keyboard focus");
        const space = { key: " ", code: "Space", windowsVirtualKeyCode: 32, nativeVirtualKeyCode: 32 };
        await send("Input.dispatchKeyEvent", { type: "keyDown", ...space, text: " ", unmodifiedText: " " });
        await send("Input.dispatchKeyEvent", { type: "keyUp", ...space });
        await waitFor(() => run("!!pick('[data-smart-category=smartRules]')"), "keyboard navigation");
      }
    }
  }
} finally {
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ id: 999999, method: "Browser.close" }));
  socket?.close();
  browser.kill();
  await exited;
}
