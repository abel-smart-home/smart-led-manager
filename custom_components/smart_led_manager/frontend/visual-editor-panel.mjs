import {
  cssGradient,
  deepClone,
  hexToRgb,
  nextPoint,
  removePoint,
  replacePoint,
  rgbToHex,
  sortPoints,
  validateDraft,
} from "./visual-editor-model.mjs";

const TEXT = {
  es: {
    admin: "Centro de administración",
    subtitle: "Reglas inteligentes locales para las luces administradas.",
    version: "Versión instalada",
    smartRules: "Reglas inteligentes",
    smartDescription: "Crea y administra reglas de estado, numéricas y de eventos.",
    native: "Configuración nativa",
    nativeDescription: "Alternativa compatible mediante el Options Flow de Home Assistant.",
    open: "Abrir",
    home: "Inicio",
    create: "Crear regla",
    edit: "Editar",
    duplicate: "Duplicar",
    enable: "Habilitar",
    disable: "Deshabilitar",
    remove: "Eliminar",
    confirmDelete: "¿Eliminar esta regla?",
    noRules: "Todavía no hay reglas.",
    loading: "Cargando…",
    reload: "Recargar",
    enabled: "Habilitada",
    disabled: "Deshabilitada",
    priority: "Prioridad",
    source: "Origen",
    targets: "Destinos",
    conditions: "Condiciones",
    schedule: "Horario",
    general: "1. Información general",
    origin: "2. Origen o disparador",
    conditionSection: "3. Condiciones",
    timeSection: "4. Horarios y permanencia",
    targetSection: "5. Destinos",
    colorSection: "6. Color y estilo",
    policySection: "7. Prioridad y duración",
    summarySection: "8. Resumen y guardado",
    name: "Nombre",
    type: "Tipo",
    state: "Estado",
    numeric: "Numérica",
    event: "Evento",
    entity: "Entidad",
    operator: "Operador",
    expected: "Estado esperado",
    equals: "Es igual",
    notEquals: "Es distinto",
    trigger: "Disparador oficial de Home Assistant (JSON)",
    conditionJson: "Árbol AND/OR/NOT (JSON, opcional)",
    scheduleJson: "Horario (JSON, opcional)",
    dwell: "Permanencia mínima (segundos)",
    individual: "Luces individuales",
    zones: "Zonas Smart LED Manager",
    areas: "Áreas de Home Assistant",
    labels: "Etiquetas de Home Assistant",
    groups: "Grupos de luces transparentes",
    allManaged: "Todas las luces administradas",
    previewTargets: "Previsualizar destinos",
    excluded: "Excluidas por autorización",
    color: "Color",
    brightness: "Brillo",
    transition: "Transición",
    animation: "Animación",
    fixed: "Fija",
    blink: "Parpadeo",
    pulse: "Pulsación",
    period: "Periodo",
    duration: "Duración del evento (segundos)",
    activation: "Activación numérica",
    noThreshold: "Siempre activa",
    above: "Por encima",
    below: "Por debajo",
    inside: "Dentro del rango",
    outside: "Fuera del rango",
    threshold: "Umbral",
    lower: "Límite inferior",
    upper: "Límite superior",
    hysteresis: "Histéresis",
    calculation: "Cálculo de color",
    interpolate: "Interpolación",
    ranges: "Rangos",
    points: "Puntos de color",
    addPoint: "Agregar punto",
    value: "Valor",
    simulator: "Simulador exacto",
    simulate: "Valor hipotético",
    discard: "Descartar",
    save: "Guardar",
    saving: "Guardando…",
    saved: "Configuración guardada.",
    unsaved: "Hay cambios sin guardar. ¿Deseas descartarlos?",
    invalidJson: "El JSON no es válido.",
    invalid: "Corrige los campos antes de guardar.",
    conflict: "La configuración cambió en otra sesión. Recarga antes de guardar.",
    advanced: "Detalles técnicos",
  },
  en: {
    admin: "Administration center",
    subtitle: "Local smart rules for managed lights.",
    version: "Installed version",
    smartRules: "Smart rules",
    smartDescription: "Create and manage state, numeric, and event rules.",
    native: "Native configuration",
    nativeDescription: "Compatible alternative through Home Assistant's Options Flow.",
    open: "Open",
    home: "Home",
    create: "Create rule",
    edit: "Edit",
    duplicate: "Duplicate",
    enable: "Enable",
    disable: "Disable",
    remove: "Delete",
    confirmDelete: "Delete this rule?",
    noRules: "There are no rules yet.",
    loading: "Loading…",
    reload: "Reload",
    enabled: "Enabled",
    disabled: "Disabled",
    priority: "Priority",
    source: "Source",
    targets: "Targets",
    conditions: "Conditions",
    schedule: "Schedule",
    general: "1. General information",
    origin: "2. Source or trigger",
    conditionSection: "3. Conditions",
    timeSection: "4. Schedules and dwell",
    targetSection: "5. Targets",
    colorSection: "6. Color and style",
    policySection: "7. Priority and duration",
    summarySection: "8. Review and save",
    name: "Name",
    type: "Type",
    state: "State",
    numeric: "Numeric",
    event: "Event",
    entity: "Entity",
    operator: "Operator",
    expected: "Expected state",
    equals: "Equals",
    notEquals: "Does not equal",
    trigger: "Official Home Assistant trigger (JSON)",
    conditionJson: "AND/OR/NOT tree (optional JSON)",
    scheduleJson: "Schedule (optional JSON)",
    dwell: "Minimum dwell (seconds)",
    individual: "Individual lights",
    zones: "Smart LED Manager zones",
    areas: "Home Assistant areas",
    labels: "Home Assistant labels",
    groups: "Transparent light groups",
    allManaged: "All managed lights",
    previewTargets: "Preview targets",
    excluded: "Excluded by authorization",
    color: "Color",
    brightness: "Brightness",
    transition: "Transition",
    animation: "Animation",
    fixed: "Fixed",
    blink: "Blink",
    pulse: "Pulse",
    period: "Period",
    duration: "Event duration (seconds)",
    activation: "Numeric activation",
    noThreshold: "Always active",
    above: "Above",
    below: "Below",
    inside: "Inside range",
    outside: "Outside range",
    threshold: "Threshold",
    lower: "Lower bound",
    upper: "Upper bound",
    hysteresis: "Hysteresis",
    calculation: "Color calculation",
    interpolate: "Interpolation",
    ranges: "Ranges",
    points: "Color points",
    addPoint: "Add point",
    value: "Value",
    simulator: "Exact simulator",
    simulate: "Hypothetical value",
    discard: "Discard",
    save: "Save",
    saving: "Saving…",
    saved: "Configuration saved.",
    unsaved: "There are unsaved changes. Discard them?",
    invalidJson: "The JSON is invalid.",
    invalid: "Correct the fields before saving.",
    conflict: "Configuration changed in another session. Reload before saving.",
    advanced: "Technical details",
  },
};

const esc = (value) => String(value ?? "")
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;").replaceAll("'", "&#039;");

const blankTargets = () => ({
  entities: [], zones: [], areas: [], labels: [], groups: [], all_managed: false,
});

const selectionFor = (rule) => rule.target_selection
  ? deepClone(rule.target_selection)
  : { ...blankTargets(), entities: [...(rule.targets ?? [])] };

const optionList = (items, selected) => (items ?? []).map((item) =>
  `<option value="${esc(item.id ?? item.entity_id)}" ${selected.includes(item.id ?? item.entity_id) ? "selected" : ""}>${esc(item.name)}</option>`
).join("");

class SmartLEDManagerVisualEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._view = "home";
    this._rules = [];
    this._selections = {};
    this._revision = undefined;
    this._selected = undefined;
    this._draft = undefined;
    this._original = undefined;
    this._creating = false;
    this._loading = false;
    this._saving = false;
    this._error = undefined;
    this._notice = undefined;
    this._targetPreview = undefined;
    this._numericPreview = undefined;
    this._simulateValue = "";
    this._previewRequest = 0;
    this._language = undefined;
    this._beforeUnload = (event) => {
      if (this._dirty()) { event.preventDefault(); event.returnValue = ""; }
    };
  }

  set hass(value) {
    const previous = this._language;
    this._hass = value;
    this._language = value?.locale?.language ?? value?.language ?? "en";
    if (this.isConnected && (!previous || previous !== this._language)) this._render();
  }
  set panel(value) { this._panel = value; if (this.isConnected) this._render(); }
  set route(value) { this._route = value; }
  set narrow(value) { this._narrow = value; }
  connectedCallback() { window.addEventListener("beforeunload", this._beforeUnload); this._render(); }
  disconnectedCallback() { window.removeEventListener("beforeunload", this._beforeUnload); }
  get _entryId() { return this._panel?.config?.entry_id; }
  get _version() { return this._panel?.config?.version ?? "0.1.0-alpha.3"; }
  get _t() {
    const language = this._hass?.locale?.language ?? this._hass?.language ?? "en";
    return String(language).toLowerCase().startsWith("es") ? TEXT.es : TEXT.en;
  }

  _dirty() { return JSON.stringify(this._draft) !== JSON.stringify(this._original); }

  async _load() {
    if (!this._hass || !this._entryId || this._loading) return;
    this._loading = true; this._error = undefined; this._render();
    try {
      const response = await this._hass.callWS({
        type: "smart_led_manager/smart_rules/get", entry_id: this._entryId,
      });
      this._rules = response.rules; this._revision = response.revision;
      this._selections = response.selections ?? {};
    } catch (error) {
      this._error = error?.message ?? String(error);
    } finally { this._loading = false; this._render(); }
  }

  _openRules() { this._view = "rules"; this._render(); if (!this._revision) this._load(); }
  _goHome() { if (this._dirty() && !window.confirm(this._t.unsaved)) return; this._closeEditor(); this._view = "home"; this._render(); }
  _closeEditor() { this._selected = undefined; this._draft = undefined; this._original = undefined; this._creating = false; this._targetPreview = undefined; this._numericPreview = undefined; this._error = undefined; }

  _edit(ruleId) {
    const selected = this._rules.find((item) => item.rule.id === ruleId);
    if (!selected) return;
    this._selected = selected;
    this._draft = deepClone(selected.rule);
    this._draft.target_selection = selectionFor(this._draft);
    delete this._draft.targets;
    if (this._draft.type === "numeric") this._draft.points = sortPoints(this._draft.points ?? []);
    this._original = deepClone(this._draft);
    this._simulateValue = this._draft.points?.length ? String(this._draft.points[0].value) : "";
    this._creating = false; this._error = undefined; this._notice = undefined; this._render();
  }

  _create() {
    const first = this._selections.managed_lights?.[0]?.entity_id;
    this._draft = {
      name: "", type: "state", enabled: true, source: "", operator: "equals", state: "on",
      target_selection: { ...blankTargets(), entities: first ? [first] : [] },
      priority: 40, rgb_color: [0, 0, 255], brightness: 255, transition: 0,
      animation: "fixed", period: 1, for_seconds: 0,
    };
    this._selected = { rule: this._draft, source: {}, targets: [] };
    this._original = undefined; this._creating = true; this._error = undefined; this._render();
  }

  async _mutate(operation, extra = {}) {
    this._saving = true; this._error = undefined; this._render();
    try {
      const response = await this._hass.callWS({
        type: "smart_led_manager/smart_rules/mutate", entry_id: this._entryId,
        revision: this._revision, operation, ...extra,
      });
      this._revision = response.revision; this._notice = this._t.saved;
      this._closeEditor(); await this._load();
    } catch (error) {
      this._error = error?.code === "conflict" ? this._t.conflict : (error?.message ?? String(error));
    } finally { this._saving = false; this._render(); }
  }

  async _save() {
    if (!this._draft?.name?.trim() || this._invalidNumeric()) { this._error = this._t.invalid; this._render(); return; }
    await this._mutate(this._creating ? "create" : "update", {
      rule_id: this._selected?.rule?.id, rule: this._draft,
    });
  }

  _invalidNumeric() {
    return this._draft?.type === "numeric" && this._draft.points
      ? Boolean(validateDraft(this._draft.mode ?? "interpolate", this._draft.points)) : false;
  }

  _set(path, value) {
    const parts = path.split("."); let target = this._draft;
    while (parts.length > 1) { const key = parts.shift(); target[key] ??= {}; target = target[key]; }
    target[parts[0]] = value; this._notice = undefined; this._render();
  }

  _setJson(path, text) {
    try { this._set(path, text.trim() ? JSON.parse(text) : null); this._error = undefined; }
    catch { this._error = this._t.invalidJson; this._render(); }
  }

  async _previewTargets() {
    try {
      this._targetPreview = await this._hass.callWS({
        type: "smart_led_manager/targets/preview", entry_id: this._entryId,
        target_selection: this._draft.target_selection,
      }); this._error = undefined;
    } catch (error) { this._targetPreview = undefined; this._error = error?.message ?? String(error); }
    this._render();
  }

  async _previewNumeric() {
    const rawValue = String(this._simulateValue ?? "").trim();
    const value = rawValue === "" ? Number.NaN : Number(rawValue);
    if (!Number.isFinite(value) || this._invalidNumeric()) { this._numericPreview = undefined; this._render(); return; }
    const requestId = ++this._previewRequest;
    try {
      const response = await this._hass.callWS({
        type: "smart_led_manager/rules/preview", entry_id: this._entryId,
        rule_id: this._selected?.rule?.id ?? "draft", mode: this._draft.mode,
        points: this._draft.points, values: [value],
      });
      if (requestId !== this._previewRequest) return;
      this._numericPreview = response.results[0];
    } catch (error) { this._error = error?.message ?? String(error); }
    this._render();
  }

  _styles() { return `
    :host{display:block;min-height:100%;color:var(--primary-text-color);background:var(--primary-background-color)}
    *{box-sizing:border-box}main{max-width:1120px;margin:auto;padding:24px max(16px,env(safe-area-inset-right)) 48px max(16px,env(safe-area-inset-left))}
    h1{margin:0 0 6px;font-size:28px}h2{margin:0;font-size:20px}h3{margin:0 0 14px;font-size:16px}.muted{color:var(--secondary-text-color)}
    .identity,.toolbar,.actions,.row,.rule-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.identity{gap:16px;margin-bottom:22px}.icon{font-size:30px;background:var(--primary-color);color:var(--text-primary-color);padding:12px;border-radius:14px}.version,.badge{display:inline-block;padding:3px 9px;border-radius:999px;background:var(--secondary-background-color);font-size:12px}.badge.on{color:var(--success-color)}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px}.card{padding:18px;border:1px solid var(--divider-color);border-radius:12px;background:var(--card-background-color);box-shadow:var(--ha-card-box-shadow,none);margin:16px 0}.home-card{display:flex;min-height:190px;flex-direction:column}.spacer{flex:1}
    button,.button,select,input,textarea{font:inherit}button,.button{border:1px solid var(--divider-color);border-radius:8px;padding:9px 13px;background:var(--secondary-background-color);color:var(--primary-text-color);cursor:pointer;text-decoration:none}.primary{background:var(--primary-color);color:var(--text-primary-color);border-color:var(--primary-color)}.danger{color:var(--error-color)}button:disabled{opacity:.55;cursor:not-allowed}
    .rule{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;padding:15px 0;border-bottom:1px solid var(--divider-color)}.rule:last-child{border:0}.meta{display:flex;gap:9px;flex-wrap:wrap;margin-top:7px;color:var(--secondary-text-color);font-size:13px}
    .form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}label{display:flex;flex-direction:column;gap:6px;font-weight:600}input,select,textarea{width:100%;padding:9px;border:1px solid var(--divider-color);border-radius:7px;background:var(--input-fill-color,var(--card-background-color));color:var(--primary-text-color)}textarea{min-height:105px;font-family:monospace}.check{flex-direction:row;align-items:center}.check input{width:auto}.multi{min-height:105px}
    .message{padding:11px;border-radius:8px;margin:12px 0}.error{background:color-mix(in srgb,var(--error-color) 12%,transparent);color:var(--error-color)}.notice{background:color-mix(in srgb,var(--success-color) 12%,transparent);color:var(--success-color)}
    .colorbar{height:34px;border-radius:8px;border:1px solid var(--divider-color)}.point{display:grid;grid-template-columns:64px 1fr 1fr auto;gap:10px;align-items:end;margin:10px 0}.swatch{height:38px;border-radius:8px;border:1px solid var(--divider-color)}.preview{display:flex;gap:12px;align-items:center;margin-top:12px}.preview .swatch{width:52px}
    .actions{justify-content:flex-end;position:sticky;bottom:0;padding:16px 0 max(16px,env(safe-area-inset-bottom));background:linear-gradient(transparent,var(--primary-background-color) 24%)}details{margin-top:12px}
    @media(max-width:700px){main{padding-top:16px}.rule{grid-template-columns:1fr}.rule-actions button{flex:1}.point{grid-template-columns:44px 1fr}.point label,.point button{grid-column:2}.actions button{flex:1}.form-grid{grid-template-columns:1fr}}
  `; }

  _renderHome() { const t = this._t; return `<main><div class="identity"><div class="icon">✦</div><div><h1>Smart LED Manager</h1><strong>${t.admin}</strong><p class="muted">${t.subtitle}</p><span class="version">${t.version}: ${esc(this._version)}</span></div></div><div class="grid"><article class="card home-card"><h2>${t.smartRules}</h2><p>${t.smartDescription}</p><span class="spacer"></span><button class="primary" data-rules>${t.open}</button></article><article class="card home-card"><h2>${t.native}</h2><p>${t.nativeDescription}</p><span class="spacer"></span><a class="button" href="/config/integrations/integration/smart_led_manager">${t.open}</a></article></div></main>`; }

  _renderList() {
    const t = this._t;
    const list = this._loading ? `<p>${t.loading}</p>` : this._error ? "" : this._rules.length ? this._rules.map(({ rule, source, targets, condition_summary, schedule_summary }) => `<article class="rule"><div><strong>${esc(rule.name)}</strong> <span class="badge ${rule.enabled !== false ? "on" : ""}">${rule.enabled !== false ? t.enabled : t.disabled}</span><div class="meta"><span>${t.type}: ${esc(t[rule.type] ?? rule.type)}</span><span>${t.priority}: ${esc(rule.priority)}</span><span>${t.source}: ${esc(source?.name)}</span><span>${t.targets}: ${esc(targets.map((item) => item.name).join(", "))}</span>${condition_summary ? `<span>${t.conditions}: ${esc(condition_summary)}</span>` : ""}${schedule_summary ? `<span>${t.schedule}: ${esc(schedule_summary)}</span>` : ""}</div></div><div class="rule-actions"><button data-edit="${esc(rule.id)}">${t.edit}</button><button data-duplicate="${esc(rule.id)}">${t.duplicate}</button><button data-toggle="${esc(rule.id)}" data-enabled="${rule.enabled !== false}">${rule.enabled !== false ? t.disable : t.enable}</button><button class="danger" data-delete="${esc(rule.id)}">${t.remove}</button></div></article>`).join("") : `<p class="muted">${t.noRules}</p>`;
    return `<main><div class="toolbar"><button data-home>← ${t.home}</button><button data-reload>${t.reload}</button><span class="spacer"></span><button class="primary" data-create>${t.create}</button></div><h1>${t.smartRules}</h1>${this._error ? `<div class="message error">${esc(this._error)}</div>` : ""}${this._notice ? `<div class="message notice">${esc(this._notice)}</div>` : ""}<section class="card">${list}</section></main>`;
  }

  _targetSelect(label, key, items) { const selected = this._draft.target_selection[key] ?? []; return `<label>${label}<select class="multi" multiple data-target="${key}">${optionList(items, selected)}</select></label>`; }

  _renderOrigin() {
    const t = this._t, r = this._draft;
    if (r.type === "event") return `<label>${t.trigger}<textarea data-json="trigger">${esc(JSON.stringify(r.trigger ?? { platform: "event", event_type: "" }, null, 2))}</textarea></label>`;
    return `<div class="form-grid"><label>${t.entity}<input data-field="source" value="${esc(r.source)}"></label>${r.type === "state" ? `<label>${t.operator}<select data-field="operator"><option value="equals" ${r.operator !== "not_equals" ? "selected" : ""}>${t.equals}</option><option value="not_equals" ${r.operator === "not_equals" ? "selected" : ""}>${t.notEquals}</option></select></label><label>${t.expected}<input data-field="state" value="${esc(r.state)}"></label>` : ""}</div>`;
  }

  _renderNumeric() {
    if (this._draft.type !== "numeric") return "";
    const t = this._t, r = this._draft, activation = r.activation ?? {}, operator = activation.operator ?? "";
    const points = sortPoints(r.points ?? []);
    const rows = points.map((point, index) => `<div class="point"><span class="swatch" style="background:${rgbToHex(point.rgb)}"></span><label>${t.value}<input type="number" step="any" value="${esc(point.value)}" data-point-value="${index}"></label><label>${t.color}<input type="color" value="${rgbToHex(point.rgb)}" data-point-color="${index}"></label><button class="danger" data-remove-point="${index}">${t.remove}</button></div>`).join("");
    return `<section class="card"><h3>${t.activation}</h3><div class="form-grid"><label>${t.operator}<select data-activation-operator><option value="" ${!operator ? "selected" : ""}>${t.noThreshold}</option>${["above","below","inside","outside"].map((item) => `<option value="${item}" ${operator === item ? "selected" : ""}>${t[item]}</option>`).join("")}</select></label>${["above","below"].includes(operator) ? `<label>${t.threshold}<input type="number" step="any" data-activation="threshold" value="${esc(activation.threshold)}"></label>` : ""}${["inside","outside"].includes(operator) ? `<label>${t.lower}<input type="number" step="any" data-activation="lower" value="${esc(activation.lower)}"></label><label>${t.upper}<input type="number" step="any" data-activation="upper" value="${esc(activation.upper)}"></label>` : ""}${operator ? `<label>${t.hysteresis}<input type="number" min="0" step="any" data-activation="hysteresis" value="${esc(activation.hysteresis ?? 0)}"></label>` : ""}</div></section><section class="card"><h3>${t.points}</h3><label>${t.calculation}<select data-field="mode"><option value="interpolate" ${r.mode !== "ranges" ? "selected" : ""}>${t.interpolate}</option><option value="ranges" ${r.mode === "ranges" ? "selected" : ""}>${t.ranges}</option></select></label><div class="colorbar" style="background:${cssGradient(points, r.mode ?? "interpolate")}"></div>${rows}<button data-add-point>${t.addPoint}</button><div class="form-grid"><label>${t.simulate}<input type="number" step="any" data-simulate value="${esc(this._simulateValue)}"></label><button data-preview-numeric>${t.simulator}</button></div>${this._numericPreview ? `<div class="preview"><span class="swatch" style="background:${esc(this._numericPreview.hex)}"></span><strong>${esc(this._numericPreview.hex)} · RGB(${this._numericPreview.rgb.join(", ")})</strong></div>` : ""}</section>`;
  }

  _renderEditor() {
    const t = this._t, r = this._draft, selection = r.target_selection ?? blankTargets();
    r.target_selection ??= selection;
    const targetNames = this._targetPreview?.targets?.map((item) => item.name).join(", ") ?? "";
    const exclusions = this._targetPreview?.excluded?.map((item) => item.name).join(", ") ?? "";
    return `<main><div class="toolbar"><button data-back>← ${t.smartRules}</button></div><h1>${esc(r.name || t.create)}</h1>${this._error ? `<div class="message error">${esc(this._error)}</div>` : ""}<section class="card"><h3>${t.general}</h3><div class="form-grid"><label>${t.name}<input data-field="name" value="${esc(r.name)}"></label><label>${t.type}<select data-field="type" ${this._creating ? "" : "disabled"}><option value="state" ${r.type === "state" ? "selected" : ""}>${t.state}</option><option value="numeric" ${r.type === "numeric" ? "selected" : ""}>${t.numeric}</option><option value="event" ${r.type === "event" ? "selected" : ""}>${t.event}</option></select></label><label class="check"><input type="checkbox" data-boolean="enabled" ${r.enabled !== false ? "checked" : ""}>${r.enabled !== false ? t.enabled : t.disabled}</label></div></section><section class="card"><h3>${t.origin}</h3>${this._renderOrigin()}</section><section class="card"><h3>${t.conditionSection}</h3><label>${t.conditionJson}<textarea data-json="conditions">${esc(r.conditions ? JSON.stringify(r.conditions, null, 2) : "")}</textarea></label></section><section class="card"><h3>${t.timeSection}</h3><div class="form-grid"><label>${t.scheduleJson}<textarea data-json="schedule">${esc(r.schedule ? JSON.stringify(r.schedule, null, 2) : "")}</textarea></label>${r.type !== "event" ? `<label>${t.dwell}<input type="number" min="0" step="0.1" data-number="for_seconds" value="${esc(r.for_seconds ?? 0)}"></label>` : ""}</div></section><section class="card"><h3>${t.targetSection}</h3><div class="form-grid">${this._targetSelect(t.individual,"entities",this._selections.managed_lights)}${this._targetSelect(t.zones,"zones",this._selections.zones)}${this._targetSelect(t.areas,"areas",this._selections.areas)}${this._targetSelect(t.labels,"labels",this._selections.labels)}${this._targetSelect(t.groups,"groups",this._selections.groups)}<label class="check"><input type="checkbox" data-target-all ${selection.all_managed ? "checked" : ""}>${t.allManaged}</label></div><button data-preview-targets>${t.previewTargets}</button>${targetNames ? `<p>${t.targets}: ${esc(targetNames)}</p>` : ""}${exclusions ? `<p class="muted">${t.excluded}: ${esc(exclusions)}</p>` : ""}</section>${this._renderNumeric()}<section class="card"><h3>${t.colorSection}</h3><div class="form-grid"><label>${t.color}<input type="color" data-color value="${rgbToHex(r.rgb_color ?? [255,255,255])}"></label><label>${t.brightness}<input type="number" min="1" max="255" data-number="brightness" value="${esc(r.brightness ?? 255)}"></label><label>${t.transition}<input type="number" min="0" step="0.1" data-number="transition" value="${esc(r.transition ?? 0)}"></label><label>${t.animation}<select data-field="animation">${["fixed","blink","pulse"].map((item) => `<option value="${item}" ${r.animation === item || (!r.animation && item === "fixed") ? "selected" : ""}>${t[item]}</option>`).join("")}</select></label><label>${t.period}<input type="number" min="0.1" step="0.1" data-number="period" value="${esc(r.period ?? 1)}"></label></div></section><section class="card"><h3>${t.policySection}</h3><div class="form-grid"><label>${t.priority}<input type="number" min="0" max="100" data-number="priority" value="${esc(r.priority ?? 40)}"></label>${r.type === "event" ? `<label>${t.duration}<input type="number" min="0.1" step="0.1" data-number="duration" value="${esc(r.duration ?? 5)}"></label>` : ""}</div></section><section class="card"><h3>${t.summarySection}</h3><p>${esc(r.name)} · ${esc(t[r.type])} · P${esc(r.priority ?? 40)}</p><details><summary>${t.advanced}</summary><pre>${esc(JSON.stringify(r, null, 2))}</pre></details></section><div class="actions"><button data-discard>${t.discard}</button><button class="primary" data-save ${this._saving || !r.name?.trim() || this._invalidNumeric() ? "disabled" : ""}>${this._saving ? t.saving : t.save}</button></div></main>`;
  }

  _render() {
    if (!this.shadowRoot) return;
    const content = this._draft ? this._renderEditor() : this._view === "rules" ? this._renderList() : this._renderHome();
    this.shadowRoot.innerHTML = `<style>${this._styles()}</style>${content}`; this._bind();
  }

  _bind() {
    const root = this.shadowRoot;
    root.querySelector("[data-rules]")?.addEventListener("click", () => this._openRules());
    root.querySelector("[data-home]")?.addEventListener("click", () => this._goHome());
    root.querySelector("[data-reload]")?.addEventListener("click", () => this._load());
    root.querySelector("[data-create]")?.addEventListener("click", () => this._create());
    root.querySelectorAll("[data-edit]").forEach((button) => button.addEventListener("click", () => this._edit(button.dataset.edit)));
    root.querySelectorAll("[data-duplicate]").forEach((button) => button.addEventListener("click", () => this._mutate("duplicate", { rule_id: button.dataset.duplicate })));
    root.querySelectorAll("[data-toggle]").forEach((button) => button.addEventListener("click", () => this._mutate("toggle", { rule_id: button.dataset.toggle, enabled: button.dataset.enabled !== "true" })));
    root.querySelectorAll("[data-delete]").forEach((button) => button.addEventListener("click", () => { if (window.confirm(this._t.confirmDelete)) this._mutate("delete", { rule_id: button.dataset.delete }); }));
    root.querySelector("[data-back]")?.addEventListener("click", () => { if (!this._dirty() || window.confirm(this._t.unsaved)) { this._closeEditor(); this._render(); } });
    root.querySelector("[data-discard]")?.addEventListener("click", () => { this._closeEditor(); this._render(); });
    root.querySelector("[data-save]")?.addEventListener("click", () => this._save());
    root.querySelectorAll("[data-field]").forEach((input) => input.addEventListener("change", () => {
      const value = input.value; this._set(input.dataset.field, value);
      if (input.dataset.field === "type") {
        if (value === "numeric") { this._draft.source = ""; this._draft.mode = "interpolate"; this._draft.points = [{ value: 0, rgb: [0,0,255] }, { value: 100, rgb: [255,0,0] }]; }
        if (value === "event") { delete this._draft.source; delete this._draft.state; this._draft.trigger = { platform: "event", event_type: "" }; this._draft.duration = 5; delete this._draft.for_seconds; }
        if (value === "state") { this._draft.source ??= ""; this._draft.operator = "equals"; this._draft.state = "on"; this._draft.for_seconds ??= 0; }
        this._render();
      }
    }));
    root.querySelectorAll("[data-number]").forEach((input) => input.addEventListener("change", () => this._set(input.dataset.number, Number(input.value))));
    root.querySelectorAll("[data-boolean]").forEach((input) => input.addEventListener("change", () => this._set(input.dataset.boolean, input.checked)));
    root.querySelectorAll("[data-json]").forEach((input) => input.addEventListener("change", () => this._setJson(input.dataset.json, input.value)));
    root.querySelectorAll("[data-target]").forEach((input) => input.addEventListener("change", () => this._set(`target_selection.${input.dataset.target}`, [...input.selectedOptions].map((item) => item.value))));
    root.querySelector("[data-target-all]")?.addEventListener("change", (event) => this._set("target_selection.all_managed", event.target.checked));
    root.querySelector("[data-preview-targets]")?.addEventListener("click", () => this._previewTargets());
    root.querySelector("[data-color]")?.addEventListener("change", (event) => this._set("rgb_color", hexToRgb(event.target.value)));
    root.querySelector("[data-activation-operator]")?.addEventListener("change", (event) => {
      const operator = event.target.value;
      this._draft.activation = operator ? { operator, ...(operator === "above" || operator === "below" ? { threshold: 0 } : { lower: 0, upper: 100 }), hysteresis: 0 } : null; this._render();
    });
    root.querySelectorAll("[data-activation]").forEach((input) => input.addEventListener("change", () => this._set(`activation.${input.dataset.activation}`, Number(input.value))));
    root.querySelector("[data-add-point]")?.addEventListener("click", () => { this._draft.points = sortPoints([...(this._draft.points ?? []), nextPoint(this._draft.points ?? [])]); this._render(); });
    root.querySelectorAll("[data-remove-point]").forEach((button) => button.addEventListener("click", () => { this._draft.points = removePoint(this._draft.points, Number(button.dataset.removePoint)); this._render(); }));
    root.querySelectorAll("[data-point-value]").forEach((input) => input.addEventListener("change", () => { try { this._draft.points = replacePoint(this._draft.points, Number(input.dataset.pointValue), { ...this._draft.points[Number(input.dataset.pointValue)], value: input.value }); this._error = undefined; } catch { this._error = this._t.invalid; } this._render(); }));
    root.querySelectorAll("[data-point-color]").forEach((input) => input.addEventListener("change", () => { const index = Number(input.dataset.pointColor); this._draft.points = replacePoint(this._draft.points, index, { ...this._draft.points[index], rgb: hexToRgb(input.value) }); this._render(); }));
    root.querySelector("[data-simulate]")?.addEventListener("change", (event) => { this._simulateValue = event.target.value; });
    root.querySelector("[data-preview-numeric]")?.addEventListener("click", () => this._previewNumeric());
  }
}

if (!customElements.get("smart-led-manager-visual-editor")) {
  customElements.define("smart-led-manager-visual-editor", SmartLEDManagerVisualEditor);
}
