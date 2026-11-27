// Local controls for the custom panel. Home Assistant provides the data and
// Python validates the saved rule. The browser does not evaluate conditions.
export const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g,
  (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);

export const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const NUMERIC_DOMAINS = ["number", "input_number", "counter"];
const INVALID_STATES = new Set(["unknown", "unavailable"]);

export const CONTROL_TEXT = {
  es: {
    search: "Buscar", choose: "Seleccionar", add: "Agregar", addCondition: "Agregar condición",
    moveUp: "Subir", moveDown: "Bajar", and: "Todas (AND)", or: "Al menos una (OR)",
    not: "Negar (NOT)", time: "Horario", after: "Hora de inicio", before: "Hora de fin",
    days: ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
    midnight: "Cruza medianoche. El día seleccionado corresponde al inicio.",
    scheduled: "Limitar por horario", seconds: "Segundos", minutes: "Minutos", hours: "Horas",
    dwellHelp: "Tiempo que la condición debe mantenerse antes de activar.",
    durationHelp: "Tiempo durante el que se mantiene una solicitud de evento.",
    transitionHelp: "Transición de la luz en segundos.", interval: "Intervalo mínimo entre cambios (s)",
    variability: "Variación mínima del sensor", trigger_state: "Cambio de estado",
    event_bus: "Evento del bus", event_entity: "Entidad de evento", input_button: "Pulsación de un ayudante",
    device: "Disparador de dispositivo", deviceName: "Dispositivo", deviceTrigger: "Disparador publicado",
    triggerFrom: "Estado anterior (opcional)", triggerTo: "Estado nuevo (opcional)",
    eventName: "Nombre del evento", eventKey: "Clave", eventValue: "Valor",
    advanced: "Disparador avanzado (conservado)", replaceTrigger: "Reemplazar disparador",
    advancedHelp: "El disparador guardado conserva sus parámetros. Puedes reemplazarlo de forma explícita.",
    duplicateTargets: "Duplicados eliminados", fixedColor: "Color fijo", unsafe: "Selección insegura",
    reloadingEntry: "Recargando la integración…", failedReload: "La integración no pudo volver a cargar.",
    intervalResult: "Intervalo", busyDevices: "Consultando disparadores…",
  },
  en: {
    search: "Search", choose: "Select", add: "Add", addCondition: "Add condition",
    moveUp: "Move up", moveDown: "Move down", and: "All (AND)", or: "Any (OR)",
    not: "Negate (NOT)", time: "Schedule", after: "Start time", before: "End time",
    days: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    midnight: "Crosses midnight. The selected day is the start day.",
    scheduled: "Limit to schedule", seconds: "Seconds", minutes: "Minutes", hours: "Hours",
    dwellHelp: "How long the condition must hold before activation.",
    durationHelp: "How long an event request remains active.",
    transitionHelp: "Light transition in seconds.", interval: "Minimum interval between changes (s)",
    variability: "Minimum sensor change", trigger_state: "State change",
    event_bus: "Bus event", event_entity: "Event entity", input_button: "Helper button press",
    device: "Device trigger", deviceName: "Device", deviceTrigger: "Published trigger",
    triggerFrom: "Previous state (optional)", triggerTo: "New state (optional)",
    eventName: "Event name", eventKey: "Key", eventValue: "Value",
    advanced: "Advanced trigger (preserved)", replaceTrigger: "Replace trigger",
    advancedHelp: "The saved trigger keeps its parameters. You can explicitly replace it.",
    duplicateTargets: "Duplicates removed", fixedColor: "Fixed color", unsafe: "Unsafe selection",
    reloadingEntry: "Reloading the integration…", failedReload: "The integration failed to reload.",
    intervalResult: "Interval", busyDevices: "Loading triggers…",
  },
};

export function entityItems(states, registered, kind) {
  const byId = new Map((registered ?? []).map((item) => [item.entity_id, item]));
  for (const [id, entity] of Object.entries(states ?? {})) {
    const attributes = entity.attributes ?? {};
    byId.set(id, {
      ...byId.get(id), entity_id: id,
      name: attributes.friendly_name ?? byId.get(id)?.name ?? id,
      state: entity.state, unit: attributes.unit_of_measurement,
      icon: attributes.icon, options: attributes.options ?? attributes.hvac_modes ?? attributes.preset_modes,
      deviceClass: attributes.device_class, stateClass: attributes.state_class,
    });
  }
  return [...byId.values()].filter((item) => {
    const domain = item.entity_id.split(".")[0];
    if (kind === "numeric") {
      if (NUMERIC_DOMAINS.includes(domain)) return true;
      if (item.state?.trim() && Number.isFinite(Number(item.state))) return true;
      if (domain !== "sensor" || ["enum", "date", "timestamp"].includes(item.deviceClass)) return false;
      return Boolean(item.unit || item.stateClass || !item.state || INVALID_STATES.has(item.state));
    }
    if (kind === "input_button" || kind === "event") return domain === kind;
    return !["event", "input_button", "button"].includes(domain) || kind === "trigger_state";
  }).sort((a, b) => a.name.localeCompare(b.name));
}

export function stateOptions(entity, current) {
  const domain = entity?.entity_id.split(".")[0];
  const known = {
    binary_sensor: ["on", "off"], input_boolean: ["on", "off"],
    light: ["on", "off"], switch: ["on", "off"], lock: ["locked", "unlocked"],
    person: ["home", "not_home"], device_tracker: ["home", "not_home"],
    sun: ["above_horizon", "below_horizon"],
    alarm_control_panel: ["disarmed", "armed_home", "armed_away", "armed_night", "armed_vacation", "armed_custom_bypass", "pending", "arming", "disarming", "triggered"],
  };
  return [...new Set([...(Array.isArray(entity?.options) ? entity.options : known[domain] ?? []),
    entity?.state, current].filter((value) => value && !INVALID_STATES.has(value)))];
}

const idFor = (item) => item.id ?? item.entity_id;

export function picker(text, path, items, selected, t, multiple = false) {
  const ids = multiple ? selected ?? [] : selected ? [selected] : [];
  const names = new Map(items.map((item) => [idFor(item), item.name]));
  const choices = items.filter((item) => !multiple || !ids.includes(idFor(item)));
  if (!multiple && selected && !names.has(selected)) choices.unshift({ id: selected, name: selected });
  const chips = multiple ? ids.map((id) =>
    `<button type="button" class="chip" data-remove-choice="${escapeHtml(path)}" data-choice="${escapeHtml(id)}" aria-label="${escapeHtml(t.remove + ' ' + (names.get(id) ?? id))}">${escapeHtml(names.get(id) ?? id)} ×</button>`
  ).join("") : "";
  return `<div class="picker" data-picker="${escapeHtml(path)}">
    <label>${text}<input type="search" data-search="${escapeHtml(path)}" placeholder="${t.search}"></label>
    <select aria-label="${text}" data-${multiple ? "add-choice" : "path"}="${escapeHtml(path)}">
      <option value="">${multiple ? t.add : t.choose}</option>
      ${choices.map((item) => {
        const id = idFor(item);
        const details = [item.icon, item.state, item.unit, item.entity_id].filter(Boolean).join(" · ");
        const label = details ? `${item.name} (${details})` : item.name;
        return `<option value="${escapeHtml(id)}" ${!multiple && id === selected ? "selected" : ""}>${escapeHtml(label)}</option>`;
      }).join("")}
    </select><div class="chips">${chips}</div></div>`;
}

export function selectField(label, path, items, value) {
  return `<label>${label}<select data-path="${path}">${items.map(([id, text]) =>
    `<option value="${escapeHtml(id)}" ${id === value ? "selected" : ""}>${escapeHtml(text)}</option>`
  ).join("")}</select></label>`;
}

export function inputField(label, path, value, type = "text", attributes = "") {
  return `<label>${label}<input type="${type}" data-path="${path}" value="${escapeHtml(value)}" ${attributes}></label>`;
}

export const numberField = (label, path, value, attributes = 'step="any"') =>
  inputField(label, path, value, "number", attributes);

export function scheduleControls(path, value, t) {
  return `<div class="form-grid">
    ${inputField(t.after, path + ".after", value.after, "time")}
    ${inputField(t.before, path + ".before", value.before, "time")}
    </div><div class="chips">${DAYS.map((day, index) =>
      `<label class="check"><input type="checkbox" data-day-path="${path}.weekdays" value="${day}" ${value.weekdays?.includes(day) ? "checked" : ""}>${t.days[index]}</label>`
    ).join("")}</div>
    ${value.after > value.before ? `<p class="muted">${t.midnight}</p>` : ""}`;
}

export const defaultSchedule = () => ({ after: "00:00", before: "00:00", weekdays: [...DAYS] });

export function newCondition(kind) {
  switch (kind) {
    case "and": case "or": return { type: kind, conditions: [newCondition("state")] };
    case "not": return { type: kind, condition: newCondition("state") };
    case "time": return { type: kind, ...defaultSchedule() };
    case "numeric": return { type: kind, entity_id: "", operator: "above", threshold: null };
    default: return { type: "state", entity_id: "", operator: "equals", state: "" };
  }
}

export function treeSize(node) {
  if (!node) return 0;
  if (node.type === "not") return 1 + treeSize(node.condition);
  return 1 + (node.conditions ?? []).reduce((total, child) => total + treeSize(child), 0);
}

export function numericControls(path, data, t, unit, hysteresis = false, allowEmpty = hysteresis) {
  const label = (text) => unit ? `${text} (${escapeHtml(unit)})` : text;
  const options = ["above", "below", "inside", "outside"].map((operator) => [operator, t[operator]]);
  if (allowEmpty) options.unshift(["", t.noThreshold]);
  return `<div class="form-grid">
    ${selectField(t.operator, path + ".operator", options, data?.operator ?? "")}
    ${["above", "below"].includes(data?.operator)
      ? numberField(label(t.threshold), path + ".threshold", data.threshold) : ""}
    ${["inside", "outside"].includes(data?.operator)
      ? numberField(label(t.lower), path + ".lower", data.lower) +
        numberField(label(t.upper), path + ".upper", data.upper) : ""}
    ${hysteresis && data?.operator
      ? numberField(label(t.hysteresis), path + ".hysteresis", data.hysteresis ?? 0, 'min="0" step="any"') : ""}
    </div>`;
}

export function stateControl(path, entity, value, t) {
  return `<label>${t.expected}<input data-path="${path}" value="${escapeHtml(value)}"
    list="state-${path}"><datalist id="state-${path}">
    ${stateOptions(entity, value).map((item) => `<option value="${escapeHtml(item)}"></option>`).join("")}
    </datalist></label>`;
}

export function conditionControls(root, context) {
  const { t, entities, numeric, simple = false, hysteresis = false } = context;
  if (!root) return `<button data-add-root>${t.addCondition}</button>`;
  function render(node, path, depth, index, count) {
    const kinds = ["state", "numeric", "time"];
    if (simple) {
      kinds.pop();
      if (depth === 1) kinds.splice(0, 2, "and", "or");
    } else if (depth < 5) kinds.push("and", "or", "not");
    const kind = selectField(t.type, path + ".type", kinds.map((key) =>
      [key, simple && key === "and" ? t.matchAll : simple && key === "or" ? t.matchAny : t[key]]), node.type);
    const buttons = `<div class="chips">
      ${index > 0 ? `<button data-move-condition="${path}" data-delta="-1" aria-label="${t.moveUp}">↑</button>` : ""}
      ${index < count - 1 ? `<button data-move-condition="${path}" data-delta="1" aria-label="${t.moveDown}">↓</button>` : ""}
      ${count > 1 || depth === 1 && !simple ? `<button data-remove-condition="${path}">${t.remove}</button>` : ""}
      </div>`;
    let body = "";
    if (node.type === "and" || node.type === "or") {
      body = node.conditions.map((child, index) => render(child, `${path}.conditions.${index}`, depth + 1, index, node.conditions.length)).join("");
      if (node.conditions.length < 16 && treeSize(root) < 32) {
        body += `<button data-add-condition="${path}">${t.addCondition}</button>`;
      }
    } else if (node.type === "not") {
      body = render(node.condition, path + ".condition", depth + 1, 0, 1);
    } else if (node.type === "time") {
      body = scheduleControls(path, node, t);
    } else {
      const items = node.type === "numeric" ? numeric : entities;
      const entity = items.find((item) => item.entity_id === node.entity_id);
      body = picker(t.entity, path + ".entity_id", items, node.entity_id, t);
      body += node.type === "numeric" ? numericControls(path, node, t, entity?.unit, hysteresis, false)
        : `<div class="form-grid">
          ${selectField(t.operator, path + ".operator", [["equals", t.equals], ["not_equals", t.notEquals]], node.operator)}
          ${stateControl(path + ".state", entity, node.state, t)}</div>`;
    }
    return `<fieldset class="condition">${kind}${body}${buttons}</fieldset>`;
  }
  return render(root, "conditions", 1, 0, 1);
}

export function triggerKind(trigger) {
  if (!trigger) return "event_bus";
  const platform = trigger.platform ?? trigger.trigger;
  const entity = trigger.entity_id;
  const keys = Object.keys(trigger).filter((key) => !["platform", "trigger"].includes(key));
  const only = (...allowed) => keys.every((key) => allowed.includes(key));
  if (platform === "device") return "device";
  if (platform === "event" && typeof trigger.event_type === "string" &&
      only("event_type", "event_data") && Object.values(trigger.event_data ?? {}).every(
        (value) => typeof value === "string")) return "event_bus";
  if (platform === "state" && typeof entity === "string" && only("entity_id", "from", "to") &&
      [trigger.from, trigger.to].every((value) => value == null || typeof value === "string")) {
    if (trigger.from === undefined && (trigger.to == null || trigger.to === "") &&
        only("entity_id", "to")) {
      if (entity.startsWith("input_button.")) return "input_button";
      if (entity.startsWith("event.")) return "event_entity";
    }
    return "trigger_state";
  }
  return "advanced";
}
