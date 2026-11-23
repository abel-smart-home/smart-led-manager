# Configuración y reglas

## Luces administradas

La primera pantalla pide una lista explícita de entidades `light`. Esa lista es
el límite de autorización: acciones y reglas que incluyan otra entidad se
rechazan. No existe una opción implícita para “todas las luces”.

Para cambiarla, abre **Ajustes > Dispositivos y servicios > Smart LED Manager
> Configurar > Luces administradas**. Si retiras una entidad, revisa también
las reglas que la usen. No se puede retirar una luz mientras una zona todavía
la contenga.

## Zonas y modos de iluminación

Una zona agrupa una o más luces administradas. Cada luz física puede pertenecer
a una sola zona, aunque una instalación puede tener tantas zonas como necesite.
Desde **Configurar > Zonas** puedes crear, renombrar, cambiar luces, asociar de
forma opcional un área de Home Assistant o eliminar una zona; primero debes
eliminar sus modos. El área afecta sólo al dispositivo virtual de la zona, no
a las luces físicas administradas.

Un modo pertenece a una zona y controla un subconjunto no vacío de sus luces.
Desde **Configurar > Modos de iluminación** puedes crear, editar o eliminar:

- nombre, prioridad `0..100` y luces del modo;
- color RGB, brillo y transición opcionales;
- permiso para encender una luz apagada;
- animación `fixed`, `blink` o `pulse` y su periodo;
- un `switch` opcional para paneles, Alexa o puentes Matter.

Home Assistant crea un `select` por zona. Elegir un modo reemplaza de forma
atómica el modo anterior de esa misma zona; otra zona no cambia. Elegir **Sin
modo** libera la solicitud de modo y deja que aparezca una regla, aviso, escena
u otra intención vigente. No envía una orden de apagado por sí misma.

La selección sobrevive reinicios porque se guarda como solicitud persistente.
Las definiciones de opciones mandan sobre el comando: editar un modo activo y
recargar aplica su definición actual; borrar el modo elimina su intención
guardada. Repetir la selección actual es idempotente y no reinicia animaciones.

Guardar cambios del options flow recarga la entrada para conservar un ciclo de
vida predecible. Las solicitudes persistentes se reconcilian, pero una
notificación temporal no persistente que estuviera activa termina durante esa
recarga y no se reproduce después; la edición no se presenta como actualización
en caliente libre de interrupciones.

Los interruptores son optativos y no integran directamente servicios de nube.
En la validación física de `8e21b28`, Home-Assistant-Matter-Hub `2.0.60` expuso
los interruptores de Cine y Lectura a Alexa y sincronizó correctamente la
selección. Smart LED Manager no se comunica directamente con Matter Hub ni con
Alexa, y el estado del `switch` expresa intención lógica, no confirmación del
color físico.

Alpha.3 crea un dispositivo virtual por zona. El dispositivo central Smart LED
Manager conserva el sensor del motor; **Sala**, por ejemplo, contiene su
selector **Modo** y switches breves como **Cine** o **Lectura**. La combinación
oficial de nombre de dispositivo y `has_entity_name` aporta contexto sin cambiar
los `unique_id`. Los nombres personalizados existentes no se sobrescriben.
Smart LED Manager no crea aliases ni supone cómo los consumirá Matter Hub.

Al eliminar permanentemente un modo se retiran su definición, su solicitud y
el registro de su switch de esa entrada. Desactivar **Exponer como switch** no
equivale a borrar el modo: el registro se conserva para que el mismo `entity_id`
regrese si se reactiva. Elimina o actualiza antes las automatizaciones, paneles
y exposiciones de voz que referencien una entidad que vas a borrar. La descarga
o recarga temporal no elimina registros.

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

El primer número es el valor de la entidad de origen y los tres siguientes son
los canales rojo, verde y azul de `0..255`; `;` separa los puntos. Fuera de los
extremos se usa el color del punto más cercano. Alpha.3 propone sustituir esta
cadena técnica por un editor con valor, unidad visible cuando sea posible,
selector de color, ordenamiento y validación, siempre que pueda implementarse
de forma segura con el Options Flow nativo.

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

La alfa permite crear, editar y eliminar zonas y modos; las reglas todavía se
agregan y eliminan mediante options flow. La edición o duplicación directa de
reglas, destinos por área/etiqueta, condiciones compuestas, horarios y
disparadores de eventos pertenecen a incrementos posteriores. El área opcional
de una zona sólo organiza su dispositivo virtual; no expande destinos. Elimina
y vuelve a crear una regla para cambiarla en este bloque.
