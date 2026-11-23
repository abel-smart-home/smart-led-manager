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
} from "./visual-editor-model.mjs";

const TEXT = {
  es: {
    title: "Editor gráfico de reglas numéricas",
    subtitle: "Los cambios permanecen en borrador hasta que los guardes.",
    rules: "Reglas numéricas",
    noRules: "No hay reglas numéricas. Créala primero con el editor nativo de Opciones.",
    edit: "Editar visualmente",
    enabled: "Habilitada",
    disabled: "Deshabilitada",
    source: "Origen",
    targets: "Luces",
    priority: "Prioridad",
    brightness: "Brillo",
    back: "Volver a reglas",
    mode: "Cálculo del color",
    interpolate: "Interpolación",
    ranges: "Rangos",
    colorBar: "Barra de colores",
    graph: "Distribución numérica",
    points: "Puntos editables",
    add: "Agregar punto",
    value: "Valor",
    color: "Color",
    remove: "Eliminar",
    simulator: "Simulador exacto",
    simulateValue: "Valor hipotético",
    result: "Resultado",
    interval: "Punto o intervalo",
    save: "Guardar cambios",
    reset: "Restaurar borrador",
    discard: "Descartar y volver",
    reload: "Recargar configuración",
    loading: "Cargando…",
    saving: "Guardando…",
    saved: "Cambios guardados; Home Assistant recargará la integración.",
    loadError: "No se pudo cargar el editor.",
    saveError: "No se pudieron guardar los cambios.",
    conflict: "La configuración cambió en otra sesión. Recarga antes de guardar.",
    unsaved: "Hay cambios sin guardar. ¿Deseas descartarlos?",
    invalid: "Corrige los puntos antes de guardar.",
    too_few_points: "Se requieren al menos dos puntos.",
    duplicate_value: "Los valores numéricos deben ser únicos.",
    invalid_value: "Todos los valores deben ser números finitos.",
    invalid_color: "El color RGB no es válido.",
    invalid_mode: "El modo de color no es válido.",
    below: "Por debajo del mínimo; se usa el primer punto",
    above: "Por encima del máximo; se usa el último punto",
    point: "Coincidencia exacta con el punto {lower}",
    between: "Intervalo de {lower} a {upper}",
    selectPoint: "Seleccionar punto {value}",
    metadata: "Datos de la regla (solo lectura en este editor)",
  },
  en: {
    title: "Numeric rule visual editor",
    subtitle: "Changes stay in a draft until you save them.",
    rules: "Numeric rules",
    noRules: "No numeric rules exist. Create one first with the native Options editor.",
    edit: "Edit visually",
    enabled: "Enabled",
    disabled: "Disabled",
    source: "Source",
    targets: "Lights",
    priority: "Priority",
    brightness: "Brightness",
    back: "Back to rules",
    mode: "Color calculation",
    interpolate: "Interpolation",
    ranges: "Ranges",
    colorBar: "Color bar",
    graph: "Numeric distribution",
    points: "Editable points",
    add: "Add point",
    value: "Value",
    color: "Color",
    remove: "Remove",
    simulator: "Exact simulator",
    simulateValue: "Hypothetical value",
    result: "Result",
    interval: "Point or interval",
    save: "Save changes",
    reset: "Reset draft",
    discard: "Discard and return",
    reload: "Reload configuration",
    loading: "Loading…",
    saving: "Saving…",
    saved: "Changes saved; Home Assistant will reload the integration.",
    loadError: "The editor could not be loaded.",
    saveError: "Changes could not be saved.",
    conflict: "Configuration changed in another session. Reload before saving.",
    unsaved: "There are unsaved changes. Discard them?",
    invalid: "Correct the points before saving.",
    too_few_points: "At least two points are required.",
    duplicate_value: "Numeric values must be unique.",
    invalid_value: "Every value must be a finite number.",
    invalid_color: "The RGB color is invalid.",
    invalid_mode: "The color mode is invalid.",
    below: "Below the minimum; the first point is used",
    above: "Above the maximum; the last point is used",
    point: "Exact match with point {lower}",
    between: "Interval from {lower} to {upper}",
    selectPoint: "Select point {value}",
    metadata: "Rule data (read-only in this editor)",
  },
};

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

class SmartLEDManagerVisualEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = undefined;
    this._panel = undefined;
    this._loaded = false;
    this._loading = false;
    this._rules = [];
    this._revision = undefined;
    this._selected = undefined;
    this._original = undefined;
    this._draft = undefined;
    this._preview = undefined;
    this._simulatedValue = "";
    this._error = undefined;
    this._notice = undefined;
    this._saving = false;
    this._beforeUnload = (event) => {
      if (this._isDirty()) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
  }

  set hass(value) {
    this._hass = value;
    if (this.isConnected && !this._loaded && !this._loading) this._load();
    else if (this.isConnected) this._render();
  }

  set panel(value) {
    this._panel = value;
    if (this.isConnected && !this._loaded && !this._loading) this._load();
  }

  set route(value) {
    this._route = value;
  }

  set narrow(value) {
    this._narrow = value;
  }

  connectedCallback() {
    window.addEventListener("beforeunload", this._beforeUnload);
    this._render();
    if (!this._loaded && !this._loading) this._load();
  }

  disconnectedCallback() {
    window.removeEventListener("beforeunload", this._beforeUnload);
  }

  get _entryId() {
    return this._panel?.config?.entry_id;
  }

  get _t() {
    const language = this._hass?.locale?.language ?? this._hass?.language ?? "en";
    return String(language).toLowerCase().startsWith("es") ? TEXT.es : TEXT.en;
  }

  _isDirty() {
    return draftChanged(this._original, this._draft);
  }

  async _load() {
    if (!this._hass || !this._entryId || this._loading) return;
    this._loading = true;
    this._error = undefined;
    this._render();
    try {
      const response = await this._hass.callWS({
        type: "smart_led_manager/rules/get",
        entry_id: this._entryId,
      });
      this._rules = response.rules;
      this._revision = response.revision;
      this._loaded = true;
      if (this._selected) {
        const selectedId = this._selected.rule.id;
        this._selected = this._rules.find((item) => item.rule.id === selectedId);
        if (this._selected) this._setDraft(this._selected);
      }
    } catch (error) {
      this._error = `${this._t.loadError} ${error?.message ?? ""}`.trim();
    } finally {
      this._loading = false;
      this._render();
    }
  }

  _setDraft(selected) {
    this._selected = selected;
    this._original = {
      mode: selected.rule.mode,
      points: sortPoints(selected.rule.points),
    };
    this._draft = deepClone(this._original);
    const points = this._draft.points;
    this._simulatedValue = points.length
      ? String((Number(points[0].value) + Number(points.at(-1).value)) / 2)
      : "0";
    this._preview = undefined;
    this._error = undefined;
    this._notice = undefined;
    this._requestPreview();
  }

  _openRule(ruleId) {
    const selected = this._rules.find((item) => item.rule.id === ruleId);
    if (selected) {
      this._setDraft(selected);
      this._render();
    }
  }

  _leaveEditor(discard = false) {
    if (this._isDirty() && !discard && !window.confirm(this._t.unsaved)) return;
    this._selected = undefined;
    this._original = undefined;
    this._draft = undefined;
    this._preview = undefined;
    this._error = undefined;
    this._notice = undefined;
    this._render();
  }

  _resetDraft() {
    this._draft = deepClone(this._original);
    this._error = undefined;
    this._notice = undefined;
    this._requestPreview();
    this._render();
  }

  _draftError() {
    const code = validateDraft(this._draft?.mode, this._draft?.points);
    return code ? this._t[code] ?? this._t.invalid : undefined;
  }

  async _requestPreview() {
    if (!this._draft || !this._selected || !this._hass) return;
    const draftError = this._draftError();
    const value = Number(this._simulatedValue);
    if (draftError || !Number.isFinite(value)) {
      this._preview = undefined;
      this._render();
      return;
    }
    try {
      const response = await this._hass.callWS({
        type: "smart_led_manager/rules/preview",
        entry_id: this._entryId,
        rule_id: this._selected.rule.id,
        mode: this._draft.mode,
        points: this._draft.points,
        values: [value],
      });
      this._preview = response.results[0];
      this._error = undefined;
    } catch (error) {
      this._preview = undefined;
      this._error = error?.message ?? this._t.invalid;
    }
    this._render();
  }

  async _save() {
    const validation = this._draftError();
    if (validation) {
      this._error = validation;
      this._render();
      return;
    }
    this._saving = true;
    this._error = undefined;
    this._notice = undefined;
    this._render();
    try {
      const response = await this._hass.callWS({
        type: "smart_led_manager/rules/save",
        entry_id: this._entryId,
        rule_id: this._selected.rule.id,
        revision: this._revision,
        mode: this._draft.mode,
        points: sortPoints(this._draft.points),
      });
      this._revision = response.revision;
      this._selected.rule = response.rule;
      this._original = {
        mode: response.rule.mode,
        points: sortPoints(response.rule.points),
      };
      this._draft = deepClone(this._original);
      this._notice = this._t.saved;
    } catch (error) {
      this._error = error?.code === "conflict" ? this._t.conflict :
        `${this._t.saveError} ${error?.message ?? ""}`.trim();
    } finally {
      this._saving = false;
      this._render();
    }
  }

  _relationText() {
    if (!this._preview) return "—";
    return (this._t[this._preview.relation] ?? this._preview.relation)
      .replace("{lower}", this._preview.lower)
      .replace("{upper}", this._preview.upper);
  }

  _styles() {
    return `
      :host { display:block; min-height:100%; color:var(--primary-text-color); background:var(--primary-background-color); }
      * { box-sizing:border-box; }
      main { max-width:1120px; margin:0 auto; padding:24px max(16px, env(safe-area-inset-right)) 40px max(16px, env(safe-area-inset-left)); }
      h1 { font-size:28px; margin:0 0 4px; }
      h2 { font-size:21px; margin:0; }
      h3 { font-size:16px; margin:0 0 14px; }
      p { line-height:1.5; }
      .muted { color:var(--secondary-text-color); }
      .toolbar, .section-title, .actions, .point-row, .metadata { display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
      .section-title { justify-content:space-between; margin-bottom:14px; }
      .card { background:var(--ha-card-background, var(--card-background-color)); border-radius:var(--ha-card-border-radius, 12px); box-shadow:var(--ha-card-box-shadow); padding:20px; margin-top:18px; border:1px solid var(--divider-color); }
      .rule-list { display:grid; gap:12px; }
      .rule { display:grid; grid-template-columns:1fr auto; gap:10px 18px; align-items:center; padding:16px; border:1px solid var(--divider-color); border-radius:10px; }
      .rule strong { font-size:17px; }
      .rule-meta { display:flex; flex-wrap:wrap; gap:8px 14px; color:var(--secondary-text-color); font-size:14px; margin-top:6px; }
      button, select, input { font:inherit; }
      button { min-height:44px; border:0; border-radius:10px; padding:10px 16px; cursor:pointer; color:var(--primary-text-color); background:var(--secondary-background-color); }
      button.primary { color:var(--text-primary-color, #fff); background:var(--primary-color); }
      button.danger { color:var(--error-color); }
      button:disabled { opacity:.55; cursor:not-allowed; }
      button:focus-visible, input:focus-visible, select:focus-visible, [tabindex]:focus-visible { outline:3px solid var(--primary-color); outline-offset:2px; }
      .badge { padding:4px 9px; border-radius:999px; font-size:12px; background:var(--secondary-background-color); }
      .badge.on { color:var(--success-color); }
      .metadata { padding:12px 0 2px; color:var(--secondary-text-color); }
      .metadata span { padding:6px 10px; border-radius:8px; background:var(--secondary-background-color); }
      label { display:grid; gap:7px; color:var(--secondary-text-color); font-size:13px; }
      input[type=number], select { min-height:44px; min-width:130px; padding:8px 10px; color:var(--primary-text-color); background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:8px; }
      input[type=color] { width:54px; height:44px; border:1px solid var(--divider-color); border-radius:8px; background:transparent; padding:3px; }
      .visual { position:relative; margin:20px 0 8px; padding-top:18px; }
      .color-bar { height:40px; border-radius:10px; border:1px solid var(--divider-color); }
      .marker { position:absolute; top:0; width:30px; height:30px; min-height:30px; padding:0; border-radius:50%; border:3px solid var(--card-background-color); box-shadow:0 0 0 1px var(--primary-text-color); transform:translateX(-50%); }
      .axis { width:100%; min-height:120px; overflow:visible; }
      .axis text { fill:var(--primary-text-color); font-size:12px; }
      .axis .baseline { stroke:var(--secondary-text-color); stroke-width:2; }
      .axis .curve { stroke-width:14; stroke-linecap:round; }
      .axis .point { stroke:var(--card-background-color); stroke-width:3; cursor:pointer; }
      .point-grid { display:grid; gap:10px; }
      .point-row { padding:12px; border:1px solid var(--divider-color); border-radius:10px; background:var(--primary-background-color); }
      .point-row.selected { border-color:var(--primary-color); box-shadow:0 0 0 1px var(--primary-color); }
      .swatch { width:32px; height:32px; border-radius:50%; border:1px solid var(--divider-color); }
      .point-row .spacer { flex:1; }
      .sim-grid { display:grid; grid-template-columns:minmax(170px, 1fr) minmax(220px, 2fr); gap:18px; align-items:end; }
      .result { min-height:70px; display:flex; align-items:center; gap:14px; padding:12px; border-radius:10px; background:var(--secondary-background-color); }
      .result .swatch { width:48px; height:48px; flex:0 0 auto; }
      .message { padding:12px 14px; margin-top:14px; border-radius:8px; }
      .error { color:var(--error-color); background:color-mix(in srgb, var(--error-color) 12%, transparent); }
      .notice { color:var(--success-color); background:color-mix(in srgb, var(--success-color) 12%, transparent); }
      .actions { justify-content:flex-end; position:sticky; bottom:0; padding:14px 0 max(14px, env(safe-area-inset-bottom)); background:linear-gradient(transparent, var(--primary-background-color) 24%); }
      @media (max-width:700px) {
        main { padding-top:16px; }
        h1 { font-size:23px; }
        .rule { grid-template-columns:1fr; }
        .rule button { width:100%; }
        .sim-grid { grid-template-columns:1fr; }
        .point-row label:first-of-type { flex:1 1 140px; }
        .actions button { flex:1 1 150px; }
      }
    `;
  }

  _renderList() {
    const t = this._t;
    const rules = this._rules.length
      ? `<div class="rule-list">${this._rules.map(({ rule, unit }) => `
          <article class="rule">
            <div>
              <strong>${escapeHtml(rule.name || rule.id)}</strong>
              <span class="badge ${rule.enabled !== false ? "on" : ""}">${rule.enabled !== false ? t.enabled : t.disabled}</span>
              <div class="rule-meta">
                <span>${t.source}: ${escapeHtml(rule.source)}${unit ? ` (${escapeHtml(unit)})` : ""}</span>
                <span>${t.priority}: ${escapeHtml(rule.priority)}</span>
                <span>${t.targets}: ${escapeHtml((rule.targets || []).join(", "))}</span>
              </div>
            </div>
            <button class="primary" data-open-rule="${escapeHtml(rule.id)}">${t.edit}</button>
          </article>`).join("")}</div>`
      : `<p class="muted">${t.noRules}</p>`;
    return `
      <main>
        <h1>${t.title}</h1>
        <p class="muted">${t.subtitle}</p>
        ${this._error ? `<div class="message error" role="alert">${escapeHtml(this._error)}</div>` : ""}
        <section class="card"><div class="section-title"><h2>${t.rules}</h2><button data-reload>${t.reload}</button></div>${rules}</section>
      </main>`;
  }

  _renderEditor() {
    const t = this._t;
    const rule = this._selected.rule;
    const unit = this._selected.unit ? ` ${escapeHtml(this._selected.unit)}` : "";
    const points = sortPoints(this._draft.points);
    const stops = gradientStopEntries(points, this._draft.mode);
    const svgStops = stops.map((stop) => `<stop offset="${stop.offset}%" stop-color="${stop.color}"></stop>`).join("");
    const markers = points.map((point, index) => `
      <button class="marker" data-select-point="${index}" style="left:${pointPercent(point.value, points)}%;background:${rgbToHex(point.rgb)}" aria-label="${escapeHtml(t.selectPoint.replace("{value}", point.value))}"></button>`).join("");
    const graphPoints = points.map((point, index) => {
      const x = 30 + pointPercent(point.value, points) * 8.4;
      return `<g class="graph-point" data-select-point="${index}" tabindex="0" role="button" aria-label="${escapeHtml(t.selectPoint.replace("{value}", point.value))}">
        <circle class="point" cx="${x}" cy="48" r="10" fill="${rgbToHex(point.rgb)}"></circle>
        <line x1="${x}" y1="60" x2="${x}" y2="72" stroke="var(--secondary-text-color)"></line>
        <text x="${x}" y="92" text-anchor="middle">${escapeHtml(point.value)}${unit}</text>
      </g>`;
    }).join("");
    const pointRows = points.map((point, index) => `
      <div class="point-row" id="point-${index}">
        <span class="swatch" style="background:${rgbToHex(point.rgb)}" aria-hidden="true"></span>
        <label>${t.value}<input type="number" step="any" value="${escapeHtml(point.value)}" data-point-value="${index}"><span>${unit || "—"}</span></label>
        <label>${t.color}<input type="color" value="${rgbToHex(point.rgb)}" data-point-color="${index}"></label>
        <code>RGB(${point.rgb.join(", ")}) ${rgbToHex(point.rgb)}</code>
        <span class="spacer"></span>
        <button class="danger" data-delete-point="${index}">${t.remove}</button>
      </div>`).join("");
    const preview = this._preview
      ? `<div class="result"><span class="swatch" style="background:${this._preview.hex}"></span><div><strong>${this._preview.hex}</strong><br>RGB(${this._preview.rgb.join(", ")})<br><span class="muted">${escapeHtml(this._relationText())}</span></div></div>`
      : `<div class="result muted">—</div>`;
    const validation = this._draftError();
    return `
      <main>
        <div class="toolbar"><button data-back>← ${t.back}</button></div>
        <h1>${escapeHtml(rule.name || rule.id)}</h1>
        <p class="muted">${t.metadata}</p>
        <div class="metadata">
          <span>${t.source}: ${escapeHtml(rule.source)}${unit}</span>
          <span>${t.targets}: ${escapeHtml((rule.targets || []).join(", "))}</span>
          <span>${t.priority}: ${escapeHtml(rule.priority)}</span>
          <span>${t.brightness}: ${escapeHtml(rule.brightness)}</span>
          <span>${rule.enabled !== false ? t.enabled : t.disabled}</span>
          <span>ID: ${escapeHtml(rule.id)}</span>
        </div>
        ${this._error ? `<div class="message error" role="alert">${escapeHtml(this._error)}</div>` : ""}
        ${this._notice ? `<div class="message notice" role="status">${escapeHtml(this._notice)}</div>` : ""}
        <section class="card">
          <label>${t.mode}<select data-mode><option value="interpolate" ${this._draft.mode === "interpolate" ? "selected" : ""}>${t.interpolate}</option><option value="ranges" ${this._draft.mode === "ranges" ? "selected" : ""}>${t.ranges}</option></select></label>
        </section>
        <section class="card"><h3>${t.colorBar}</h3><div class="visual"><div class="color-bar" style="background:${cssGradient(points, this._draft.mode)}"></div>${markers}</div></section>
        <section class="card"><h3>${t.graph}</h3><svg class="axis" viewBox="0 0 900 115" role="img" aria-label="${t.graph}"><defs><linearGradient id="graph-gradient">${svgStops}</linearGradient></defs><line class="baseline" x1="30" y1="48" x2="870" y2="48"></line><line class="curve" x1="30" y1="48" x2="870" y2="48" stroke="url(#graph-gradient)"></line>${graphPoints}</svg></section>
        <section class="card">
          <div class="section-title"><h3>${t.points}</h3><button data-add-point>${t.add}</button></div>
          <div class="point-grid">${pointRows}</div>
          ${validation ? `<div class="message error" role="alert">${escapeHtml(validation)}</div>` : ""}
        </section>
        <section class="card"><h3>${t.simulator}</h3><div class="sim-grid"><label>${t.simulateValue}<input type="number" step="any" value="${escapeHtml(this._simulatedValue)}" data-simulate><span>${unit || "—"}</span></label><div><span class="muted">${t.result} · ${t.interval}</span>${preview}</div></div></section>
        <div class="actions">
          <button data-discard>${t.discard}</button>
          <button data-reset ${!this._isDirty() ? "disabled" : ""}>${t.reset}</button>
          <button class="primary" data-save ${this._saving || !this._isDirty() || validation ? "disabled" : ""}>${this._saving ? t.saving : t.save}</button>
        </div>
      </main>`;
  }

  _render() {
    if (!this.shadowRoot) return;
    const content = this._loading && !this._loaded
      ? `<main><h1>${this._t.title}</h1><p>${this._t.loading}</p></main>`
      : this._selected ? this._renderEditor() : this._renderList();
    this.shadowRoot.innerHTML = `<style>${this._styles()}</style>${content}`;
    this._bindEvents();
  }

  _bindEvents() {
    const root = this.shadowRoot;
    root.querySelectorAll("[data-open-rule]").forEach((button) =>
      button.addEventListener("click", () => this._openRule(button.dataset.openRule)),
    );
    root.querySelector("[data-reload]")?.addEventListener("click", () => {
      this._loaded = false;
      this._load();
    });
    root.querySelector("[data-back]")?.addEventListener("click", () => this._leaveEditor());
    root.querySelector("[data-discard]")?.addEventListener("click", () => this._leaveEditor(true));
    root.querySelector("[data-reset]")?.addEventListener("click", () => this._resetDraft());
    root.querySelector("[data-save]")?.addEventListener("click", () => this._save());
    root.querySelector("[data-mode]")?.addEventListener("change", (event) => {
      this._draft.mode = event.target.value;
      this._notice = undefined;
      this._requestPreview();
      this._render();
    });
    root.querySelector("[data-add-point]")?.addEventListener("click", () => {
      this._draft.points = sortPoints([...this._draft.points, nextPoint(this._draft.points)]);
      this._notice = undefined;
      this._requestPreview();
      this._render();
    });
    root.querySelectorAll("[data-delete-point]").forEach((button) =>
      button.addEventListener("click", () => {
        this._draft.points = removePoint(this._draft.points, Number(button.dataset.deletePoint));
        this._notice = undefined;
        this._requestPreview();
        this._render();
      }),
    );
    root.querySelectorAll("[data-point-value]").forEach((input) =>
      input.addEventListener("change", () => {
        const index = Number(input.dataset.pointValue);
        this._draft.points = replacePoint(this._draft.points, index, {
          ...this._draft.points[index], value: input.value,
        });
        this._notice = undefined;
        this._requestPreview();
        this._render();
      }),
    );
    root.querySelectorAll("[data-point-color]").forEach((input) =>
      input.addEventListener("change", () => {
        const index = Number(input.dataset.pointColor);
        this._draft.points = replacePoint(this._draft.points, index, {
          ...this._draft.points[index], rgb: hexToRgb(input.value),
        });
        this._notice = undefined;
        this._requestPreview();
        this._render();
      }),
    );
    root.querySelector("[data-simulate]")?.addEventListener("change", (event) => {
      this._simulatedValue = event.target.value;
      this._requestPreview();
    });
    root.querySelectorAll("[data-select-point]").forEach((marker) => {
      const select = () => this._focusPoint(Number(marker.dataset.selectPoint));
      marker.addEventListener("click", select);
      marker.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          select();
        }
      });
    });
  }

  _focusPoint(index) {
    const row = this.shadowRoot.getElementById(`point-${index}`);
    if (!row) return;
    this.shadowRoot.querySelectorAll(".point-row.selected").forEach((item) => item.classList.remove("selected"));
    row.classList.add("selected");
    row.scrollIntoView({ behavior: "smooth", block: "center" });
    row.querySelector("input")?.focus({ preventScroll: true });
  }
}

if (!customElements.get("smart-led-manager-visual-editor")) {
  customElements.define("smart-led-manager-visual-editor", SmartLEDManagerVisualEditor);
}
