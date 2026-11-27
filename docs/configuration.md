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
instante crea una regla de evento; no los simules como estado persistente.

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
**intervalo mínimo** evitan ruido y exceso de órdenes. La activación opcional
puede ser por encima, debajo, dentro o fuera de rango, con histéresis. Esto
decide si la regla participa; los puntos o el color fijo deciden su RGB.

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

### Centro gráfico de reglas inteligentes

Una cuenta administradora puede abrir **Smart LED Manager** en la barra lateral,
entrar directamente en `/smart-led-manager-editor` o seguir el enlace interno
de **Configurar > Centro de administración**. Esa pantalla también permite
mostrar u ocultar el acceso lateral; ocultarlo no elimina la ruta. **Configurar
> Reglas inteligentes > Abrir editor gráfico avanzado** conserva otro enlace.
El Options Flow no intenta forzar navegación con una API interna de Home
Assistant. El Options Flow nativo continúa disponible y usa el mismo modelo y
validación.

El panel abre en un centro modular que muestra identidad y versión, una lista
unificada de reglas de estado, numéricas y de eventos, y acceso a la
configuración nativa. Usa primero nombres amigables; identificadores y el
borrador normalizado quedan en detalles técnicos. Permite crear, editar,
duplicar, habilitar, deshabilitar y eliminar. En una regla numérica conserva:

- color fijo, interpolación o rangos;
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

**Restaurar borrador** vuelve a los datos cargados. Si pulsas **Cancelar** o
vuelves al catálogo con cambios, puedes **Continuar editando**, **Descartar
cambios y salir** o **Guardar y salir**. **Guardar** valida en Python, solicita
la recarga normal y vuelve al catálogo cuando la revisión se aplica.
Si el Options Flow u otra pestaña cambia la configuración, el guardado se
rechaza con un conflicto. Conserva el borrador para consultar qué cambiaste,
comprueba el estado y abre la versión vigente para volver a aplicar tus cambios.

Las actualizaciones ordinarias de estados de Home Assistant no reconstruyen el
formulario ni quitan el foco. Una respuesta antigua del simulador se descarta
si ya existe una solicitud posterior o cambió el borrador. Los campos vacíos
conservan su condición de vacíos. Durante la recarga se muestra el estado y
se bloquean las escrituras. Si la recarga falla, el panel deja el formulario
abierto. Puedes revisar el registro de HA, recargar la integración y usar
**Comprobar estado** para volver a leer el resultado. Una reconexión también
comprueba el resultado de un envío pendiente.

La recarga no es edición completamente en caliente. Conserva solicitudes
persistentes válidas y selecciones de modo, pero una notificación temporal no
persistente puede terminar. Las políticas configurables de recuperación y la
pausa/reanudación temporal siguen reservadas al Bloque D.

## Destinos, condiciones y tiempo del Bloque C

Una regla puede combinar luces individuales, zonas de Smart LED Manager, áreas,
etiquetas, grupos transparentes y **todas las luces administradas**. La vista
previa muestra las luces físicas resultantes, los duplicados y las excluidas de un área o
etiqueta. Un grupo no es una orden multicast: debe poder expandirse por completo
a luces autorizadas. Si contiene un miembro opaco, ausente o no autorizado, o
un ciclo, se rechaza. Nunca uses una entidad de grupo como luz administrada.

En **Condiciones**, agrega **Todas (AND)**, **Al menos una (OR)**, **Negar
(NOT)** o una condición de estado, número u horario. Los controles permiten
anidar y reordenar ramas. Los datos inválidos conservan el resultado
desconocido también bajo NOT. En **Horarios y permanencia**, activa el horario,
elige horas y días. Si cruza medianoche, el día elegido es el día en que
comienza el intervalo. La permanencia mínima se aplica al resultado total:
si cualquier parte falla antes, el contador se cancela; tras una recarga o
reinicio comienza otra vez.

Las reglas de evento pueden usar cambios de estado, entidades de evento, un
ayudante de tipo botón, el nombre de un evento del bus o una acción publicada
por un dispositivo. Usa **Duración** para indicar cuánto se mostrará el aviso.
Una repetición renueva la solicitud temporal de la misma regla. Los disparadores
avanzados que el formulario local no puede representar se conservan hasta que
los reemplaces explícitamente. El Options Flow ofrece el selector nativo de
disparadores. El constructor nativo de condiciones admite el subconjunto que
puede convertirse sin cambiar el resultado de Smart LED Manager. Usa el panel
para comparaciones compuestas dentro/fuera de rango y condiciones preservadas.

### Ejemplos de diseño

- **Temperatura:** `sensor.temperatura_sala`, activación `above 28`, histéresis
  `2`, prioridad 40 y puntos azul–verde–rojo. Se activa sólo al superar 28 °C y
  conserva la activación dentro de la banda configurada.
- **Seguridad consultiva:** puerta abierta AND horario 22:00–06:00 AND persona
  en casa, permanencia 30 s, rojo `pulse` P90. No sustituye una alarma.
- **Energía:** consumo por encima de 3000 W durante 60 s, naranja fijo P60. La
  unidad se muestra, pero Smart LED Manager no la convierte.
- **Presencia:** persona `home` y horario permitido, todas las luces de una zona
  con prioridad baja; al salir libera su solicitud.
- **Horario:** luz de cortesía de lunes a viernes, 22:00–01:00. La madrugada del
  martes pertenece al intervalo iniciado el lunes.
- **Botón:** trigger `input_button` o evento oficial, verde `blink`, P80 y ocho
  segundos. Otra pulsación renueva esos ocho segundos sin crear otra cola.

Los destinos de reglas continuas se vuelven a resolver ante eventos oficiales
de estado y registro. Una regla temporal activa puede moverse sólo mientras no
haya vencido y conserva su fecha final. Las acciones explícitas resuelven sus
destinos al ejecutarse. Las zonas y modos existentes no cambian: cada modo
sigue limitado a las luces de su propia zona.
