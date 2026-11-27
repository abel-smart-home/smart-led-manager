# Instalar y probar Smart LED Manager C.2.4 en VirtualBox

El propietario aprobó S-01–S-08, la revisión visual y las dos comprobaciones
adicionales de ejecución real en la VM. [Registro del propietario](haos-test-plan.md#resultado-de-c24-en-virtualbox).

Usa tu máquina de laboratorio con HAOS y Home Assistant Core 2026.11.3.
La versión visible sigue siendo **0.1.0-alpha.3**. Instala el SHA
`05e0674c941f8b67f7b3a21bd66eb32a998eae68`.
[Descargar el ZIP de ese SHA](https://github.com/abel-smart-home/smart-led-manager/archive/05e0674c941f8b67f7b3a21bd66eb32a998eae68.zip).

## Copia e instalación

1. En **Ajustes → Sistema → Copias de seguridad**, crea una copia completa,
   comprueba que terminó y descárgala a Windows. Guarda el kit de emergencia
   si la copia está cifrada. Copia también a Windows la carpeta instalada
   `custom_components/smart_led_manager` con el nombre `smart_led_manager-anterior`.
   [Copias de seguridad de HAOS](https://www.home-assistant.io/common-tasks/os/#backup).
2. Descomprime el ZIP. En la consola de VirtualBox, en `ha >`, escribe
   `core stop`. Con el acceso a archivos que ya usas en la VM, reemplaza
   **la carpeta completa** `custom_components/smart_led_manager` por la del ZIP.
   Comprueba que quedaron dentro `manifest.json`, `services.yaml`,
   `frontend/plan-views.mjs` y `translations/es.json`. Conserva la entrada
   instalada de Smart LED Manager y deja `.storage` y `configuration.yaml` intactos.
3. En la consola escribe `core start`. Cuando vuelva Home Assistant, recarga
   la página, abre **Smart LED Manager** y comprueba que siguen tus luces,
   zonas, modos y reglas.

Para recuperar la instalación anterior, detén Core, vuelve a poner la carpeta
guardada e inicia Core. Esto revierte los archivos de la integración. Para
recuperar también la configuración anterior a las pruebas, restaura la copia
completa. [Restaurar una copia de HAOS](https://www.home-assistant.io/integrations/backup/#restoring-a-backup).

## Recorrido práctico en VirtualBox

Usa una luz autorizada de laboratorio. Anota el resultado de cada caso y
deja pendiente el que requiera un sensor o equipo que no tengas disponible.

| Caso | Qué hacer y qué observar |
| --- | --- |
| S-01 — Catálogo | En **Iluminación inteligente → Notificaciones**, crea un aviso con un destino de prueba. Elige color, brillo y efecto. Marca una duración corta y ajusta el periodo dentro de las opciones del efecto. Guarda, espera **Configuración guardada** y localízalo tanto en Notificaciones como en Mis automatizaciones. Ábrelo de nuevo, cambia el nombre y verifica que la edición quedó guardada. Duplica el aviso, verifica que la copia aparece deshabilitada y elimínala con confirmación. |
| S-02 — Simulación y prueba | Pulsa **Simular aviso en pantalla** con cada efecto. Observa la barra y comprueba que ningún dispositivo cambia. Con la definición guardada y habilitada, pulsa **Probar en las luces** y cancela la confirmación. La orden al motor solo se solicita al aceptar la confirmación. Registra el resultado físico aparte si la luz de laboratorio es real. |
| S-03 — Selector de Home Assistant | Desde **Ajustes → Automatizaciones y escenas → Automatizaciones**, crea una automatización de prueba. En acciones elige **Ejecutar aviso guardado** y selecciona el aviso por nombre. Guarda la automatización. En otra pestaña crea un segundo aviso, renombra el primero y elimina el segundo, recargando la página del editor después de cada cambio y comprobando la lista. El aviso renombrado sigue seleccionado en la automatización guardada. Si eliminas un aviso referenciado, elige un aviso válido antes de volver a ejecutar esa automatización. |
| S-04 — Horario diurno | En **Horarios**, elige el día de hoy y un intervalo próximo con un color identificable. Confirma que se puede guardar sin elegir un sensor. En el simulador usa la fecha de hoy: justo antes del inicio, a la hora de inicio y a la hora de fin. Debe solicitar iluminación desde el inicio hasta antes del fin. Al editar, prueba horas iguales y comprueba que el formulario pide corregirlas. |
| S-05 — Medianoche y reinicio | Crea un horario el lunes de 22:00 a 06:00. Simula lunes 22:00, martes 05:59 y martes 06:00. Los dos primeros casos deben estar activos. Para comprobar la recarga y el reinicio, usa cualquier intervalo corto que esté activo a la hora local de la VM. Recarga Smart LED Manager y después reinicia Home Assistant dentro del intervalo. Comprueba que se recupera la regla vigente y que al deshabilitarla se libera su solicitud. |
| S-06 — Condiciones combinadas | En **Regla avanzada**, combina un estado real y un umbral numérico sin limitar por horario. En **Simular las condiciones**, prueba un valor compatible y otro incompatible para cada entidad. Con **Todas** se requieren las dos condiciones y con **Cualquiera** basta una condición válida que se cumpla. Comprueba que una lectura no disponible no activa por sí sola la regla. Activa después **Limitar por horario** y prueba fuera de ese intervalo. La simulación deja las luces sin cambios. |
| S-07 — Guardado y borradores | Edita un horario y pulsa **Cancelar**. Prueba **Continuar editando**, luego **Descartar cambios y salir**. Comprueba que el catálogo conserva el valor anterior. Haz otro cambio, recarga la integración desde **Dispositivos y servicios** y comprueba que el borrador sigue abierto. Guarda y espera la confirmación. Reinicia y revisa los avisos, horarios y condiciones guardados, además de una regla anterior de C.2.3. |
| S-08 — Revisión visual | Compara Notificaciones, Horarios y Regla avanzada con la referencia, además del menú compacto aprobado. Revisa texto, foco de teclado, controles táctiles y opciones avanzadas en escritorio claro y móvil oscuro. [Capturas y diferencias](design/c24-evidence/README.md). |

## Con una luz física de laboratorio

Usa un modo de fondo y un aviso de prioridad mayor que actúe sobre esa misma
luz. Ejecuta el aviso, repítelo antes de que venza y comprueba que dura desde
la última ejecución. Cambia el modo de fondo durante el aviso. Al terminar,
debe verse el modo vigente. Después ejecuta el aviso bajo una solicitud de
mayor prioridad y retira esa solicitud cuando el aviso haya vencido. El aviso
vencido no debe reaparecer. Prueba por separado guardar un cambio en un aviso
en ejecución y eliminarlo. Guardar los cambios recarga la integración y
finaliza los avisos temporales activos. Al reiniciar se conservan las
definiciones guardadas y se vuelven a evaluar los horarios y las condiciones.

## Si aparece un error

Abre **Ajustes → Sistema → Registros** y busca `smart_led_manager` en el
registro de Home Assistant Core. En la consola de la VM también puedes usar
`core logs`. Si falla una automatización, abre su **Traza** para ver qué acción
falló. Anota el SHA, la versión de Core, el caso, la hora local, el mensaje de
error y si se conservó el borrador. Omite secretos al compartir los registros.
[Registros de Home Assistant](https://www.home-assistant.io/integrations/system_log/).

Codex comprueba en CI la concurrencia de guardado, WebSocket, vencimiento,
prioridad, cambios de hora local, esquemas y compatibilidad. El recorrido de
VirtualBox y los resultados físicos se registran al recibir la confirmación
del propietario. [Plan de pruebas](haos-test-plan.md#resultado-de-c24-en-virtualbox).
