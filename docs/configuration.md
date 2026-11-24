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
prioridad, RGB, brillo, transición y si queda habilitada. Cuando la condición
deja de cumplirse se libera la solicitud y el motor calcula de nuevo el ganador
de cada luz.

Ejemplos: un `input_boolean` para modo cine, un `binary_sensor` de puerta, el
estado de una persona o el estado de `sun`. Para botones o eventos de un solo
instante usa por ahora una acción explícita; no simules un evento como estado
persistente.

## Regla numérica

Define al menos dos puntos desde el editor visual. Cada punto combina un campo
numérico con el selector RGB nativo de Home Assistant. El resumen muestra la
unidad publicada por la entidad cuando está disponible; permite agregar,
elegir y editar o eliminar puntos. Los valores se ordenan automáticamente y no
se aceptan duplicados, NaN, infinito ni canales fuera de `0..255`.

El formato guardado continúa siendo una lista compatible con alpha.1/alpha.2,
por ejemplo `[{"value": 20, "rgb": [0, 0, 255]}, ...]`; no hace falta escribir
ni mantener una cadena técnica. El modo `interpolate` mezcla linealmente los
puntos contiguos; `ranges` usa el rango inferior más próximo. Fuera de los
extremos se usa el color del punto más cercano. **Variación mínima** e
**intervalo mínimo** evitan ruido y exceso de órdenes.

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

## Administración de reglas

Desde **Configurar > Reglas inteligentes** se puede agregar, editar, duplicar,
activar o desactivar y eliminar una regla. Editar conserva el `id` interno,
aunque cambie el nombre, origen, destinos, prioridad o color. Una copia recibe
un `id` nuevo, añade `(2)` al nombre inicial y queda deshabilitada para evitar
un conflicto accidental; revisa sus campos antes de activarla. Las reglas de
alpha.1/alpha.2 que no contienen `enabled` se consideran habilitadas.

El editor numérico es multipaso. Los cambios de metadatos y puntos permanecen
en el flujo hasta elegir **Guardar regla**; **Descartar cambios** vuelve al menú
sin alterar las opciones. No hay vista previa física durante la edición: el
selector permite ver el color, pero ninguna orden se envía antes del guardado.
Guardar recarga la entrada, cancela y espera evaluaciones antiguas y reconstruye
la solicitud desde la definición y el estado actuales. Una regla activa que
cambia de destinos deja de participar en los anteriores; una deshabilitada o
eliminada no reaparece al terminar una solicitud superior.

### Editor gráfico avanzado B.1

Una cuenta administradora puede abrir **Smart LED Manager** en la barra lateral,
entrar directamente en `/smart-led-manager-editor` o seguir el enlace interno
de **Configurar > Centro de administración**. Esa pantalla también permite
mostrar u ocultar el acceso lateral; ocultarlo no elimina la ruta. **Configurar
> Reglas inteligentes > Abrir editor gráfico avanzado** conserva otro enlace.
El Options Flow no intenta forzar navegación con una API interna de Home
Assistant. El editor nativo anterior continúa disponible para crear reglas y
editar todos sus metadatos.

El panel abre en un centro modular que muestra identidad y versión, acceso a las
reglas numéricas y acceso a la configuración nativa de la integración. No
simula secciones futuras. En el catálogo usa primero los nombres amigables de
sensores y luces; los `entity_id` y el `id` interno permanecen en información
técnica desplegable. Al elegir una regla carga unidad, prioridad, destinos y
brillo como información de sólo lectura. En B.1 sólo cambia:

- `interpolate` o `ranges`;
- valor numérico y color de cada punto;
- alta y eliminación de puntos.

La barra y la gráfica colocan cada punto según su valor real, no a distancias
uniformes. Los marcadores se seleccionan con ratón, tacto o teclado y siempre
hay un campo numérico equivalente. Los colores también aparecen como RGB y
hexadecimal para no depender sólo de la percepción cromática.

El simulador acepta un valor hipotético y devuelve el color, RGB/hexadecimal y
el punto o intervalo usado. El cálculo ocurre en el backend con el mismo código
que evalúa la regla activa. Simular o editar un borrador nunca ordena encender o
apagar una luz.

**Restaurar borrador** vuelve a los datos cargados; **Descartar y volver** sale
sin modificar opciones; **Guardar cambios** valida otra vez en Python y provoca
la recarga normal de la entrada. Si el Options Flow u otra pestaña cambió la
configuración después de cargarla, el panel rechaza el guardado como conflicto:
elige **Recargar configuración**, revisa la versión nueva y repite la edición.
No se combinan silenciosamente dos borradores.

Las actualizaciones ordinarias de estados de Home Assistant no reconstruyen el
formulario ni quitan el foco. Una respuesta antigua del simulador se descarta
si ya existe una solicitud posterior; un valor vacío no se evalúa como cero. Si
la entrada se descarga, el catálogo muestra el error y ofrece recargar en lugar
de presentarlo como vacío.

La recarga no es edición completamente en caliente. Conserva solicitudes
persistentes válidas y selecciones de modo, pero una notificación temporal no
persistente puede terminar. Destinos por área/etiqueta, condiciones compuestas,
horarios, duración mínima, histéresis, eventos y políticas configurables de
recuperación o pausa/reanudación siguen reservados a los Bloques C y D. El área
opcional de una zona sólo organiza su dispositivo virtual; no expande destinos.
