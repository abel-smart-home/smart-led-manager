# Historial de cambios

Este proyecto sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y usa versionado semántico. La versión del manifest conserva la forma de
pre-release (`0.1.0-alpha.3`) y `pyproject.toml` usa su equivalente PEP 440
(`0.1.0a3`).

## [0.1.0-alpha.3] — Sin publicar

### Planificación aprobada — Bloque C.2

- El propietario aprobó el prototipo v1.0 como referencia preliminar y adelantó
  a C.2 los módulos gráficos previstos en beta.1 que requiere ese diseño. La
  [hoja de ruta](docs/roadmap.md) registra el alcance y las etapas internas.

### Corregido — C.2.1

- El editor confirma **Configuración guardada** cuando el coordinador ya
  ejecuta la revisión guardada. Puede comprobar el resultado tras perder un
  evento o reconectar. Un fallo de recarga deja el borrador y muestra el
  estado de la entrada.
- El guardado concurrente conserva la revisión del borrador. Al cancelar o
  volver con cambios, el diálogo ofrece continuar editando, descartar y
  salir, o guardar y salir.
- Las recargas de opciones y las solicitadas desde Home Assistant mantienen
  la ruta del panel. [Recorrido de verificación C.2.1](docs/haos-c21-checks.md).
- El propietario reportó P-01–P-06 aprobadas en HAOS VirtualBox con
  `cf2f371353dc6321baaef67c0ca8858e6d564110`. [Registro de pruebas](docs/haos-test-plan.md#resultado-de-c21-en-virtualbox).

### Añadido — C.2.2

- Centro de administración de cinco secciones. Iluminación inteligente conserva
  el editor de reglas y Configuración abre los ajustes nativos de Home Assistant.
- Selección buscable de luces administradas, zonas con área opcional y modos
  agrupados por zona. Las retiradas comprueban dependencias de zonas, modos y
  reglas, incluidas las deshabilitadas.
- Editor de modos con color, brillo, efectos compatibles, vista previa local
  e interruptor opcional. La selección activa y el guardado usan el coordinador
  y la revisión aplicada de la única entrada.
- El propietario aprobó Q-01–Q-10 en HAOS VirtualBox con Core 2026.11.3.
  Indicó que el inicio ocupaba demasiado espacio. [Resultado funcional y observación visual](docs/haos-test-plan.md#resultado-de-c22-en-virtualbox).

### Añadido — C.2.3

- Inicio compacto centrado con las cinco tarjetas y sus accesos.
- Iluminación inteligente agrupa el catálogo y las plantillas de temperatura,
  humedad, potencia, energía acumulada, seguridad y presencia. Las reglas
  heredadas conservan el editor compatible.
- Las plantillas numéricas guardan la unidad exacta de calibración. Si
  cambia, liberan la solicitud y requieren recalibrar los valores.
- Las reglas de estado pueden esperar antes de finalizar. Recuperar la
  condición cancela la espera. La pérdida del sensor libera la solicitud.
- El propietario aprobó R-01–R-12, el tamaño del inicio y la validación visual
  en HAOS VirtualBox con Core 2026.11.3. [Registro](docs/haos-test-plan.md#resultado-de-c23-en-virtualbox).

### Añadido — C.2.4

- Catálogo de avisos guardados, simulación en pantalla y prueba explícita en
  luces autorizadas. La acción `smart_led_manager.run_notice` usa un ID estable.
  Recarga el editor de automatizaciones de Home Assistant para ver los cambios
  del catálogo si ya estaba abierto.
- Horarios independientes y reglas continuas basadas sólo en condiciones.
  La simulación evalúa el borrador localmente sin enviar órdenes a luces.
- [Guía de instalación y validación práctica en VirtualBox](docs/haos-c24-checks.md).

### Añadido — Bloque A

- Un dispositivo virtual estable por zona, identificado por `entry_id` y
  `zone_id`, con su selector de modo y los interruptores opcionales de sus
  modos. El dispositivo central conserva únicamente el diagnóstico del motor.
- Asociación opcional del dispositivo de zona con un área existente de Home
  Assistant, sin cambiar las áreas de las luces físicas.
- Migración de ConfigEntry `1.1` a `1.2` que añade el área opcional sin cambiar
  identificadores de zonas, modos o entidades.

### Añadido — Bloque B

- Administrador gráfico de reglas con alta, edición, duplicación, activación o
  desactivación y eliminación desde el Options Flow nativo.
- Edición de reglas de estado y numéricas conservando su `id` estable; las
  copias reciben un identificador nuevo, un nombre diferenciable y comienzan
  deshabilitadas.
- Editor multipaso de puntos numéricos con `NumberSelector`, selector visual
  RGB, unidad del sensor cuando está disponible, alta, edición, eliminación,
  ordenamiento automático y validación de valores finitos, colores, duplicados
  y mínimo de dos puntos.
- Compatibilidad con reglas anteriores sin `enabled`, que continúan habilitadas
  por defecto y conservan identificadores y formato persistente de puntos.

### Añadido — Bloque B.1

- Panel personalizado local para Home Assistant 2026.11, visible sólo para
  administradores en `/smart-led-manager-editor`, con componente web incluido
  en la integración y sin CDN, nube, YAML ni compilación para el usuario.
- Lista de reglas numéricas existentes con nombre, origen y estado; editor de
  borrador para `mode` y puntos que conserva el `id` y todos los campos no
  editados de la regla.
- Selector de color, alta, edición, eliminación y ordenamiento visual de puntos;
  barra y gráfica respetan sus posiciones numéricas reales, incluso con
  negativos, decimales e intervalos no uniformes.
- Simulador WebSocket que reutiliza el cálculo exacto de `core/color.py` para
  interpolación, rangos y clamp de extremos, sin crear solicitudes ni llamar a
  servicios de luces.
- Lectura, simulación y guardado WebSocket restringidos a administradores. El
  guardado vuelve a validar opciones, luces autorizadas, puntos y formato en
  Python y usa una revisión SHA-256 de las opciones completas para rechazar
  conflictos concurrentes.
- El editor nativo del Bloque B permanece disponible. El Options Flow documenta
  la ruta oficial del panel sin depender de APIs privadas de navegación.
- Centro de administración inicial con identidad y versión instalada, acceso al
  editor de reglas numéricas y enlace a la configuración nativa. El menú
  principal del Options Flow ofrece un enlace interno Markdown compatible.
- Opción persistente **Mostrar Smart LED Manager en la barra lateral**, activada
  por defecto. Al ocultarla, la ruta administrativa permanece disponible sin
  registrar otro panel, motor o catálogo.
- Nombres amigables de sensores y luces en la vista habitual; los `entity_id` y
  el identificador interno de la regla quedan en información técnica desplegable.

### Añadido — Bloque C

- Catálogo común de reglas de estado, numéricas y de eventos, usado por el
  panel y el Options Flow con identificadores estables, validación Python y
  revisión optimista de las opciones.
- Destinos combinables por luz, zona de Smart LED Manager, área, etiqueta,
  grupo transparente o todas las administradas. La expansión deduplica luces,
  filtra áreas/etiquetas y rechaza grupos opacos, ciclos y miembros inseguros.
- Condiciones AND/OR/NOT con estado, comparación numérica, horario y día; la
  evaluación usa tres estados para que un dato desconocido no se acepte por
  negación. Los árboles tienen límites explícitos de profundidad y tamaño.
- Horarios locales con días y cruce de medianoche, reevaluados mediante
  callbacks de límites; el día seleccionado identifica el inicio del intervalo
  nocturno. La permanencia mínima se aplica al resultado completo de una regla
  continua y se reinicia tras recarga o reinicio.
- Activación numérica por encima, debajo, dentro o fuera de rango, con
  histéresis independiente del cálculo de color. Los límites de entrada son
  estrictos para `above`/`below`, inclusivos para `inside` y se liberan en el
  borde ampliado por la histéresis.
- Reglas temporales conectadas a los disparadores oficiales de Home Assistant,
  incluidos estado, bus, entidades `event`, `input_button` y device triggers
  compatibles. Repetir el evento renueva la misma solicitud; no se mantiene
  una cola ni se reproduce historia al iniciar.
- Centro de administración ampliado a **Reglas inteligentes**, con lista
  unificada, CRUD completo, destinos previsualizables, animaciones existentes,
  editor numérico conservado y protección frente a respuestas obsoletas.
- Listeners, temporizadores de permanencia, límites horarios y tareas de
  evaluación quedan bajo `RuleManager`; descarga y recarga los cancelan y
  esperan sin crear un segundo motor ni un sondeo permanente.

### Compatibilidad y correcciones

- C.1 conserva el panel al recargar después de guardar y muestra la confirmación
  en el catálogo o el editor. El propietario había observado redirecciones a
  `/home/overview` durante la edición. Se mantienen el borrador y la revisión
  ante un error o conflicto.
- C.1 incorpora selectores para orígenes y destinos, un constructor de
  condiciones, horario, permanencia y disparadores visuales, y conserva las
  curvas y el simulador de B.1. El horario nocturno vuelve a programar su
  cierre al iniciar Core después de medianoche.
- C.1 rechaza grupos con miembros ausentes, vuelve a seguir la composición
  aunque el grupo llegue tarde y comprueba la autorización antes del envío
  de cualquier comando, incluidos modos, acciones y recuperación.

- Se conservan los `unique_id` de alpha.2; Home Assistant reasocia las mismas
  entidades a los dispositivos de zona y mantiene `entity_id`, nombres
  personalizados y referencias existentes.
- Los nombres propios de entidad usan `has_entity_name`: el dispositivo aporta
  el contexto de zona y cada modo conserva su nombre breve.
- Al eliminar permanentemente un modo o una zona se limpian sólo los registros
  exactos de esa entrada. Desactivar la exposición de un modo conserva su
  registro; descargar la integración no ejecuta limpieza.
- Un catálogo inválido desactiva la limpieza destructiva, y un dispositivo de
  zona borrada se conserva si otra entidad todavía lo referencia.
- Las evaluaciones de reglas y sus demoras quedan bajo propiedad de
  `RuleManager`: la descarga o recarga cancela y espera ese trabajo antes de
  iniciar el catálogo nuevo, y recupera cualquier excepción de tarea para que
  no quede como error sin observar.
- Una regla que incluya cualquier destino ajeno a la lista autorizada se
  rechaza completa. Editar destinos reemplaza la intención del mismo `id`,
  incluso si está enmascarada; desactivar o eliminar evita que reaparezca.
- Guardar una regla continúa recargando la ConfigEntry. Los cambios intermedios
  del editor no envían órdenes; las solicitudes temporales no persistentes
  pueden terminar durante esa recarga, como en alpha.2.
- Se corrigió la serialización de `MappingProxyType` de ConfigEntry al calcular
  la revisión, leer y guardar reglas, incluidos mapas anidados. El primer intento
  B1-01 falló por ese motivo y el propietario confirmó que el panel corregido ya
  carga una regla numérica existente y muestra su barra y distribución.
- El panel ya no se reconstruye con cada actualización global de `hass`, ignora
  respuestas de simulación obsoletas, no interpreta una entrada vacía como cero
  y distingue carga, catálogo vacío y error de WebSocket. Los comandos rechazan
  explícitamente una ConfigEntry descargada.
- La ampliación unificada conserva **Restaurar borrador**, la barra, la gráfica
  numérica y la selección accesible de puntos validadas en B.1; el catálogo
  nuevo no sustituye esas interacciones por una representación reducida.

### Validación

- El Bloque A tiene cobertura automatizada para migración, dispositivos,
  áreas, nombres, compatibilidad y limpieza selectiva. La matriz Linux aprobó
  135 pruebas y cobertura de ramas `87.50 %` en Home Assistant `2026.11.0` y
  `2026.11.2`; Ruff, Hassfest y HACS/Marketplace también aprobaron.
- El propietario reportó el 23 de noviembre de 2026 la aprobación 8/8 de A-01
  a A-08 en HAOS VirtualBox con el Bloque A
  `fa9ecd650485e27ee1f1f22654972a1c47379c17`. La evidencia es el resultado
  comunicado por el propietario; no se atribuyen logs ni métricas no
  entregados. La repetición física Raspberry Pi/ZHA/GLEDOPTO y los nombres por
  Alexa/Matter permanecen pendientes.
- El Bloque B añade regresiones automatizadas de edición, identidad,
  duplicación deshabilitada, destinos, puntos visuales, reglas heredadas,
  intención enmascarada, tareas diferidas y reconstrucción tras recarga. Su
  validación manual B-01 a B-10 fue reportada por el propietario como 10/10 en
  HAOS VirtualBox el 23 de noviembre de 2026 con `f8b9fc9`; no se atribuyen
  capturas, logs o métricas adicionales. La repetición física en Raspberry
  Pi/ZHA/GLEDOPTO continúa pendiente.
- El Bloque B.1 cubre backend y modelo frontend: lectura, borradores, edición y
  ordenamiento de puntos, simulación exacta, guardado conservador, rechazo de
  datos inválidos y destinos no autorizados, conflictos concurrentes,
  autorización administrativa y ciclo de vida del panel. El propietario
  reportó B1-01 a B1-10 aprobadas, 10/10, en HAOS VirtualBox sobre
  `6ad79e0c3c388f714f08c727ba17f315807310a4`. Se conserva el fallo inicial de
  serialización `MappingProxyType`, su corrección manual en `9ba3b0c` y el
  endurecimiento posterior. La suma reportada A/B/B.1 es 28/28.
- El commit del Bloque B cerró 148 pruebas con cobertura de ramas `87.14 %` en
  Home Assistant `2026.11.0` como en `2026.11.2`; Ruff, Hassfest y
  HACS/Marketplace también aprobaron. El pytest completo no se atribuye al
  entorno local Windows, donde `pytest-homeassistant` requiere el módulo POSIX
  `fcntl`; la matriz Linux conserva la evidencia ejecutable.
- Para B.1, la matriz Linux aprobó 157 pruebas Python con cobertura de ramas
  `87.21 %` en Home Assistant `2026.11.0` y `2026.11.2`; el job Node aprobó 6
  pruebas del modelo/panel. Ruff, Hassfest y HACS/Marketplace aprobaron sin
  exclusiones. B1-01 a B1-10 son evidencia manual comunicada por el propietario;
  B1-05, B1-06, B1-07 y B1-10 todavía requieren repetición física separada.
- El Bloque C añade pruebas puras y de integración para condiciones, horarios,
  histéresis, seguridad de destinos, CRUD, concurrencia, eventos, permanencia y
  ciclo de vida. El SHA funcional `2b9c4dd` aprobó 185 pruebas con cobertura de
  ramas `80.72 %` en Home Assistant `2026.11.0` y `2026.11.2`, 6/6 pruebas
  Node, Ruff, Hassfest y HACS/Marketplace. La batería manual C-01 a C-20 queda
  pendiente hasta el reporte del propietario; no se atribuye a CI ninguna
  validación visual o física.
- C.1 (`85770ce`) aprobó 228 pruebas en cada variante Linux con Home
  Assistant `2026.11.0` y `2026.11.2`. La cobertura global con ramas
  habilitadas fue `85.13 %`. Pasaron las 9 pruebas Node, la regresión en
  Edge con backend simulado, Ruff, Hassfest y HACS/Marketplace. Los pasos
  de HAOS siguen en la [guía C-01 a C-20](docs/haos-block-c-walkthrough.md).

## [0.1.0-alpha.2] — Sin publicar

### Añadido

- Zonas gráficas con identificador estable, nombre y subconjunto no vacío de
  luces autorizadas; una luz física sólo puede pertenecer a una zona.
- Modos persistentes por zona con prioridad, color, brillo, transición,
  permiso de encendido y animaciones `fixed`, `blink` o `pulse`.
- `ModeManager` que representa la selección como una solicitud persistente del
  motor, reemplaza el modo anterior de la zona en una sola transacción y
  reconcilia datos guardados contra la definición vigente al arrancar.
- Un `select` por zona con la opción **Sin modo**, y un `switch` estable sólo
  para cada modo que el propietario decida exponer.
- Acciones `activate_mode`, `deactivate_mode` y `set_zone_mode`, con esquemas y
  traducciones en inglés y español.
- Flujos gráficos para crear, editar y eliminar zonas y modos sin YAML.

### Seguridad y compatibilidad

- La entrada se clasifica como integración de tipo `service`, no como
  `helper`, para que Home Assistant la muestre en **Integraciones**. Este cambio
  sólo afecta a metadatos del manifest y no recrea ni migra la entrada.
- Se añade el catálogo completo `es-419` para que Español (Latinoamérica) no
  caiga al fallback inglés del Options Flow; `es` continúa disponible.
- Las solicitudes internas de modo usan identificadores protegidos y no pueden
  modificarse con las acciones genéricas.
- Cambiar de modo no muestra estados intermedios de menor prioridad; reactivar
  el mismo modo no altera su antigüedad, no reinicia animaciones, no repite el
  comando físico y no reescribe el almacenamiento.
- **Sin modo** libera únicamente la solicitud de modo y deja que el motor
  calcule la intención vigente; nunca ordena apagar a ciegas.
- No se cambia el esquema de config entry ni el Store de alpha.1: las nuevas
  definiciones son opciones con valores vacíos compatibles y las solicitudes
  conservan el formato persistente existente.

### Validación

- Cobertura automatizada de creación, edición, selección, reemplazo atómico,
  idempotencia, prioridades, reinicio, limpieza de huérfanos, varias zonas y
  entidades `select`/`switch`.
- La validación local aprobó 123 pruebas y 27 subpruebas, con 7 pruebas de
  runtime Home Assistant omitidas en Windows porque requieren Linux. La
  cobertura total de ramas fue `85.14 %`; Ruff y formato aprobaron.
- La matriz de CI aprobó 130 pruebas en Linux, sin omisiones, tanto con Home
  Assistant `2026.11.0` como con `2026.11.2`; la cobertura total fue
  `86.96 %`. Hassfest y HACS/Marketplace también aprobaron en el PR #2.

### Validación física y de laboratorio reportada por el propietario

- El commit `8e21b28` se probó durante noviembre de 2026 en HAOS `18.5`, Core
  `2026.11.2`, Raspberry Pi 5, ZHA y GLEDOPTO GL-C-007P. Pruebas posteriores en
  HAOS VirtualBox usaron dos luces RGBW/RGBWW de la integración Demo. La
  consolidación registra 16 casos M completos, 3 parciales y M-06 pendiente
  con hardware físico; no equivale a 16 pruebas completas sobre Zigbee.
- La evidencia física cubre selección exclusiva Cine/Lectura, prioridades,
  animaciones, reinicio de Core, recuperación Zigbee, cambios rápidos,
  desempates, clasificación, traducción y exposición Alexa/Matter Hub. También
  se confirmaron la repetición idempotente de modos y **Sin modo** sin una
  solicitud inferior, sin atribuir un entorno no registrado a Zigbee físico.
- El laboratorio comprobó dos zonas independientes con luces Demo, eliminación
  de la entrada y del Store, la secuencia de diagnóstico
  `winner → partial → winner → no_mode`, limpieza de solicitudes guardadas
  huérfanas/no autorizadas y actualización/reversión alpha.1 ↔ alpha.2 sin
  recrear la entrada.
- La clasificación `service` apareció en **Integraciones** y el Options Flow se
  mostró en Español (Latinoamérica). La actualización conservó luces, reglas y
  modos; no se atribuye una prueba independiente al perfil `es`.
- Los interruptores de Cine y Lectura se expusieron mediante
  Home-Assistant-Matter-Hub `2.0.60` y funcionaron con Alexa. Smart LED Manager
  no se comunica directamente con esos servicios y sus interruptores expresan
  selección lógica, no confirmación física del color.
- Al eliminar un modo, Home Assistant conservó una entidad virtual residual
  marcada como no proporcionada; el propietario la eliminó manualmente. Queda
  pendiente evaluar una limpieza selectiva del Entity Registry.
- M-10, M-15 y M-17 permanecen parciales. M-06 requiere dos controladores
  Zigbee reales pese a la simulación satisfactoria; también siguen visibles la
  entidad residual de M-10, la inyección adicional de configuración para M-15,
  las regresiones heredadas de M-17 y la corrupción sintáctica total no probada.
  Alpha.2 continúa **sin publicar** y como candidata experimental.

## [0.1.0-alpha.1] — Sin publicar

### Añadido

- Motor puro de solicitudes priorizadas, resolución independiente por luz,
  desempates deterministas, solicitudes enmascaradas y expiración UTC.
- Adaptador RGB consciente de capacidades, deduplicación, limitación de
  frecuencia y resincronización tras indisponibilidad.
- Config flow para la lista explícita de luces autorizadas y options flow para
  ajustes, reglas de estado y reglas numéricas.
- Acciones `activate`, `deactivate`, `notify`, `set_scene`, `cancel`,
  `clear_notifications` y `set_manual_override`.
- Persistencia versionada de solicitudes persistentes, recuperación, historial
  acotado, diagnóstico y sensor de estado del motor.
- Animaciones fija, parpadeo y pulsación con propiedad y cancelación por luz.
- Traducciones en inglés y español, documentación de uso, CI,
  hassfest y validación HACS/Marketplace.
- Auditoría de proyectos comunitarios sin reutilización de código de terceros.

### Seguridad

- Ninguna acción puede resolver una entidad fuera de la lista de luces
  administradas.
- Las órdenes internas conservan contexto para no tratarse como control manual
  externo y la detección directa permanece conservadora y optativa.

### Corregido

- Los temporizadores de vencimiento que se ejecutan con retraso reconstruyen el
  ganador anterior en el límite real de expiración de cada luz. De este modo,
  una notificación temporal libera su animación y sus órdenes obsoletas antes
  de recuperar la solicitud válida de menor prioridad.
- La resincronización tras volver de `unavailable` contiene los fallos
  transitorios del servicio de luz y usa intentos acotados con espera
  progresiva. Cada intento conserva sólo la intención vigente; reemplazarla o
  cancelarla descarta trabajo obsoleto y los fallos quedan diagnosticados sin
  excepciones de tareas no recuperadas.
- Un fallo de envío mientras ZHA conserva la entidad como `on` u `off` agenda
  una recuperación automática de fondo, sin depender de un evento
  `unavailable`. La caché de deduplicación se invalida tras cada fallo y sólo
  la ganadora vigente puede reintentarse; cancelaciones, vencimientos, cambios
  de prioridad y descargas eliminan inmediatamente el trabajo anterior.

### Validación automatizada

- Ruff y la matriz pytest completaron 93 pruebas en Home Assistant `2026.11.0`
  y `2026.11.2`, con cobertura total de ramas igual o superior al `80 %`.
- Hassfest y HACS/Marketplace Action superaron la validación del PR #1.

### Validación física

- El propietario validó `f283d36` en HAOS con ZHA, un coordinador Sonoff
  Dongle-P MG24 Plus y un GLEDOPTO GL-C-007P instalado manualmente. Se aprobaron
  F-01, F-03 a F-10, R-01, R-02, cancelación durante recuperación y R-03.
  F-08 cubrió completamente interpolación y los estados inválidos `unknown` y
  `unavailable`; ambos liberaron la regla sin convertirse en cero.
- La recarga de R-04 detuvo una animación activa y recuperó la solicitud
  persistente sin trabajo tardío. R-05 aprobó una carga mixta de 20 cambios
  numéricos con avisos `pulse` P95 y `blink` P98, recuperación del control
  numérico y estado final correcto; no fue estrés extremo multidispositivo.
- Se repitieron satisfactoriamente los dos fallos encontrados durante la
  validación: la excepción Zigbee sin manejar corregida en `cf57d64` y la falta
  de recuperación con estado ZHA obsoleto corregida en `f283d36`. Los fallos de
  comunicación aún producen advertencias controladas y útiles en el registro.

### Pendiente antes de publicar

- Completar F-02, la eliminación de entrada de R-04, estrés extremo
  multidispositivo, R-06, Alexa/Matter y diversidad de controladores; registrar
  firmware y fecha que siguen pendientes.
- Recibir aprobación explícita antes de fusionar, etiquetar, crear la
  pre-release o enviar la integración al catálogo Marketplace.

[0.1.0-alpha.1]: https://github.com/abel-smart-home/smart-led-manager/compare/a04e925b9fea426464742644943fd79bb4ed9550...163ff8f274d6894ab239ef74ef5ba6a8b545c77a
[0.1.0-alpha.2]: https://github.com/abel-smart-home/smart-led-manager/compare/163ff8f274d6894ab239ef74ef5ba6a8b545c77a...a14d9afb465c698c0354d18892ecac3537d5f6b4
[0.1.0-alpha.3]: https://github.com/abel-smart-home/smart-led-manager/compare/a14d9afb465c698c0354d18892ecac3537d5f6b4...fa9ecd650485e27ee1f1f22654972a1c47379c17
