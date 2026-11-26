import { escapeHtml as esc, inputField, numberField, scheduleControls, selectField } from "./rule-controls.mjs";
import { rgbToHex } from "./visual-editor-model.mjs";

export const PLAN_TEXT = {
  es: {
    notice: "Aviso luminoso", noticeCatalog: "Notificaciones y avisos luminosos",
    noticeName: "Nombre del aviso", newNotice: "Crear aviso", physicalRun: "Probar en las luces",
    confirmPhysicalRun: "Esta prueba usará las luces reales autorizadas del aviso guardado. ¿Ejecutarla?",
    noticeRequested: "Aviso solicitado al motor.", notice_not_found: "El aviso guardado ya no existe.",
    notice_disabled: "Habilita el aviso antes de ejecutarlo.",
    notice_invalid: "Revisa la configuración y los destinos autorizados del aviso.",
    notice_entry_not_ready: "Espera a que la integración termine de aplicar la configuración.",
    noticeHelp: "Guarda avisos temporales y selecciónalos por nombre en la acción Ejecutar aviso guardado de Home Assistant.",
    previewNotice: "Simular aviso en pantalla", stopNotice: "Detener simulación",
    noticeDuration: "Duración del aviso (s)", noticePeriod: "Periodo del efecto (s)",
    continuous: "Regla continua", scheduleTitle: "Iluminación por horarios",
    matchAll: "Todas las condiciones", matchAny: "Cualquiera de las condiciones",
    when: "¿Cuándo debe activarse?", previewActivation: "Simular las condiciones",
    activationTime: "Fecha y hora local de prueba", useLive: "Usar el estado actual",
    plan_true: "Solicitaría la iluminación.", plan_false: "La regla no solicitaría iluminación.",
    plan_unknown: "Faltan datos válidos para activar la regla.",
    invalid_schedule: "Selecciona días y horas de inicio y fin diferentes.",
    invalid_conditions: "Completa las condiciones, sus entidades y valores.",
    empty_activation: "Agrega al menos una condición o un horario.",
    planCompatibleEditor: "Abrir editor compatible",
  },
  en: {
    notice: "Light notice", noticeCatalog: "Notifications and light notices",
    noticeName: "Notice name", newNotice: "Create notice", physicalRun: "Test on real lights",
    confirmPhysicalRun: "This test uses the saved notice and sends commands to real authorized lights. Run it?",
    noticeRequested: "Notice submitted to the engine.", notice_not_found: "The saved notice no longer exists.",
    notice_disabled: "Enable the notice before running it.",
    notice_invalid: "Check the saved notice and its authorized targets.",
    notice_entry_not_ready: "Wait for the integration to finish applying its settings.",
    noticeHelp: "Save temporary notices and choose one by name in Home Assistant's Run saved notice action.",
    previewNotice: "Simulate notice on screen", stopNotice: "Stop simulation",
    noticeDuration: "Notice duration (s)", noticePeriod: "Effect period (s)",
    continuous: "Continuous rule", scheduleTitle: "Scheduled lighting",
    matchAll: "All conditions", matchAny: "Any condition",
    when: "When should it activate?", previewActivation: "Simulate conditions",
    activationTime: "Test date and local time", useLive: "Use the current state",
    plan_true: "Would request lighting.", plan_false: "The rule would not request lighting.",
    plan_unknown: "Valid data is required before the rule can activate.",
    invalid_schedule: "Select weekdays and different start and end times.",
    invalid_conditions: "Complete the conditions, entities, and values.",
    empty_activation: "Add at least one condition or a schedule.",
    planCompatibleEditor: "Open compatible editor",
  },
};

export function planTitle(rule, t) {
  if (rule.type === "notice") return t.notice;
  if (rule.type !== "continuous") return null;
  return rule.conditions ? t.advancedTemplate : t.scheduleTitle;
}

export function simpleConditions(rule) {
  return ["and", "or"].includes(rule.conditions?.type) &&
    rule.conditions.conditions.every((child) => ["state", "numeric"].includes(child.type));
}

export function renderPlan(model) {
  const { rule: r, t, conditions, targets, preview, busy, status, error, canSave, canRun, simulating } = model;
  const isNotice = r.type === "notice";
  const advanced = !isNotice && Boolean(r.conditions);
  const percent = Math.max(1, Math.round(r.brightness * 100 / 255));
  return `<main class="template-editor plan-editor">
    <div class="toolbar"><button data-back>← ${t.back}</button>
    ${status && !busy ? `<button data-reload>${t.checkStatus}</button>` : ""}</div>
    <h1>${isNotice ? t.noticeCatalog : planTitle(r, t)}</h1>
    ${status ? `<p role="status" class="message">${esc(status)}</p>` : ""}
    ${error ? `<p role="alert" class="message error">${esc(error)}</p>` : ""}
    <fieldset class="editor-fields" ${busy ? "disabled" : ""}>
      <section class="card">${isNotice ? `<p class="muted">${t.noticeHelp}</p>` : ""}
        ${inputField(isNotice ? t.noticeName : t.automationName, "name", r.name)}</section>
      ${advanced ? `<section class="card"><h3>${t.when}</h3>${conditions}
        <label class="check"><input type="checkbox" data-schedule-enabled ${r.schedule ? "checked" : ""}>${t.scheduled}</label></section>` : ""}
      ${r.schedule ? `<section class="card"><h3>${t.scheduleTemplate}</h3>${scheduleControls("schedule", r.schedule, t)}
        ${r.schedule.after === r.schedule.before ? `<p role="alert">${t.invalid_schedule}</p>` : ""}</section>` : ""}
      <section class="card"><h3>${t.templateTargets}</h3>${targets}</section>
      <section class="card"><h3>${t.templateColor}</h3>
        <label>${t.color}<input type="color" data-color value="${rgbToHex(r.rgb_color)}"></label>
        <label><span>${t.brightness} <span data-template-brightness-label>${percent}%</span></span>
          <input type="range" min="1" max="100" data-template-brightness value="${percent}"></label>
        ${selectField(t.effect, "animation", ["fixed","pulse","blink"].map(key => [key,t[key]]), r.animation)}
        ${isNotice ? numberField(t.noticeDuration, "duration", r.duration, 'min="0.1" max="86400"') : ""}
        ${r.animation !== "fixed" ? numberField(t.noticePeriod, "period", r.period, isNotice ? 'min="0.5" max="60"' : 'min="0.1" max="3600"') : ""}
      </section>
      <section class="card"><h3>${isNotice ? t.previewNotice : t.previewActivation}</h3>
        <p class="muted">${t.simulationHelp}</p>${preview}
        ${isNotice ? `<div class="row"><button data-simulate-notice>${simulating ? t.stopNotice : t.previewNotice}</button>
          ${canRun ? `<button data-run-notice="${esc(r.id)}">${t.physicalRun}</button>` : ""}</div>` : `<button data-simulate-plan>${t.previewActivation}</button>`}
      </section>
      <label class="check"><input type="checkbox" data-boolean="enabled" ${r.enabled ? "checked" : ""}>${t.enabled}</label>
      <details class="card" data-admin-expanded="plan-advanced"><summary>${t.advancedOptions}</summary>
        <div class="form-grid">${numberField(t.priority, "priority", r.priority, 'min="0" max="100" step="1"')}
          ${numberField(t.transition, "transition", r.transition, 'min="0" max="300" step="any"')}
          ${!isNotice ? numberField(t.activationDelay, "for_seconds", r.for_seconds, 'min="0" max="604800" step="any"') : ""}
        </div>${model.advancedTargets}
          ${!isNotice ? `<button data-plan-advanced>${t.planCompatibleEditor}</button>` : ""}
      </details>
    </fieldset>
    <div class="actions"><button data-discard>${t.cancel}</button>
      <button class="primary" data-save ${canSave ? "" : "disabled"}>${busy ? t.saving : t.save}</button></div>
    </main>`;
}
