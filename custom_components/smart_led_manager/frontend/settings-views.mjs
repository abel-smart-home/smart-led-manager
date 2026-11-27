import { escapeHtml as esc, numberField, selectField } from "./rule-controls.mjs";

export const PREFERENCE_VIEWS = ["general", "priorities"];
export const SETTINGS_VIEWS = [...PREFERENCE_VIEWS, "recovery", "diagnostics", "nativeSettings"];

export const SETTINGS_TEXT = {
  es: {
    general: "General", generalHint: "Preferencias de la integración",
    priorities: "Prioridades y control", prioritiesMenu: "Prioridades", prioritiesHint: "Prioridad, control manual y protección de la red",
    recovery: "Recuperación", recoveryHint: "Disponibilidad y recuperación de dispositivos",
    diagnostics: "Diagnóstico", diagnosticsHint: "Estado y resumen de la configuración",
    nativeSettings: "Configuración nativa", nativeSettingsHint: "Acceso alternativo de Home Assistant",
    versionLabel: "Versión de la integración", sidebar: "Mostrar Smart LED Manager en la barra lateral",
    openCenter: "Abrir el centro de administración", nativeCenter: "El centro seguirá disponible desde Configuración nativa → Centro de administración.",
    discardSettings: "Descartar", engineDefaults: "Restablecer valores iniciales",
    equalPriority: "Cuando coinciden dos iluminaciones", priorityHelp: "La prioridad más alta gana. Este ajuste solo resuelve empates.",
    tieLabel: "Si tienen la misma prioridad, ¿cuál gana?",
    tieChoices: { newest: "La solicitud más reciente", oldest: "La solicitud más antigua", lexical: "Orden del identificador" },
    tieExample: { newest: "Ejemplo con dos solicitudes de prioridad 60. Gana la que se activó después.", oldest: "Ejemplo con dos solicitudes de prioridad 60. Gana la que se activó primero.", lexical: "En empate, el identificador de la solicitud decide de forma estable." },
    manualGroup: "Control manual", manualLabel: "¿Qué ocurre cuando alguien cambia una luz manualmente?",
    manualChoices: { service_only: "Solo mediante una acción manual explícita", respect: "Respetar cambios manuales detectados", temporary: "Respetar cambios detectados durante 15 minutos" },
    manualExplain: { service_only: "Los cambios directos de una luz no crean una solicitud manual. Usa la acción de control manual explícito.", respect: "Un cambio detectado puede crear una solicitud manual persistente.", temporary: "Un cambio detectado puede crear una solicitud manual con vencimiento de 15 minutos." },
    detectionLimit: "La detección depende del cambio de estado y del contexto que publique Home Assistant. La atribución puede variar por dispositivo o integración.",
    network: "Protección de la red (avanzado)", interval: "Intervalo mínimo entre órdenes por luz (segundos)",
    intervalHelp: "Valor inicial 0,75 s. Afecta a la frecuencia de los efectos y al tiempo de respuesta.",
    invalid_command_interval: "Introduce entre 0,10 y 10 segundos en pasos de 0,05.",
    invalid_sidebar_preference: "Selecciona si el panel aparece en la barra lateral.",
    invalid_engine_preference: "Elige opciones válidas de desempate y control manual.",
    recoveryTitle: "Recuperación automática", recoveryIntro: "Si una luz deja de estar disponible, el motor sigue evaluando las solicitudes. Al volver la luz, recupera la intención que siga vigente en ese momento.",
    recoveryExisting: "Comportamiento actual", recoveryDetail: "La integración reintenta fallos de envío de forma limitada y cancela el trabajo que queda obsoleto. La entrega y respuesta de la luz deben comprobarse en el dispositivo.",
    recoveryDemo: "Demostración de recuperación", recoveryDemoHelp: "Simulación en pantalla. No envía órdenes a las luces.",
    loseLight: "Simular desconexión", restoreLight: "Simular reconexión", resetDemo: "Reiniciar demostración",
    recoveryState: { available: "Luz disponible · modo Cine de ejemplo", lost: "Luz desconectada · ahora corresponde el modo Lectura", restored: "Luz disponible · se aplica el modo Lectura vigente" },
    recoveryPending: "Pendiente del Bloque D", recoveryPendingHelp: "Parámetros de reintentos, tiempos de recuperación y verificación física.",
    diagHelp: "Las solicitudes ganadoras describen la intención del motor. Home Assistant puede aceptar una orden sin confirmar que la luz física la recibió.",
    enabledRules: "Reglas habilitadas", activeModes: "Modos activos", engineState: "Estado del coordinador", entryState: "Estado de la integración",
    activeRequests: "Solicitudes activas", idleRequests: "No hay solicitudes activas.", perLight: "Ganadoras por luz", noWinners: "Sin solicitudes ganadoras.",
    maskedFor: "Enmascarada en", winsFor: "Ganadora en", animations: "Animaciones activas", queued: "Órdenes pendientes", latestError: "Último error", noError: "Sin error registrado",
    activity: "Actividad reciente", emptyActivity: "Sin cambios registrados.", noData: "No disponible", noItems: "Ninguno", refreshDiagnostics: "Actualizar",
    downloadDiagnostics: "Descargar diagnóstico", diagnosticsFailed: "No se pudo consultar el diagnóstico.", downloadFailed: "No se pudo descargar el diagnóstico.",
    engineStates: { idle: "En espera", active: "Activo", error: "Con error", stopped: "Detenido" },
    issueKinds: { invalid_catalog: "Catálogo de modos inválido", invalid_storage: "Solicitudes guardadas inválidas", send_failed: "Falló el envío a Home Assistant", unsupported_command: "La luz no admite la orden", target_unavailable: "No se pudo enviar a la luz", recovery_failed: "Falló la recuperación" },
    nativeIntro: "Los ajustes nativos de Home Assistant son otra forma de configurar esta integración.",
    openNative: "Abrir ajustes en Home Assistant", nativePath: "Ajustes → Dispositivos y servicios → Integraciones → Smart LED Manager → Configurar.",
    backSettings: "Volver a configuración",
  },
  en: {
    general: "General", generalHint: "Integration preferences",
    priorities: "Priority and control", prioritiesMenu: "Priority", prioritiesHint: "Priority, manual control, and network protection",
    recovery: "Recovery", recoveryHint: "Device availability and recovery",
    diagnostics: "Diagnostics", diagnosticsHint: "Status and configuration summary",
    nativeSettings: "Native configuration", nativeSettingsHint: "Alternative access through Home Assistant",
    versionLabel: "Integration version", sidebar: "Show Smart LED Manager in the sidebar",
    openCenter: "Open the administration center", nativeCenter: "The center remains available from Native configuration → Administration center.",
    discardSettings: "Discard", engineDefaults: "Restore initial values",
    equalPriority: "When two lighting requests overlap", priorityHelp: "Higher priority wins. This setting only resolves ties.",
    tieLabel: "Which request wins at the same priority?",
    tieChoices: { newest: "Newest request", oldest: "Oldest request", lexical: "Identifier order" },
    tieExample: { newest: "If two requests have priority 60, the most recently activated one wins.", oldest: "If two requests have priority 60, the first one activated wins.", lexical: "Ties use the stable order of request identifiers." },
    manualGroup: "Manual control", manualLabel: "What happens when someone changes a light manually?",
    manualChoices: { service_only: "Only through an explicit manual action", respect: "Respect detected manual changes", temporary: "Respect detected changes for 15 minutes" },
    manualExplain: { service_only: "Direct light changes do not create a manual request. Use the explicit manual control action.", respect: "A detected change can create a persistent manual request.", temporary: "A detected change can create a manual request that expires after 15 minutes." },
    detectionLimit: "Detection relies on state changes and context reported by Home Assistant. Attribution can vary by device or integration.",
    network: "Network protection (advanced)", interval: "Minimum interval between commands per light (seconds)",
    intervalHelp: "Initial value 0.75 s. It affects effect frequency and response time.",
    invalid_command_interval: "Enter 0.10 to 10 seconds in increments of 0.05.",
    invalid_sidebar_preference: "Select whether the panel appears in the sidebar.",
    invalid_engine_preference: "Choose valid tie-break and manual control options.",
    recoveryTitle: "Automatic recovery", recoveryIntro: "If a light becomes unavailable, the engine keeps evaluating requests. When it returns, the engine applies the intent that is still current.",
    recoveryExisting: "Current behavior", recoveryDetail: "The integration retries failed sends a limited number of times and cancels obsolete work. Delivery and response must be checked on the device.",
    recoveryDemo: "Recovery demonstration", recoveryDemoHelp: "On-screen simulation. It sends no commands to lights.",
    loseLight: "Simulate disconnection", restoreLight: "Simulate reconnection", resetDemo: "Reset demonstration",
    recoveryState: { available: "Light available · example Cinema mode", lost: "Light disconnected · Reading mode is now scheduled", restored: "Light available · the current Reading mode is applied" },
    recoveryPending: "Planned for Block D", recoveryPendingHelp: "Retry settings, recovery timing, and physical verification.",
    diagHelp: "Winning requests are the engine's desired state. A command accepted by Home Assistant does not confirm delivery to the physical light.",
    enabledRules: "Enabled rules", activeModes: "Active modes", engineState: "Coordinator status", entryState: "Integration status",
    activeRequests: "Active requests", idleRequests: "There are no active requests.", perLight: "Winners by light", noWinners: "No winning requests.",
    maskedFor: "Masked on", winsFor: "Winning on", animations: "Active animations", queued: "Pending commands", latestError: "Latest error", noError: "No error recorded",
    activity: "Recent activity", emptyActivity: "No changes recorded.", noData: "Unavailable", noItems: "None", refreshDiagnostics: "Refresh",
    downloadDiagnostics: "Download diagnostics", diagnosticsFailed: "Could not read diagnostics.", downloadFailed: "Could not download diagnostics.",
    engineStates: { idle: "Idle", active: "Active", error: "Error", stopped: "Stopped" },
    issueKinds: { invalid_catalog: "Invalid mode catalog", invalid_storage: "Invalid stored requests", send_failed: "Send to Home Assistant failed", unsupported_command: "The light does not support the command", target_unavailable: "Could not send to the light", recovery_failed: "Recovery failed" },
    nativeIntro: "Home Assistant's native settings are another way to configure this integration.",
    openNative: "Open settings in Home Assistant", nativePath: "Settings → Devices & services → Integrations → Smart LED Manager → Configure.",
    backSettings: "Back to settings",
  },
};

export function validInterval(value) {
  return Number.isFinite(value) && value >= 0.1 && value <= 10 &&
    Math.abs(value * 20 - Math.round(value * 20)) < 1e-9;
}

export function settingsMenu(t) {
  return SETTINGS_VIEWS.map((view) => `<button class="slm-row slm-link" data-settings-view="${view}">
    <strong>${view === "priorities" ? t.prioritiesMenu : t[view]}</strong>
    <small>${t[view + "Hint"]}</small><span aria-hidden="true">›</span></button>`).join("");
}

function preferenceForm({ view, t, draft, status, version, ready, canSave, saving }) {
  if (!draft) return status ? "" : `<p>${t.noData}</p>`;
  const general = view === "general";
  const networkOpen = !validInterval(draft.min_command_interval);
  const lock = saving || !ready;
  const optionRows = (labels) => Object.entries(labels);
  const controls = general ? `<label class="slm-check"><input type="checkbox" data-admin-boolean="show_sidebar" ${draft.show_sidebar ? "checked" : ""}>${t.sidebar}</label>
    <p class="slm-settings-hint">${t.nativeCenter}</p><p>${t.versionLabel} · ${esc(version)}</p>
    <div><button data-home ${saving ? "disabled" : ""}>${t.openCenter}</button></div>` : `<section class="slm-settings-section">
      <h2>${t.equalPriority}</h2><p>${t.priorityHelp}</p>
      ${selectField(t.tieLabel, "tie_breaker", optionRows(t.tieChoices), draft.tie_breaker)}
      <p class="slm-settings-note">${t.tieExample[draft.tie_breaker] ?? t.noData}</p></section>
    <section class="slm-settings-section"><h2>${t.manualGroup}</h2>
      ${selectField(t.manualLabel, "manual_policy", optionRows(t.manualChoices), draft.manual_policy)}
      <p>${t.manualExplain[draft.manual_policy] ?? t.noData}</p><p class="slm-settings-hint">${t.detectionLimit}</p></section>
    <details class="slm-picker" data-admin-expanded="network" ${networkOpen ? "open" : ""}>
      <summary>${t.network}</summary>
      ${numberField(t.interval, "min_command_interval", draft.min_command_interval, 'min="0.1" max="10" step="0.05" required')}
      <p class="slm-settings-hint">${t.intervalHelp}</p>
      <p data-interval-error role="alert" ${networkOpen ? "" : "hidden"}>${t.invalid_command_interval}</p></details>`;
  return `<div class="slm-form slm-settings-form"><fieldset ${lock ? "disabled" : ""}>${controls}</fieldset>
    <div class="slm-actions">${general ? "" : `<button data-reset-preferences ${lock ? "disabled" : ""}>${t.engineDefaults}</button>`}
    <button data-discard ${saving ? "disabled" : ""}>${general ? t.discardSettings : t.cancel}</button>
    <button class="primary" data-save ${canSave ? "" : "disabled"}>${saving ? t.saving : t.save}</button></div></div>`;
}

function recoveryForm(t, stage) {
  const color = { available: "#6633ff", lost: "#455061", restored: "#ffcc80" }[stage];
  return `<div class="slm-form slm-settings-form"><h2>${t.recoveryTitle}</h2><p>${t.recoveryIntro}</p>
    <div class="slm-settings-note"><strong>${t.recoveryExisting}</strong><p>${t.recoveryDetail}</p></div>
    <h2>${t.recoveryDemo}</h2><p>${t.recoveryDemoHelp}</p>
    <div class="slm-preview slm-recovery-preview" role="status"><div class="slm-strip" style="--strip:${color};--intensity:${stage === "lost" ? ".22" : "1"}"></div>
    <span>${t.recoveryState[stage]}</span></div>
    <div class="slm-actions"><button data-recovery-step="lost" ${stage === "lost" ? "disabled" : ""}>${t.loseLight}</button>
    <button class="primary" data-recovery-step="restored" ${stage === "lost" ? "" : "disabled"}>${t.restoreLight}</button>
    <button data-recovery-step="available">${t.resetDemo}</button></div>
    <div class="slm-settings-note"><strong>${t.recoveryPending}</strong><p>${t.recoveryPendingHelp}</p></div></div>`;
}

function diagnosticsForm({ t, diagnostics, diagBusy, diagError, version, friendly }) {
  const runtime = diagnostics?.runtime;
  const options = diagnostics?.entry?.options;
  const requestsById = new Map(runtime?.requests?.map((request) => [request.request_id, request]));
  const requestName = (id) => requestsById.get(id)?.name || id;
  const rows = (entries) => `<dl class="slm-diagnostic-rows">${entries.map(([label, value]) =>
    `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join("")}</dl>`;
  const listLights = (values) => values?.map(friendly).join(", ") || (values ? t.noItems : t.noData);
  const activeModes = runtime?.mode_catalog?.modes?.filter((mode) =>
    Object.values(runtime.mode_catalog.selected).includes(mode.mode_id));
  const issue = runtime?.last_error;
  const error = !runtime ? t.noData : issue ? [t.issueKinds[issue.kind] ?? t.noData, issue.target && friendly(issue.target)].filter(Boolean).join(" · ") : t.noError;
  const requests = Object.entries(runtime?.request_decisions ?? {});
  const winners = Object.entries(runtime?.winners ?? {});
  const displayTime = (value) => value ? new Date(value).toLocaleString() : t.noData;
  const summary = [
    [t.lights, runtime?.managed_targets?.length],
    [t.zones, diagnostics ? options?.zones?.length ?? 0 : undefined],
    [t.enabledRules, diagnostics ? (options?.rules ?? []).filter((rule) => rule.type !== "notice" && rule.enabled !== false).length : undefined],
  ];
  return `<div class="slm-form slm-settings-form" aria-busy="${diagBusy}">
    <p class="slm-settings-note">${t.diagHelp}</p>
    ${diagError ? `<p class="message error" role="alert">${esc(diagError)}</p>` : ""}
    <div class="slm-diagnostic-summary">${summary.map(([label, count]) =>
      `<div><strong>${count ?? t.noData}</strong><span>${label}</span></div>`).join("")}</div>
    <h2>${t.activeModes}</h2><p>${esc(activeModes?.map((mode) => mode.name).join(", ") || (activeModes ? t.noItems : t.noData))}</p>
    <h2>${t.entryState}</h2>${rows([[t.versionLabel, runtime?.version ?? version], [t.engineState, t.engineStates[runtime?.status] ?? t.noData],
      [t.latestError, error], [t.animations, listLights(runtime?.animation_targets)], [t.queued, listLights(runtime?.pending_controller_targets)]])}
    <h2>${t.activeRequests}</h2>${requests.length ? `<ul class="slm-diagnostic-list">${requests.map(([id, decision]) => {
      const request = requestsById.get(id);
      return `<li><strong>${esc(requestName(id))} · ${t.priority} ${esc(request?.priority ?? t.noData)}</strong>
        <small>${t.winsFor} · ${esc(listLights(decision.winning_targets))}</small>
        <small>${t.maskedFor} · ${esc(listLights(decision.masked_targets))}</small></li>`;
    }).join("")}</ul>` : `<p>${runtime ? t.idleRequests : t.noData}</p>`}
    <h2>${t.perLight}</h2>${winners.length ? rows(winners.map(([light, id]) => [friendly(light), requestName(id)])) : `<p>${runtime ? t.noWinners : t.noData}</p>`}
    <details class="slm-picker" data-admin-expanded="diagnostic-activity"><summary>${t.activity}</summary>
      ${runtime?.history?.length ? `<ol class="slm-diagnostic-list">${[...runtime.history].reverse().map((entry) =>
        `<li><time datetime="${esc(entry.timestamp)}">${esc(displayTime(entry.timestamp))}</time><span>${esc(friendly(entry.target))} · ${esc(entry.current ? requestName(entry.current) : t.noWinners)}</span></li>`).join("")}</ol>` : `<p>${runtime ? t.emptyActivity : t.noData}</p>`}
    </details>
    ${runtime?.captured_at ? `<p role="status" class="slm-settings-hint">${esc(displayTime(runtime.captured_at))}</p>` : ""}
    <div class="slm-actions"><button data-refresh-diagnostics ${diagBusy ? "disabled" : ""}>${t.refreshDiagnostics}</button>
    <button class="primary" data-download-diagnostics ${diagBusy ? "disabled" : ""}>${t.downloadDiagnostics}</button></div></div>`;
}

export function renderSettings(details) {
  const { view, t } = details;
  if (PREFERENCE_VIEWS.includes(view)) return preferenceForm(details);
  if (view === "recovery") return recoveryForm(t, details.recoveryState);
  if (view === "diagnostics") return diagnosticsForm(details);
  return `<div class="slm-form slm-settings-form"><p>${t.nativeIntro}</p><p class="slm-settings-note">${t.nativePath}</p>
    <div class="slm-actions"><button data-back>${t.backSettings}</button>
    <a class="slm-native-action" href="/config/integrations/integration/smart_led_manager">${t.openNative}</a></div></div>`;
}

export const SETTINGS_STYLES = `
  .slm-settings-form h2{font-size:18px;margin:16px 0 8px}
  .slm-settings-form p{margin:8px 0;line-height:1.45}
  .slm-settings-section{border-block-start:1px solid var(--divider-color)}
  .slm-settings-note{border-inline-start:3px solid var(--primary-color);border-radius:6px;background:var(--secondary-background-color);padding:10px 12px;margin-block:12px}
  .slm-settings-hint{color:var(--secondary-text-color)}
  .slm-settings-form .slm-picker label{margin-top:12px}
  .slm-settings-form [role=alert]{color:var(--error-color,#b91c1c)}
  .slm-settings-form [data-reset-preferences]{margin-inline-end:auto}
  .slm-recovery-preview{grid-template-rows:1fr auto auto 1fr;gap:10px;color:#f2f5fb;text-align:center;padding:14px}
  .slm-recovery-preview .slm-strip{grid-row:2}.slm-recovery-preview span{grid-row:3}
  .slm-diagnostic-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:14px 0}
  .slm-diagnostic-summary div,.slm-diagnostic-list li,.slm-diagnostic-rows div{border:1px solid var(--divider-color);border-radius:9px;padding:10px;overflow-wrap:anywhere}
  .slm-diagnostic-summary strong,.slm-diagnostic-summary span,.slm-diagnostic-list :is(small,span){display:block}
  .slm-diagnostic-summary span,.slm-diagnostic-list small{color:var(--secondary-text-color)}
  .slm-diagnostic-rows,.slm-diagnostic-list{display:grid;gap:6px;padding:0;margin:8px 0}
  .slm-diagnostic-list li{list-style:none}
  .slm-diagnostic-rows div{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,3fr);gap:10px}
  .slm-diagnostic-rows dd{margin:0;text-align:end}
  .slm-native-action{border:1px solid var(--divider-color);border-radius:8px;display:inline-flex;align-items:center;padding:8px 12px;color:var(--primary-text-color);text-decoration:none;text-align:center}
  .slm-native-action:hover,.slm-native-action:focus-visible{outline:2px solid var(--primary-color)}
  @media(max-width:520px){.slm-settings-form [data-reset-preferences]{flex-basis:100%;margin:0}.slm-diagnostic-summary{grid-template-columns:repeat(2,minmax(0,1fr))}}
`;
