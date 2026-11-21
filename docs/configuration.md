# Configuración y reglas

## Luces administradas

La primera pantalla pide una lista explícita de entidades `light`. Esa lista es
el límite de autorización: acciones y reglas que incluyan otra entidad se
rechazan. No existe una opción implícita para “todas las luces”.

Para cambiarla, abre **Ajustes > Dispositivos y servicios > Smart LED Manager
> Configurar > Luces administradas**. Si retiras una entidad, revisa también
las reglas que la usen.

## Ajustes del motor

- **Desempate:** `newest` favorece la solicitud activada más recientemente;
  `oldest`, la activada más antigua; `lexical`, el orden estable de
  `request_id`. La
  prioridad numérica siempre se compara primero.
- **Intervalo mínimo por luz:** limita la frecuencia de órdenes. Una orden más
  reciente sustituye trabajo pendiente obsoleto.
- **Política de control manual directo:** `service_only` sólo acepta la acción
  explícita. `respect` y `temporary` habilitan atribución conservadora basada
  en contexto; esta detección es experimental en la alfa y debe probarse con
  cada integración de luz.

## Regla de estado

La regla está activa mientras una entidad persistente cumpla una igualdad o
desigualdad. Configura nombre, origen, operador, valor, luces administradas,
prioridad, RGB, brillo y transición. Cuando la condición deja de cumplirse se
libera la solicitud y el motor calcula de nuevo el ganador de cada luz.

Ejemplos: un `input_boolean` para modo cine, un `binary_sensor` de puerta, el
estado de una persona o el estado de `sun`. Para botones o eventos de un solo
instante usa por ahora una acción explícita; no simules un evento como estado
persistente.

## Regla numérica

Define al menos dos puntos con el formato:

```text
16:0,0,255;20:0,255,255;24:0,255,0;28:255,255,0;32:255,128,0;36:255,0,0
```

Cada entrada es `valor:R,G,B`. Los valores se ordenan y los extremos se
limitan al primer/último color. El modo `interpolate` mezcla linealmente los
puntos contiguos; `ranges` usa el rango inferior más próximo. **Variación
mínima** y **intervalo mínimo** evitan ruido y exceso de órdenes.

`unknown`, `unavailable`, NaN e infinito nunca se convierten en cero ni en un
color válido. Comprueba que la entidad de origen publique un valor numérico
real.

## Prioridades y duración

Las prioridades válidas son `0..100`; el número mayor gana. La resolución se
hace de forma independiente por entidad, por lo que una solicitud puede ganar
en una habitación y quedar oculta en otra. Actualizar una solicitud oculta
conserva su intención más reciente.

Las solicitudes temporales consumen su duración en tiempo real incluso cuando
están ocultas. Si vencen antes de ganar, no se reproducen después. Al terminar
una ganadora se reevalúan solicitudes y fuentes vigentes; nunca se restaura un
snapshot físico antiguo sin comprobarlo.

## Capacidades y disponibilidad

El adaptador consulta `supported_color_modes` y envía sólo atributos
representables. RGBW/RGBWW reciben una proyección RGB compatible; una entidad
sin capacidad de color conserva un error diagnosticable en lugar de recibir
datos inválidos. Cuando una luz está `unavailable`, se conserva la intención,
pero al regresar se vuelve a comprobar qué solicitud sigue vigente.

## Estado actual de edición

La alfa permite agregar y eliminar reglas mediante options flow. La edición o
duplicación directa, condiciones compuestas, áreas/etiquetas, horarios y
disparadores de eventos pertenecen a incrementos posteriores de la hoja de
ruta. Elimina y vuelve a crear una regla para cambiarla en esta versión.

