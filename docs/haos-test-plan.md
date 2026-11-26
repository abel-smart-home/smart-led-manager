# Plan de validación física en HAOS

Este plan debe ejecutarlo el propietario sobre su instalación y hardware. Las
pruebas unitarias, los mocks y la simulación de estados no constituyen evidencia
de HAOS, Zigbee, GLEDOPTO, Alexa o Matter Hub.

## Registro de ejecución

| Campo | Valor |
|---|---|
| Fecha/hora | Pendiente |
| Zona horaria | `America/Tijuana` |
| Commit y versión | `f283d36a4a11834fa812043697a0dead33de3110`, `0.1.0-alpha.1` |
| Home Assistant Core | `2026.11.2` |
| Home Assistant OS | `18.5` |
| Supervisor | `2026.11.0` |
| Python | `3.14.10` |
| Hardware y plataforma | Raspberry Pi 5; `aarch64` |
| Tipo de instalación | Home Assistant OS |
| Estado del sistema | `healthy`; `supported` |
| Instalación de Smart LED Manager | Manual en `/config/custom_components/smart_led_manager/` |
| Coordinador Zigbee y firmware | Sonoff Dongle-P MG24 Plus; firmware pendiente |
| Modelos/firmware de controladores LED | GLEDOPTO GL-C-007P; firmware pendiente |
| Integraciones de luz | ZHA; `light.gledopto_gl_c_007p` |
| Home-Assistant-Matter-Hub | Instalado, versión `2.0.60`; validación funcional pendiente |
| Ejecutor | Propietario |
| Resultado general | **Validación física parcial completada — casos aprobados y pendientes detallados abajo** |

No cambies el resultado a “aprobado” sin conservar observaciones y evidencia
por caso. Realiza una copia de seguridad y evita probar parpadeos con personas
fotosensibles presentes.

## Preparación

1. Instala el commit candidato en una instancia de prueba de HAOS.
2. Configura al menos dos tiras, preferiblemente una GLEDOPTO RGB+CCT y otra con
   capacidades distintas, en habitaciones diferentes.
3. Verifica primero encendido, apagado, brillo y color desde la integración
   física de cada entidad.
4. Autoriza sólo esas entidades en Smart LED Manager y deja otra luz sin
   autorizar como control negativo.
5. Registra estados, capacidades y latencia aproximada de referencia.

## Casos funcionales

| ID | Procedimiento | Resultado esperado | Resultado/observaciones |
|---|---|---|---|
| F-01 | Intenta una acción sobre la luz no autorizada. | Se rechaza toda la llamada; ninguna luz cambia. | **Aprobada.** `light.sonoff_100268aa47_1` no estaba autorizada y la integración rechazó la solicitud con `These lights are not authorized for Smart LED Manager: light.sonoff_100268aa47_1`. |
| F-02 | Activa P40 azul en dos tiras y P60 verde sólo en una. | Una queda verde y la otra azul. | Pendiente |
| F-03 | Actualiza P40 a rojo mientras P60 gana; cancela P60. | No hay cambio durante P60; después aparece rojo. | **Aprobada, 6/6.** Azul P70 quedó enmascarado por verde P90; se actualizó a rojo y, al cancelar P90, apareció el rojo actualizado. No reapareció el azul ni hubo errores. |
| F-04 | Prueba empates con `newest`, `oldest` y `lexical`. | Resultado determinista según la política. | **Aprobada.** `newest` 6/6, `oldest` 6/6 y `lexical` 7/7. Cada cancelación recuperó la solicitud correcta; en `lexical` ganó `a_prueba_f04_azul` sobre `z_prueba_f04_rojo`. Se restauró `newest`; sin errores. |
| F-05 | Envía `notify` P70 y una alarma de prueba P100. | Gana P100; después se reevalúa el aviso sólo si sigue vigente. | **Aprobada, 7/7.** Secuencia física: azul P60 → naranja P70 → violeta P100 → naranja P70 → azul P60. La alerta venció a los 8 s y el aviso a los 30 s; no quedaron solicitudes temporales obsoletas ni hubo excepciones. |
| F-06 | Ejecuta `blink` y `pulse`, después reemplaza/cancela. | La tarea anterior se detiene sin cuadros tardíos. | **Aprobada en el escenario ejecutado, 8/8.** Un `pulse` violeta P90 se canceló durante su ejecución y regresó azul fijo P60; no reapareció durante 30 s. `blink` también funcionó durante notificaciones y recarga. Sin excepciones. |
| F-07 | Crea regla de estado y cambia la fuente. | Activa/libera sin sondeo perceptible. | **Aprobada, 7/7.** Una regla temporal sobre `input_boolean` activó naranja y, al desactivarse, devolvió el color de la regla de temperatura. Se repitió la secuencia y se eliminaron regla y ayudante; sin errores. |
| F-08 | Recorre una regla numérica y después usa `unknown`/`unavailable`. | Colores correctos; valores inválidos nunca se vuelven cero. | **Completamente aprobada.** Interpolación y `unavailable`: 9/9; la tabla `20:0,0,255;25:0,255,0;30:255,0,0` produjo azul, verde, rojo y un intermedio a 27.5 °C, y `unavailable` liberó la regla antes de reactivarse con un valor válido. Variante `unknown`: 7/7 con `f283d36`; valor 25 mostró magenta, `unknown` liberó la regla y devolvió el control habitual sin interpretarse como cero, y valor 26 recuperó el magenta. Regla y ayudante se eliminaron sin errores. |
| F-09 | Apaga una tira y prueba `allow_turn_on` falso/verdadero. | Sólo la solicitud autorizada puede encenderla. | **Aprobada, 6/6.** Rojo P100 con `allow_turn_on: false` permaneció apagado 10 s; al actualizar la misma solicitud con `true`, se encendió rojo. Cancelación y retorno habitual correctos; sin errores. |
| F-10 | Cambia manualmente la luz con `service_only`. | No se crea una solicitud externa implícita. | **Aprobada, 7/7.** Con la política **Only explicit manual action**, un cambio directo a rojo fue reafirmado automáticamente al azul P100 vigente y permaneció azul tras 15 s. Cancelación correcta; sin errores. |

## Desconexión, carga y recuperación

| ID | Procedimiento | Resultado esperado | Resultado/observaciones |
|---|---|---|---|
| R-01 | Activa azul persistente P95; desconecta la alimentación; mantén el estado ZHA en `on`/`off`; actualiza el mismo `request_id` a rojo y reconecta sin provocar un evento `unavailable`. | El fallo conserva la intención, invalida la caché y agenda recuperación acotada. Al responder de nuevo se aplica automáticamente el rojo vigente, sin acción adicional, comandos obsoletos ni tareas huérfanas. | **Aprobada con `f283d36`, 8/8.** El envío rojo inicial falló con el GLEDOPTO desconectado y ZHA aún disponible. Al recuperar alimentación se reintentó automáticamente y terminó rojo, sin reinicio, acción adicional ni excepciones sin manejar. Se observaron advertencias controladas de intento y espera Zigbee. |
| R-02 | Desconecta durante un aviso corto y reconecta tras su vencimiento. | El aviso obsoleto no se reproduce; cuando el dispositivo responda se aplica sólo la ganadora vigente. Los fallos transitorios se contienen y los intentos terminan de forma acotada, sin duplicar animaciones. | **Aprobada con `f283d36`, 7/7.** El aviso naranja venció desconectado; al reconectar se recuperó automáticamente el azul persistente y nunca reapareció el naranja. No hubo acciones adicionales ni excepciones sin manejar; sí advertencias controladas por fallos Zigbee. |
| R-02-C | Cancela una solicitud durante la recuperación Zigbee y reconecta. | La solicitud cancelada no se reproduce; se aplica la ganadora vigente. | **Aprobada, 7/7.** Rojo P100 se canceló tras fallar desconectado; al reconectar regresó azul P80 y el rojo nunca apareció. Sin excepciones sin manejar. |
| R-03 | Reinicia Home Assistant Core con solicitudes persistente y temporal. | Se recupera sólo lo válido; no hay temporizadores duplicados. | **Aprobada con `f283d36`, 7/7, para reinicio de Core.** Violeta persistente P95 sobrevivió; verde P70 quedó en espera y apareció al cancelar violeta. Limpieza correcta y sin errores. No se reinició todo HAOS. |
| R-04 | Recarga y después elimina la entrada. | No quedan listeners, animaciones u órdenes tardías. | **Recarga aprobada en el alcance físico ejecutado, 8/8.** `homeassistant.reload_config_entry` detuvo `blink` naranja, recuperó azul persistente y no reapareció la animación en 30 s. La eliminación no se ejecutó entonces en la Raspberry Pi; posteriormente M-16 la aprobó en laboratorio HAOS para alpha.2. |
| R-05 | Genera cambios rápidos de sensor y varias animaciones. | Deduplicación/rate limit evitan tormenta y HA sigue estable. | **Carga mixta aprobada con `f283d36`, 9/9.** Se ejecutaron 20 cambios sucesivos de un sensor numérico, una notificación `pulse` P95 y su interrupción por `blink` P98. Al finalizar los avisos se recuperó el control numérico y el estado final fue verde, correspondiente al último valor 25. No hubo colores atrasados, excepciones ni errores inesperados; los elementos temporales se eliminaron correctamente. No fue una prueba de estrés extremo con múltiples dispositivos. |
| R-06 | Usa grupos Zigbee si están disponibles y observa multicast/unicast. | Sin duplicados inesperados; registrar comportamiento real. | Pendiente |

### Cobertura automatizada complementaria de R-04

- `async_unload_entry` cubre descarga exitosa, fallo al descargar plataformas y
  retirada del runtime sólo tras un cierre correcto.
- `async_shutdown` cubre la cancelación y espera de recuperación, expiración,
  animación y controlador, además de liberar listeners de luces, listeners de
  reglas y evaluaciones diferidas.
- Una prueba de integración descarga con `blink` activo y verifica que no haya
  cuadros tardíos, comandos pendientes ni tareas de recuperación restantes.
- `async_remove_entry` y `SmartLEDStorage` cubren eliminación del Store; una
  instancia nueva con la misma clave carga una lista vacía y no recupera
  solicitudes antiguas.

Esta cobertura automatizada no sustituyó en su momento la eliminación de la
entrada. M-16 añadió después una eliminación completa en laboratorio HAOS para
alpha.2, sin convertirla retroactivamente en una prueba Raspberry/Zigbee de
R-04 sobre alpha.1.

## Incidencias encontradas y corregidas

1. En versiones anteriores a `cf57d64` se observó `Task exception was never
   retrieved` junto con `HomeAssistantError: Failed to send request: device did
   not respond`. `cf57d64` contuvo esas excepciones y añadió recuperación
   controlada.
2. Con `cf57d64`, ZHA podía mantener `on`/`off` durante la desconexión: la
   intención roja quedaba retenida, pero no se reenviaba al reconectar.
   `f283d36` añadió recuperación de fondo sin depender sólo de
   `unavailable`.

Ambos escenarios se repitieron físicamente con `f283d36` y fueron
satisfactorios. Las advertencias controladas, por ejemplo un intento fallido
seguido de `retrying current intent in 5.00 seconds`, son diagnóstico esperado
de una comunicación Zigbee fallida y no deben ocultarse.

## Escenarios pendientes de alpha.1

- F-02: dos tiras independientes y resolución simultánea por destino.
- R-04: eliminación física en la Raspberry Pi del registro alpha.1; M-16 ya
  cubre la eliminación y limpieza de alpha.2 en laboratorio HAOS.
- Estrés extremo adicional con simultaneidad intensa, múltiples dispositivos y
  varias tiras; no forma parte de la carga mixta aprobada en R-05.
- R-06: grupos Zigbee y comportamiento multicast/unicast.
- Otros modelos GLEDOPTO y combinaciones RGB, RGBW y RGB+CCT.
- Firmware del coordinador, firmware del controlador y fecha/hora exacta de
  ejecución.

La validación específica de Alexa/Matter Hub se efectuó posteriormente con
alpha.2 y se registra abajo; no se atribuye retroactivamente a alpha.1.

## Registro independiente de `0.1.0-alpha.2`

Estos resultados fueron **reportados por el propietario** y reúnen dos capas de
evidencia: las pruebas físicas de noviembre de 2026 sobre Raspberry Pi,
ZHA/GLEDOPTO y pruebas posteriores de laboratorio en HAOS VirtualBox con luces
Demo. Codex no ejecutó las pruebas en HAOS. La fecha y hora exactas, el firmware
del coordinador y el firmware del GLEDOPTO no fueron proporcionados y
permanecen pendientes.

| Campo | Valor |
|---|---|
| Commit y versión | `8e21b28`, `0.1.0-alpha.2` |
| Home Assistant | Core `2026.11.2`; OS `18.5`; Supervisor `2026.11.0` |
| Python y hardware | `3.14.10`; Raspberry Pi 5 `aarch64` |
| Zona horaria | `America/Tijuana` |
| Zigbee | ZHA; Sonoff Dongle-P MG24 Plus; firmware pendiente |
| Controlador y entidad | GLEDOPTO GL-C-007P; firmware pendiente; `light.gledopto_gl_c_007p` |
| Catálogo probado | Zona Sala; modos Cine y Lectura |
| Matter | Home-Assistant-Matter-Hub `2.0.60` |
| Resultado general | **Validación consolidada: 16 casos completos, 3 parciales y 1 pendiente de hardware físico** |

### Entornos y alcance de la evidencia

| Capa | Entorno | Alcance |
|---|---|---|
| Hardware físico | Raspberry Pi 5, ZHA, Sonoff Dongle-P MG24 Plus y GLEDOPTO GL-C-007P | Evidencia física real de selección, prioridades, animaciones, recuperación Zigbee, reinicio de Core, traducción, clasificación y Alexa/Matter Hub descrita por caso. |
| Laboratorio HAOS | HAOS en VirtualBox; integración Demo; `light.office_rgbw_lights` RGBW y `light.living_room_rgbww_lights` RGBWW | Varias zonas, estados de diagnóstico, eliminación de entrada/Store, recuperación de solicitudes guardadas y actualización/reversión. No prueba dos controladores Zigbee reales. |
| Automatización | Pytest en la matriz de Home Assistant y validadores del PR | Regresiones de motor e integración, Hassfest y HACS/Marketplace. No sustituye ninguna comprobación visual o de hardware. |

Las 16 pruebas completas son el resultado **consolidado** de esas capas. No
representan 16 pruebas completas sobre Zigbee físico. Cuando la consolidación
no identifica por separado el entorno de una repetición reportada, el registro
no la atribuye a hardware adicional.

## Resultados consolidados M-01 a M-20

| ID | Estado | Evidencia reportada | Origen, alcance pendiente u observación |
|---|---|---|---|
| M-01 | **Completa** | Se repitió la activación del mismo modo fijo y de un modo animado `pulse`; ambos conservaron el comportamiento idempotente esperado. | Confirmación adicional del propietario; no se registra como una nueva prueba con dos dispositivos Zigbee. |
| M-02 | **Completa** | Cine y Lectura se sustituyeron de forma exclusiva; al activar uno el otro pasó a OFF y el selector reflejó la selección. | No se midió latencia; no se atribuye una medición inexistente. |
| M-03 | **Completa** | Cine P50 quedó seleccionado bajo una notificación roja P70; al vencer el aviso, Cine recuperó automáticamente el control físico. | — |
| M-04 | **Completa** | Cine se desactivó mientras P70 ganaba y no reapareció al terminar la notificación. | — |
| M-05 | **Completa** | La regla numérica P40 siguió procesando el sensor detrás de Cine P50 y, al liberar Cine, apareció el color del valor más reciente, no uno obsoleto. | La interfaz actual de puntos RGB es técnica y se propone mejorar en alpha.3. |
| M-06 | **Pendiente de hardware físico; simulación satisfactoria** | En HAOS VirtualBox, dos zonas sobre `light.office_rgbw_lights` y `light.living_room_rgbww_lights` funcionaron independientemente, conservaron prioridades y recuperaron solicitudes inferiores. | Las dos entidades procedían de Demo. Falta repetir con dos controladores Zigbee reales. |
| M-07 | **Completa** | Tras reiniciar Home Assistant Core, el modo seleccionado y su configuración se recuperaron sin reactivación manual. | No equivale a reiniciar todo HAOS. |
| M-08 | **Completa** | **Sin modo** desactivó la selección, sincronizó interruptores y liberó la intención sin ordenar un apagado físico forzado. También se repitió sin ninguna solicitud inferior activa y funcionó correctamente. | M-05 conserva además la evidencia de recuperación de una regla inferior. |
| M-09 | **Completa** | Se editó el color de Cine; tras guardar, recargar y reiniciar Core prevaleció la definición nueva y no reapareció el color anterior. | Guardar Options Flow recarga la entrada; no fue una edición en caliente sin interrupción. |
| M-10 | **Parcial** | Un modo temporal activo se eliminó y dejó de estar disponible para Smart LED Manager. | Home Assistant conservó una entidad residual en su registro y el propietario la eliminó manualmente. La integración no limpió automáticamente ese registro. |
| M-11 | **Completa** | Con el GLEDOPTO sin alimentación se alternó Cine/Lectura; al reconectar se aplicó únicamente el naranja de Lectura, que era la selección final. | Los fallos de comunicación durante la desconexión fueron esperados. |
| M-12 | **Completa** | Con ZHA aún mostrando `on`, Lectura se recuperó automáticamente al responder otra vez el controlador. | Sólo consta el primer fallo de 8 posibles intentos; no se afirma que se observaran los ocho. |
| M-13 | **Completa** | Alternancias rápidas mediante interruptores y selector dejaron como ganadora la última selección, con entidades sincronizadas y color correcto. | No fue estrés extremo ni multidispositivo. |
| M-14 | **Completa** | Con solicitudes P50 se verificaron `newest`, `oldest` y `lexical`; al cancelar la ganadora se recuperó el modo correcto. | La configuración habitual quedó en `newest`. |
| M-15 | **Parcial** | `light.luz_no_autorizada` fue rechazada y los selectores sólo ofrecieron la tira autorizada. Los dos registros WebSocket/script correspondían al mismo rechazo. | No se inyectaron datos alterados manualmente para intentar eludir la lista autorizada. |
| M-16 | **Completa en laboratorio** | Además de la recarga con `pulse`, se eliminó la entrada después de usar un modo animado. Desaparecieron la integración y sus entidades virtuales sin errores; `/config/.storage` no conservó archivos `smart_led_manager.*`. | Ejecutada en laboratorio HAOS. No se atribuye a la Raspberry Pi ni a hardware Zigbee físico. |
| M-17 | **Parcial** | `blink` rojo P70, `pulse` rojo y cancelación anticipada de un `pulse` de 60 s funcionaron; Cine recuperó el control sin órdenes rojas tardías. | No se repitió físicamente toda la batería alpha.1; el resto conserva su evidencia heredada y automatizada. |
| M-18 | **Completa en el alcance de diagnóstico** | En Raspberry Pi ya se habían observado `winner`, `masked` y `no_mode`. En VirtualBox, un modo P70 compartido entre dos luces Demo produjo `winner → partial → winner → no_mode`; durante `partial`, P90 controló Oficina mientras Sala conservó P70, y al cancelar P90 ambas recuperaron el modo. | Se confirmaron seis verificaciones. Los JSON originales de la ejecución VirtualBox no se adjuntaron y no se presenta como prueba física con dos Zigbee. |
| M-19 | **Completa en el alcance de recuperación probado** | En VirtualBox se añadieron al Store `smart_led_manager:mode:orphan_m19` y `lab_m19_unmanaged` sobre `light.kitchen_lights`. Tras reiniciar Core ambas desaparecieron; `lab_m20_oficina` permaneció y las luces siguieron operativas. | El registro confirmó el rechazo del objetivo no administrado. No se probó corrupción completa de la sintaxis JSON. |
| M-20 | **Completa en laboratorio** | Alpha.1 se configuró con una solicitud persistente P60 para Oficina y una regla numérica P40 para Sala. La actualización a alpha.2 aprobó siete comprobaciones y la reversión posterior del código a alpha.1, sin recrear la entrada, aprobó otras siete. | Conservó entrada, luces, solicitudes, regla y comportamiento anterior; la prueba fue HAOS VirtualBox, no hardware Zigbee físico. |

### Advertencia controlada de M-12

Durante la falta de respuesta se observó:

```text
Light command for light.gledopto_gl_c_007p failed on attempt 1/8: Failed to send request: device did not respond; retrying current intent in 5.00 seconds
```

La advertencia representa el primer fallo controlado y la espera progresiva de
la recuperación Zigbee. La tira terminó mostrando Lectura sin una nueva acción,
por lo que no se clasifica como defecto de recuperación.

### Rechazo controlado de M-15

La acción sobre `light.luz_no_autorizada` devolvió:

```text
These lights are not authorized for Smart LED Manager: light.luz_no_autorizada
```

Las entradas de registro de `homeassistant.components.websocket_api.http.connection`
y `homeassistant.helpers.script.websocket_api_script` reflejaron el mismo
rechazo deliberado; no fueron dos fallos independientes del motor.

### Recuperación controlada de M-19

Tras insertar en el almacenamiento de laboratorio una solicitud de modo
huérfana y otra dirigida a una luz no administrada, el reinicio de Core retiró
ambas sin afectar la solicitud válida. El registro mostró:

```text
Ignoring unauthorized or invalid stored request lab_m19_unmanaged: unmanaged targets: light.kitchen_lights
```

Esta evidencia cierra M-19 para la recuperación de solicitudes semánticamente
inválidas o no autorizadas. No demuestra recuperación frente a un archivo JSON
con sintaxis completamente corrupta, escenario que se conserva como prueba de
endurecimiento separada.

### Eliminación de definición frente al registro de entidades

M-10 confirmó que eliminar un modo retira su definición y su solicitud del
motor. Esto no equivale necesariamente a borrar de inmediato la entrada
persistente del Entity Registry de Home Assistant. La entidad residual quedó
marcada como no proporcionada y pudo eliminarse manualmente. Debe estudiarse en
un ciclo posterior si Smart LED Manager puede limpiar de forma selectiva las
entidades que realmente posee, sin eliminar registros indiscriminadamente ni
romper automatizaciones.

## Alexa y Matter Hub — validación alpha.2

La exposición fue **validada funcionalmente por el propietario** con
Home-Assistant-Matter-Hub `2.0.60`. Smart LED Manager creó interruptores para
Cine y Lectura; el propietario les asignó etiquetas en Home Assistant, Matter
Hub los expuso y Alexa permitió activar y desactivar ambos modos. La exclusividad
y la sincronización de estados en ambos sentidos fueron satisfactorias y no se
reportaron errores funcionales.

Smart LED Manager no se comunica directamente con Alexa ni con Matter Hub:
expone entidades `switch` y el puente presenta esas entidades al ecosistema
Matter. El estado del interruptor expresa **selección lógica del modo**, no una
confirmación física independiente del color.

Alexa recibió inicialmente nombres como **Smart LED Manager Cine**. El
propietario lo renombró manualmente a **Cine** para obtener órdenes naturales.
Queda propuesta para alpha.3 una estrategia de nombres o aliases breves que
pueda incluir la zona cuando existan duplicados, conservando los `unique_id` y
las automatizaciones existentes.

## Clasificación y traducciones — verificadas

Con el commit `8e21b28`, el propietario confirmó en HAOS `2026.11.2` que:

- Smart LED Manager aparece en **Ajustes > Dispositivos y servicios >
  Integraciones**, no solamente como Ayudante;
- el Options Flow aparece en español con el perfil **Español
  (Latinoamérica)** (`es-419`);
- la actualización conservó luces autorizadas, reglas y modos;
- no aparecieron errores nuevos.

No se realizó una comprobación independiente con el perfil `es`; sólo se
atribuye validación física a `es-419`.

## Pendientes consolidados de alpha.2

- M-06: repetir las dos zonas con dos controladores Zigbee físicos; la
  simulación RGBW/RGBWW mediante Demo ya fue satisfactoria.
- M-10: evaluar el ciclo de vida del Entity Registry tras eliminar modos.
- M-15: configuración alterada en un entorno seguro, sin manipular la
  instalación principal.
- M-17: no se repitió toda la matriz física heredada de alpha.1.
- Endurecimiento adicional: corrupción sintáctica completa de un archivo JSON;
  M-19 ya cubre solicitudes guardadas huérfanas y no autorizadas.
- Firmware del coordinador y del GLEDOPTO, y fecha/hora exacta de ejecución.
- Estrés extremo multidispositivo, grupos Zigbee/R-06 y otros controladores.

## Cierre

Adjunta este archivo actualizado o un informe equivalente al PR candidato,
incluyendo fallos y limitaciones. Un fallo de hardware/integración externa debe
distinguirse de un fallo del motor, pero no ocultarse. La autorización para
fusionar o publicar sigue siendo una decisión separada.

## `0.1.0-alpha.3`, Bloque A — resultado reportado

| Campo | Registro |
|---|---|
| Fecha del reporte | 23 de noviembre de 2026 |
| Entorno | HAOS VirtualBox |
| Versión | `0.1.0-alpha.3`, Bloque A |
| SHA | `fa9ecd650485e27ee1f1f22654972a1c47379c17` |
| Resultado | **8/8 aprobadas por reporte del propietario** |
| Evidencia | Resultados comunicados por el propietario; no se recibieron ni se atribuyen logs o métricas adicionales. |

| Caso | Alcance | Resultado reportado |
|---|---|---|
| A-01 | Migración alpha.2 → alpha.3 | Aprobada |
| A-02 | Organización de dispositivos | Aprobada |
| A-03 | Conservación de entidades | Aprobada |
| A-04 | Renombrar y asignar área | Aprobada |
| A-05 | Exposición de switches | Aprobada |
| A-06 | Eliminación selectiva | Aprobada |
| A-07 | Persistencia y reinicio | Aprobada |
| A-08 | Regresión de prioridades | Aprobada |

Este resultado cierra el plan VirtualBox del Bloque A, pero no convierte la
ejecución en prueba física Zigbee. Continúan pendientes la repetición en
Raspberry Pi 5/ZHA/GLEDOPTO, la comprobación física de nombres y control por
Alexa/Matter Hub, M-06 con dos controladores Zigbee reales y las demás pruebas
físicas parciales heredadas de alpha.2. Alpha.3 no está completamente validada
ni publicada.

## `0.1.0-alpha.3`, Bloque B — resultado reportado

| Campo | Registro |
|---|---|
| Fecha del reporte | 23 de noviembre de 2026 |
| Entorno | HAOS VirtualBox |
| SHA funcional | `f8b9fc9ec8dc0a31378bb50595d605a2c88a48fe` |
| Resultado | **B-01 a B-10, 10/10 aprobadas por reporte del propietario** |
| Evidencia | Resultados comunicados por el propietario; no se recibieron ni se atribuyen capturas, logs o métricas adicionales. |

### HAOS VirtualBox — administrador y editor de reglas

| Caso | Procedimiento | Resultado esperado | Estado |
|---|---|---|---|
| B-01 | Actualiza desde el Bloque A sin eliminar la entrada. Abre una regla de estado antigua. | Conserva `id`, valores, luces, zonas, modos, selectores, switches y solicitudes persistentes; la regla heredada aparece habilitada. | Aprobada (reporte) |
| B-02 | Edita nombre, origen, condición, prioridad, RGB y brillo de una regla de estado activa. | Tras guardar y recargar se aplica sólo la definición nueva; no aparece una intención anterior. | Aprobada (reporte) |
| B-03 | Edita origen, destino, prioridad, modo y límites de una regla numérica. | Conserva el mismo `id` y responde al origen nuevo, sin órdenes del origen anterior. | Aprobada (reporte) |
| B-04 | Agrega, edita y elimina puntos con el selector RGB; intenta duplicar un valor y dejar un solo punto. | Ordena automáticamente, muestra la unidad disponible y bloquea duplicados o menos de dos puntos. No exige cadenas RGB. | Aprobada (reporte) |
| B-05 | Abre el editor, cambia metadatos y puntos y elige **Descartar cambios**. | No cambia opciones ni envía órdenes físicas intermedias. | Aprobada (reporte) |
| B-06 | Duplica una regla, revisa su nombre e identificador y actívala después de ajustar prioridad/destino. | La original queda intacta; la copia usa `id` nuevo y comienza deshabilitada. | Aprobada (reporte) |
| B-07 | Mantén una regla inferior enmascarada por un modo superior; edita color, prioridad y destino, luego libera el modo. | No hay destello intermedio; aparece únicamente la intención editada vigente en el destino nuevo. | Aprobada (reporte) |
| B-08 | Cambia los destinos de Sala a Oficina; después deshabilita y elimina la regla activa. | Sala deja de recibir la regla, Oficina recibe la vigente y, al deshabilitar/eliminar, no hay recuperación tardía. | Aprobada (reporte) |
| B-09 | Reinicia Core con una regla habilitada, otra deshabilitada y un modo persistente. | Se reconstruyen sólo intenciones vigentes; no se duplican listeners, solicitudes, animaciones ni entidades. | Aprobada (reporte) |
| B-10 | Provoca una actualización numérica dentro del intervalo mínimo y guarda otra definición antes de la evaluación diferida. | La tarea del catálogo anterior termina durante la recarga y no reintroduce la solicitud obsoleta. | Aprobada (reporte) |

Comprueba también que una notificación temporal activa puede terminar durante
la recarga: es la política documentada, no una edición completamente en
caliente. Si se observa una orden después de descartar el flujo o una regla
vieja reaparece, registra el log y detén la prueba.

### Raspberry Pi 5, ZHA y GLEDOPTO — repetición física separada

1. Repite B-02, B-04, B-07 y B-08 sobre
   `light.gledopto_gl_c_007p`, registrando cada orden visible y cualquier
   advertencia ZHA.
2. Cambia entre Sala y Oficina sólo si ambas tienen controladores reales. No
   marques M-06 completo usando dos entidades Demo o un único controlador.
3. Durante una recarga confirma que no queda una animación anterior ni se
   reproduce una regla eliminada al reconectar el controlador.
4. Reinicia Core y confirma la regla habilitada vigente, la regla deshabilitada
   ausente y la selección de modo persistente.
5. Si se prueba Matter Hub/Alexa, registra por separado los nombres y acciones
   recibidos. La organización correcta en Home Assistant no demuestra por sí
   sola compatibilidad de voz.

No ejecutes eliminaciones sobre la instalación principal sin copia de
seguridad. Este 10/10 corresponde a HAOS VirtualBox y no sustituye la repetición
física Zigbee pendiente.

## Registro de `0.1.0-alpha.3`, Bloque B.1

Usa una copia de seguridad o una instancia aislada. Registra SHA completo,
fecha/hora, versión de Home Assistant, navegador, tamaño de pantalla y resultado
real. Las pruebas automatizadas no cuentan como ejecución visual HAOS.

### HAOS VirtualBox — panel gráfico avanzado

| Caso | Procedimiento | Resultado esperado | Estado |
|---|---|---|---|
| B1-01 | Actualiza la carpeta completa sin eliminar la entrada, reinicia Core e inicia sesión como administrador. | Smart LED Manager aparece en la barra lateral; `/smart-led-manager-editor` abre el panel sin YAML, CDN ni error de carga. Un usuario no administrador no puede acceder. | **Aprobada (reporte del propietario)**. El primer intento falló por `MappingProxyType`; se corrigió manualmente en `9ba3b0c` y se endureció después. |
| B1-02 | Abre una regla numérica creada en el Bloque B. | Aparecen el mismo nombre, `id`, origen, estado, unidad, modo y puntos; prioridad, destinos y brillo se muestran sin alterarse. | **Aprobada (reporte del propietario)** |
| B1-03 | Revisa una curva con intervalos desiguales, negativos y decimales en tema claro y oscuro, escritorio y móvil. | Barra, eje, marcas y etiquetas respetan posiciones reales; los datos siguen legibles y utilizables con teclado y tacto. | **Aprobada (reporte del propietario)** |
| B1-04 | Agrega un punto, cambia valor/color, selecciona desde barra y gráfica, elimina otro y prueba duplicado/NaN/menos de dos. | Ordena automáticamente; RGB/hex y muestra coinciden; validación impide guardar datos inválidos sin perder el borrador. | **Aprobada (reporte del propietario)** |
| B1-05 | Simula valores exactos, intermedios y fuera de extremos en `interpolate` y `ranges`. | Color, RGB/hex y punto/intervalo coinciden con la regla; no se envían órdenes `light.*` ni cambia la tira. | **Aprobada en HAOS VirtualBox (reporte); repetición física pendiente** |
| B1-06 | Modifica puntos y usa **Restaurar borrador**; repite y usa **Descartar y volver**. | Restaurar recupera lo cargado; descartar deja opciones, Store, motor y estado físico sin cambios. | **Aprobada en HAOS VirtualBox (reporte); repetición física pendiente** |
| B1-07 | Guarda una edición válida y vuelve a abrir tras la recarga. | Conserva `id` y todos los campos no editados; persiste sólo modo/puntos nuevos y la regla activa se reevalúa normalmente. | **Aprobada en HAOS VirtualBox (reporte); repetición física pendiente** |
| B1-08 | Abre la misma regla en dos sesiones; guarda en la primera y luego intenta guardar el borrador antiguo. | La segunda recibe conflicto claro, no sobrescribe y puede recargar la configuración vigente. | **Aprobada (reporte del propietario)** |
| B1-09 | Reinicia Core, descarga/recarga y elimina la entrada en la instancia aislada. | El panel reaparece sólo con entrada cargada; no quedan tareas, animaciones ni panel visible tras descargar/eliminar, y una instalación nueva no muestra reglas antiguas. | **Aprobada (reporte del propietario)** |
| B1-10 | Edita la misma regla con el editor nativo y repite una prioridad/modo/notificación del Bloque B. | Ambos editores siguen disponibles, el formato heredado continúa compatible y no hay regresión de prioridades, modos, zonas o recuperación. | **Aprobada en HAOS VirtualBox (reporte); repetición física pendiente** |

El propietario reportó el recorrido B1-01 a B1-10 como 10/10 sobre
`6ad79e0c3c388f714f08c727ba17f315807310a4` en HAOS VirtualBox. Sumado a A
8/8 y B 10/10, el total comunicado es 28/28. Este registro no atribuye capturas,
logs ni métricas no entregados y no convierte VirtualBox en prueba Zigbee.

### Repetición física separada

Después de B1-01 a B1-10 en VirtualBox, repite B1-05, B1-06, B1-07 y B1-10
con Raspberry Pi 5/ZHA/GLEDOPTO. Distingue la ausencia de órdenes durante la
simulación de la aplicación real posterior al guardado. No marques el panel
validado en hardware físico hasta recibir el reporte del propietario.

## Resultado de C.2.1 en VirtualBox

El propietario confirmó el 26 de noviembre de 2026 el recorrido práctico
en HAOS VirtualBox sobre `cf2f371353dc6321baaef67c0ca8858e6d564110`.
Resultado informado de 6/6, sin observaciones adicionales.

| Caso | Comprobación | Resultado |
| --- | --- | --- |
| P-01 | Crear y guardar | Aprobada |
| P-02 | Editar y cancelar | Aprobada |
| P-03 | Guardar y salir | Aprobada |
| P-04 | Recargar la integración | Aprobada |
| P-05 | Persistencia | Aprobada |
| P-06 | Eliminar | Aprobada |

[Recorrido C.2.1](haos-c21-checks.md). Los casos C-01–C-20, U-01–U-06 y la
validación física Zigbee conservan su registro independiente.

## Plan pendiente de `0.1.0-alpha.3`, Bloque C

Sigue el [recorrido detallado C-01 a C-20](haos-block-c-walkthrough.md) para
preparar las entidades Demo, configurar cada regla y registrar los resultados.

### Incidencias antes de C.1

El propietario reprodujo en HAOS VirtualBox, sobre `1b3499c`, un salto desde
`/smart-led-manager-editor` a `/home/overview` durante la edición o el
guardado. También reportó campos que pedían JSON e identificadores de entidad
en el catálogo gráfico. El reporte disponible describe las pantallas y la
navegación. La evidencia adjunta al repositorio es textual.

El código anterior retiraba el panel al descargar la entrada en cada
guardado. El [enrutador del frontend 20261028.6](https://github.com/home-assistant/frontend/blob/20261028.6/src/layouts/partial-panel-resolver.ts)
reconstruye las rutas y selecciona la vista predeterminada cuando la ruta
activa desaparece. C.1 conserva el panel en la recarga de opciones, valida la
disponibilidad antes de escribir y usa controles gráficos para las reglas.
También comprueba la presencia de miembros de grupos, vuelve a resolver la
membresía y valida el destino justo antes del envío. C-03, C-06, C-08,
C-10 y C-19 incluyen regresiones específicas. Conserva las 10/10 de B.1
sobre su commit y repite su recorrido de edición en C.1.

### Casos

Ejecuta esta batería en una copia de HAOS VirtualBox partiendo de B.1. Registra
el SHA exacto instalado, fecha/hora, zona horaria, Home Assistant, navegador y
resultado observado. Usa el HEAD publicado de C.1, cuyo SHA funcional figura
en el [proceso de release](release.md). Todos los casos siguientes están
**pendientes** y sólo el propietario puede cerrarlos.

| Caso | Procedimiento | Resultado esperado | Estado |
|---|---|---|---|
| C-01 | Haz copia, actualiza la carpeta completa desde B.1 sin eliminar la entrada y reinicia Core. | Conserva `entry_id`, luces, Store, zonas, modos, entidades, nombres y reglas; aparece el catálogo unificado sin duplicados. | Pendiente |
| C-02 | Abre y ejecuta reglas heredadas de estado y numéricas, incluida una sin `enabled`. | Mantienen `id`, puntos, prioridad y comportamiento; la ausencia de `enabled` equivale a habilitada. | Pendiente |
| C-03 | Desde el panel crea, edita, duplica, deshabilita y elimina una regla de cada tipo; descarta otro borrador. | CRUD completo, copia con `id` nuevo y deshabilitada, guardado estable y descarte sin efectos físicos. | Pendiente |
| C-04 | Combina luces individuales y dos zonas con destinos superpuestos. | Se resuelve cada luz física una sola vez y ningún modo deja las luces de su zona. | Pendiente |
| C-05 | Selecciona un área y una etiqueta que incluyan luces administradas y ajenas. | Sólo aparecen/controlan las administradas; la vista previa muestra las exclusiones. | Pendiente |
| C-06 | Prueba grupo anidado válido y después ciclo, grupo opaco, miembro ausente y luz no autorizada. | El válido se expande a luces físicas; cada variante insegura se rechaza completa y no envía al grupo. | Pendiente |
| C-07 | Selecciona “todas las administradas” junto con otros destinos y luego intenta guardar una selección vacía. | Deduplica todas las autorizadas; vacío se rechaza y nunca se interpreta como todas. | Pendiente |
| C-08 | Con una regla continua activa cambia membresía de grupo, área o etiqueta y elimina/renombra una entidad. | Retira destinos anteriores, aplica sólo a los nuevos seguros, registra inválidos y no toca solicitudes ajenas. | Pendiente |
| C-09 | Crea puerta abierta AND (presencia OR ayudante) AND NOT alarma; alterna cada fuente y usa `unknown`/`unavailable`. | Reevalúa fuentes secundarias; NOT no convierte datos desconocidos en verdadero. | Pendiente |
| C-10 | Prueba horario diurno, 22:00–06:00, cambio de día y arranque dentro del intervalo en la zona local. | Entra/sale sin cambio del sensor; en el nocturno el día es el de inicio y no hay polling visible. | Pendiente |
| C-11 | Exige permanencia y rompe la condición antes del plazo; repite hasta cumplir y después recarga durante la espera. | Cancela el primer contador, reevalúa al cumplir y tras recarga empieza desde cero. | Pendiente |
| C-12 | Prueba `above`, `below`, `inside` y `outside` en los límites exactos, primero con color fijo y después con puntos/rangos. | Activación y RGB son independientes y respetan límites documentados y unidades sin conversión. | Pendiente |
| C-13 | Recorre la banda de histéresis y después publica `unknown`, `unavailable`, NaN/valor no numérico y recuperación. | No oscila en la banda; inválidos liberan y la recuperación parte del estado inicial seguro. | Pendiente |
| C-14 | Dispara una regla desde `input_button` y desde un trigger de cambio de estado. | Cada pulso crea una solicitud temporal; el botón no se interpreta como interruptor persistente. | Pendiente |
| C-15 | Dispara un evento del bus y una entidad del dominio `event`; haz que una condición descartada se cumpla después. | Sólo el evento actual activa; el descartado no se reproduce posteriormente. | Pendiente |
| C-16 | Configura un device trigger realmente disponible en la instancia y luego uno inválido. | El compatible se registra y cancela correctamente; el inválido se rechaza al guardar sin listener residual. | Pendiente |
| C-17 | Repite rápidamente el mismo evento, enmárcalo con prioridad superior y deja que venza. | Renueva una sola solicitud, no crea cola ni animación duplicada y una vencida nunca aparece al liberar la superior. | Pendiente |
| C-18 | Edita destinos, color y prioridad de una regla activa mientras está enmascarada; deshabilítala antes de liberar la superior. | Sólo existe la intención editada vigente y la deshabilitada no reaparece. | Pendiente |
| C-19 | Guarda en dos sesiones, prueba usuario no administrador, entrada descargada y previsualizaciones. | Conflicto claro, acceso denegado, escritura rechazada y cero cambios en luces, Store o motor. | Pendiente |
| C-20 | Reinicia, descarga/recarga, elimina en instancia aislada y repite prioridades, zonas, modos, panel y recuperación anteriores. | Sin listeners, timers, tareas, animaciones o solicitudes tardías; una instalación nueva no hereda reglas. | Pendiente |

### Repetición física Zigbee separada para C

Tras cerrar VirtualBox, repite C-04, C-08, C-12, C-13, C-17, C-18 y C-20 en
Raspberry Pi 5 con ZHA y controladores reales cuando el caso lo permita. M-06
sigue exigiendo dos controladores Zigbee. B-02, B-04, B-07, B-08, B1-05,
B1-06, B1-07 y B1-10 conservan su repetición física pendiente. Alexa/Matter
Hub, M-10, M-15 y M-17 mantienen el alcance parcial ya documentado. La mera
instalación de Matter Hub o la existencia de un device trigger no aprueba esas
pruebas.

## Resultado de C.2.2 en VirtualBox

El propietario confirmó **10/10 pruebas funcionales aprobadas** en HAOS
VirtualBox con Home Assistant Core 2026.11.3 y el SHA funcional
`7a0fc49c2eda8a15e9b0e658e10b6da2efaede29`.
[Guía usada para el recorrido](haos-c22-checks.md).

| Caso | Prueba | Resultado |
| --- | --- | --- |
| Q-01 | Centro de administración | Aprobada |
| Q-02 | Luces administradas | Aprobada |
| Q-03 | Crear y editar zonas | Aprobada |
| Q-04 | Protección de dependencias | Aprobada |
| Q-05 | Crear y editar modos | Aprobada |
| Q-06 | Activación exclusiva | Aprobada |
| Q-07 | Control externo | Aprobada |
| Q-08 | Borradores y recarga | Aprobada |
| Q-09 | Persistencia y eliminación | Aprobada |
| Q-10 | Regresión C.2.1 | Aprobada |

**Validación visual con observaciones.** El propietario indicó:

> Por lo que estuve probando es completamente funcional, solo que se presenta
> algo grande el menú principal, ya que abarca toda la pantalla completa, tal
> vez un ajuste de tamaño sería más conveniente

El propietario aprobó compactar el inicio en C.2.3. La aprobación visual
definitiva sigue pendiente. C-01–C-20, U-01–U-06 y las pruebas físicas
conservan sus estados.

El [recorrido de C.2.3](haos-c23-checks.md) queda pendiente de ejecución por
el propietario en VirtualBox.
