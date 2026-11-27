import { escapeHtml as esc, inputField, selectField } from "./rule-controls.mjs";
import { renderSettings, settingsMenu, SETTINGS_VIEWS } from "./settings-views.mjs";
import { rgbToHex } from "./visual-editor-model.mjs";

export const ADMIN_TEXT = {
  es: {
    back: "Volver",
    lights: "Luces administradas", lightsHint: "Seleccionar controladores",
    zones: "Zonas", zonesHint: "Organizar habitaciones",
    modes: "Modos de iluminación", modesHint: "Ambientes, escenas y efectos",
    smart: "Iluminación inteligente", smartHint: "Sensores y automatizaciones",
    settings: "Configuración", settingsHint: "Ajustes y diagnóstico",
    lightsHelp: "Elige las luces que Smart LED Manager puede controlar.",
    lightsLimit: "Sólo las luces seleccionadas estarán autorizadas.",
    zonesHelp: "Organiza las luces por habitación.",
    modesHelp: "Crea ambientes para cada habitación y actívalos cuando quieras.",
    modesExclusive: "Cada zona admite un modo activo a la vez. Activar otro lo reemplaza.",
    searchLight: "Buscar luz…",
    zoneLights: "Luces de la zona", modeLights: "Luces del modo",
    lightChoices: "Luces disponibles", selectedLights: "seleccionadas",
    invalidLights: "Selecciona al menos una luz.",
    noMatches: "No hay luces que coincidan.",
    newZone: "Crear zona", editZone: "Editar zona", zoneName: "Nombre de la zona",
    area: "Área de Home Assistant", noArea: "Sin asignar",
    deleteZone: "Eliminar zona", confirmZone: "¿Eliminar esta zona?",
    newMode: "Crear modo", createMode: "Crear modo de iluminación",
    editMode: "Editar modo de iluminación", modeName: "Nombre del modo",
    zone: "Zona", modeHelp: "Configura el ambiente que deseas activar.",
    zoneFirst: "Crea una zona para poder añadir un modo.",
    noZones: "Todavía no hay zonas.", noModes: "Aún no hay modos en esta zona.",
    modeZoneHint: "Las luces del modo deben pertenecer a esta zona.",
    active: "Activo", noActiveMode: "Ningún modo activo", activate: "Activar",
    deactivate: "Desactivar", winner: "Efectivo", masked: "Enmascarado",
    partial: "Parcial", unavailableMode: "Sin luces disponibles", partialAvailability: "Algunas luces no están disponibles",
    lighting: "Iluminación", effect: "Efecto", simulateEffect: "Simular efecto",
    stopPreview: "Detener simulación", previewHint: "Simulación en pantalla. No controla luces reales.",
    colorUnset: "Conservar color de la luz", brightnessUnset: "Conservar brillo de la luz",
    external: "Control externo", voiceSwitch: "Crear interruptor para Alexa y otros controles",
    voiceHelp: "Si quieres usar voz, comparte el interruptor desde Matter Hub u otro puente compatible.",
    modeAdvanced: "Opciones avanzadas", turnOn: "Permitir encender luces",
    deleteMode: "Eliminar modo", confirmMode: "¿Eliminar este modo?",
    modeError: {
      rules_use_removed_lights: "Modifica primero las reglas que dependen de las luces retiradas.",
      zones_use_removed_lights: "Modifica primero las zonas que contienen las luces retiradas.",
      zone_has_modes: "Elimina o mueve primero los modos de esta zona.",
      zone_has_rules: "Modifica primero las reglas que usan esta zona, incluidas las deshabilitadas.",
      light_not_available: "Una luz seleccionada ya no está disponible. Comprueba el estado y vuelve a seleccionarla.",
      group_not_authorized: "Selecciona luces individuales. Los grupos no se pueden autorizar directamente.",
      duplicate_zone: "Ya existe una zona con ese nombre.",
      duplicate_mode_name: "Ya existe un modo con ese nombre en la zona.",
      mode_target_outside_zone: "Todas las luces de un modo deben permanecer en su zona.",
      target_in_multiple_zones: "Una de las luces ya pertenece a otra zona.",
      target_not_managed: "Selecciona únicamente luces administradas.",
      deactivate_before_move: "Desactiva este modo antes de moverlo a otra zona.",
      area_not_found: "El área seleccionada ya no existe.",
      invalid_mode: "Revisa el brillo, la prioridad, la transición y el efecto del modo.",
      invalid_zone: "Introduce un nombre de zona válido.",
      reserved_mode_name: "Elige un nombre distinto de «Sin modo».",
      zone_without_targets: "Selecciona al menos una luz para la zona.",
      mode_without_targets: "Selecciona al menos una luz para el modo.",
      zone_not_found: "La zona ya no está en el catálogo.",
      mode_not_found: "El modo ya no está en el catálogo.",
    },
  },
  en: {
    back: "Back",
    lights: "Managed lights", lightsHint: "Select controllers",
    zones: "Zones", zonesHint: "Organize rooms",
    modes: "Lighting modes", modesHint: "Ambiences, scenes, and effects",
    smart: "Smart lighting", smartHint: "Sensors and automations",
    settings: "Settings", settingsHint: "Settings and diagnostics",
    lightsHelp: "Choose the lights Smart LED Manager can control.",
    lightsLimit: "Only the lights you select will be authorized.",
    zonesHelp: "Organize your lights by room or space.",
    modesHelp: "Create ambiences for each zone and activate them whenever you like.",
    modesExclusive: "Each zone supports one active mode at a time. Activating another replaces it.",
    searchLight: "Search lights…",
    zoneLights: "Zone lights", modeLights: "Mode lights",
    lightChoices: "Available lights", selectedLights: "selected",
    invalidLights: "Select at least one light.",
    noMatches: "No matching lights.",
    newZone: "Create zone", editZone: "Edit zone", zoneName: "Zone name",
    area: "Home Assistant area", noArea: "Unassigned",
    deleteZone: "Delete zone", confirmZone: "Delete this zone?",
    newMode: "Create mode", createMode: "Create lighting mode",
    editMode: "Edit lighting mode", modeName: "Mode name",
    zone: "Zone", modeHelp: "Configure the ambience you want to activate.",
    zoneFirst: "Create a zone before adding a mode.",
    noZones: "There are no zones yet.", noModes: "There are no modes in this zone yet.",
    active: "Active", noActiveMode: "No active mode", activate: "Activate",
    modeZoneHint: "The mode's lights must belong to this zone.",
    deactivate: "Deactivate", winner: "Effective", masked: "Masked",
    partial: "Partial", unavailableMode: "No lights available", partialAvailability: "Some lights are unavailable",
    lighting: "Lighting", effect: "Effect", simulateEffect: "Simulate effect",
    stopPreview: "Stop simulation", previewHint: "On-screen simulation. It does not control real lights.",
    colorUnset: "Keep the light's color", brightnessUnset: "Keep the light's brightness",
    external: "External control", voiceSwitch: "Create a switch for Alexa and other controls",
    voiceHelp: "For voice control, expose the switch through Matter Hub or another compatible bridge.",
    modeAdvanced: "Advanced options", turnOn: "Allow lights to turn on",
    deleteMode: "Delete mode", confirmMode: "Delete this mode?",
    modeError: {
      rules_use_removed_lights: "First update the rules that depend on the removed lights.",
      zones_use_removed_lights: "First update the zones that contain the removed lights.",
      zone_has_modes: "Delete or move this zone's modes first.",
      zone_has_rules: "Update the rules that use this zone first, including disabled rules.",
      light_not_available: "A selected light is no longer available. Check the status and select it again.",
      group_not_authorized: "Select individual lights. Groups cannot be authorized directly.",
      duplicate_zone: "A zone already uses that name.",
      duplicate_mode_name: "This zone already has a mode with that name.",
      mode_target_outside_zone: "All lights in a mode must remain in its zone.",
      target_in_multiple_zones: "One of these lights already belongs to another zone.",
      target_not_managed: "Select only managed lights.",
      deactivate_before_move: "Deactivate this mode before moving it to a different zone.",
      area_not_found: "The selected area no longer exists.",
      invalid_mode: "Check the mode brightness, priority, transition, and effect.",
      invalid_zone: "Enter a valid zone name.",
      reserved_mode_name: "Choose a name other than No mode.",
      zone_without_targets: "Select at least one light for this zone.",
      mode_without_targets: "Select at least one light for this mode.",
      zone_not_found: "The zone is no longer in the catalog.",
      mode_not_found: "The mode is no longer in the catalog.",
    },
  },
};

const SECTIONS = ["lights", "zones", "modes", "smart", "settings"];
const ICONS = {
  lights: '<path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12v2h8v-2a7 7 0 0 0-4-12Z"/>',
  zones: '<path d="m3 10 4-5h10l4 5H3Zm1 4h16M6 18h12"/>',
  modes: '<path d="M12 3a9 9 0 1 0 0 18h1a2 2 0 0 0 0-4h-1a1 1 0 1 1 0-2h3a6 6 0 0 0-3-12Z"/><circle cx="7" cy="12" r=".8"/><circle cx="9" cy="7.5" r=".8"/><circle cx="14" cy="7" r=".8"/>',
  smart: '<rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/><path d="m6 15 2 2-2 2M9 17h2m5-12-2 2 2 2m-4-2h2"/>',
  settings: '<path d="m9 3 1 2h4l1-2 3 2v2l2 2h2v4l-2 1-2 2v2l-3 2-1-2h-4l-1 2-3-2v-2l-2-2H2v-4h2l2-2V5l3-2Z"/><circle cx="12" cy="12" r="3"/>',
};

const PALETTE = ["#6633ff", "#0000ff", "#00ffff", "#00cc66", "#ffcc80", "#ff8800", "#ff0000", "#ffffff"];

function frame(title, content, t, status, back = "", home = false) {
  return `<main class="slm-admin${home ? " slm-home" : ""}"><section class="slm-shell">
    ${back ? `<div class="slm-bar">${back}</div>` : ""}
    <h1>${esc(title)}</h1>${status}${content}
  </section></main>`;
}

const homeButton = (t) => `<button data-home>← ${t.home}</button>`;
const checkBox = (field, label, checked) =>
  `<label class="slm-check"><input type="checkbox" data-admin-boolean="${field}" ${checked ? "checked" : ""}> ${label}</label>`;

export function renderAdminHome(t, version, status) {
  const cards = SECTIONS.map((section) => `<button class="slm-tile slm-tile-${section}" ${section === "smart" ? "data-rules" : `data-admin-view="${section}"`}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">${ICONS[section]}</svg>
      <strong>${t[section]}</strong><span>${t[section + "Hint"]}</span>
    </button>`).join("");
  return frame("Smart LED Manager",
    `<p class="slm-sub">${t.admin}</p><div class="slm-grid">${cards}</div><p class="slm-version">${esc(version)}</p>`,
    t, status, "", true);
}

function targetPicker(t, title, lights, selected) {
  const names = new Map(lights.map((item) => [item.entity_id, item.name]));
  const ids = [...new Set([...lights.map((item) => item.entity_id), ...selected])];
  return `<div class="slm-form-row">${title ? `<strong>${title}</strong>` : ""}
    <details class="slm-picker" data-admin-expanded="lights" open>
      <summary>${t.lightChoices} · ${selected.length} ${t.selectedLights}</summary>
      <input class="slm-search" type="search" aria-label="${t.searchLight}" placeholder="${t.searchLight}" data-admin-search>
      <div class="slm-choices">${ids.map((id) => `<label class="slm-check" data-choice-label="true">
        <input type="checkbox" data-admin-target="${esc(id)}" ${selected.includes(id) ? "checked" : ""}>
        <span>${esc(names.get(id) ?? id)}</span>
      </label>`).join("")}<p data-admin-empty class="muted" hidden>${t.noMatches}</p></div>
    </details></div>`;
}

function formActions(t, canSave, saving, deleting = "", cancel = t.cancel) {
  return `<div class="slm-actions">${deleting}<button data-discard>${cancel}</button>
    <button data-save class="primary" ${canSave ? "" : "disabled"}>${saving ? t.saving : t.save}</button></div>`;
}

function adminEditor({ kind, draft, data, t, status, ready, canSave, saving, effect }) {
  const back = `<button data-back>← ${kind === "lights" ? t.home : t.back}</button>`;
  const lock = saving ? "disabled" : "";
  const managed = data.lights.filter((light) => data.managed.includes(light.entity_id));
  if (kind === "lights") {
    return frame(t.lights, `<p>${t.lightsHelp}</p><div class="slm-form">
        <fieldset ${lock}>${targetPicker(t, "", data.lights, draft.targets)}
        <p class="muted">${t.lightsLimit}</p></fieldset>
        ${formActions(t, canSave, saving, "", t.back)}</div>`, t, status, back);
  }
  if (kind === "zone") {
    const areas = data.areas.map((area) => [area.id, area.name]);
    if (draft.area_id && !areas.some(([id]) => id === draft.area_id)) areas.push([draft.area_id, draft.area_id]);
    return frame(draft.zone_id ? t.editZone : t.newZone,
      `<div class="slm-form"><fieldset ${lock}>
        ${inputField(t.zoneName, "name", draft.name)}
        ${selectField(t.area, "area_id", [["", t.noArea], ...areas], draft.area_id ?? "")}
        ${targetPicker(t, t.zoneLights, managed, draft.targets)}
      </fieldset>${formActions(t, canSave, saving,
        draft.zone_id ? `<button data-admin-delete="${esc(draft.zone_id)}" class="danger" ${ready ? "" : "disabled"}>${t.deleteZone}</button>` : "")}</div>`, t, status, back);
  }
  const color = draft.rgb_color ? rgbToHex(draft.rgb_color) : "#ffffff";
  const animation = draft.animation ?? "fixed";
  const brightness = draft.brightness ?? 255;
  const percent = Math.max(1, Math.round(brightness * 100 / 255));
  const seconds = Math.min(60, Math.max(0.5, Number(draft.period) || 1));
  const zone = data.zones.find((item) => item.zone_id === draft.zone_id);
  const zones = data.zones.map((item) => [item.zone_id, item.name]);
  const palette = PALETTE.map((hex) => `<button data-admin-color="${hex}" class="slm-color"
    aria-label="${hex}" aria-pressed="${hex.toLowerCase() === color.toLowerCase()}"
    style="--swatch:${hex}"></button>`).join("");
  return frame(draft.mode_id ? t.editMode : t.createMode, `<p>${t.modeHelp}</p>
    <div class="slm-form slm-mode-editor"><fieldset ${lock}>
      ${inputField(t.modeName, "name", draft.name)}
      ${selectField(t.zone, "zone_id", zones, draft.zone_id)}<small class="muted">${t.modeZoneHint}</small>
      <section class="slm-mode-section"><h2>${t.lighting}</h2>
        <div><strong>${t.color}</strong><div class="slm-palette">${palette}</div>
          <input aria-label="${t.color}" type="color" data-admin-color-input value="${color}">
          ${draft.rgb_color === null ? `<small class="muted">${t.colorUnset}</small>` : ""}</div>
        <label><span>${t.brightness} <span data-admin-brightness>${draft.brightness === null ? t.brightnessUnset : percent + "%"}</span></span>
          <input type="range" min="1" max="100" value="${percent}" data-admin-brightness-input></label>
        ${selectField(t.effect, "animation", ["fixed", "pulse", "blink"].map((id) => [id, t[id]]), animation)}
        <div class="slm-preview"><div class="slm-strip ${effect ? "slm-" + animation : ""}"
          style="--strip:${color};--intensity:${percent / 100};--period:${seconds}s"></div></div>
        <div class="slm-preview-meta"><span data-admin-effect-meta>${t[animation]} · ${percent}%</span>
          ${animation !== "fixed" ? `<button type="button" data-preview-effect>${effect ? t.stopPreview : t.simulateEffect}</button>` : ""}</div>
        <small class="muted">${t.previewHint}</small>
      </section>
      <section class="slm-mode-section"><h2>${t.external}</h2>
        ${checkBox("expose_switch", t.voiceSwitch, draft.expose_switch)}
        <small class="muted">${t.voiceHelp}</small>
      </section>
      <details class="slm-mode-section" data-admin-expanded="advanced"><summary>${t.modeAdvanced}</summary>
        ${inputField(t.priority, "priority", draft.priority, "number", 'min="0" max="100" step="1"')}
        ${inputField(t.transition, "transition", draft.transition, "number", 'min="0" max="300" step="any"')}
        ${animation !== "fixed" ? inputField(t.period, "period", draft.period, "number", 'min="0.5" max="60" step="any"') : ""}
        ${checkBox("allow_turn_on", t.turnOn, draft.allow_turn_on)}
        ${checkBox("keep_color", t.colorUnset, draft.rgb_color === null)}
        ${checkBox("keep_brightness", t.brightnessUnset, draft.brightness === null)}
        ${targetPicker(t, t.modeLights, managed.filter((light) => zone?.targets.includes(light.entity_id)), draft.targets)}
      </details>
    </fieldset>${formActions(t, canSave, saving,
      draft.mode_id ? `<button data-admin-delete="${esc(draft.mode_id)}" class="danger" ${ready ? "" : "disabled"}>${t.deleteMode}</button>` : "")}</div>`, t, status, back);
}

function modeGroups(data, t, ready) {
  const available = new Set(data.available);
  return data.zones.map((zone) => {
    const modes = data.modes.filter((mode) => mode.zone_id === zone.zone_id);
    const status = data.status[zone.zone_id];
    const selected = modes.find((mode) => mode.mode_id === status?.selected_mode_id);
    return `<section class="slm-zone-group"><h2>${esc(zone.name)}</h2>
      ${modes.length ? `<p class="muted">${selected ? t.active + " · " + esc(selected.name) : t.noActiveMode}</p>` :
        `<p class="slm-row muted">${t.noModes}</p>`}
      ${modes.map((mode) => {
        const on = selected === mode;
        const online = mode.targets.filter((id) => available.has(id)).length;
        const state = online ? t[status?.state] : t.unavailableMode;
        return `<article class="slm-row slm-mode-row ${on ? "slm-active" : ""}">
          <span class="slm-mode-swatch" style="--swatch:${mode.rgb_color ? rgbToHex(mode.rgb_color) : "var(--divider-color)"}" aria-hidden="true"></span>
          <div><strong>${esc(mode.name)}</strong>${on ? `<span class="slm-active-label">${t.active}</span>` : ""}
          <small class="muted">${mode.brightness === null ? t.brightnessUnset : `${t.brightness} ${Math.max(1, Math.round(mode.brightness * 100 / 255))}%`} · ${esc(t[mode.animation ?? "fixed"])}${mode.expose_switch ? " · " + t.external : ""}
            ${on ? ` · ${esc(state)}${online > 0 && online < mode.targets.length ? " · " + t.partialAvailability : ""}` : ""}</small></div>
          <div class="slm-row-actions"><button class="${on ? "" : "primary"}" data-mode-active="${esc(mode.mode_id)}"
            data-on="${on}" ${ready ? "" : "disabled"}>${on ? t.deactivate : t.activate}</button>
          <button data-admin-edit="${esc(mode.mode_id)}" ${ready ? "" : "disabled"}>${t.edit}</button></div>
        </article>`;
      }).join("")}</section>`;
  }).join("");
}

export function renderAdministration(model) {
  const { view, t, data, draft, status, ready } = model;
  if (view === "settings") return frame(t.settings, settingsMenu(t), t, status, homeButton(t));
  if (SETTINGS_VIEWS.includes(view)) return frame(t[view], renderSettings(model), t, status, `<button data-back>← ${t.back}</button>`);
  if (draft && data) return adminEditor(model);
  if (!data || view === "lights") return frame(t[view], "", t, status, homeButton(t));
  if (view === "zones") {
    const names = new Map(data.lights.map((light) => [light.entity_id, light.name]));
    const rows = data.zones.map((zone) => `<button class="slm-row slm-link" data-admin-edit="${esc(zone.zone_id)}" ${ready ? "" : "disabled"}>
      <strong>${esc(zone.name)}</strong><small>${esc(zone.targets.map((id) => names.get(id) ?? id).join(", "))}</small>
      <span aria-hidden="true">›</span></button>`).join("");
    return frame(t.zones, `<p>${t.zonesHelp}</p>${rows || `<p class="muted">${t.noZones}</p>`}
      <button class="primary slm-create" data-admin-create ${ready ? "" : "disabled"}>+ ${t.newZone}</button>`, t, status, homeButton(t));
  }
  const content = data.zones.length ? modeGroups(data, t, ready) :
    `<p class="muted">${t.zoneFirst}</p><button data-admin-view="zones">${t.zones}</button>`;
  return frame(t.modes, `<div class="slm-list-top"><p>${t.modesHelp}</p>
      ${data.zones.length ? `<button class="primary" data-admin-create ${ready ? "" : "disabled"}>+ ${t.newMode}</button>` : ""}
      </div>${content}${data.zones.length ? `<p class="muted">${t.modesExclusive}</p>` : ""}`, t, status, homeButton(t));
}

export const ADMIN_STYLES = `
  main.slm-admin{max-width:1600px;padding:34px}
  .slm-shell{border:2px solid var(--divider-color,#ddd);border-radius:32px;padding:24px}
  .slm-shell h1{font-size:38px;font-weight:650;line-height:1.25;margin:5px 0 26px}
  .slm-sub{font-size:26px;color:var(--secondary-text-color);margin:0 0 24px}
  .slm-bar{margin-bottom:24px}.slm-bar button{border-radius:9px}
  .slm-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .slm-tile{background:var(--secondary-background-color,var(--card-background-color));border:2px solid var(--divider-color);border-radius:24px;min-height:220px;padding:24px;display:flex;flex-direction:column;align-items:flex-start;text-align:left;gap:22px}
  .slm-tile:hover,.slm-link:hover{border-color:var(--primary-color)}
  .slm-tile svg{width:44px;height:44px}.slm-tile strong{font-size:30px;font-weight:650;line-height:1.25}.slm-tile span{font-size:26px}
  .slm-tile span,.slm-version{color:var(--secondary-text-color)}
  .slm-tile-settings{grid-column:1/-1;min-height:150px}.slm-tile-settings svg{color:#84909d}
  .slm-tile-lights svg{color:#d5a13b}.slm-tile-zones svg{color:#438aca}
  .slm-tile-modes svg{color:#8b5cce}.slm-tile-smart svg{color:#299b65}
  .slm-version{margin:14px 0 0;font-size:12px}
  .slm-form{border:1px solid var(--divider-color);border-radius:16px;background:var(--card-background-color);padding:22px;max-width:100%}
  .slm-mode-editor{max-width:900px}.slm-mode-editor .slm-actions .danger{margin-inline-end:auto}
  .slm-form fieldset{display:grid;gap:17px;border:0;min-width:0;margin:0;padding:0}
  .slm-form label,.slm-form-row{display:flex;flex-direction:column;gap:7px}
  .slm-form label.slm-check{font-weight:400;flex-direction:row;align-items:center;gap:8px}
  .slm-form input:is([type=checkbox],[type=range]){accent-color:var(--primary-color)}
  .slm-form input[type=checkbox]{width:20px;height:20px}
  .slm-form input:not([type=checkbox]),.slm-form select{padding:12px;border-radius:8px}
  .slm-form :is(input,select,summary,button):focus-visible,.slm-shell button:focus-visible{outline:3px solid var(--primary-color);outline-offset:2px}
  .slm-picker,.slm-mode-section{border:1px solid var(--divider-color);border-radius:12px;padding:12px;min-width:0}
  .slm-picker summary,.slm-mode-section summary{cursor:pointer;font-weight:600}
  .slm-picker input[type=search]{margin:10px 0;width:100%}
  .slm-choices{display:grid;gap:8px;max-height:260px;overflow:auto;padding:0 2px}.slm-choices [hidden]{display:none!important}
  .slm-actions{display:flex;gap:9px;justify-content:flex-end;flex-wrap:wrap;margin-top:20px}
  .slm-row{width:100%;border:1px solid var(--divider-color);border-radius:13px;background:var(--card-background-color);padding:18px;text-align:left;margin:9px 0}
  .slm-link{position:relative;display:grid;padding-right:36px;gap:4px;color:var(--primary-text-color);text-decoration:none}
  .slm-link small,.slm-mode-row small{display:block;color:var(--secondary-text-color)}
  .slm-link span{position:absolute;right:14px;top:50%;transform:translateY(-50%);font-size:20px}
  .slm-create{margin-top:12px}.slm-list-top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
  .slm-zone-group{margin:24px 0}.slm-mode-row{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:14px}.slm-mode-row.slm-active{border-color:var(--primary-color)}
  .slm-mode-swatch{width:44px;height:44px;border-radius:10px;background:var(--swatch);border:1px solid var(--divider-color)}
  .slm-row-actions,.slm-palette,.slm-preview-meta{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  .slm-active-label{margin-inline-start:8px;color:var(--primary-color);font-weight:600}
  .slm-mode-section{display:grid;gap:13px;padding:15px}.slm-mode-section:not([open])>summary{list-style-position:inside}
  .slm-mode-section:not([open])>summary~*{display:none}.slm-mode-section h2{font-size:18px;margin:0}
  .slm-palette{margin:8px 0}.slm-color{width:38px;height:38px;padding:0;border-radius:50%;background:var(--swatch)}
  .slm-color[aria-pressed=true]{outline:2px solid var(--primary-color);outline-offset:2px}
  .slm-form input[type=color]{width:100%;padding:3px;height:44px}
  .slm-preview{height:134px;border-radius:13px;background:#14161b;display:grid;place-items:center}
  .slm-strip{width:84%;height:9px;border-radius:12px;background:var(--strip);box-shadow:0 0 20px var(--strip);opacity:var(--intensity)}
  .slm-strip.slm-blink{animation:slm-fade var(--period) steps(1,end) infinite}
  .slm-strip.slm-pulse{animation:slm-fade var(--period) ease-in-out infinite}
  @keyframes slm-fade{0%,100%{opacity:var(--intensity)}50%{opacity:.07}}
  @media(prefers-reduced-motion:reduce){.slm-strip.slm-blink,.slm-strip.slm-pulse{animation:none}}
  @media(max-width:800px){main.slm-admin{padding:16px}.slm-shell{padding:16px;border-radius:20px}.slm-shell h1{font-size:28px;margin-bottom:15px}.slm-sub{font-size:18px}.slm-tile{min-height:155px;padding:17px;gap:12px;border-radius:16px}.slm-tile strong{font-size:20px}.slm-tile span{font-size:16px}.slm-tile svg{width:32px;height:32px}}
  @media(max-width:520px){.slm-grid{grid-template-columns:1fr;gap:16px}.slm-tile{min-height:130px}.slm-form{padding:16px}.slm-mode-section{padding:10px}.slm-row-actions{grid-column:2}.slm-actions button{flex:1}.slm-mode-editor .slm-actions .danger{flex-basis:100%;margin:0}}
  main.slm-home{max-width:1000px;margin-inline:auto;padding:20px}
  .slm-home .slm-shell{padding:18px;border-radius:20px}
  .slm-home h1{font-size:30px;margin:4px 0 10px}
  .slm-home .slm-sub{font-size:18px;margin-bottom:16px}
  .slm-home .slm-grid{gap:12px}
  .slm-home .slm-tile{min-height:145px;padding:18px;gap:9px;border-radius:16px}
  .slm-home .slm-tile-settings{min-height:100px}
  .slm-home .slm-tile svg{width:28px;height:28px}
  .slm-home .slm-tile strong{font-size:21px}
  .slm-home .slm-tile span{font-size:16px}
  @media(max-width:520px){main.slm-home{padding:12px}.slm-home .slm-shell{padding:14px}.slm-home .slm-tile{min-height:110px}.slm-home .slm-tile-settings{min-height:100px}}
`;
