# Correspondencia con backend
Auditoría inicial en `a0df3c48711f8b40fe48f8ded122d5a572906c83`. Contratos de C.2.4 comprobados en `05e0674c941f8b67f7b3a21bd66eb32a998eae68`.

| Pantalla | Base existente | Trabajo / riesgo |
|---|---|---|
| Luces | config_flow.py; CONF_LIGHTS; targeting.py | Gestionar dependencias y límites; panel autenticado |
| Zonas | ModeManager, CONF_ZONES, Options Flow | CRUD gráfico estable, IDs/áreas, eliminación segura |
| Modos | ModeManager, acciones activate_mode/deactivate_mode/set_zone_mode, switch/select | Edición en panel y exposición opcional; no cambiar unique_id |
| Numérico | RuleCatalog, numeric rule, visual_editor.py | Plantillas, device_class y unidades reales, conservar interpolación/rangos |
| Seguridad / Presencia | state rule, RuleManager | `release_seconds` para la espera de finalización y `for_seconds` para la permanencia inicial |
| Avisos | `notify`, `cancel`, `clear_notifications`, animaciones y vencimiento | Definición persistente `notice` y ejecución temporal con `run_notice` por ID |
| Horario | time condition/schedule y RuleManager | Regla `continuous` con horario local asociado a los días de inicio |
| Avanzada | condition tree, rule_schema.py | Regla `continuous` con árbol de condiciones, horario opcional y editor compatible para árboles anidados |
| General/motor | config_flow.py, const.py, CONF_SHOW_SIDEBAR, tie_breaker, manual_policy, min_command_interval | Exponer valores reales, validar intervalo 0.1–10 s paso 0.05 |
| Recuperación | coordinator.py, controller, scheduling | Mostrar comportamiento y estado real; configuración de D pendiente |
| Diagnóstico | diagnostics.py, coordinator.async_diagnostics | Redacción de secretos, actividad acotada, no inventar conexión física |

`visual_editor.py` contiene registro del panel, WebSocket autenticado, revisión optimista y mutación de reglas. Investigar causa de `Smart LED Manager config entry is not loaded` durante recarga/configuración. No eludir permisos o validaciones. Mantener coordinador, PriorityEngine, catálogo, Store, entry_id, entity IDs y lógica de recuperación. Toda mutación debe revalidar autorización y evitar listeners/tareas duplicadas o comandos obsoletos. Deduplicar destinos y mantener rate limit por luz. No introducir backend paralelo ni dependencias externas innecesarias.

El HTML usa datos ficticios y funciones directas. La implementación usa las APIs asíncronas de HA y traducciones en/es.

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

## Contrato de C.2.4

El catálogo amplía las opciones existentes con `notice` y `continuous`.
Conserva la versión de ConfigEntry y los registros `state`, `numeric` y
`event`. El editor compatible preserva árboles anidados, NOT, disparadores
por evento y destinos avanzados cuando el formulario sencillo no los puede
representar. Los guardados conservan la revisión optimista y la confirmación
después de que la revisión se aplica. La simulación de horarios y condiciones
evalúa datos de ejemplo mediante WebSocket de administración, sin solicitar
iluminación al motor. La simulación de avisos se ejecuta en el navegador.

`notice` conserva su ID al renombrar. `run_notice` vuelve a validar los
destinos autorizados y envía una solicitud temporal al motor existente.
Repetir el aviso renueva el vencimiento de la misma solicitud. Al expirar
se resuelve la intención vigente por cada luz. Guardar un cambio o eliminar
una definición recarga la integración y acaba los avisos temporales activos,
incluidas otras ejecuciones transitorias. Las definiciones sobreviven al
reinicio y las ejecuciones transitorias se descartan. `notify` conserva su
esquema y ejecución directa. El prefijo `smart_led_manager:notice:` queda
reservado para las solicitudes internas de `run_notice`.

`continuous` admite horario, árbol de condiciones o ambos. El inicio es
inclusivo y el fin exclusivo. En intervalos nocturnos, el día es el de inicio.
Se emplea la zona de Home Assistant y se programa la siguiente transición
aplicable. El gestor reevalúa en cambios de estado, de hora local, de zona
horaria, recarga y arranque. Los valores desconocidos o no disponibles nunca
activan por sí solos una condición, incluso bajo NOT. La histéresis de una
condición numérica se mantiene en memoria y se reinicia al perder el origen
o recargar.

### Selector nativo de avisos

`run_notice` se registra una vez. Al cargar la revisión, `async_set_service_schema`
publica las opciones del selector `select` con el nombre como `label` y el
ID como `value`. Las opciones contienen los avisos habilitados. El navegador
en Core 2026.11.3 abrió una automatización real y comprobó la publicación por
`get_services` y el contenido que usa el editor después de crear, renombrar
y eliminar definiciones. Con el editor abierto, la copia local de servicios
conservó las opciones previas. Al recargar la página se reflejaron las tres
operaciones y el ID guardado en la automatización se mantuvo. Una referencia
a un aviso eliminado produce un error de validación al ejecutarse.
[Registro del navegador](https://github.com/abel-smart-home/smart-led-manager/actions/runs/45897281530/job/140174208661).

La biblioteca de Home Assistant refresca su colección al registrar o retirar
una acción. Una actualización de metadatos mediante la API oficial no emite
esos eventos. La alternativa operativa es guardar el borrador de la
automatización y recargar la página del editor. Una actualización automática
dentro del editor requeriría soporte de Home Assistant o una decisión de
producto con aprobación previa. [Selector `select`](https://www.home-assistant.io/docs/blueprint/selectors/#select-selector) · [Colección de acciones del cliente](https://github.com/home-assistant/home-assistant-js-websocket/blob/master/lib/services.ts).
