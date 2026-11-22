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
| R-04 | Recarga y después elimina la entrada. | No quedan listeners, animaciones u órdenes tardías. | **Recarga aprobada en el alcance ejecutado, 8/8.** `homeassistant.reload_config_entry` detuvo `blink` naranja, recuperó azul persistente y no reapareció la animación en 30 s. La eliminación completa de la entrada y su limpieza posterior quedan pendientes. |
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

Esta cobertura automatizada no sustituye la eliminación física de la entrada
en una instancia aislada, que continúa pendiente para cerrar R-04.

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

## Escenarios pendientes

- F-02: dos tiras independientes y resolución simultánea por destino.
- R-04: eliminación de la entrada y verificación de limpieza posterior.
- Estrés extremo adicional con simultaneidad intensa, múltiples dispositivos y
  varias tiras; no forma parte de la carga mixta aprobada en R-05.
- R-06: grupos Zigbee y comportamiento multicast/unicast.
- Validación formal específica de Alexa y Matter Hub.
- Otros modelos GLEDOPTO y combinaciones RGB, RGBW y RGB+CCT.
- Firmware del coordinador, firmware del controlador y fecha/hora exacta de
  ejecución.

## Plan adicional de `0.1.0-alpha.2` — zonas y modos

Este bloque todavía **no se ha ejecutado físicamente**. Debe registrarse con el
SHA candidato alpha.2, fecha/hora y entorno real sin reemplazar los resultados
alpha.1 anteriores. Las pruebas automatizadas indicadas son cobertura de
software, no evidencia de HAOS, Zigbee, Alexa o Matter Hub.

| ID | Validación física propuesta | Cobertura automatizada | Resultado físico |
|---|---|---|---|
| M-01 | Activa dos veces el mismo modo fijo y animado; observa que no reinicie. | Idempotencia de solicitud, antigüedad, aplicación y guardado. | Pendiente |
| M-02 | Cambia Cine → Lectura con una regla inferior visible en el historial. | Reemplazo atómico sin ganador intermedio. | Pendiente |
| M-03 | Mantén Cine P50 durante un aviso P70 y espera su vencimiento. | Enmascaramiento y recuperación del modo vigente. | Pendiente |
| M-04 | Desactiva Cine mientras gana P70 y espera. | Recuperación de la regla inferior, no del modo retirado. | Pendiente |
| M-05 | Cambia varias veces el sensor P40 bajo Cine y después libera Cine. | Actualización enmascarada y último comando vigente. | Pendiente |
| M-06 | Selecciona modos distintos en dos zonas/tiras. | Catálogos y solicitudes independientes por zona. | Pendiente; requiere al menos dos luces |
| M-07 | Reinicia Core con definiciones y selección activas. | Serialización, restauración y reconciliación. | Pendiente |
| M-08 | Elige **Sin modo** con y sin regla inferior. | Liberación sin comando de apagado ni snapshot. | Pendiente |
| M-09 | Edita un modo seleccionado, guarda y verifica la recarga. | La definición actual reemplaza el comando histórico. | Pendiente |
| M-10 | Elimina un modo activo y comprueba entidades/Store tras recarga. | Limpieza de solicitudes huérfanas. | Pendiente |
| M-11 | Cambia de modo con el GLEDOPTO sin alimentación y reconecta. | Sólo la última solicitud de modo conserva recuperación. | Pendiente |
| M-12 | Repite M-11 mientras ZHA mantiene `on`/`off`. | Regresiones de recuperación acotada, caché y tarea única. | Pendiente |
| M-13 | Alterna rápidamente selector, switch y acciones. | Serialización por bloqueo y una sola selección final. | Pendiente |
| M-14 | Combina modo con solicitudes de igual prioridad bajo tres desempates. | Suite existente de `newest`, `oldest` y `lexical`. | Pendiente |
| M-15 | Intenta guardar una zona/modo con luz no autorizada. | Rechazo de catálogo y allowlist. | Pendiente |
| M-16 | Recarga y elimina la entrada con animación de modo activa. | Cancelación de plataformas, listeners, tareas y Store. | Pendiente |
| M-17 | Repite acciones/reglas principales de alpha.1. | Suite completa de regresión alpha.1. | Pendiente |
| M-18 | Enmascara el modo y compara selector/switch con la luz física. | Entidades derivadas de selección y diagnóstico winner/masked/partial. | Pendiente |
| M-19 | Prueba identificadores inválidos mediante la UI y datos huérfanos simulados. | Validación, catálogo contenido y reconciliación determinista. | Pendiente |
| M-20 | Actualiza manualmente alpha.1, recarga, reinicia y revierte de forma controlada. | Entrada alpha.1 sin nuevas claves y Store anterior compatibles. | Pendiente |

En M-09, guardar opciones recarga la entrada. Una notificación temporal no
persistente termina durante esa recarga y no debe reproducirse después; registra
este límite en lugar de describir la edición como actualización en caliente.

## Alexa y Matter Hub

Alpha.2 puede crear un `switch` por cada modo marcado para exposición. Smart
LED Manager no se comunica con Matter Hub ni con Alexa: el interruptor sólo
representa **modo seleccionado**, no confirmación física del color.

Procedimiento pendiente para el propietario:

1. Crea un modo fijo seguro y habilita su interruptor opcional.
2. Verifica primero ON/OFF desde Home Assistant y que el selector de zona se
   sincronice.
3. Expón únicamente ese `switch` mediante Home-Assistant-Matter-Hub `2.0.60`.
4. Confirma descubrimiento, cambio ON, selección de otro modo, cambio OFF y
   recuperación después de un aviso temporal.
5. Registra nombres de entidad, latencia, estados del selector/switch, estado
   físico y logs. Retira la exposición temporal al finalizar.

No marques Alexa/Matter como validado sólo porque Matter Hub esté instalado o
la luz subyacente responda. La validación formal continúa pendiente.

## Cierre

Adjunta este archivo actualizado o un informe equivalente al PR candidato,
incluyendo fallos y limitaciones. Un fallo de hardware/integración externa debe
distinguirse de un fallo del motor, pero no ocultarse. La autorización para
fusionar o publicar sigue siendo una decisión separada.
