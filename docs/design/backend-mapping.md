# Correspondencia con backend
Fuente revisada: `a0df3c48711f8b40fe48f8ded122d5a572906c83`. Verificar nuevamente los contratos, pruebas y schemas antes de implementar.

| Pantalla | Base existente | Trabajo / riesgo |
|---|---|---|
| Luces | config_flow.py; CONF_LIGHTS; targeting.py | Gestionar dependencias y límites; panel autenticado |
| Zonas | ModeManager, CONF_ZONES, Options Flow | CRUD gráfico estable, IDs/áreas, eliminación segura |
| Modos | ModeManager, acciones activate_mode/deactivate_mode/set_zone_mode, switch/select | Edición en panel y exposición opcional; no cambiar unique_id |
| Numérico | RuleCatalog, numeric rule, visual_editor.py | Plantillas, device_class y unidades reales, conservar interpolación/rangos |
| Seguridad / Presencia | state rule, RuleManager | Estados compatibles, espera tras desactivación requiere verificar/ampliar contrato (no confundir con permanencia de activación) |
| Avisos | services.yaml notify, cancel, clear_notifications, motor de animaciones/expiry | Catálogo por ID persistente, acción por referencia; extensión pendiente |
| Horario | time condition/schedule y RuleManager | El esquema actual admite state/numeric/event; regla solo-horario sin fuente requiere confirmar representación o añadir tipo/contrato, sin entidad ficticia obligatoria |
| Avanzada | condition tree, rule_schema.py | Mapear todas/cualquiera; regla solo-condiciones sin origen principal requiere verificar; conservar anidación/semántica desconocida |
| General/motor | config_flow.py, const.py, CONF_SHOW_SIDEBAR, tie_breaker, manual_policy, min_command_interval | Exponer valores reales, validar intervalo 0.1–10 s paso 0.05 |
| Recuperación | coordinator.py, controller, scheduling | Mostrar comportamiento y estado real; configuración de D pendiente |
| Diagnóstico | diagnostics.py, coordinator.async_diagnostics | Redacción de secretos, actividad acotada, no inventar conexión física |

`visual_editor.py` contiene registro del panel, WebSocket autenticado, revisión optimista y mutación de reglas. Investigar causa de `Smart LED Manager config entry is not loaded` durante recarga/configuración. No eludir permisos o validaciones. Mantener coordinador, PriorityEngine, catálogo, Store, entry_id, entity IDs y lógica de recuperación. Toda mutación debe revalidar autorización y evitar listeners/tareas duplicadas o comandos obsoletos. Deduplicar destinos y mantener rate limit por luz. No introducir backend paralelo ni dependencias externas innecesarias.

El HTML usa datos ficticios y funciones directas; no son contratos de API. Implementar usando API asíncrona oficial de HA y traducciones en/es. No asumir que un selector dinámico de avisos ya existe. Registrar capacidades nuevas como pendientes hasta validar.

## Contrato de reglas de C.2.3

Las plantillas usan el mismo catálogo WebSocket, opciones y motor. La
clasificación procede del tipo de entidad, clase y unidad publicados por
Home Assistant. Las reglas guardadas desde las plantillas pueden incluir
`category` y `source_unit`. La unidad queda vinculada a los puntos y umbrales.
Un cambio de unidad requiere confirmación y recalibración. El motor libera la
solicitud mientras las unidades difieran.

`release_seconds` es opcional para reglas de estado y equivale a cero cuando
falta. Es independiente de `for_seconds`, que retrasa la activación. El
temporizador vive en memoria, se cancela cuando vuelve a cumplirse la
condición y se limpia al descargar. Un origen no disponible o desconocido
libera la solicitud. Tras reiniciar o recargar se reevalúan las fuentes
vigentes. Los campos opcionales no requieren reescritura de las reglas
heredadas ni cambio de versión de ConfigEntry.
