import { escapeHtml as esc } from "./rule-controls.mjs";

export const SMART_TEXT = {
  es: {
    smartRules: "Mis automatizaciones", smartQuestion: "¿Qué deseas automatizar?",
    smartDescription: "Administra las iluminaciones inteligentes configuradas.",
    temperature: "Temperatura", humidity: "Humedad", power: "Potencia instantánea",
    energy: "Energía acumulada", energyMenu: "Energía", security: "Seguridad", presence: "Presencia",
    powerHelp: "Usa la potencia que se está utilizando en este momento, por ejemplo en W o kW.",
    energyHelp: "Usa la energía acumulada, por ejemplo en Wh o kWh.",
    categories: ["Revisar las reglas configuradas", "Cambiar los colores según la temperatura",
      "Representar niveles de humedad", "Indicar potencia o consumo eléctrico",
      "Avisos de puertas y alarmas", "Iluminación según ocupación",
      "Avisos luminosos temporales", "Iluminación programada", "Combinar condiciones"],
    notifications: "Notificaciones", scheduleTemplate: "Horarios", advancedTemplate: "Regla avanzada",
    nativeNotify: "Abrir acciones de Home Assistant",
    notifyHelp: "Selecciona la acción Smart LED Manager: Notificar para enviar un aviso temporal.",
    scheduleHelp: "Puedes programar una regla con un sensor o dispositivo y limitarla a un horario.",
    createSchedule: "Crear una regla con horario",
    advancedOptions: "Opciones avanzadas", compatibleEditor: "Abrir editor avanzado",
    automationName: "Nombre de la automatización", sensor: "Sensor o dispositivo",
    actualUnit: "Unidad del sensor", noSources: "Home Assistant no tiene sensores compatibles con esta categoría.",
    noSelectedSource: "Selecciona un sensor o dispositivo",
    templateTitles: { temperature: "Iluminación por temperatura", humidity: "Iluminación por humedad",
      power: "Iluminación por potencia instantánea", energy: "Iluminación por energía acumulada",
      security: "Iluminación por seguridad", presence: "Iluminación por presencia" },
    templateTargets: "¿Dónde quieres aplicar la iluminación?",
    templateColor: "¿Cómo quieres que se ilumine?", afterRule: "Al finalizar",
    stateUnavailable: "No disponible", stateUnknown: "Desconocido",
    stateLabels: { on: "Detectado", off: "Sin detección", home: "En casa", not_home: "Fuera de casa",
      disarmed: "Desarmada", armed_home: "Armada en casa", armed_away: "Armada fuera", triggered: "Disparada",
      locked: "Cerrada con llave", unlocked: "Desbloqueada" },
    stateActive: "Activaría la iluminación", stateInactive: "Liberaría la iluminación al finalizar la espera",
    stateUnknownResult: "Sin datos válidos. La iluminación de la regla se libera.",
    stateSimulate: "Simular el estado", simulationHelp: "La simulación no controla luces reales.",
    activationState: "Estado de activación", activationDelay: "Permanencia antes de activar (s)",
    releaseDelay: "Espera antes de finalizar (s)", releaseHelp: "La espera se cancela si se cumple de nuevo la condición.",
    securityHelp: "La iluminación de seguridad es informativa. Usa un sistema de alarma certificado para la protección.",
    recalibrate: "El nuevo sensor usa otra unidad. ¿Quieres borrar los puntos y umbrales para calibrarlos de nuevo?",
    rule_unit_changed: "La unidad cambió. Vuelve a elegir el sensor y calibra los puntos y umbrales.",
    incompatible_template_source: "Selecciona un sensor compatible con la categoría.",
    invalid_template_state: "Selecciona un estado de activación válido.",
  },
  en: {
    smartRules: "My automations", smartQuestion: "What would you like to automate?",
    smartDescription: "Manage your smart lighting automations.",
    temperature: "Temperature", humidity: "Humidity", power: "Instantaneous power",
    energy: "Accumulated energy", energyMenu: "Energy", security: "Security", presence: "Presence",
    powerHelp: "Use the current power draw, such as W or kW.",
    energyHelp: "Use accumulated energy, such as Wh or kWh.",
    categories: ["Review configured rules", "Change colors based on temperature",
      "Represent humidity levels", "Display power or energy usage", "Alerts for doors and alarms",
      "Lighting based on occupancy", "Temporary light alerts", "Scheduled lighting", "Combine conditions"],
    notifications: "Notifications", scheduleTemplate: "Schedules", advancedTemplate: "Advanced rule",
    nativeNotify: "Open Home Assistant actions",
    notifyHelp: "Select the Smart LED Manager: Notify action to send a temporary alert.",
    scheduleHelp: "Create a rule with a sensor or device and restrict it to a schedule.",
    createSchedule: "Create a rule with a schedule",
    advancedOptions: "Advanced options", compatibleEditor: "Open advanced editor",
    automationName: "Automation name", sensor: "Sensor or device",
    actualUnit: "Sensor unit", noSources: "Home Assistant has no sensors compatible with this category.",
    noSelectedSource: "Choose a sensor or device",
    templateTitles: { temperature: "Lighting by temperature", humidity: "Lighting by humidity",
      power: "Lighting by power draw", energy: "Lighting by accumulated energy",
      security: "Security lighting", presence: "Presence lighting" },
    templateTargets: "Where should this lighting apply?",
    templateColor: "How should it light up?", afterRule: "When the rule ends",
    stateUnavailable: "Unavailable", stateUnknown: "Unknown",
    stateLabels: { on: "Detected", off: "Not detected", home: "Home", not_home: "Away",
      disarmed: "Disarmed", armed_home: "Armed home", armed_away: "Armed away", triggered: "Triggered",
      locked: "Locked", unlocked: "Unlocked" },
    stateActive: "Would activate the lighting", stateInactive: "Would release lighting after the delay",
    stateUnknownResult: "No valid data. The rule releases its lighting.",
    stateSimulate: "Simulate state", simulationHelp: "The simulation does not control physical lights.",
    activationState: "Activation state", activationDelay: "Hold before activating (s)",
    releaseDelay: "Wait before ending (s)", releaseHelp: "The delay is cancelled if the condition becomes true again.",
    securityHelp: "Security lighting is advisory. Use a certified alarm system for protection.",
    recalibrate: "The new sensor uses a different unit. Clear the points and thresholds to recalibrate?",
    rule_unit_changed: "The unit changed. Select the sensor again and recalibrate the points and thresholds.",
    incompatible_template_source: "Select a compatible sensor for this category.",
    invalid_template_state: "Select a valid activation state.",
  },
};

export const NUMERIC_CATEGORIES = ["temperature", "humidity", "power", "energy"];
const CATEGORIES = ["smartRules", "temperature", "humidity", "energyMenu", "security", "presence", "notifications", "scheduleTemplate", "advancedTemplate"];

export function smartFrame(title, back, body) {
  return `<main class="slm-admin"><section class="slm-shell"><div class="slm-bar">${back}</div>
    <h1>${esc(title)}</h1>${body}</section></main>`;
}

export function renderSmartMenu(t, view) {
  const home = `<button data-home>← ${t.home}</button>`;
  const back = `<button data-smart-menu>← ${t.smart}</button>`;
  const row = (key, label, hint) => `<button class="slm-row slm-link" data-smart-category="${key}">
    <strong>${label}</strong><small>${hint}</small><span aria-hidden="true">›</span></button>`;
  if (view === "energyMenu") {
    return smartFrame(t.energyMenu, back, row("power", t.power, t.powerHelp) + row("energy", t.energy, t.energyHelp));
  }
  return smartFrame(t.smart, home, `<p>${t.smartQuestion}</p>` +
    CATEGORIES.map((key, index) => row(key, t[key], t.categories[index])).join(""));
}

export const SMART_STYLES = `
 .template-editor{max-width:960px}.template-editor .card{margin:12px 0}
 .template-editor .actions{position:static;background:none;padding-bottom:0}
 .template-editor details summary{font-weight:650;cursor:pointer;padding-block:10px}
 .template-editor details[open]>summary{margin-bottom:7px}
 .template-editor summary:focus-visible,.template-editor input:focus-visible,.template-editor select:focus-visible{outline:3px solid var(--primary-color);outline-offset:2px}
 .template-strip{min-height:105px;border-radius:12px;background:#181820;display:grid;place-items:center;margin-top:12px}
 .template-strip[hidden]{display:none}
 .template-strip span{height:8px;border-radius:6px;width:84%;background:var(--strip);opacity:var(--intensity);box-shadow:0 0 20px var(--strip)}
 .template-strip .preview-pulse{animation:slm-fade var(--period) ease-in-out infinite}
 .template-strip .preview-blink{animation:slm-fade var(--period) steps(1,end) infinite}
 .template-strip span{--intensity:var(--preview-intensity,0)}
 .template-editor .template-source{padding:0 12px;border:1px solid var(--divider-color);border-radius:9px}
 .template-editor .template-source .picker{padding-bottom:12px}
 .template-editor input[type=range]{accent-color:var(--primary-color)}
 .template-editor input[type=color]{min-height:36px;padding:4px}
 @media(prefers-reduced-motion:reduce){.template-strip span{animation:none!important}}
`;
