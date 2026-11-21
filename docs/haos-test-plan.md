# Plan de validación física en HAOS

Este plan debe ejecutarlo el propietario sobre su instalación y hardware. Las
pruebas unitarias, los mocks y la simulación de estados no constituyen evidencia
de HAOS, Zigbee, GLEDOPTO, Alexa o Matter Hub.

## Registro de ejecución

| Campo | Valor |
|---|---|
| Fecha/hora y zona | Pendiente |
| Commit y versión | Pendiente |
| Home Assistant OS/Core | Pendiente |
| Coordinador Zigbee y firmware | Pendiente |
| Modelos/firmware de controladores LED | Pendiente |
| Integraciones de luz | Pendiente |
| Ejecutor | Pendiente |
| Resultado general | **No ejecutado** |

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
| F-01 | Intenta una acción sobre la luz no autorizada. | Se rechaza toda la llamada; ninguna luz cambia. | Pendiente |
| F-02 | Activa P40 azul en dos tiras y P60 verde sólo en una. | Una queda verde y la otra azul. | Pendiente |
| F-03 | Actualiza P40 a rojo mientras P60 gana; cancela P60. | No hay cambio durante P60; después aparece rojo. | Pendiente |
| F-04 | Prueba empates con `newest`, `oldest` y `lexical`. | Resultado determinista según la política. | Pendiente |
| F-05 | Envía `notify` P70 y una alarma de prueba P100. | Gana P100; después se reevalúa el aviso sólo si sigue vigente. | Pendiente |
| F-06 | Ejecuta `blink` y `pulse`, después reemplaza/cancela. | La tarea anterior se detiene sin cuadros tardíos. | Pendiente |
| F-07 | Crea regla de estado y cambia la fuente. | Activa/libera sin sondeo perceptible. | Pendiente |
| F-08 | Recorre una regla numérica y después usa `unknown`/`unavailable`. | Colores correctos; valores inválidos nunca se vuelven cero. | Pendiente |
| F-09 | Apaga una tira y prueba `allow_turn_on` falso/verdadero. | Sólo la solicitud autorizada puede encenderla. | Pendiente |
| F-10 | Cambia manualmente la luz con `service_only`. | No se crea una solicitud externa implícita. | Pendiente |

## Desconexión, carga y recuperación

| ID | Procedimiento | Resultado esperado | Resultado/observaciones |
|---|---|---|---|
| R-01 | Desconecta una tira con una solicitud persistente; cambia otra solicitud y reconecta. | Se aplica la ganadora actual, no el último snapshot enviado. | Pendiente |
| R-02 | Desconecta durante un aviso corto y reconecta tras su vencimiento. | El aviso obsoleto no se reproduce. | Pendiente |
| R-03 | Reinicia HAOS con solicitudes persistente y temporal. | Se recupera sólo lo válido; no hay temporizadores duplicados. | Pendiente |
| R-04 | Recarga y después elimina la entrada. | No quedan listeners, animaciones u órdenes tardías. | Pendiente |
| R-05 | Genera cambios rápidos de sensor y varias animaciones. | Deduplicación/rate limit evitan tormenta y HA sigue estable. | Pendiente |
| R-06 | Usa grupos Zigbee si están disponibles y observa multicast/unicast. | Sin duplicados inesperados; registrar comportamiento real. | Pendiente |

## Alexa y Matter Hub

La alfa no promete entidades virtuales específicas para exposición. Si el
propietario ya expone las entidades `light` subyacentes, comprueba que una orden
de Alexa/Matter y una solicitud del motor produzcan un resultado comprensible,
pero registra la atribución exacta. No marques integración nativa con Alexa o
Matter como validada sólo porque la luz física responde.

## Cierre

Adjunta este archivo actualizado o un informe equivalente al PR candidato,
incluyendo fallos y limitaciones. Un fallo de hardware/integración externa debe
distinguirse de un fallo del motor, pero no ocultarse. La autorización para
fusionar o publicar sigue siendo una decisión separada.
