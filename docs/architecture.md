# Arquitectura de Smart LED Manager

## Propósito y límites

Smart LED Manager es una capa local de arbitraje sobre entidades `light` ya existentes. No sustituye ZHA, Matter, ESPHome, WLED ni el controlador físico. Recibe intenciones de diferentes orígenes, decide una ganadora por tira y proyecta esa intención únicamente a luces autorizadas.

La primera versión se diseña para RGB, RGBW, RGB+CCT y RGBWW sin lógica exclusiva para GLEDOPTO. La resolución de prioridades no conoce protocolos ni píxeles; por eso un futuro controlador direccionable podrá mapear una intención a segmentos sin reconstruir el motor.

## Capas

1. **Modelo y motor puro** (`models.py`, `core/priority.py`, `core/engine.py`). Conservan solicitudes activas, validan tiempos/prioridades y resuelven un ganador independiente por destino bajo un bloqueo asíncrono.
2. **Módulos** (`modules/`). `rule_schema.py` normaliza un catálogo común;
   `targeting.py` expande destinos contra el límite autorizado y `rules.py`
   traduce estados, valores y disparadores oficiales a solicitudes del mismo
   motor. `ModeManager` conserva las zonas/modos. `RuleManager` posee listeners,
   demoras, límites horarios, disparadores y tareas, y los cancela y espera
   antes de una recarga.
3. **Orquestación** (`coordinator.py`). Posee suscripciones, historial acotado, persistencia, vencimientos, disponibilidad y ciclo de vida de la entrada.
4. **Planificación** (`core/scheduler.py`). Cancela el trabajo del ganador anterior y ejecuta expiraciones/animaciones con tareas asíncronas por destino.
5. **Proyección física** (`controllers/rgb.py`). Consulta el estado y capacidades reales, convierte la intención a `light.turn_on`/`light.turn_off`, deduplica y limita órdenes.
6. **Superficie Home Assistant** (`config_flow.py`, `services.py`, `select.py`,
   `switch.py`, `sensor.py`, `registry.py`, `diagnostics.py`, `visual_editor.py`
   y `frontend/`). Ofrece configuración nativa,
   acciones con selectores, un selector por zona, interruptores de modo
   opcionales, dispositivos virtuales estables por zona, diagnóstico y una
   entidad de estado del motor.

```text
reglas / modos / acciones / control manual
                │
                ▼
       solicitudes de intención
                │
                ▼
 motor ── resolución por light.entity_id ── ganador
                │                            │
     persistencia/expiración                 ▼
                                      animación/proyección
                                             │
                                             ▼
                                    API oficial light.*
```

## Solicitud

Cada solicitud tiene un identificador estable, origen, nombre, módulo, conjunto no vacío de destinos, prioridad `0..100`, estado activo, estilo de luz, fechas UTC de creación/actualización/activación/vencimiento, permiso de encendido, persistencia y metadatos de animación/restauración. La serialización rechaza fechas sin zona horaria y datos fuera de rango.

El estilo es una intención portable: encendido/apagado, RGB opcional, brillo, transición y animación. No incluye atributos específicos de ZHA o de un fabricante.

## Resolución y concurrencia

- Primero gana la prioridad numérica mayor.
- En empate se usa `newest`, `oldest` o `lexical`, siempre con `request_id` como último criterio estable.
- Una solicitud se evalúa por cada destino; destinos superpuestos se convierten en un conjunto para no duplicar órdenes.
- Actualizar una solicitud inferior reemplaza su intención aun cuando no sea visible.
- Al desactivar, cancelar o vencer la ganadora se calcula el siguiente estado vigente; no se restaura un snapshot antiguo.
- Todas las mutaciones del motor están protegidas por un único `asyncio.Lock`. Las llamadas físicas ocurren después de liberar ese bloqueo.
- La política temporal de `alpha.1` es **vencimiento en tiempo real**: una solicitud interrumpida sigue consumiendo su TTL. La reanudación con tiempo restante se mantiene como política futura explícita.

El cambio de modo usa `async_replace_matching`: retira la solicitud anterior de
la zona e inserta la nueva bajo el mismo bloqueo del motor. Los cambios físicos
comparan el ganador anterior con el resultado final, por lo que una regla o
escena de menor prioridad no aparece entre ambos modos. La reactivación del
mismo modo se detecta antes de mutar el motor.

## Capacidades y comandos

El controlador lee `supported_color_modes`, `supported_features`, disponibilidad y efectos de la entidad. Envía solo atributos representables. RGB se proyecta sobre modos RGB/RGBW/RGBWW compatibles; si una luz no puede representar color, el error queda diagnosticado sin un bucle de reintentos.

Cada luz conserva intención deseada, firma del último comando y una sola tarea pendiente. El intervalo mínimo es configurable; una orden nueva sustituye trabajo obsoleto. Una luz `unavailable` conserva la intención y se resincroniza al reaparecer, siempre que la solicitud siga vigente.

Si un envío falla aunque Home Assistant todavía publique `on` u `off`, el controlador invalida tanto su firma como el estado aplicado en caché y el coordinador agenda una única recuperación de fondo. Tras una espera inicial de 5 segundos, esa recuperación realiza como máximo ocho envíos de la intención vigente, con pausas de 5, 10, 20, 40 y después 60 segundos hasta el límite. El último intento ocurre tras un máximo de 260 segundos de espera programada desde el fallo inicial, sin contar la latencia o timeout propio del servicio de luz. Un cambio de ganadora, cancelación, vencimiento o descarga cancela y espera ese trabajo antes de aplicar o liberar la intención; nunca se conserva un comando histórico para reproducirlo después.

## Persistencia y recuperación

La configuración, las zonas, los modos y las reglas viven en la entrada de
configuración. La selección activa no se duplica en opciones: se guarda como
la solicitud persistente de modo mediante el mismo `Store` versionado. En el
arranque, `ModeManager` elimina modos huérfanos o duplicados y reconstruye el
comando desde la definición vigente, conservando la antigüedad válida para el
desempate. Después se vuelven a evaluar fuentes y ganador actual. Nunca se
restaura una definición borrada ni se recrean temporizadores duplicados.

Alpha.2 añadió claves opcionales `zones` y `modes` con listas vacías por
defecto. Alpha.3 migra el ConfigEntry de `1.1` a `1.2` y añade `area_id: null`
a cada zona existente. No cambia `zone_id`, `mode_id`, los `unique_id` de las
entidades ni el esquema serializado de `Request`.

El Bloque B no requiere otra migración: `enabled` es opcional y su ausencia se
interpreta como `true`. Las reglas conservan su `id` al editarse y las copias
reciben uno nuevo. Los puntos permanecen en el formato de lista estructurada de
alpha.1/alpha.2. El Options Flow guarda la definición completa y la recarga
ordinaria descarta el motor en memoria anterior; el catálogo nuevo reevalúa las
fuentes actuales. Las tareas de la instancia anterior se cancelan y esperan
antes de crear listeners nuevos, por lo que no pueden reinsertar una solicitud
obsoleta.

El Bloque C tampoco incrementa el esquema de ConfigEntry ni el Store. Las
reglas heredadas conservan `targets`; una definición nueva puede usar
`target_selection`, condiciones, horario, permanencia, activación numérica o
trigger. Esos campos se normalizan al editar, pero no cambian el `id` ni crean
estado derivado persistente.

## Destinos avanzados y autorización

`AdvancedTargetResolver` convierte luces, zonas, áreas, etiquetas, grupos
transparentes y “todas las administradas” en un conjunto de entidades físicas
individuales antes de tocar el motor. La lista explícita de luces autorizadas
es el límite absoluto. Un destino explícito ajeno se rechaza; áreas y etiquetas
se intersectan con la lista y exponen sus exclusiones; un grupo opaco, circular,
desconocido o con un solo miembro inseguro se rechaza completo. La lista
autorizada también se audita para impedir que una entidad `light` con miembros
actúe como puerta trasera.

Las reglas continuas vuelven a resolver destinos ante cambios de membresía,
aparición de un miembro y eventos oficiales de Entity, Device, Area y Label
Registry. El conjunto de suscripciones sigue el árbol actual incluso si un
miembro todavía está ausente. Retiran la misma
solicitud de los destinos anteriores y la aplican a los nuevos. Una solicitud
de evento ya activa puede moverse mientras no venza, sin renovar su plazo; un
evento pasado no se recrea. Las acciones explícitas conservan la semántica de
instantánea en el momento de la llamada. No existe sondeo general.

El controlador consulta estados y metadatos de agrupación antes de despachar,
incluidos los registrados por HA y los grupos identificables de ZHA y Hue. Las
rutas de acciones, modos y recuperación comparten ese control. Para reglas
vigentes también se revalida pertenencia al destino y, en eventos, el plazo.
Una entidad con estado `unavailable` puede formar parte de un grupo seguro
si está identificada individualmente. Un miembro ausente invalida el grupo
hasta que aparezca.

## Condiciones, tiempo y activación numérica

`core/conditions.py` es puro y usa `TRUE`, `FALSE` y `UNKNOWN`. AND, OR y NOT
propagan lo desconocido para que `unknown`, `unavailable`, una entidad ausente
o un número inválido nunca se conviertan en éxito por negación. Los árboles se
limitan a cinco niveles y 32 nodos. `RuleManager` escucha la fuente principal y
todas las fuentes secundarias.

Los horarios usan la zona local de Home Assistant y callbacks en el próximo
límite, sin polling. En un intervalo que cruza medianoche el día configurado es
el día de inicio. Core iniciado dentro del intervalo evalúa inmediatamente; la
recarga vuelve a calcular el siguiente límite. La permanencia mínima se aplica
al resultado completo de una regla continua, se cancela si deja de cumplirse y
se reevalúa al vencer. No se restaura como ya cumplida después de reiniciar.

La activación numérica mantiene un estado de histéresis sólo en memoria y está
separada de `core/color.py`. Tras iniciar o recuperar un sensor inválido parte
inactiva: `above` exige `>`, `below` exige `<`, `inside` incluye ambos límites y
`outside` los excluye. Una vez activa, la banda de histéresis determina la
liberación; el color puede seguir siendo fijo, interpolado o por rangos.

## Centro de administración y editor de reglas

El Bloque B.1 añade una superficie de configuración; no añade otro motor de
reglas. Home Assistant sirve los módulos ES incluidos en `frontend/` mediante
`StaticPathConfig` y registra un panel personalizado local con
`panel_custom.async_register_panel`. La ruta exige administrador; el título
lateral puede omitirse mediante una opción persistente sin retirar el panel ni
duplicar backend. Cada comando WebSocket también aplica `require_admin`, por lo
que ocultar la interfaz no constituye la barrera de seguridad.

El Bloque C conserva el mismo panel y lo amplía a un catálogo unificado de
reglas de estado, numéricas y de eventos. Crear, editar, duplicar, habilitar,
eliminar, previsualizar destinos o simular puntos usa contratos WebSocket
administrativos compartidos con el validador del Options Flow. El frontend
mantiene un borrador completo. Ninguna previsualización toca ConfigEntry,
Store, motor ni servicios `light.*`; el cálculo numérico continúa delegado a
`core/color.py`, sin una segunda implementación.

Al guardar, `visual_editor.py` construye un `RuleCatalog`, vuelve a validar la
regla completa, expande sus destinos y, para eventos, delega la validación al
helper oficial de triggers. Relee las opciones bajo un bloqueo, compara una
revisión SHA-256 y rechaza una sesión obsoleta con `conflict`. El endpoint
heredado que sólo modifica `mode` y `points` se conserva para compatibilidad;
el catálogo nuevo usa `async_update_entry` y el listener normal ejecuta la
recarga ya probada por el Bloque B.

Desde C.2.1 el coordinador registra la revisión de las opciones con las que se
construyó. El WebSocket de administrador `smart_led_manager/editor/status`
informa la revisión guardada, la cargada y el estado de la ConfigEntry. Los
eventos y la reconexión del cliente motivan lecturas de estado. El frontend
confirma el guardado al leer el catálogo de la misma revisión que el runtime
aplicó. Las lecturas durante una recarga tienen un número acotado de intentos.
La entrada en transición rechaza escrituras y previsualizaciones con
`entry_not_loaded`. Para estos comandos, un ID inexistente devuelve
`entry_not_found`.

Cada envío del editor puede llevar un identificador. El backend guarda en
memoria los últimos 32 recibos por entrada. Eso permite comprobar una
actualización cuya respuesta se perdió y deduplicar la repetición del mismo
envío. Una revisión obsoleta sigue produciendo un conflicto. Los recibos se
descartan al eliminar la entrada o reiniciar Core.

El panel mantiene su ruta durante la recarga. Para las recargas nativas, se
espera a que Core termine la transición de la entrada antes de decidir si se
retira el panel. La descarga definitiva y la eliminación retiran el panel y los
trabajos del runtime. Los comandos WebSocket y la ruta estática siguen
registrados una sola vez a nivel de integración.

El Device Registry contiene un dispositivo central identificado por
`(smart_led_manager, entry_id)` y un dispositivo por zona identificado por
`(smart_led_manager, entry_id:zone:zone_id)`. El sensor del motor permanece en
el central; los selectores e interruptores se asocian a su zona. Renombrar una
zona actualiza el nombre del mismo dispositivo. El área opcional se aplica sólo
al dispositivo virtual mediante la API oficial y nunca a las luces físicas.

La reconciliación del Entity Registry se ejecuta al cargar una entrada válida.
Retira únicamente selectores de zonas y switches de modos cuya definición ya
no existe en esa misma entrada. Un modo que conserva su definición pero deja
de exponerse no se borra del registro; una descarga temporal tampoco limpia.
Si el catálogo está dañado, se omite la limpieza. No se escriben archivos
internos de `.storage` directamente.

Al descargar la integración se eliminan listeners, se cancelan vencimientos/animaciones/tareas de controlador y se vacía el registro de runtime. La política de descarga no fuerza restauraciones físicas ciegas.

## Reglas inteligentes

- **Estado:** igualdad o desigualdad sobre entidades persistentes (sensores binarios, interruptores, ayudantes, clima, alarma, presencia, persona y sol). La condición falsa libera su solicitud.
- **Numérica:** N puntos ordenados, interpolación RGB o rango inferior, clamp en extremos, variación mínima e intervalo mínimo. `unknown`, `unavailable`, NaN e infinito liberan/ignoran la solicitud según corresponda.
- **Administración:** alta, edición con identificador estable, copia inicialmente
  deshabilitada, activación/desactivación y eliminación. El editor multipaso usa
  selectores nativos y no aplica órdenes hasta guardar.
- **Eventos/botones:** usan la validación e inicialización oficial de triggers
  de Home Assistant. Un cambio de estado, evento del bus, entidad `event`,
  `input_button` o device trigger compatible crea una solicitud temporal. Un
  evento repetido renueva el mismo `request_id`; no crea cola, no usa
  permanencia y no se reproduce al iniciar.

## Animaciones iniciales

`fixed`, `blink` y `pulse` usan una tarea por destino y respetan el intervalo del controlador. Una nueva ganadora cancela la tarea anterior antes de emitir el siguiente cuadro. Alternancia multicolor, respiración avanzada, secuencias editables y efectos direccionables están en la hoja de ruta.

## Decisiones de compatibilidad

- Home Assistant mínimo: `2026.11.0`, porque esta rama usa el contrato actual de esquemas `probatio`, traducciones de integraciones personalizadas y se valida para Marketplace integrado.
- Python mínimo: `3.14.2`, igual que el entorno de desarrollo de Home Assistant 2026.11.
- No se usa polling periódico general. Los cambios provienen de eventos de estado, deadlines de expiración y cuadros de una animación activa.
- No hay interceptores globales de `light.turn_on`; el control manual directo se basa en contexto/eco cuando se habilite y se mantiene conservador.

## Riesgos que requieren pruebas físicas

La conversión de color de una entidad concreta, la latencia ZHA, el multicast de grupos Zigbee, la propagación de `Context`, los límites aceptables de animación y la recuperación de un GLEDOPTO desconectado no pueden validarse plenamente en pruebas unitarias. El procedimiento está en [haos-test-plan.md](haos-test-plan.md).
