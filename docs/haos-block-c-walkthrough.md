# Guía de laboratorio para C-01 a C-20

Realiza los casos en una copia aislada de HAOS VirtualBox. Guarda una copia
completa antes de empezar y otra cuando termines de preparar el laboratorio.
Anota el SHA instalado, fecha y hora local, zona horaria, versión de Core,
navegador y evidencia observada por cada caso. B.1 conserva su resultado
histórico 10/10 sobre `6ad79e0`. Los casos de esta guía comienzan pendientes.

## Preparación

1. En **Ajustes → Dispositivos y servicios → Entidades**, identifica tres
   luces Demo con color. En esta guía se llaman **Demo A**, **Demo B** y
   **Demo externa**. Apunta sus nombres reales. Si sólo tienes dos luces,
   deja pendiente la parte de exclusiones hasta disponer de una tercera.
2. En **Ajustes → Dispositivos y servicios → Integraciones → Smart LED
   Manager → Configurar → Luces administradas**, habilita sólo A y B. En
   **Zonas**, crea **Lab A** para A y **Lab B** para B. En **Modos de
   iluminación**, crea **Base A** y **Base B**, fijos, azules, prioridad 20,
   brillo 160, transición 0. Activa cada modo desde su selector.
3. En **Ajustes → Dispositivos y servicios → Ayudantes → Crear ayudante**, crea
   tres **Interruptores** llamados **Lab puerta**, **Lab presencia** y
   **Lab alarma**. Crea **Lab temperatura** de tipo **Número**, de −20 a 100,
   paso 1, unidad °C. Crea **Lab botón** de tipo **Botón**. Empieza con los
   interruptores apagados y la temperatura en 20.
4. En **Herramientas de desarrollo → Estados** puedes comprobar la entidad
   Demo, su estado y sus atributos de color. Para cambiar un ayudante de
   manera normal, usa su tarjeta o su diálogo de más información. En las
   pruebas de estados inválidos usa **Establecer estado** para simular el
   dato. Cambiar ahí el estado de una luz tampoco envía un comando físico.
5. Abre **Smart LED Manager → Reglas inteligentes** desde la barra lateral.
   Si el acceso lateral está oculto, abre **Configururar → Centro de
   administración** en la integración y sigue el enlace. En los pasos
   siguientes, **catálogo** se refiere a **Reglas inteligentes**.

### Valores de referencia y registro

Una **regla base de estado** usa **Lab puerta**, operador **Igual**, estado
`on`, Demo A, rojo `#FF0000`, brillo 180, transición 0, estilo fijo y
prioridad 60. Déjala habilitada, sin condiciones, horario ni permanencia
salvo indicación del caso. Un **aviso base** es de tipo **Evento**, apunta a
Demo A, usa naranja `#FF8000`, brillo 180, transición 0, prioridad 80,
duración 8 s y estilo fijo.

Abre el diagnóstico de la entrada mediante **Ajustes → Dispositivos y
servicios → Integraciones → Smart LED Manager → menú ⋮ → Descargar
diagnósticos** si el resultado visual es ambiguo. Las luces Demo pueden
mostrar el color en RGB o en otro formato equivalente. Comprueba también
**Ajustes → Sistema → Registros**. Usa **Aprobado** cuando se cumplan todos
los resultados del caso, **Fallido** si diverge alguno reproducible,
**Parcial** cuando sólo se cubra una variante y **Pendiente** si no se
ejecutó. Anota por separado las variantes automatizadas o de hardware.

## C-01 · Actualización sobre la entrada B.1

**Objetivo y preparación.** Comprueba identidad y opciones existentes. Desde
B.1 conserva una regla base **Lab legado** y una regla numérica **Lab escala**
con Demo B, prioridad 40, brillo 180 e interpolación entre 20/azul y 30/rojo.
Anota el ID de la entrada, los nombres/IDs de selectores y switches y el número
de reglas. Descarga los diagnósticos de referencia.

**Pasos y comprobación.** Detén Core, sustituye la carpeta completa por el
SHA C.1 y vuelve a iniciar, siguiendo [Instalación](installation.md). Abre
**Integraciones → Smart LED Manager** y luego el catálogo. Confirma una sola
entrada, ambos modos y las dos reglas, sus IDs, luces y puntos. A 20 Demo B
debe estar azul y al activar la puerta, Demo A roja. Apaga la puerta y comprueba
azul de nuevo. **Aprueba** si se conservan la identidad y el comportamiento.
**Limpieza.** Conserva ambas reglas para C-02 y después restaura el laboratorio.

## C-02 · Compatibilidad de reglas heredadas

**Objetivo y preparación.** Usa las dos reglas previas. Una variante sin
`enabled` requiere una copia anterior que realmente contenga ese formato.

**Pasos y comprobación.** En el catálogo abre **Lab legado** y descarta.
Activa y desactiva la puerta y comprueba rojo y luego azul. En **Lab escala**
introduce 20, 25 y 30. Debe dar azul, violeta `#800080` y rojo. Reabre y
confirma puntos, prioridad y brillo. **Aprueba** ambas si se conservan esos
datos y resultados. La variante heredada sin `enabled` tiene cobertura
automatizada si tu copia no contiene una regla de ese formato.
**Limpieza.** Devuelve la temperatura a 20 y deshabilita las reglas heredadas
para que no interfieran con C-03 en adelante.

## C-03 · CRUD y permanencia de la ruta

**Objetivo y preparación.** Usa una cuenta administradora en
`/smart-led-manager-editor` y el laboratorio inactivo.

**Pasos y comprobación.** Crea **C03 estado** con la regla base; **C03 número**
con temperatura, Demo B, prioridad 40, color fijo verde `#00FF00` y activación
por encima de 26; y **C03 botón** con el aviso base y **Pulsación de un
ayudante → Lab botón**. Después de cada alta deben aparecer el mensaje de
guardado y el catálogo en el mismo panel. Edita los nombres y la prioridad a
62/42/82. Tras guardar debes seguir en el editor, ver el nuevo valor y poder
volver al catálogo. Duplica cada regla, comprueba que la copia empieza
deshabilitada, actívala, desactívala y elimínala con confirmación. Descarta otra
edición y comprueba que el nombre anterior sigue vigente. **Aprueba** si el
panel conserva su URL, los cambios persisten y el descarte no cambia luces ni
el catálogo. Anota como fallo cualquier salto a `/home/overview`.
**Limpieza.** Elimina las tres reglas y sus copias.

## C-04 · Zonas y luces superpuestas

**Objetivo y preparación.** Mantén **Base A** y **Base B** activos.

**Pasos y comprobación.** Crea **C04 zonas**, regla base con Demo A elegida
individualmente, más **Lab A** y **Lab B** en Destinos. Pulsa **Previsualizar
destinos**. A y B deben aparecer una vez cada una y A en duplicados. Antes de
guardar, ambas luces siguen azules. Guarda, activa la puerta, comprueba que
ambas quedan rojas y luego azules al apagarla. Confirma que cada selector de
modo conserva su zona. **Aprueba** si la vista previa y el estado final
coinciden. Repite en Zigbee con dos controladores si están disponibles.
**Limpieza.** Elimina la regla y apaga la puerta.

## C-05 · Áreas, etiquetas y exclusiones

**Objetivo y preparación.** Crea **Área Lab C** y **Etiqueta Lab C** desde
**Ajustes → Áreas, etiquetas y zonas**. Asigna A y Demo externa al área y a la
etiqueta desde sus fichas en **Dispositivos y servicios → Entidades**. Anota
las asignaciones anteriores para recuperarlas.

**Pasos y comprobación.** Crea la regla base **C05 área**, quita el destino
individual y elige el área y la etiqueta de laboratorio. Previsualiza. Debe
mostrar A efectiva y deduplicada, Demo externa excluida. Guarda, cambia
puerta de apagado a encendido y verifica rojo sólo en A. Apágala y verifica
azul en A y cero cambios en Demo externa. **Aprueba** con ambos filtros y
sin efectos fuera de la selección autorizada.
**Limpieza.** Elimina la regla, devuelve las asignaciones previas y retira
el área y la etiqueta temporales.

## C-06 · Grupos transparentes e inseguros

**Objetivo y preparación.** Crea un **Grupo de luces** en **Ayudantes → Crear
ayudante → Grupo** llamado **Lab grupo interno** con B y **Lab grupo
externo** con A y el grupo interno, si HA permite seleccionarlo. Usa además
**Lab no autorizado** con A y Demo externa.

**Pasos y comprobación.** Crea **C06 grupos** con la regla base, sólo el
grupo externo como destino, y previsualiza. Debe resolver A y B. Guarda y
activa la puerta para verificar ambas. Repite en un borrador seleccionando
**Lab no autorizado**. Debe aparecer un error que identifique la selección
insegura y el guardado debe rechazarse. En **Configurar → Luces
administradas**, verifica que intentar autorizar un grupo tampoco se acepta.
**Aprueba** sólo la parte que se pueda reproducir. Ciclos, miembros ausentes
y grupos opacos se verifican en las pruebas automatizadas si el Options Flow
de HA impide construirlos. No edites archivos internos para forzar un ciclo.
**Limpieza.** Elimina la regla y luego los grupos desde Ayudantes.

## C-07 · Todas las administradas y selección vacía

**Objetivo y preparación.** Usa A, B y Demo externa.

**Pasos y comprobación.** Crea **C07 todas** con la regla base, Demo A y
**Todas las luces administradas**. Previsualiza A y B, A como duplicada y sin
Demo externa efectiva. Guarda y activa la puerta. Apágala y edita la regla:
retira A y desmarca **Todas**. Previsualizar y guardar deben informar que
falta un destino. El borrador debe quedar abierto y la regla registrada debe
seguir con la selección anterior. **Aprueba** si los resultados se cumplen.
**Limpieza.** Descarta y elimina C07.

## C-08 · Cambio de membresía durante una regla activa

**Objetivo y preparación.** Crea **Lab C08 grupo** con A. Si se pueden crear
grupos anidados en esta instancia, crea **Lab C08 interno** con B pero no lo
añadas aún. Crea la regla base **C08 dinámico** sólo sobre el primer grupo.

**Pasos y comprobación.** Activa la puerta y confirma A roja y B azul. Desde
**Ayudantes**, cambia los miembros del grupo a B o a **Lab C08 interno**.
Sin tocar la puerta, A debe volver a azul y B pasar a rojo. Si hay grupo
interno, cambia su composición a A y comprueba el cambio inverso. Añade una
luz ajena al grupo y comprueba liberación. Retírala y comprueba recuperación.
Si se renombra un miembro, revisa que sólo vuelvan a aplicarse destinos
resolubles y autorizados. La misma prueba se puede hacer cambiando la
etiqueta de A a B en las fichas de entidad, con una regla sobre esa etiqueta.
**Aprueba** si cada cambio válido se refleja sin reenviar la regla. Registra
qué variantes pudiste ejecutar y repite en Zigbee donde corresponda.
**Limpieza.** Apaga la puerta, elimina la regla y restaura grupos/etiquetas.

## C-09 · Condiciones anidadas y estados inválidos

**Objetivo y preparación.** Crea **C09 condiciones** con la regla base y un
grupo **Todas (AND)**. El primer hijo es **Al menos una (OR)** con
**Lab presencia = on** y **Lab temperatura por encima de 24**. El segundo es
**Negar (NOT)** con **Lab alarma = on**.

**Pasos y comprobación.** Pon la puerta en encendido y conserva presencia
apagada, alarma apagada y temperatura 20. Espera azul. Enciende sólo la
presencia y espera rojo. Apágala y fija 25 para recuperar rojo por la otra
rama. Enciende alarma y espera azul. Desde Estados establece primero
`unknown` y luego `unavailable` en alarma. A debe seguir en azul. Devuelve
alarma a apagado y confirma rojo sin tocar la puerta. **Aprueba** si cada
fuente secundaria cambia el resultado como se indica.
**Limpieza.** Restaura ayudantes, elimina C09.

## C-10 · Horario diurno, nocturno y reinicio dentro de un intervalo

**Objetivo y preparación.** Crea **C10 horario** con la regla base y activa
la puerta. Consulta la hora local en **Ajustes → Sistema → General**. Para
la variante rápida, en **Horario** elige el día de hoy, desde dos minutos
después de guardar hasta cuatro minutos después.

**Pasos y comprobación.** Guarda antes de la hora inicial y observa azul.
Sin tocar la puerta, en el inicio debe cambiar a rojo. Reinicia Core dentro
de un nuevo intervalo de al menos diez minutos y comprueba que arranca en
rojo cuando la puerta sigue encendida. Al llegar al final, espera azul.
Para la variante nocturna configura 22:00–06:00 y selecciona sólo el día de
inicio. Confirma el aviso de cruce, rojo desde 22:00, continuidad tras
medianoche y azul a 06:00. Si puedes, reinicia Core entre medianoche y las
06:00 del día siguiente y confirma que el cierre sigue ocurriendo a las
06:00. Si no puedes esperar al cruce, conserva esa
variante como pendiente manual y registra la cobertura automatizada. Igual
para una transición de hora de verano fuera de las fechas de laboratorio.
**Aprueba** cuando estén comprobados los límites que reportes.
**Limpieza.** Apaga la puerta y elimina C10.

## C-11 · Permanencia, cancelación y recarga

**Objetivo y preparación.** Crea **C11 permanencia** con la regla base y
**Permanencia mínima → 15 segundos**.

**Pasos y comprobación.** Activa la puerta durante 5 s y apágala. La luz
sigue azul incluso después de 15 s. Actívala de nuevo 15 s y espera rojo.
Apágala y espera azul. Actívala, y a los 5 s abre **Integraciones → Smart
LED Manager → menú ⋮ → Recargar**. Mide desde que termina la recarga:
la regla debe esperar 15 s completos antes de rojo. **Aprueba** si ningún
contador antiguo aplica una orden y el tiempo de espera se reinicia.
**Limpieza.** Apaga la puerta y elimina C11.

## C-12 · Límites exactos y estilo numérico

**Objetivo y preparación.** Crea **C12 umbral** para Lab temperatura,
Demo A, prioridad 60, color fijo magenta `#FF00FF`, brillo 180, transición 0,
intervalo y variación mínima 0, histéresis 0.

**Pasos y comprobación.** Selecciona **Por encima de 28** y pasa por
27, 28, 29. Debe activarse sólo al pasar a 29. Cambia la regla a **Por debajo
de 28** y pasa por 29, 28, 27. Debe activarse al entrar en 27. Empieza cada
variante desde el estado inactivo. Para **Dentro** usa límites 20 y 30 y
valores 19, 20, 25, 30 y 31; los tres centrales activan. Para **Fuera** usa
20, 19, 20, 30 y 31; sólo 19 y 31 activan. Guarda con interpolación entre
20/azul y 30/rojo y vuelve a **Dentro**: a 25 verás violeta. Con **Rangos**
el mismo 25 da azul. Comprueba °C en umbral, gráfica y simulador. **Aprueba**
si activación y color se comportan independientemente.
**Limpieza.** Elimina C12 y deja Lab temperatura en 20.

## C-13 · Histéresis, invalidación y recuperación

**Objetivo y preparación.** Usa la configuración fija de C12 con **Por
encima de 28**, histéresis 2 y temperatura inicial 27.

**Pasos y comprobación.** 27 y 28 dejan azul; 29 cambia a magenta. Baja
a 28, 27 y 26 y observa que se mantiene. A 25 vuelve a azul. Sube a 29 y
aplica `unknown` desde Estados: debe volver a azul. Restablece 27, que
debe quedar azul hasta que subas a 29. Repite con `unavailable` y con
`NaN` como texto. Si la UI no acepta un dato simulado, registra ese caso
como automatizado. **Aprueba** si no se interpreta un inválido como cero
y cada recuperación comienza desde inactivo.
**Limpieza.** Restaura 20 desde el ayudante y elimina C13.

## C-14 · Botón y cambio de estado

**Objetivo y preparación.** Crea el aviso base **C14 botón** con
**Pulsación de un ayudante → Lab botón**. Crea **C14 estado** con
**Cambio de estado → Lab puerta → Estado nuevo on**, color verde,
prioridad 81 y 8 s.

**Pasos y comprobación.** Desde el diálogo del botón pulsa una vez y
comprueba naranja, luego azul tras 8 s. Activa puerta y déjala encendida
15 s. Debe haber verde sólo durante 8 s. Apagar puerta no activa. **Aprueba**
si ambos orígenes producen avisos puntuales y la puerta no queda controlando
de manera persistente.
**Limpieza.** Elimina ambas y apaga la puerta.

## C-15 · Bus, entidad de evento y descarte irreversible

**Objetivo y preparación.** Crea **C15 bus** con el aviso base y
**Evento del bus → slm_lab_c15**, sin datos adicionales. Añade la
condición **Lab presencia = on**. Si tienes una entidad del dominio
`event`, crea **C15 entidad** con esa entidad, color verde y 8 s.

**Pasos y comprobación.** Con presencia apagada abre **Herramientas de
desarrollo → Eventos → Disparar un evento**, escribe `slm_lab_c15` en
**Tipo de evento**, deja datos vacíos y pulsa **Disparar evento**. No debe
aparecer naranja. Enciende presencia, espera 10 s y confirma que no aparece
el aviso anterior. Dispara uno nuevo, comprueba naranja y luego azul. Para
la entidad `event`, acciona su fuente legítima y comprueba verde y vuelta
a azul. Si la única opción es un origen simulado, registra esa evidencia por
separado. **Aprueba** ambos orígenes si se ejecutaron. Marca la parte de
entidad pendiente de hardware si no existe en la instancia.
**Limpieza.** Elimina las reglas y apaga presencia.

## C-16 · Disparador publicado por un dispositivo

**Objetivo y preparación.** Elige un dispositivo de prueba que ofrezca una
acción repetible, por ejemplo un mando. Para verificar qué expone, abre
**Ajustes → Automatizaciones y escenas → Crear automatización → Añadir
disparador → Dispositivo** y lista sus acciones. Descarta ese borrador.

**Pasos y comprobación.** Crea **C16 dispositivo** con el aviso base,
**Disparador de dispositivo**, el dispositivo y la acción publicada.
Acciónalo y comprueba naranja y azul. Deshabilita C16 y repite. No debe
emitirse un aviso. Si un dispositivo carece de disparadores, el selector
debe ofrecer una lista vacía y rechazar un borrador incompleto al guardar.
**Aprueba** sólo los pasos observados. La ruta de validación de triggers está
cubierta en CI. El mando físico y los disparadores que publique tu integración
requieren verificación en la instancia.
**Limpieza.** Elimina C16 y cualquier borrador de automatización.

## C-17 · Repetición, enmascaramiento y vencimiento

**Objetivo y preparación.** Crea el aviso base **C17 aviso** con Lab botón,
prioridad 80 y 8 s. Crea **C17 máscara** con Lab puerta, Demo A, rojo fijo
y prioridad 98.

**Pasos y comprobación.** Activa la puerta. Pulsa el botón a t=0, t=2 y
t=4 s. Debe verse rojo todo el tiempo. En diagnósticos debe haber como
máximo una intención para el aviso. A t=14 s apaga la puerta y comprueba que
A vuelve directamente a azul. Pulsa dos veces sin máscara, con 2 s entre
pulsaciones, y confirma que el aviso dura 8 s desde la última. **Aprueba**
si no se acumulan avisos, animaciones ni colores vencidos. Repite en Zigbee.
**Limpieza.** Elimina ambas reglas.

## C-18 · Edición de una regla activa bajo otra prioridad

**Objetivo y preparación.** Crea **C18 vigente** con Lab presencia,
Demo A, verde, prioridad 60. Crea **C18 máscara** con Lab puerta, A y B,
rojo, prioridad 98.

**Pasos y comprobación.** Activa presencia y puerta. A y B deben quedar
rojas. Edita C18 vigente a Demo B, magenta y prioridad 65. Guarda bajo la
máscara y comprueba que siguen rojas. Apaga puerta y verifica A azul,
B magenta. Vuelve a activar puerta, deshabilita C18 vigente y apaga puerta.
Ambas deben quedar azules. **Aprueba** si se recupera la definición vigente
exactamente cuando corresponde. Repite en Zigbee donde sea posible.
**Limpieza.** Desactiva ayudantes y elimina ambas reglas.

## C-19 · Revisiones concurrentes, permisos y previsualización

**Objetivo y preparación.** Abre dos sesiones administradoras y una cuenta
normal de laboratorio creada en **Ajustes → Personas → Usuarios**.
Crea **C19 conflicto** usando el ejemplo numérico de C-02 en Demo A.

**Pasos y comprobación.** Edita la misma regla en dos sesiones. En la
primera pon prioridad 64 y guarda; sin volver a cargar la segunda, intenta
guardar prioridad 66. Debe mostrar conflicto y conservar el borrador. Abre
un formulario nativo de la regla, guarda un cambio desde el panel e intenta
guardar el formulario nativo antiguo. Debe rechazarse. Con la cuenta
normal prueba la URL del panel; el catálogo y comandos quedan inaccesibles.
Como administrador simula el color de 25 y previsualiza un destino distinto
sin guardar. Verifica que ni los diagnósticos ni el color de A cambian. El
bloqueo durante la descarga se verifica también en CI porque en HAOS
la ventana puede durar menos de un segundo. **Aprueba** las variantes
observadas y registra las automáticas aparte.
**Limpieza.** Descarta el borrador, elimina la regla y la cuenta temporal.

## C-20 · Reinicio, limpieza definitiva y regresiones

**Objetivo y preparación.** Usa una copia nueva del laboratorio. Crea un
aviso de botón en pulsación con duración 60 s y una regla continua tras
15 s de permanencia. Conserva los modos de zona y el editor numérico.

**Pasos y comprobación.** Pulsa el botón y empieza la permanencia; durante
ambos, recarga la integración. Revisa que el aviso no se repita y que el
contador empiece de nuevo. Repite con **Ajustes → Sistema → Reiniciar Home
Assistant**. Comprueba barra, gráfica, teclado, simulación, Restaurar y
Descartar, y los modos de A/B. En la instancia aislada usa **Integraciones →
Smart LED Manager → menú ⋮ → Eliminar**. Tras 60 s no deben quedar panel,
entidades propias ni animaciones. Añade de nuevo la integración y autoriza
A. Debe comenzar sin reglas, modos ni solicitudes antiguas. **Aprueba** si
se observa toda la limpieza. Valida recuperación y ausencia de órdenes
tardías sobre Zigbee siguiendo además R-01 y R-02 si hay hardware.
**Limpieza.** Vuelve a la copia de seguridad de laboratorio o elimina sólo
los ayudantes y ajustes temporales creados para C.

## Repetición física y resultados

Repite C-04, C-08, C-12, C-13, C-17, C-18 y C-20 sobre Raspberry Pi/ZHA y
luces reales donde corresponda. M-06 requiere dos controladores Zigbee.
Conserva aparte los pendientes de A/B/B.1 y Alexa/Matter. Registra el
resultado en el [plan HAOS](haos-test-plan.md) con el SHA realmente
instalado. Ejecutar una prueba automatizada no cambia la columna de
validación manual.
