# Auditoría de proyectos comunitarios

## Estado del documento

- Proyecto: Smart LED Manager.
- Versión objetivo: `v0.1.0-alpha.1`.
- Fecha de auditoría: 20 de noviembre de 2026.
- Alcance: repositorios y blueprints públicos relacionados con prioridades,
  notificaciones luminosas, animaciones, restauración, control manual e
  iluminación adaptativa para Home Assistant.

Esta auditoría es una revisión documental y de código fuente público. Se
comprobaron los repositorios, metadatos de GitHub, archivos de licencia,
estructura, pruebas, flujos de GitHub Actions, releases e issues relevantes.
No se ejecutaron pruebas físicas con luces ni se validó el comportamiento en
una instalación real de Home Assistant.

Los datos de actividad, estrellas, issues y CI son una fotografía de la fecha
indicada y pueden cambiar después.

## Decisión de procedencia para alpha.1

**Smart LED Manager `v0.1.0-alpha.1` no copia, adapta, incorpora ni distribuye
código procedente de los proyectos auditados.**

Las referencias siguientes se utilizaron únicamente para:

- identificar patrones arquitectónicos útiles;
- conocer fallos ya encontrados por otros proyectos;
- convertir casos reales en requisitos y criterios de aceptación;
- evitar restauraciones ciegas, saturación de redes malladas y atribuciones
  incorrectas de control manual.

El motor, modelos, algoritmos y adaptadores de Smart LED Manager se desarrollan
como implementación propia. Si en el futuro se incorpora código de terceros,
la decisión deberá documentarse antes de fusionarlo y se actualizará
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

## Resumen ejecutivo

Los cinco proyectos requeridos existen, son públicos y no estaban archivados
en la fecha de revisión:

- **Layers** es la referencia más cercana para un motor central por dispositivo,
  con capas vivas, persistencia, vencimientos y políticas de control manual.
- **Adaptive Lighting** es la referencia más madura para capacidades reales de
  luces, tolerancias, grupos, control manual y efectos del tráfico periódico.
- **Color Notify** aporta patrones útiles para animaciones y serialización de
  trabajo por luz.
- **Accent & Signal Light** aporta un wrapper virtual sencillo y servicios de
  entidad, pero confirma los riesgos de permitir acceso directo a la luz física.
- **Signal Lights** aporta una separación clara entre motor, almacenamiento,
  interfaz y pruebas dentro de Home Assistant.

Ninguna implementación se adopta completa. Las decisiones que sí se trasladan
como requisitos propios son: núcleo puro y testeable, resolución individual por
destino, base viva en vez de snapshots, desempate explícito, contextos propios,
cancelación, persistencia de deuda, deduplicación, límites de tráfico y pruebas
de reconexión/control manual.

## 1. Color Notify

- Repositorio: <https://github.com/cobryan05/ha-color-notify>
- Licencia: [Apache License 2.0](https://github.com/cobryan05/ha-color-notify/blob/main/LICENSE).
- Estado observado: público, no archivado; último push el 24 de octubre de
  2026; release estable [`0.2.6`](https://github.com/cobryan05/ha-color-notify/releases/tag/0.2.6);
  22 estrellas y 0 issues abiertas en la fecha de auditoría.

### Arquitectura observada

- Envuelve una entidad física en una entidad `light` virtual.
- Representa las notificaciones como entidades `switch`.
- Agrupa notificaciones en pools y permite suscripciones por luz.
- Mantiene prioridades, presentación temporal de una solicitud inferior
  ("peek") y rotación de solicitudes empatadas.
- Serializa mutaciones mediante `asyncio.Queue`.
- Incluye un lenguaje de secuencias con colores, pausas, transiciones y bucles.
- Usa `RestoreEntity` para el estado visible del wrapper.

Código revisado:

- [entidad y cola de luz](https://github.com/cobryan05/ha-color-notify/blob/main/custom_components/color_notify/light.py)
- [planificador de secuencias](https://github.com/cobryan05/ha-color-notify/blob/main/custom_components/color_notify/utils/light_sequence.py)
- [config flow](https://github.com/cobryan05/ha-color-notify/blob/main/custom_components/color_notify/config_flow.py)

### Pruebas y validación

El repositorio incluye pruebas de la entidad, secuencias, preview, swatches y
registro de eventos. El flujo de pruebas instala `pytest` y `pytest-asyncio`.
Las pruebas sustituyen módulos de Home Assistant por `MagicMock`; por tanto,
comprueban unidades concretas pero no el ciclo de vida real dentro de HA.

- [directorio de pruebas](https://github.com/cobryan05/ha-color-notify/tree/main/tests)
- [workflow de pytest](https://github.com/cobryan05/ha-color-notify/blob/main/.github/workflows/tests.yaml)
- [último pytest observado como correcto](https://github.com/cobryan05/ha-color-notify/actions/runs/40054238751)
- [validación programada correcta del 15 de noviembre](https://github.com/cobryan05/ha-color-notify/actions/runs/43682138016)

### Riesgos y limitaciones

- El README advierte que controlar directamente la luz física genera conflictos.
- Un cambio inesperado de la luz subyacente reinicia trabajo, pero no constituye
  una política completa de base/manual override.
- No se encontró rate limiting global o por dispositivo; una secuencia con
  pausas muy cortas puede producir tráfico excesivo.
- La deduplicación observada se limita principalmente al último color enviado.
- La entidad de luz concentra cola, prioridades, animación y control físico, lo
  que no conviene trasladar a un motor multiobjetivo.

### Recomendación

Usar como referencia conceptual la cola serializada, la cancelación de
animaciones y la validación de secuencias. Implementar de forma propia un
planificador separado del motor y del adaptador físico. No copiar código.

## 2. Signal Lights

- Repositorio: <https://github.com/prestomation/ha-signal-lights>
- Licencia: [MIT](https://github.com/prestomation/ha-signal-lights/blob/main/LICENSE),
  copyright 2026 Preston Tamkin.
- Estado observado: público, no archivado; último push el 14 de noviembre de
  2026; release estable [`v1.3.2`](https://github.com/prestomation/ha-signal-lights/releases/tag/v1.3.2);
  6 estrellas y 0 issues abiertas en la fecha de auditoría.

### Arquitectura observada

- Motor Python sin dependencias de Home Assistant para elegir una señal por luz.
- `DataUpdateCoordinator` para listeners de plantillas, vencimientos y estado.
- `Store` basado en almacenamiento oficial de Home Assistant.
- Señales de evento y de condición, filtros por luz y orden de prioridad.
- Config flow, options flow, servicios, sensores de diagnóstico, WebSocket y
  tarjeta Lovelace.
- Listener reactivo de plantillas con sondeo de 30 segundos como respaldo.

Código revisado:

- [diseño](https://github.com/prestomation/ha-signal-lights/blob/main/DESIGN.md)
- [motor puro](https://github.com/prestomation/ha-signal-lights/blob/main/custom_components/signal_lights/engine.py)
- [coordinador](https://github.com/prestomation/ha-signal-lights/blob/main/custom_components/signal_lights/coordinator.py)
- [almacenamiento](https://github.com/prestomation/ha-signal-lights/blob/main/custom_components/signal_lights/store.py)

### Pruebas y validación

El proyecto incluye pruebas de unidad, cobertura, frontend JavaScript y una
instancia real de Home Assistant estable en Docker. También revisa logs para
detectar llamadas bloqueantes, warnings y errores propios de la integración.
En el último push observado fueron correctos pytest, JavaScript, lint, HACS y
las pruebas integrales.

- [directorio de pruebas](https://github.com/prestomation/ha-signal-lights/tree/main/tests)
- [workflow de cobertura](https://github.com/prestomation/ha-signal-lights/blob/main/.github/workflows/pytest_coverage.yml)
- [workflow integral](https://github.com/prestomation/ha-signal-lights/blob/main/.github/workflows/integration.yml)
- [ejecución integral correcta del 14 de noviembre](https://github.com/prestomation/ha-signal-lights/actions/runs/43631530472)

### Riesgos y limitaciones

- Si no hay señal activa, el motor solicita apagar la luz; no mantiene una capa
  base viva.
- La plantilla generada para un umbral numérico usa `float(0)`. Un estado
  `unknown` o `unavailable` puede convertirse en cero y activar erróneamente
  una condición `below`.
- Los comandos de luz se envían con `blocking=False` y no se verifican contra
  el estado alcanzado.
- No se observó rate limiting, backoff o deduplicación de comandos por luz.
- El ciclo opcional recorre señales activas; Smart LED Manager solo debe rotar
  solicitudes cuando la política de empate lo autorice.

### Recomendación

Tomar como referencia la separación motor/adaptador/Store y sus pruebas Docker.
No adoptar la política de apagar al vaciar la cola ni su conversión numérica.
No copiar código.

## 3. Accent & Signal Light

- Repositorio: <https://github.com/arkane-systems/ha-accent-signal-light>
- Licencia: [MIT](https://github.com/arkane-systems/ha-accent-signal-light/blob/master/LICENSE),
  copyright 2026 Arkane Systems.
- Estado observado: público, no archivado; último push el 6 de noviembre de
  2026; release estable [`0.3.1`](https://github.com/arkane-systems/ha-accent-signal-light/releases/tag/0.3.1);
  5 estrellas y una issue abierta.

### Arquitectura observada

- Una entrada de configuración envuelve una luz física o grupo.
- Modelo de tres capas: señales, acentos y base.
- Señales y acentos son colas ordenadas por prioridad; la base se expone como
  entidad `light` virtual.
- Sensores muestran señal activa, acento activo y tamaños de cola.
- Los cuatro servicios se registran como servicios de entidad.
- El coordinador reenvía capacidades de la luz física y reaplica el estado
  deseado cuando la entidad vuelve a estar disponible.
- Solo la base usa restauración; señales y acentos no se persisten.

Código revisado:

- [coordinador](https://github.com/arkane-systems/ha-accent-signal-light/blob/master/custom_components/signal_light/coordinator.py)
- [entidad de luz](https://github.com/arkane-systems/ha-accent-signal-light/blob/master/custom_components/signal_light/light.py)
- [flujo de eventos](https://github.com/arkane-systems/ha-accent-signal-light/blob/master/docs/event-flow.md)

### Pruebas y validación

Incluye pruebas de config flow, coordinador, setup/unload, luz y sensores con
`pytest-homeassistant-custom-component` y Home Assistant 2026.2.3. El 6 de
noviembre fueron correctos pytest, Hassfest y validación.

- [directorio de pruebas](https://github.com/arkane-systems/ha-accent-signal-light/tree/master/tests)
- [workflow de pruebas](https://github.com/arkane-systems/ha-accent-signal-light/blob/master/.github/workflows/test.yml)
- [ejecución correcta](https://github.com/arkane-systems/ha-accent-signal-light/actions/runs/42169966121)

### Riesgos y limitaciones

- No hay TTL, persistencia de señales/acento, animador ni rate limiting.
- Reemplazar una entrada la elimina y la agrega de nuevo; en empates, el orden
  estable de la lista puede cambiar, por lo que no es una política de desempate
  explícita.
- La arquitectura actual es una instancia por una luz/grupo y no resuelve un
  conjunto global de destinos.
- La [issue #13](https://github.com/arkane-systems/ha-accent-signal-light/issues/13)
  confirma que controlar la entidad física deja la base virtual desincronizada,
  y propone varias luces por instancia y ocultar entidades subyacentes.

### Recomendación

Usar como referencia la luz virtual, los servicios de entidad y el espejo de
capacidades. Diseñar el motor central y la resolución multiobjetivo de forma
independiente. No copiar código.

## 4. Layers

- Repositorio: <https://github.com/lukab-dev/ha-layers>
- Licencia: [MIT](https://github.com/lukab-dev/ha-layers/blob/main/LICENSE),
  copyright 2026 lukab-dev.
- Estado observado: público, no archivado; creado el 22 de septiembre de 2026;
  último push el 19 de noviembre de 2026; estable
  [`v0.2.0`](https://github.com/lukab-dev/ha-layers/releases/tag/v0.2.0) y
  prerelease activa [`v0.4.0b8`](https://github.com/lukab-dev/ha-layers/releases/tag/v0.4.0b8);
  42 estrellas.

### Arquitectura observada

- Núcleo de decisiones sin imports de Home Assistant (`logic/`).
- Un registro por luz con base y capas que contienen **comandos vivos**, no
  snapshots. Al retirar una capa se resuelve lo que la capa inferior pide ahora.
- Resolución determinista por prioridad y secuencia.
- Capas `set`, `adjust` y `follow`.
- TTL, políticas de expiración segura y opción de re-render explícito.
- Persistencia de capas, temporizadores, estado observado, comandos pendientes
  y divergencias.
- Contextos propios para distinguir comandos de la integración.
- Políticas de control manual: recuperar la luz, editar capa activa, conservar
  capas y reafirmar.
- Tombstones para impedir que una automatización insistente recupere de
  inmediato una luz tomada manualmente.
- Proyección por capacidades, tolerancias, verificación, retry/backoff y
  resincronización de dispositivos desconectados.
- Expansión de targets, diagnósticos, logbook y modo de observación sin aplicar.

Código y especificación revisados:

- [especificación](https://github.com/lukab-dev/ha-layers/blob/main/docs/SPEC.md)
- [modelos](https://github.com/lukab-dev/ha-layers/blob/main/custom_components/layers/logic/model.py)
- [resolución](https://github.com/lukab-dev/ha-layers/blob/main/custom_components/layers/logic/resolve.py)
- [políticas](https://github.com/lukab-dev/ha-layers/blob/main/custom_components/layers/logic/policy.py)
- [motor de Home Assistant](https://github.com/lukab-dev/ha-layers/blob/main/custom_components/layers/engine.py)

### Pruebas y validación

Separa pruebas del núcleo puro y pruebas dentro de Home Assistant. El núcleo se
ejecuta con Python 3.12 y 3.14; la integración se prueba contra la versión
seleccionada y contra HA 2026.7.0, mínimo declarado. El último CI de la beta
observada fue correcto.

- [pruebas de lógica](https://github.com/lukab-dev/ha-layers/tree/main/tests/logic)
- [pruebas de integración](https://github.com/lukab-dev/ha-layers/tree/main/tests/ha)
- [workflow](https://github.com/lukab-dev/ha-layers/blob/main/.github/workflows/tests.yml)
- [CI correcto de `v0.4.0b8`](https://github.com/lukab-dev/ha-layers/actions/runs/44530751875)

### Riesgos y problemas conocidos

El proyecto es joven y varias decisiones todavía están estabilizándose:

- [Issue #3](https://github.com/lukab-dev/ha-layers/issues/3): un cambio solo
  RGB/HS puede considerarse sincronizado y no enviarse.
- [Issue #2](https://github.com/lukab-dev/ha-layers/issues/2): expandir grupos
  a miembros individuales puede perder multicast Zigbee, elevar el tráfico y
  producir cambios no simultáneos.
- [Issue #1](https://github.com/lukab-dev/ha-layers/issues/1): la interacción
  entre control manual, tombstones y reaplicación de una capa puede resultar
  inesperada para el usuario.

### Recomendación

Es la principal referencia conceptual para Smart LED Manager: núcleo puro,
capas vivas, base actual, resolución por luz, contexto propio, persistencia de
trabajo pendiente y recuperación segura. Implementar una variante propia y más
acotada, con pruebas específicas para RGB/HS, grupos Zigbee y reactivación tras
control manual. No copiar código.

## 5. Adaptive Lighting

- Repositorio: <https://github.com/basnijholt/adaptive-lighting>
- Licencia: [Apache License 2.0](https://github.com/basnijholt/adaptive-lighting/blob/main/LICENSE).
- Estado observado: público, no archivado; último push el 19 de noviembre de
  2026; release estable [`v1.32.0`](https://github.com/basnijholt/adaptive-lighting/releases/tag/v1.32.0);
  3,591 estrellas.

### Arquitectura observada

- Cálculo solar y curvas de brillo/color separado de la capa Home Assistant.
- Config flow/options, perfiles y switches para adaptación, color y modo sueño.
- Detección de control manual mediante eventos de llamadas, contextos y cambios
  de estado.
- Proyección de comandos según `supported_color_modes` y features reales.
- Expansión configurable de grupos y administración selectiva por atributo.
- Intervalos, transiciones, tolerancias y opción para omitir comandos
  redundantes.
- Diagnósticos descargables y numerosos escenarios documentados.

Código revisado:

- [cálculo de luz y sol](https://github.com/basnijholt/adaptive-lighting/blob/main/custom_components/adaptive_lighting/color_and_brightness.py)
- [gestor e integración con luces](https://github.com/basnijholt/adaptive-lighting/blob/main/custom_components/adaptive_lighting/switch.py)
- [utilidades de adaptación](https://github.com/basnijholt/adaptive-lighting/blob/main/custom_components/adaptive_lighting/adaptation_utils.py)
- [documentación de control manual](https://github.com/basnijholt/adaptive-lighting/blob/main/docs/advanced/manual-control.md)

### Pruebas y validación

El repositorio tiene una matriz histórica amplia de Home Assistant y exige al
menos 89% de cobertura de líneas y 80% de ramas para versiones estables. Las
pruebas cubren configuración, adaptación, color/brillo, diagnósticos, setup y
switches. La issue #1659 informa que, después de los cambios propuestos para el
nuevo arnés, 508 pruebas pasan en HA 2026.11.1; ese cambio aún no formaba parte
del estado auditado.

- [directorio de pruebas](https://github.com/basnijholt/adaptive-lighting/tree/main/tests)
- [workflow de pytest](https://github.com/basnijholt/adaptive-lighting/blob/main/.github/workflows/pytest.yaml)

El [Hassfest programado del 20 de noviembre](https://github.com/basnijholt/adaptive-lighting/actions/runs/44674505941)
falló porque `ulid-transform` ya es una dependencia de Home Assistant y
Hassfest impide declararla en el manifest de una integración personalizada.
Este fallo es relevante para compatibilidad/Marketplace y no debe ocultarse.

### Riesgos y problemas conocidos

- [Issue #1659](https://github.com/basnijholt/adaptive-lighting/issues/1659):
  el arnés de pruebas del estado auditado no podía ejecutarse todavía contra HA
  2026.11.
- [Issue #1658](https://github.com/basnijholt/adaptive-lighting/issues/1658):
  el interceptor ignoraba `exclude` al resolver targets y podía encender luces
  excluidas.
- [Issue #1655](https://github.com/basnijholt/adaptive-lighting/issues/1655):
  carrera entre adaptación inicial e intervalo que marca falsamente control
  manual.
- [Issue #1654](https://github.com/basnijholt/adaptive-lighting/issues/1654):
  un cambio de opciones puede volver a encender una luz cuyo apagado sigue en
  tránsito.
- [Issue #1652](https://github.com/basnijholt/adaptive-lighting/issues/1652):
  comparaciones RGB podían fallar por lista/tupla o conversión de color y
  reenviar comandos cada intervalo.
- Su documentación advierte que un volumen alto de comandos agrava redes
  Zigbee débiles y recomienda grupos Zigbee reales cuando las luces siempre se
  controlan juntas.

### Recomendación

Estudiar su matemática, detección de capacidades, tolerancias, grupos y fallos
de atribución manual. Smart LED Manager no debe interceptar ni reescribir
servicios globales: debe identificar únicamente sus propios contextos y
observar cambios de las luces autorizadas. No copiar código.

## 6. Blueprints comunitarios

### Temperature-based light color

- Repositorio: <https://github.com/tobus3000/hass-temperature-based-light-color-blueprint>
- Hilo: <https://community.home-assistant.io/t/temperature-based-light-color/1027511>
- Licencia: [MIT](https://github.com/tobus3000/hass-temperature-based-light-color-blueprint/blob/main/LICENSE),
  copyright 2026 tobus3000.
- Estado observado: creado el 19 de septiembre de 2026; último push el 5 de
  octubre de 2026; no archivado.

Implementa interpolación por tramos entre tres referencias RGB o Kelvin,
clamping, variación mínima, actualización opcional solo de luces encendidas y
sincronización al encender una luz o iniciar HA. Usa `is_number` antes de la
conversión y rechaza efectivamente `unknown`/`unavailable`.

Recomendación: usarlo como especificación funcional, pero implementar un
algoritmo propio genérico para N puntos, con unidades de medida, histéresis,
variación mínima y rate limiting. No copiar código.

### Light Blink Pro

- Repositorio: <https://github.com/ccpk1/HA-Blueprints>
- Hilo: <https://community.home-assistant.io/t/light-blink-pro-state-restoration-stuck-color-light-recovery-and-programmatic-control/948771>
- Estado observado: último push el 8 de octubre de 2026.
- Licencia: no se encontró archivo `LICENSE` ni licencia declarada.

Guarda estados mediante escenas temporales, ejecuta alternancia de colores,
reintenta restauraciones y aplica un fallback a luces que quedan atascadas.
Demuestra que la latencia y el reporte tardío son problemas reales. No debe
copiarse: carece de licencia explícita y la restauración por snapshot puede
quedar obsoleta cuando existen solicitudes simultáneas.

### Flash lights y flashing_lights.yaml

- Hilo: <https://community.home-assistant.io/t/script-blueprint-to-flash-a-custom-color-light-a-x-amount-of-times-and-restore-its-previous-state/496217>
- Original: <https://github.com/myGithub-Markus/home-assistant_blueprints/blob/main/flashing_lights.yaml>
- Licencia: no se encontró licencia explícita en el repositorio original.
- Estado observado: el último push de código del repositorio fue el 9 de abril
  de 2022.

El hilo documenta importaciones rotas, restauraciones incorrectas y soluciones
mediante pausas adicionales. Se conserva como evidencia contra snapshots y
restauración ciega; no se reutiliza código.

### Custom Blinking Lights

- Hilo: <https://community.home-assistant.io/t/custom-blinking-lights-blueprint/796494>
- Licencia: no se encontró una licencia de código verificable.

El hilo reconoce problemas para recuperar luces que estaban apagadas y casos
en que conservan el color de la animación al encenderse después. Se usa como
caso de prueba negativo; no se reutiliza código.

### Blueprints de Adaptive Lighting

- Directorio: <https://github.com/basnijholt/adaptive-lighting/tree/main/blueprints/automation>
- Licencia: Apache-2.0, como el repositorio.

Se revisaron los blueprints de modo sueño, brillo mínimo, control manual al
mínimo, perfil por horario y límite por luz diurna. Están probados mediante el
motor de automatizaciones de Home Assistant. Se usarán como escenarios de
aceptación para horarios/control manual, no como fuente de código.

## 7. Conclusiones de diseño para Smart LED Manager

La auditoría produce los siguientes criterios obligatorios:

1. El núcleo de prioridades no debe importar Home Assistant.
2. Cada luz se resuelve por separado; una regla global se expande y deduplica
   antes de emitir comandos.
3. Las solicitudes inferiores permanecen vivas y actualizadas.
4. La base es un comando vivo, no una escena capturada.
5. Prioridad, secuencia y política configurable forman un desempate explícito.
6. `unknown` y `unavailable` nunca son números.
7. Las animaciones son tareas cancelables administradas por un solo
   planificador por destino.
8. El contexto identifica los comandos propios; no se interceptan servicios
   globales ni se emplean monkey patches.
9. Deduplicación, rate limiting, tolerancias y grupos reales deben evitar
   saturación Zigbee.
10. Un dispositivo desconectado conserva el estado deseado, pero una
    notificación vencida no se reproduce al reconectar.
11. Las pruebas deben cubrir Home Assistant real/simulado, no solo módulos
    sustituidos por mocks.
12. La restauración manual, TTL interrumpido, apagados en tránsito y atributos
    RGB/HS requieren pruebas de carrera específicas.

## 8. Matriz de licencias

| Fuente | Licencia observada | Uso en alpha.1 |
|---|---|---|
| Color Notify | Apache-2.0 | Investigación; sin código copiado |
| Signal Lights | MIT | Investigación; sin código copiado |
| Accent & Signal Light | MIT | Investigación; sin código copiado |
| Layers | MIT | Investigación; sin código copiado |
| Adaptive Lighting | Apache-2.0 | Investigación; sin código copiado |
| Temperature-based light color | MIT | Investigación; sin código copiado |
| Light Blink Pro | Sin licencia explícita | No reutilizar |
| Blueprints de Markus/fragmentos del foro | Sin licencia explícita verificable | No reutilizar |

La ausencia de código incorporado significa que `alpha.1` no requiere avisos
de copyright de estos proyectos. Las obligaciones futuras se mantienen en
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).
