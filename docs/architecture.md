# Arquitectura de Smart LED Manager

## Propósito y límites

Smart LED Manager es una capa local de arbitraje sobre entidades `light` ya existentes. No sustituye ZHA, Matter, ESPHome, WLED ni el controlador físico. Recibe intenciones de diferentes orígenes, decide una ganadora por tira y proyecta esa intención únicamente a luces autorizadas.

La primera versión se diseña para RGB, RGBW, RGB+CCT y RGBWW sin lógica exclusiva para GLEDOPTO. La resolución de prioridades no conoce protocolos ni píxeles; por eso un futuro controlador direccionable podrá mapear una intención a segmentos sin reconstruir el motor.

## Capas

1. **Modelo y motor puro** (`models.py`, `core/priority.py`, `core/engine.py`). Conservan solicitudes activas, validan tiempos/prioridades y resuelven un ganador independiente por destino bajo un bloqueo asíncrono.
2. **Reglas** (`modules/`). Traducen cambios de estado y valores numéricos de Home Assistant a solicitudes estables. Una regla oculta por otra prioridad continúa actualizándose.
3. **Orquestación** (`coordinator.py`). Posee suscripciones, historial acotado, persistencia, vencimientos, disponibilidad y ciclo de vida de la entrada.
4. **Planificación** (`core/scheduler.py`). Cancela el trabajo del ganador anterior y ejecuta expiraciones/animaciones con tareas asíncronas por destino.
5. **Proyección física** (`controllers/rgb.py`). Consulta el estado y capacidades reales, convierte la intención a `light.turn_on`/`light.turn_off`, deduplica y limita órdenes.
6. **Superficie Home Assistant** (`config_flow.py`, `services.py`, `sensor.py`, `diagnostics.py`). Ofrece configuración nativa, acciones con selectores, diagnóstico y una entidad de estado del motor.

```text
reglas / acciones / control manual
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

## Capacidades y comandos

El controlador lee `supported_color_modes`, `supported_features`, disponibilidad y efectos de la entidad. Envía solo atributos representables. RGB se proyecta sobre modos RGB/RGBW/RGBWW compatibles; si una luz no puede representar color, el error queda diagnosticado sin un bucle de reintentos.

Cada luz conserva intención deseada, firma del último comando y una sola tarea pendiente. El intervalo mínimo es configurable; una orden nueva sustituye trabajo obsoleto. Una luz `unavailable` conserva la intención y se resincroniza al reaparecer, siempre que la solicitud siga vigente.

## Persistencia y recuperación

La configuración y las reglas viven en la entrada de configuración. Las solicitudes marcadas persistentes se guardan mediante `Store` con versión de esquema. En el arranque se descartan entradas inválidas o vencidas, se vuelven a evaluar las fuentes y se calcula el ganador actual. Nunca se recrean temporizadores duplicados.

Al descargar la integración se eliminan listeners, se cancelan vencimientos/animaciones/tareas de controlador y se vacía el registro de runtime. La política de descarga no fuerza restauraciones físicas ciegas.

## Reglas iniciales

- **Estado:** igualdad o desigualdad sobre entidades persistentes (sensores binarios, interruptores, ayudantes, clima, alarma, presencia, persona y sol). La condición falsa libera su solicitud.
- **Numérica:** N puntos ordenados, interpolación RGB o rango inferior, clamp en extremos, variación mínima e intervalo mínimo. `unknown`, `unavailable`, NaN e infinito liberan/ignoran la solicitud según corresponda.
- **Eventos/botones:** se activan mediante acciones explícitas en `alpha.1`; listeners de eventos y disparadores por dispositivo se añadirán sin fingir semántica de interruptor persistente.

## Animaciones iniciales

`fixed`, `blink` y `pulse` usan una tarea por destino y respetan el intervalo del controlador. Una nueva ganadora cancela la tarea anterior antes de emitir el siguiente cuadro. Alternancia multicolor, respiración avanzada, secuencias editables y efectos direccionables están en la hoja de ruta.

## Decisiones de compatibilidad

- Home Assistant mínimo: `2026.11.0`, porque esta rama usa el contrato actual de esquemas `probatio`, traducciones de integraciones personalizadas y se valida para Marketplace integrado.
- Python mínimo: `3.14.2`, igual que el entorno de desarrollo de Home Assistant 2026.11.
- No se usa polling periódico general. Los cambios provienen de eventos de estado, deadlines de expiración y cuadros de una animación activa.
- No hay interceptores globales de `light.turn_on`; el control manual directo se basa en contexto/eco cuando se habilite y se mantiene conservador.

## Riesgos que requieren pruebas físicas

La conversión de color de una entidad concreta, la latencia ZHA, el multicast de grupos Zigbee, la propagación de `Context`, los límites aceptables de animación y la recuperación de un GLEDOPTO desconectado no pueden validarse plenamente en pruebas unitarias. El procedimiento está en [haos-test-plan.md](haos-test-plan.md).

