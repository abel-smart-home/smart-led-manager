import {
  cssGradient,
  deepClone,
  gradientStopEntries,
  hexToRgb,
  nextPoint,
  pointPercent,
  removePoint,
  replacePoint,
  rgbToHex,
  sortPoints,
  validateDraft,
} from "./visual-editor-model.mjs";
import {
  CONTROL_TEXT,
  conditionControls,
  defaultSchedule,
  entityItems,
  inputField,
  newCondition,
  numericControls,
  numberField,
  picker,
  scheduleControls,
  selectField,
  stateControl,
  treeSize,
  triggerKind,
} from "./rule-controls.mjs";

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
    colorBar: "Barra de colores",
    graph: "Distribución numérica",
    selectPoint: "Seleccionar punto {value}",
    addPoint: "Agregar punto",
    value: "Valor",
    simulator: "Simulador exacto",
    simulate: "Valor hipotético",
    restore: "Restaurar borrador",
    save: "Guardar",
    saving: "Guardando…",
    saved: "Configuración guardada.",
    unsaved: "Cambios sin guardar",
    unsavedPrompt: "Has modificado la configuración. ¿Qué deseas hacer?",
    keepEditing: "Continuar editando",
    discardExit: "Descartar cambios y salir",
    saveExit: "Guardar y salir",
    cancel: "Cancelar",
    checkStatus: "Comprobar estado",
    checking: "Comprobando el estado de la integración…",
    applying: "Opciones recibidas. Esperando a que la integración las aplique…",
    applyFailed: "Las opciones se recibieron, pero la integración todavía no las aplica. Revisa la entrada y el registro de Home Assistant.",
    changedAfterSave: "Se aplicó el envío anterior. Los cambios nuevos siguen en el borrador.",
    uncertainSave: "Se perdió la confirmación. Comprueba la configuración antes de volver a enviar cambios.",
    offline: "Se perdió la conexión con Home Assistant.",
    unloaded: "La entrada de Smart LED Manager está descargada.",
    disabledEntry: "La entrada de Smart LED Manager está deshabilitada.",
    missingEntry: "La entrada de Smart LED Manager ya no está disponible.",
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
    colorBar: "Color bar",
    graph: "Numeric distribution",
    selectPoint: "Select point {value}",
    addPoint: "Add point",
    value: "Value",
    simulator: "Exact simulator",
    simulate: "Hypothetical value",
    restore: "Restore draft",
    save: "Save",
    saving: "Saving…",
    saved: "Configuration saved.",
    unsaved: "Unsaved changes",
    unsavedPrompt: "You changed the configuration. What would you like to do?",
    keepEditing: "Continue editing",
    discardExit: "Discard changes and exit",
    saveExit: "Save and exit",
    cancel: "Cancel",
    checkStatus: "Check status",
    checking: "Checking integration status…",
    applying: "Options accepted. Waiting for the integration to apply them…",
    applyFailed: "The options were accepted, but the integration has not applied them yet. Check the entry and the Home Assistant logs.",
    changedAfterSave: "The previous submission was applied. Your newer changes are still in the draft.",
    uncertainSave: "The confirmation was lost. Check the configuration before submitting changes again.",
    offline: "The connection to Home Assistant was lost.",
    unloaded: "The Smart LED Manager entry is unloaded.",
    disabledEntry: "The Smart LED Manager entry is disabled.",
    missingEntry: "The Smart LED Manager entry is no longer available.",
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
  ? { ...blankTargets(), ...deepClone(rule.target_selection) }
  : { ...blankTargets(), entities: [...(rule.targets ?? [])] };

const draftValue = (rule, key, fallback) => Object.hasOwn(rule, key) ? rule[key] : fallback;

const RUNTIME_READ_DELAYS = [0, 150, 450, 1000, 2000];

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
    this._targetRequest = 0;
    this._runtimeStatus = "checking";
    this._loadGeneration = 0;
    this._loadAgain = false;
    this._sending = false;
    this._pendingMutation = undefined;
    this._exitView = undefined;
    this._searches = new Map();
    this._pointInput = new Map();
    this._eventPairs = [];
    this._deviceRequest = 0;
    this._language = undefined;
    this._beforeUnload = (event) => {
      if (this._dirty()) { event.preventDefault(); event.returnValue = ""; }
    };
  }

  set hass(value) {
    const previous = this._language;
    this._hass = value;
    this._language = value?.locale?.language ?? value?.language ?? "en";
    if (this.isConnected) this._subscribeStatus();
    if (this.isConnected && (!previous || previous !== this._language)) this._render();
  }
  set panel(value) {
    if (this._panel === value) return;
    const previousEntry = this._entryId;
    this._panel = value;
    if (previousEntry && previousEntry !== this._entryId) {
      this._detachStatus();
      this._revision = undefined;
      this._catalogRevision = undefined;
      this._pendingMutation = undefined;
      this._rules = [];
      this._selections = {};
      this._runtimeStatus = "checking";
      this._error = this._draft ? this._t.missingEntry : undefined;
      this._notice = undefined;
    }
    if (this.isConnected) { this._subscribeStatus(); this._render(); }
  }
  set route(value) { this._route = value; }
  set narrow(value) { this._narrow = value; }
  connectedCallback() {
    window.addEventListener("beforeunload", this._beforeUnload);
    this._subscribeStatus();
    this._render();
  }
  disconnectedCallback() {
    window.removeEventListener("beforeunload", this._beforeUnload);
    this._detachStatus();
    this._invalidatePreviews();
  }
  _detachStatus() {
    this._statusSubscription?.then((unsubscribe) => unsubscribe()).catch(() => {});
    this._statusSubscription = undefined;
    this._statusConnection?.removeEventListener?.("ready", this._onReconnect);
    this._statusConnection?.removeEventListener?.("disconnected", this._onDisconnect);
    this._statusConnection = undefined;
    this._loadGeneration++;
    this._loadAgain = false;
  }
  _subscribeStatus() {
    const connection = this._hass?.connection;
    if (!this._entryId || !connection || connection === this._statusConnection) return;
    this._detachStatus();
    this._statusConnection = connection;
    this._onReconnect = () => {
      this._runtimeStatus = "checking";
      this._loadGeneration++;
      if (this._view === "rules" || this._pendingMutation) this._load();
    };
    this._onDisconnect = () => {
      this._loadGeneration++;
      this._runtimeStatus = "offline";
      this._invalidatePreviews();
      this._render();
    };
    connection.addEventListener?.("ready", this._onReconnect);
    connection.addEventListener?.("disconnected", this._onDisconnect);
    this._statusSubscription = connection.subscribeEvents?.(({ data }) => {
      if (this._statusConnection === connection && data.entry_id === this._entryId &&
          (this._view === "rules" || this._pendingMutation)) this._load();
    }, "smart_led_manager_editor_entry_status");
    this._statusSubscription?.catch(() => {
      if (this._statusConnection === connection && this._view === "rules") this._load();
    });
    if (this._view === "rules" || this._pendingMutation) this._load();
  }
  get _entryId() { return this._panel?.config?.entry_id; }
  get _version() { return this._panel?.config?.version ?? "0.1.0-alpha.3"; }
  get _t() {
    const language = this._hass?.locale?.language ?? this._hass?.language ?? "en";
    const locale = String(language).toLowerCase().startsWith("es") ? "es" : "en";
    return { ...TEXT[locale], ...CONTROL_TEXT[locale] };
  }

  _dirty() {
    return this._pointInput.size > 0 ||
      JSON.stringify(this._draft) !== JSON.stringify(this._original) ||
      (triggerKind(this._draft?.trigger) === "event_bus" && Boolean(this._draft?.trigger) &&
        JSON.stringify(this._eventPairs) !== JSON.stringify(Object.entries(this._original?.trigger?.event_data ?? {})));
  }

  async _load() {
    if (!this._hass || !this._entryId || this._runtimeStatus === "offline") return;
    if (this._loading || this._sending) {
      this._loadAgain = true;
      return;
    }
    const generation = this._loadGeneration;
    this._loadAgain = false;
    this._loading = true;
    this._render();
    try {
      for (const delay of RUNTIME_READ_DELAYS) {
        if (delay) await new Promise((resolve) => setTimeout(resolve, delay));
        if (generation !== this._loadGeneration) return;
        const pending = this._pendingMutation;
        const status = await this._hass.callWS({
          type: "smart_led_manager/editor/status", entry_id: this._entryId,
          ...(pending && { mutation_id: pending.id }),
        });
        if (generation !== this._loadGeneration) return;
        this._runtimeStatus = status.status;
        this._entryState = status.entry_state;
        if (pending && status.mutation) pending.receipt = status.mutation;
        if (status.status === "reloading") {
          this._render();
          continue;
        }
        if (status.status !== "ready") return;
        try {
          const response = await this._hass.callWS({
            type: "smart_led_manager/smart_rules/get", entry_id: this._entryId,
          });
          if (generation !== this._loadGeneration) return;
          if (response.revision === status.applied_revision) {
            this._applyCatalog(response);
            this._confirmMutation(pending, response.revision);
            return;
          }
        } catch (error) {
          if (error?.code !== "entry_not_loaded") throw error;
          if (generation !== this._loadGeneration) return;
        }
        this._runtimeStatus = "reloading";
      }
    } catch (error) {
      if (generation === this._loadGeneration) {
        this._runtimeStatus = "checking";
        this._error = error?.message ?? error?.error?.message ?? String(error);
      }
    } finally {
      this._loading = false;
      const again = this._loadAgain;
      this._loadAgain = false;
      this._render();
      if (again) this._load();
    }
  }

  _applyCatalog(response) {
    this._rules = response.rules;
    this._catalogRevision = response.revision;
    this._selections = response.selections ?? {};
    if (!this._draft) this._revision = response.revision;
  }

  _confirmMutation(pending, revision) {
    if (!pending) return;
    this._pendingMutation = undefined;
    if (!pending.receipt) {
      this._error = pending.revision === revision ? this._t.uncertainSave : this._t.conflict;
      return;
    }
    if (pending.receipt.revision !== revision) {
      this._error = this._t.conflict;
      return;
    }
    this._error = undefined;
    this._notice = this._t.saved;
    if (pending.draft && this._draft === pending.draft) {
      if (pending.stamp === this._draftStamp()) {
        this._exitEditor(pending.destination);
      } else {
        this._selected = this._rules.find(({ rule }) => rule.id === pending.receipt.rule.id);
        this._original = this._draftFromRule(pending.receipt.rule);
        this._draft.id = this._original.id;
        this._creating = false;
        this._revision = revision;
        this._notice = this._t.changedAfterSave;
      }
    }
  }

  _draftStamp() {
    return JSON.stringify([this._draft, [...this._pointInput], this._eventPairs]);
  }

  _canWrite() {
    return Boolean(this._revision) && this._runtimeStatus === "ready" &&
      !this._loading && !this._saving && !this._pendingMutation;
  }

  _openRules() { this._view = "rules"; this._render(); this._load(); }
  _goHome() { this._requestExit("home"); }

  _requestExit(destination) {
    if (this._saving) return;
    if (this._dirty()) {
      this._exitView = destination;
      this._exitFocus = this.shadowRoot.activeElement?.hasAttribute("data-discard")
        ? "[data-discard]" : "[data-back]";
      this._render();
    } else {
      this._exitEditor(destination);
      this._render();
    }
  }

  _exitEditor(destination) {
    this._exitView = undefined;
    this._selected = undefined;
    this._draft = undefined;
    this._original = undefined;
    this._creating = false;
    this._revision = this._catalogRevision;
    this._view = destination;
    this._resetControls();
    this._invalidatePreviews();
    if (!this._pendingMutation) this._error = undefined;
  }

  _closeExit() {
    this._exitView = undefined;
    this._render();
    this.shadowRoot.querySelector(this._exitFocus ?? "[data-back]")?.focus();
  }

  _resetControls() {
    this._searches.clear();
    this._pointInput.clear();
    this._eventPairs = Object.entries(this._draft?.trigger?.event_data ?? {});
    this._triggerKind = undefined;
    this._deviceId = undefined;
    this._deviceChoice = undefined;
    this._deviceTriggers = [];
    this._loadingTriggers = false;
    this._deviceRequest++;
    this._dwellUnit = "seconds";
    this._previousPoints = undefined;
  }

  _invalidatePreviews() {
    this._previewRequest++;
    this._targetRequest++;
    this._targetPreview = undefined;
    this._numericPreview = undefined;
    for (const element of this.shadowRoot.querySelectorAll("[data-preview-result]")) element.hidden = true;
  }

  _restore() {
    if (!this._original) return;
    this._draft = deepClone(this._original);
    this._resetControls();
    this._invalidatePreviews();
    this._simulateValue = this._draft.points?.length ? String(this._draft.points[0].value) : "";
    this._error = undefined; this._notice = undefined; this._render();
  }

  _edit(ruleId) {
    const selected = this._rules.find((item) => item.rule.id === ruleId);
    if (!selected) return;
    this._invalidatePreviews();
    this._selected = selected;
    this._revision = this._catalogRevision ?? this._revision;
    this._draft = this._draftFromRule(selected.rule);
    this._original = deepClone(this._draft);
    this._resetControls();
    this._simulateValue = this._draft.points?.length ? String(this._draft.points[0].value) : "";
    this._creating = false; this._error = undefined; this._notice = undefined; this._render();
  }

  _draftFromRule(rule) {
    const draft = deepClone(rule);
    draft.target_selection = selectionFor(draft);
    delete draft.targets;
    if (draft.type === "numeric" && draft.points) draft.points = sortPoints(draft.points);
    return draft;
  }

  _create() {
    this._revision = this._catalogRevision ?? this._revision;
    this._invalidatePreviews();
    const first = this._selections.managed_lights?.[0]?.entity_id;
    this._draft = {
      name: "", type: "state", enabled: true, source: "", operator: "equals", state: "on",
      target_selection: { ...blankTargets(), entities: first ? [first] : [] },
      priority: 40, rgb_color: [0, 0, 255], brightness: 255, transition: 0,
      animation: "fixed", period: 1, for_seconds: 0,
    };
    this._selected = { rule: this._draft, source: {}, targets: [] };
    this._resetControls();
    this._original = undefined; this._creating = true; this._error = undefined; this._render();
  }

  async _mutate(operation, extra = {}, destination = "rules") {
    if (!this._canWrite()) return;
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    const id = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
    const pending = {
      id, revision: this._revision, destination,
      draft: this._draft, stamp: this._draftStamp(),
    };
    this._pendingMutation = pending;
    this._invalidatePreviews();
    this._saving = true;
    this._sending = true;
    this._error = undefined;
    this._notice = undefined;
    this._render();
    try {
      pending.receipt = await this._hass.callWS({
        type: "smart_led_manager/smart_rules/mutate", entry_id: this._entryId,
        revision: pending.revision, operation, mutation_id: id, ...extra,
      });
    } catch (error) {
      if (typeof error?.code === "string" && error.code !== "internal_error") {
        this._pendingMutation = undefined;
        this._error = error.code === "conflict" ? this._t.conflict : (error.message ?? error.code);
      } else {
        this._error = this._t.uncertainSave;
      }
    } finally {
      this._sending = false;
      try { await this._load(); } finally {
        this._saving = false;
        this._render();
      }
    }
  }

  async _save(destination = "rules") {
    if (!this._draft?.name?.trim() || this._invalidNumeric()) {
      this._error = this._t.invalid; this._render(); return;
    }
    const rule = deepClone(this._draft);
    if (rule.points) rule.points = this._draftPoints();
    if (rule.type === "event" && (this._triggerKind ?? triggerKind(rule.trigger)) === "event_bus") {
      const keys = this._eventPairs.map(([key]) => key.trim());
      if (keys.some((key) => !key) || new Set(keys).size !== keys.length) {
        this._error = this._t.invalid; this._render(); return;
      }
      if (keys.length) rule.trigger.event_data = Object.fromEntries(this._eventPairs);
      else delete rule.trigger.event_data;
    }
    await this._mutate(this._creating ? "create" : "update", {
      rule_id: this._selected?.rule?.id, rule,
    }, destination);
  }

  _invalidNumeric() {
    return this._draft?.type === "numeric" && this._draft.points
      ? this._draftPoints() === null : false;
  }

  _draftPoints(validate = true) {
    const ordered = sortPoints(this._draft.points ?? []);
    const points = ordered.map((point, index) => {
      const value = this._pointInput.get(index);
      return value === undefined ? point : { ...point, value: value.trim() ? Number(value) : NaN };
    });
    if (validate && validateDraft(this._draft.mode ?? "interpolate", points)) return null;
    return points.some((point) => !Number.isFinite(point.value)) ? null : sortPoints(points);
  }

  _updatePoints(points) {
    this._pointInput.clear();
    this._set("points", sortPoints(points));
  }

  _get(path) {
    return path.split(".").reduce((value, key) => value?.[key], this._draft);
  }

  _set(path, value, render = true) {
    const parts = path.split("."); let target = this._draft;
    while (parts.length > 1) { const key = parts.shift(); target[key] ??= {}; target = target[key]; }
    target[parts[0]] = value;
    this._notice = undefined;
    this._invalidatePreviews();
    if (render) this._render();
    else this._refreshSave();
  }

  _refreshSave() {
    const button = this.shadowRoot.querySelector("[data-save]");
    if (button) button.disabled = !this._canWrite() ||
      !this._draft.name?.trim() || this._invalidNumeric();
  }

  _filterPicker(input) {
    const query = input.value.toLocaleLowerCase();
    const options = input.closest(".picker")?.querySelector("select").options ?? [];
    for (const option of options) {
      option.hidden = Boolean(option.value && !option.selected && !option.text.toLocaleLowerCase().includes(query));
    }
  }

  _moveCondition(path, delta) {
    if (path === "conditions") { this._set(path, null); return; }
    const parts = path.split(".");
    const index = Number(parts.pop()), parent = parts.join(".");
    const items = [...this._get(parent)];
    if (delta) [items[index], items[index + delta]] = [items[index + delta], items[index]];
    else items.splice(index, 1);
    this._set(parent, items);
  }

  _changeField(path, value, render = true) {
    if (path === "type") {
      this._draft.type = value;
      if (value === "numeric") {
        this._draft.source = ""; this._draft.mode = "interpolate";
        this._draft.points = [{ value: 0, rgb: [0,0,255] }, { value: 100, rgb: [255,0,0] }];
      } else delete this._draft.points;
      if (value === "event") {
        this._draft.trigger = { platform: "event", event_type: "" };
        this._draft.duration = 5; delete this._draft.for_seconds;
      } else {
        delete this._draft.trigger; this._draft.for_seconds ??= 0;
      }
      this._resetControls(); this._invalidatePreviews(); this._render(); return;
    }
    if (path === "numeric_style") {
      if (value === "fixed") {
        this._previousPoints = this._draftPoints() ?? this._draft.points;
        this._pointInput.clear();
        delete this._draft.points;
        this._draft.rgb_color ??= [0, 0, 255];
      } else {
        this._draft.points ??= this._previousPoints ??
          [{ value: 0, rgb: [0,0,255] }, { value: 100, rgb: [255,0,0] }];
        this._draft.mode = value;
      }
      this._invalidatePreviews(); this._render(); return;
    }
    if (path === "dwell_unit") { this._dwellUnit = value; this._render(); return; }
    if (path === "dwell_value") {
      const factor = { seconds: 1, minutes: 60, hours: 3600 }[this._dwellUnit ?? "seconds"];
      this._set("for_seconds", value == null ? null : value * factor, render); return;
    }
    if (path === "trigger_kind") {
      this._triggerKind = value;
      this._deviceId = undefined;
      this._deviceTriggers = [];
      this._deviceChoice = undefined;
      this._deviceRequest++;
      this._loadingTriggers = false;
      this._eventPairs = [];
      this._set("trigger", value === "event_bus" ? { platform: "event", event_type: "" }
        : value === "device" ? { platform: "device" } : { platform: "state", entity_id: "", to: null });
      return;
    }
    if (path === "trigger_device") { this._loadDeviceTriggers(value); return; }
    if (path === "trigger_device_choice") {
      if (value !== "") {
        this._deviceChoice = value;
        const { metadata, ...trigger } = this._deviceTriggers[Number(value)];
        this._set("trigger", { ...trigger, platform: "device" });
      }
      return;
    }
    if (path.startsWith("event_pairs.")) {
      const [, index, part] = path.split(".");
      this._eventPairs[Number(index)][Number(part)] = value;
      return;
    }
    if (path.startsWith("conditions") && path.endsWith(".type")) {
      const key = path.slice(0, -5);
      const replacement = newCondition(value);
      if (treeSize(this._draft.conditions) - treeSize(this._get(key)) + treeSize(replacement) <= 32) {
        this._set(key, replacement);
      }
      return;
    }
    if (path === "activation.operator" || path.startsWith("conditions") && path.endsWith(".operator") &&
        ["above", "below", "inside", "outside"].includes(value)) {
      const key = path.slice(0, -9);
      const current = this._get(key);
      this._set(key, value ? {
        ...current, operator: value,
        ...(["above", "below"].includes(value) ? { threshold: current?.threshold ?? null }
          : { lower: current?.lower ?? null, upper: current?.upper ?? null }),
      } : null);
      return;
    }
    if ((path === "trigger.from" || path === "trigger.to") && !value) {
      const key = path.split(".")[1];
      if (key === "to") this._draft.trigger.to = null;
      else delete this._draft.trigger.from;
      this._invalidatePreviews(); return;
    }
    this._set(path, value, render);
  }

  async _loadDeviceTriggers(deviceId) {
    const request = ++this._deviceRequest;
    this._deviceId = deviceId;
    this._deviceChoice = undefined;
    this._deviceTriggers = [];
    this._set("trigger", { platform: "device" }, false);
    this._loadingTriggers = Boolean(deviceId);
    this._render();
    if (!deviceId) return;
    try {
      const triggers = await this._hass.callWS({ type: "device_automation/trigger/list", device_id: deviceId });
      if (request !== this._deviceRequest) return;
      this._deviceTriggers = triggers ?? [];
    } catch (error) {
      if (request !== this._deviceRequest) return;
      this._error = error?.message ?? String(error);
    } finally {
      if (request === this._deviceRequest) { this._loadingTriggers = false; this._render(); }
    }
  }

  async _previewTargets() {
    const requestId = ++this._targetRequest;
    try {
      const result = await this._hass.callWS({
        type: "smart_led_manager/targets/preview", entry_id: this._entryId,
        target_selection: this._draft.target_selection,
      });
      if (requestId !== this._targetRequest) return;
      this._targetPreview = result;
      this._error = undefined;
    } catch (error) {
      if (requestId !== this._targetRequest) return;
      this._targetPreview = undefined;
      this._error = error?.message ?? String(error);
    }
    this._render();
  }

  async _previewNumeric() {
    const requestId = ++this._previewRequest;
    const rawValue = String(this._simulateValue ?? "").trim();
    const value = rawValue === "" ? Number.NaN : Number(rawValue);
    if (!Number.isFinite(value) || this._invalidNumeric()) { this._numericPreview = undefined; this._render(); return; }
    try {
      const response = await this._hass.callWS({
        type: "smart_led_manager/rules/preview", entry_id: this._entryId,
        rule_id: this._selected?.rule?.id ?? "draft", mode: this._draft.mode,
        points: this._draftPoints(), values: [value],
      });
      if (requestId !== this._previewRequest) return;
      this._numericPreview = response.results[0];
    } catch (error) {
      if (requestId !== this._previewRequest) return;
      this._error = error?.message ?? String(error);
    }
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
    .picker{display:grid;gap:6px;min-width:0}.chips{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}.chip{border-radius:999px;text-align:left}.chips label{font-weight:400}.condition{min-width:0;border:1px solid var(--divider-color);border-radius:8px;margin:10px 0;padding:12px}.condition .condition{border-left:3px solid var(--primary-color)}.rule-color{margin-top:9px;height:8px;max-width:220px;border-radius:5px;border:1px solid var(--divider-color)}.editor-fields{padding:0;margin:0;border:0;min-width:0}
    .visual{position:relative;margin:20px 0 8px;padding-top:18px}.colorbar{height:34px;border-radius:8px;border:1px solid var(--divider-color)}.marker{position:absolute;top:0;width:30px;height:30px;padding:0;border-radius:50%;border:3px solid var(--card-background-color);box-shadow:0 0 0 1px var(--primary-text-color);transform:translateX(-50%)}
    .axis{width:100%;min-height:120px;overflow:visible}.axis text{fill:var(--primary-text-color);font-size:12px}.axis .baseline{stroke:var(--secondary-text-color);stroke-width:2}.axis .curve{stroke-width:14;stroke-linecap:round}.axis .graph-point{cursor:pointer}.axis .graph-point:focus{outline:none}.axis .graph-point:focus circle{stroke:var(--primary-color);stroke-width:5}.axis circle{stroke:var(--card-background-color);stroke-width:3}
    .point{display:grid;grid-template-columns:64px 1fr 1fr auto;gap:10px;align-items:end;margin:10px 0}.swatch{height:38px;border-radius:8px;border:1px solid var(--divider-color)}.preview{display:flex;gap:12px;align-items:center;margin-top:12px}.preview .swatch{width:52px}
    .actions{justify-content:flex-end;position:sticky;bottom:0;padding:16px 0 max(16px,env(safe-area-inset-bottom));background:linear-gradient(transparent,var(--primary-background-color) 24%)}details{margin-top:12px}
    dialog{box-sizing:border-box;width:min(520px,calc(100% - 32px));border:1px solid var(--divider-color);border-radius:16px;padding:22px;color:var(--primary-text-color);background:var(--card-background-color)}
    dialog::backdrop{background:rgba(0,0,0,.50)}dialog .actions{position:static;background:none;padding-bottom:0}button:focus-visible{outline:3px solid var(--primary-color);outline-offset:2px}
    @media(max-width:700px){main{padding-top:16px}.rule{grid-template-columns:1fr}.rule-actions button{flex:1}.point{grid-template-columns:44px 1fr}.point label,.point button{grid-column:2}.actions button{flex:1}.form-grid{grid-template-columns:1fr}}
  `; }

  _renderHome() { const t = this._t; return `<main><div class="identity"><div class="icon">✦</div><div><h1>Smart LED Manager</h1><strong>${t.admin}</strong><p class="muted">${t.subtitle}</p><span class="version">${t.version}: ${esc(this._version)}</span></div></div><div class="grid"><article class="card home-card"><h2>${t.smartRules}</h2><p>${t.smartDescription}</p><span class="spacer"></span><button class="primary" data-rules>${t.open}</button></article><article class="card home-card"><h2>${t.native}</h2><p>${t.nativeDescription}</p><span class="spacer"></span><a class="button" href="/config/integrations/integration/smart_led_manager">${t.open}</a></article></div></main>`; }

  _runtimeMessage() {
    const t = this._t;
    const accepted = Boolean(this._pendingMutation?.receipt);
    switch (this._runtimeStatus) {
      case "checking": return t.checking;
      case "reloading": return accepted ? t.applying : t.reloadingEntry;
      case "failed": return `${accepted ? t.applyFailed : t.failedReload}${this._entryState ? ` (${this._entryState})` : ""}`;
      case "offline": return t.offline;
      case "unloaded": return t.unloaded;
      case "disabled": return t.disabledEntry;
      case "missing": return t.missingEntry;
      default: return "";
    }
  }

  _renderExitDialog() {
    if (!this._exitView) return "";
    const t = this._t;
    const canSave = this._canWrite() && this._draft?.name?.trim() && !this._invalidNumeric();
    return `<dialog data-exit-dialog aria-labelledby="exit-title"><h2 id="exit-title">${t.unsaved}</h2>
      <p>${t.unsavedPrompt}</p><div class="actions">
      <button data-exit-continue autofocus>${t.keepEditing}</button>
      <button data-exit-discard>${t.discardExit}</button>
      <button class="primary" data-exit-save ${canSave ? "" : "disabled"}>${t.saveExit}</button>
      </div></dialog>`;
  }

  _renderList() {
    const t = this._t;
    const status = this._runtimeMessage();
    const disabled = this._canWrite() ? "" : "disabled";
    const rows = this._rules.map(({ rule, source, targets, target_error, condition_summary, schedule_summary }) => {
      const targetNames = (targets ?? []).map((item) => item.name).join(", ");
      const color = rule.points ? cssGradient(rule.points, rule.mode) : rgbToHex(rule.rgb_color ?? [255,255,255]);
      return `<article class="rule"><div><strong>${esc(rule.name)}</strong>
        <span class="badge ${rule.enabled !== false ? "on" : ""}">${rule.enabled !== false ? t.enabled : t.disabled}</span>
        <div class="meta"><span>${t.type}: ${esc(t[rule.type] ?? rule.type)}</span><span>${t.priority}: ${esc(rule.priority)}</span>
        <span>${t.source}: ${esc(source?.name ?? rule.source)}</span><span>${t.targets}: ${esc(targetNames)}</span>
        ${condition_summary ? `<span>${t.conditions}: ${esc(condition_summary)}</span>` : ""}
        ${schedule_summary ? `<span>${t.schedule}: ${esc(schedule_summary)}</span>` : ""}</div>
        <div class="rule-color" style="background:${color}"></div>
        ${target_error ? `<p role="status">${t.unsafe}: ${esc(target_error)}</p>` : ""}
        </div><div class="rule-actions">
        <button data-edit="${esc(rule.id)}">${t.edit}</button>
        <button data-duplicate="${esc(rule.id)}" ${disabled}>${t.duplicate}</button>
        <button data-toggle="${esc(rule.id)}" data-enabled="${rule.enabled !== false}" ${disabled}>
        ${rule.enabled !== false ? t.disable : t.enable}</button>
        <button class="danger" data-delete="${esc(rule.id)}" ${disabled}>${t.remove}</button></div></article>`;
    }).join("");
    const list = this._loading ? `<p>${t.loading}</p>` : rows || (this._error || status ? "" : `<p class="muted">${t.noRules}</p>`);
    return `<main><div class="toolbar"><button data-home>← ${t.home}</button>
      <button data-reload ${this._loading || this._saving || this._runtimeStatus === "offline" ? "disabled" : ""}>${t.checkStatus}</button>
      <span class="spacer"></span><button class="primary" data-create ${disabled}>${t.create}</button></div><h1>${t.smartRules}</h1>
      ${status ? `<div class="message" role="status">${esc(status)}</div>` : ""}
      ${this._error ? `<div class="message error" role="alert">${esc(this._error)}</div>` : ""}
      ${this._notice ? `<div class="message notice" role="status">${esc(this._notice)}</div>` : ""}
      <section class="card">${list}</section></main>`;
  }

  _targetSelect(label, key, items) {
    return picker(label, `target_selection.${key}`, items ?? [],
      this._draft.target_selection?.[key] ?? [], this._t, true);
  }

  _entities(kind) {
    return entityItems(this._hass?.states, this._selections.entities, kind);
  }

  _unit() {
    return this._hass?.states?.[this._draft.source]?.attributes?.unit_of_measurement ??
      (this._selected?.rule?.source === this._draft.source ? this._selected?.unit : undefined);
  }

  _renderOrigin() {
    const t = this._t, r = this._draft;
    if (r.type === "event") return this._renderTrigger();
    const items = this._entities(r.type);
    const entity = items.find((item) => item.entity_id === r.source);
    return `<div class="form-grid">${picker(t.entity, "source", items, r.source, t)}
      ${r.type === "state" ? selectField(t.operator, "operator",
        [["equals", t.equals], ["not_equals", t.notEquals]], r.operator) +
        stateControl("state", entity, r.state, t) : ""}</div>`;
  }

  _renderTrigger() {
    const t = this._t;
    const trigger = this._draft.trigger ?? {};
    const kind = this._triggerKind ?? triggerKind(trigger);
    const types = ["trigger_state", "input_button", "event_entity", "event_bus", "device"];
    if (kind === "advanced") types.push("advanced");
    const mode = selectField(t.trigger, "trigger_kind", types.map((type) => [type, t[type]]), kind);
    if (kind === "advanced") return `${mode}<p class="muted">${t.advancedHelp}</p>`;
    if (kind === "device") {
      const deviceId = this._deviceId ?? trigger.device_id;
      const triggers = this._deviceTriggers ?? [];
      const options = [[ "", trigger.device_id ? t.advanced : t.choose ],
        ...triggers.map((item, index) => [String(index),
          [item.type, item.subtype, item.entity_id, item.domain].filter(Boolean).join(" · ")])];
      return `<div class="form-grid">${mode}
        ${picker(t.deviceName, "trigger_device", this._selections.devices ?? [], deviceId, t)}
        ${selectField(t.deviceTrigger, "trigger_device_choice", options, this._deviceChoice ?? "")}
        </div>${this._loadingTriggers ? `<p role="status">${t.busyDevices}</p>` : ""}
        ${trigger.device_id ? `<p class="muted">${esc(trigger.type)} · ${esc(trigger.subtype ?? trigger.domain)}</p>` : ""}`;
    }
    if (kind === "event_bus") {
      const fields = this._eventPairs.map(([key, value], index) => `<div class="row">
        ${inputField(t.eventKey, `event_pairs.${index}.0`, key)}
        ${inputField(t.eventValue, `event_pairs.${index}.1`, value)}
        <button data-remove-event-pair="${index}">${t.remove}</button></div>`).join("");
      return `${mode}${inputField(t.eventName, "trigger.event_type", trigger.event_type)}
        ${fields}<button data-add-event-pair>${t.add} · ${t.eventKey}</button>`;
    }
    const entityKind = kind === "event_entity" ? "event" : kind;
    const items = this._entities(entityKind);
    const entity = items.find((item) => item.entity_id === trigger.entity_id);
    return `<div class="form-grid">${mode}
      ${picker(t.entity, "trigger.entity_id", items, trigger.entity_id, t)}
      ${kind === "trigger_state" ? stateControl("trigger.from", entity, trigger.from,
        { ...t, expected: t.triggerFrom }) + stateControl("trigger.to", entity, trigger.to,
        { ...t, expected: t.triggerTo }) : ""}</div>`;
  }

  _renderTime() {
    const t = this._t, r = this._draft;
    const unit = this._dwellUnit ?? "seconds";
    const factor = { seconds: 1, minutes: 60, hours: 3600 }[unit];
    return `<label class="check"><input type="checkbox" data-schedule-enabled ${r.schedule ? "checked" : ""}>
      ${t.scheduled}</label>${r.schedule ? scheduleControls("schedule", r.schedule, t) : ""}
      ${r.type === "event" ? "" : `<div class="form-grid">
        ${numberField(t.dwell, "dwell_value", r.for_seconds == null ? "" : r.for_seconds / factor, 'min="0" step="any"')}
        ${selectField(t.dwell, "dwell_unit", ["seconds", "minutes", "hours"].map((key) => [key, t[key]]), unit)}
        </div><p class="muted">${t.dwellHelp}</p>`}`;
  }

  _renderNumeric() {
    if (this._draft.type !== "numeric") return "";
    const t = this._t, r = this._draft, unit = this._unit();
    const mode = r.points ? r.mode ?? "interpolate" : "fixed";
    const unitLabel = unit ? ` (${esc(unit)})` : "";
    const style = selectField(t.calculation, "numeric_style",
      [["fixed", t.fixedColor], ["interpolate", t.interpolate], ["ranges", t.ranges]], mode);
    const activation = `<section class="card"><h3>${t.activation}</h3>
      ${numericControls("activation", r.activation, t, unit, true)}
      <div class="form-grid">${numberField(t.variability + unitLabel, "minimum_change", draftValue(r, "minimum_change", 0), 'min="0" step="any"')}
      ${numberField(t.interval, "minimum_interval", draftValue(r, "minimum_interval", 0), 'min="0" step="any"')}</div></section>`;
    if (mode === "fixed") return activation + `<section class="card">${style}</section>`;
    const points = sortPoints(r.points ?? []);
    const stops = gradientStopEntries(points, mode);
    const svgStops = stops.map((stop) => `<stop offset="${stop.offset}%" stop-color="${stop.color}"></stop>`).join("");
    const markers = points.map((point, index) =>
      `<button class="marker" data-select-point="${index}" style="left:${pointPercent(point.value, points)}%;background:${rgbToHex(point.rgb)}" aria-label="${esc(t.selectPoint.replace("{value}", point.value))}"></button>`).join("");
    const graphPoints = points.map((point, index) => {
      const x = 30 + pointPercent(point.value, points) * 8.4;
      return `<g class="graph-point" data-select-point="${index}" tabindex="0" role="button"
        aria-label="${esc(t.selectPoint.replace("{value}", point.value))}"><circle cx="${x}" cy="48" r="10"
        fill="${rgbToHex(point.rgb)}"></circle><line x1="${x}" y1="60" x2="${x}" y2="72" stroke="var(--secondary-text-color)"></line>
        <text x="${x}" y="92" text-anchor="middle">${esc(point.value)}${unitLabel}</text></g>`;
    }).join("");
    const rows = points.map((point, index) => `<div class="point">
      <span class="swatch" style="background:${rgbToHex(point.rgb)}"></span>
      <label>${t.value}${unitLabel}<input type="number" step="any" value="${esc(this._pointInput?.get(index) ?? point.value)}" data-point-value="${index}"></label>
      <label>${t.color}<input type="color" value="${rgbToHex(point.rgb)}" data-point-color="${index}"></label>
      <button class="danger" data-remove-point="${index}">${t.remove}</button>
      <code>${rgbToHex(point.rgb)} · RGB(${point.rgb.join(", ")})</code></div>`).join("");
    const p = this._numericPreview;
    const preview = p ? `<div class="preview" data-preview-result><span class="swatch" style="background:${esc(p.hex)}"></span>
      <div><strong>${esc(p.hex)} · RGB(${p.rgb.join(", ")})</strong><p>${t.intervalResult} ${esc(p.lower)}${p.lower !== p.upper ? `–${esc(p.upper)}` : ""}${unitLabel}</p></div></div>` : "";
    return activation + `<section class="card"><h3>${t.points}</h3>${style}
      <h3>${t.colorBar}</h3><div class="visual"><div class="colorbar" style="background:${cssGradient(points, mode)}"></div>${markers}</div>
      <h3>${t.graph}</h3><svg class="axis" viewBox="0 0 900 115" role="group" aria-label="${t.graph}">
      <defs><linearGradient id="graph-gradient">${svgStops}</linearGradient></defs>
      <line class="baseline" x1="30" y1="48" x2="870" y2="48"></line><line class="curve" x1="30" y1="48" x2="870" y2="48" stroke="url(#graph-gradient)"></line>
      ${graphPoints}</svg>${rows}<button data-add-point>${t.addPoint}</button>
      <div class="form-grid"><label>${t.simulate}${unitLabel}<input type="number" step="any" data-simulate value="${esc(this._simulateValue)}"></label>
      <button data-preview-numeric>${t.simulator}</button></div>${preview}</section>`;
  }

  _focusPoint(index) {
    const input = this.shadowRoot.querySelector(`[data-point-value="${index}"]`);
    input?.scrollIntoView?.({ behavior: "smooth", block: "center" });
    input?.focus?.({ preventScroll: true });
  }

  _renderEditor() {
    const t = this._t, r = this._draft, selection = r.target_selection ?? blankTargets();
    const items = this._selections;
    const names = (key) => this._targetPreview?.[key]?.map((item) => item.name).join(", ");
    const preview = [["targets", t.targets], ["excluded", t.excluded], ["duplicates", t.duplicateTargets]]
      .map(([key, title]) => names(key) ? `<p data-preview-result>${title}: ${esc(names(key))}</p>` : "").join("");
    const status = this._runtimeMessage();
    const ruleError = this._selected?.target_error;
    return `<main><div class="toolbar"><button data-back>← ${t.smartRules}</button>
      <button data-reload ${this._loading || this._saving || this._runtimeStatus === "offline" ? "disabled" : ""}>${t.checkStatus}</button></div>
      <h1>${esc(r.name || t.create)}</h1>
      ${status ? `<div class="message" role="status">${esc(status)}</div>` : ""}
      ${this._notice ? `<div class="message notice" role="status">${esc(this._notice)}</div>` : ""}
      ${this._error ? `<div class="message error" role="alert">${esc(this._error)}</div>` : ""}
      <fieldset class="editor-fields" ${this._saving ? "disabled" : ""}>
      <section class="card"><h3>${t.general}</h3><div class="form-grid">
        ${inputField(t.name, "name", r.name)}
        ${this._creating ? selectField(t.type, "type", ["state", "numeric", "event"].map((kind) => [kind, t[kind]]), r.type)
          : `<p>${t[r.type]}</p>`}
        <label class="check"><input type="checkbox" data-boolean="enabled" ${r.enabled !== false ? "checked" : ""}>${t.enabled}</label>
      </div></section>
      <section class="card"><h3>${t.origin}</h3>${this._renderOrigin()}</section>
      <section class="card"><h3>${t.conditionSection}</h3>${conditionControls(r.conditions,
        { t, entities: this._entities("state"), numeric: this._entities("numeric") })}</section>
      <section class="card"><h3>${t.timeSection}</h3>${this._renderTime()}</section>
      <section class="card"><h3>${t.targetSection}</h3><div class="form-grid">
        ${this._targetSelect(t.individual, "entities", items.managed_lights)}
        ${this._targetSelect(t.zones, "zones", items.zones)}
        ${this._targetSelect(t.areas, "areas", items.areas)}
        ${this._targetSelect(t.labels, "labels", items.labels)}
        ${this._targetSelect(t.groups, "groups", items.groups)}
        <label class="check"><input type="checkbox" data-target-all ${selection.all_managed ? "checked" : ""}>${t.allManaged}</label>
      </div><button data-preview-targets ${status ? "disabled" : ""}>${t.previewTargets}</button>
      ${ruleError && !this._targetPreview ? `<p role="alert">${t.unsafe}: ${esc(ruleError)}</p>` : ""}${preview}</section>
      ${this._renderNumeric()}
      <section class="card"><h3>${t.colorSection}</h3><div class="form-grid">
        ${r.type !== "numeric" || !r.points ? `<label>${t.color}<input type="color" data-color
          value="${rgbToHex(r.rgb_color ?? [255,255,255])}"></label>` : ""}
        ${numberField(t.brightness, "brightness", draftValue(r, "brightness", 255), 'min="1" max="255"')}
        ${numberField(t.transition, "transition", draftValue(r, "transition", 0), 'min="0" step="0.1"')}
        ${selectField(t.animation, "animation", ["fixed","blink","pulse"].map((key) => [key, t[key]]), r.animation ?? "fixed")}
        ${r.animation && r.animation !== "fixed" ? numberField(t.period, "period", draftValue(r, "period", 1), 'min="0.1" step="0.1"') : ""}
      </div><p class="muted">${t.transitionHelp}</p></section>
      <section class="card"><h3>${t.policySection}</h3><div class="form-grid">
        ${numberField(t.priority, "priority", draftValue(r, "priority", 40), 'min="0" max="100"')}
        ${r.type === "event" ? numberField(t.duration, "duration", draftValue(r, "duration", 5), 'min="0.1" step="0.1"') : ""}
      </div>${r.type === "event" ? `<p class="muted">${t.durationHelp}</p>` : ""}</section>
      <section class="card"><h3>${t.summarySection}</h3><p>${esc(r.name)} · ${esc(t[r.type])} · P${esc(r.priority ?? 40)}</p>
        <details><summary>${t.advanced}</summary><pre>${esc(JSON.stringify(r, null, 2))}</pre></details></section>
      </fieldset>
      <div class="actions">${this._original ? `<button data-restore>${t.restore}</button>` : ""}
        <button data-discard>${t.cancel}</button><button class="primary" data-save
        ${!this._canWrite() || !r.name?.trim() || this._invalidNumeric() ? "disabled" : ""}>${this._saving ? t.saving : t.save}</button>
      </div></main>`;
  }

  _render() {
    if (!this.shadowRoot) return;
    const active = this.shadowRoot.activeElement;
    const focus = active && [...active.attributes].find((attr) => attr.name.startsWith("data-"));
    const content = this._draft ? this._renderEditor() : this._view === "rules" ? this._renderList() : this._renderHome();
    this.shadowRoot.innerHTML = `<style>${this._styles()}</style>${content}${this._renderExitDialog()}`; this._bind();
    const dialog = this.shadowRoot.querySelector("[data-exit-dialog]");
    if (dialog?.isConnected) dialog.showModal();
    if (focus) {
      const element = [...this.shadowRoot.querySelectorAll(`[${focus.name}]`)]
        .find((candidate) => candidate.getAttribute(focus.name) === focus.value);
      element?.focus({ preventScroll: true });
      if (element && typeof active.selectionStart === "number") {
        element.setSelectionRange?.(active.selectionStart, active.selectionEnd);
      }
    }
  }

  _bind() {
    const root = this.shadowRoot;
    const on = (selector, event, handler) =>
      root.querySelectorAll(selector).forEach((element) =>
        element.addEventListener(event, (e) => handler(element, e)));
    const click = (selector, handler) => on(selector, "click", handler);
    click("[data-rules]", () => this._openRules());
    click("[data-home]", () => this._goHome());
    click("[data-reload]", () => {
      this._error = this._draft && this._revision !== this._catalogRevision ? this._t.conflict : undefined;
      this._load();
    });
    click("[data-create]", () => this._create());
    click("[data-edit]", (el) => this._edit(el.dataset.edit));
    click("[data-duplicate]", (el) => this._mutate("duplicate", { rule_id: el.dataset.duplicate }));
    click("[data-toggle]", (el) => this._mutate("toggle", {
      rule_id: el.dataset.toggle, enabled: el.dataset.enabled !== "true",
    }));
    click("[data-delete]", (el) => {
      if (window.confirm(this._t.confirmDelete)) this._mutate("delete", { rule_id: el.dataset.delete });
    });
    click("[data-back]", () => this._requestExit("rules"));
    click("[data-restore]", () => { if (!this._saving) this._restore(); });
    click("[data-discard]", () => this._requestExit("rules"));
    click("[data-save]", () => this._save());
    click("[data-exit-continue]", () => this._closeExit());
    on("[data-exit-dialog]", "cancel", (_dialog, event) => {
      event.preventDefault();
      this._closeExit();
    });
    click("[data-exit-discard]", () => {
      this._exitEditor(this._exitView);
      this._render();
    });
    click("[data-exit-save]", () => {
      const destination = this._exitView;
      this._closeExit();
      this._save(destination);
    });
    on("[data-search]", "input", (el) => {
      this._searches.set(el.dataset.search, el.value);
      this._filterPicker(el);
    });
    for (const el of root.querySelectorAll("[data-search]")) {
      el.value = this._searches.get(el.dataset.search) ?? "";
      this._filterPicker(el);
    }
    on("[data-path]", "input", (el) => {
      if (el.tagName !== "INPUT" || el.type === "time") return;
      const value = el.type === "number" ? (el.value === "" ? null : Number(el.value)) : el.value;
      this._changeField(el.dataset.path, value, false);
    });
    on("[data-path]", "change", (el) => {
      if (el.tagName !== "INPUT" || el.type === "time") this._changeField(el.dataset.path, el.value);
    });
    on("[data-add-choice]", "change", (el) => {
      if (el.value) this._set(el.dataset.addChoice, [...this._get(el.dataset.addChoice), el.value]);
    });
    click("[data-remove-choice]", (el) => this._set(el.dataset.removeChoice,
      this._get(el.dataset.removeChoice).filter((value) => value !== el.dataset.choice)));
    on("[data-boolean]", "change", (el) => this._set(el.dataset.boolean, el.checked));
    on("[data-target-all]", "change", (el) => this._set("target_selection.all_managed", el.checked));
    on("[data-schedule-enabled]", "change", (el) => this._set("schedule", el.checked ? defaultSchedule() : null));
    on("[data-day-path]", "change", (el) => {
      const previous = this._get(el.dataset.dayPath) ?? [];
      this._set(el.dataset.dayPath, el.checked ? [...previous, el.value] :
        previous.filter((day) => day !== el.value));
    });
    click("[data-add-root]", () => this._set("conditions", newCondition("state")));
    click("[data-add-condition]", (el) => {
      const path = el.dataset.addCondition + ".conditions";
      if (treeSize(this._draft.conditions) < 32) this._set(path, [...this._get(path), newCondition("state")]);
    });
    click("[data-remove-condition]", (el) => this._moveCondition(el.dataset.removeCondition));
    click("[data-move-condition]", (el) => this._moveCondition(el.dataset.moveCondition, Number(el.dataset.delta)));
    click("[data-add-event-pair]", () => {
      this._eventPairs.push(["", ""]); this._render();
    });
    click("[data-remove-event-pair]", (el) => {
      this._eventPairs.splice(Number(el.dataset.removeEventPair), 1); this._render();
    });
    click("[data-preview-targets]", () => this._previewTargets());
    on("[data-color]", "change", (el) => this._set("rgb_color", hexToRgb(el.value)));
    click("[data-add-point]", () => {
      const points = this._draftPoints(false);
      if (points) this._updatePoints([...points, nextPoint(points)]);
    });
    click("[data-remove-point]", (el) => {
      const index = Number(el.dataset.removePoint);
      this._pointInput.delete(index);
      const ordered = sortPoints(this._draft.points);
      const remaining = removePoint(ordered, index);
      const changed = new Map([...this._pointInput].map(([key, value]) => [key > index ? key - 1 : key, value]));
      this._pointInput = changed;
      this._set("points", remaining);
    });
    on("[data-point-value]", "input", (el) => {
      this._pointInput.set(Number(el.dataset.pointValue), el.value);
      this._invalidatePreviews();
      this._refreshSave();
    });
    on("[data-point-color]", "change", (el) => {
      const index = Number(el.dataset.pointColor);
      const ordered = sortPoints(this._draft.points);
      this._set("points", replacePoint(ordered, index, { ...ordered[index], rgb: hexToRgb(el.value) }));
    });
    click("[data-select-point]", (el) => this._focusPoint(Number(el.dataset.selectPoint)));
    on(".graph-point[data-select-point]", "keydown", (el, event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        this._focusPoint(Number(el.dataset.selectPoint));
      }
    });
    on("[data-simulate]", "input", (el) => {
      this._simulateValue = el.value;
      this._invalidatePreviews();
    });
    click("[data-preview-numeric]", () => this._previewNumeric());
  }
}

if (!customElements.get("smart-led-manager-visual-editor")) {
  customElements.define("smart-led-manager-visual-editor", SmartLEDManagerVisualEditor);
}
