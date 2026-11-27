# Instalar y probar Smart LED Manager C.2.3 en VirtualBox

El propietario aprobó R-01–R-12, el tamaño del inicio y la validación visual
en Core 2026.11.3, sin observaciones. [Registro del propietario](haos-test-plan.md#resultado-de-c23-en-virtualbox).

Usa tu máquina de laboratorio de HAOS. La versión visible sigue siendo
**0.1.0-alpha.3**. Instala el código del SHA
`98e77d013ef03581f3aa1359d8576935effe4645`.
[Descargar el ZIP](https://github.com/abel-smart-home/smart-led-manager/archive/98e77d013ef03581f3aa1359d8576935effe4645.zip).

## Copia e instalación

1. Crea una copia completa en **Ajustes → Sistema → Copias de seguridad**.
   Descárgala a Windows. Guarda también el kit de emergencia si la copia está
   cifrada. Copia a Windows la carpeta instalada
   `custom_components/smart_led_manager` y ponle el nombre
   `smart_led_manager-anterior`. [Copias de seguridad de Home Assistant](https://www.home-assistant.io/common-tasks/general/#backups).
2. Descomprime el ZIP en Windows. En la consola de la VM, en `ha >`, escribe
   `core stop`. Sustituye la carpeta instalada
   `custom_components/smart_led_manager` por **la carpeta completa** del ZIP.
   Comprueba que contiene `manifest.json`, `frontend/smart-views.mjs` y
   `modules/rule_templates.py`. Conserva la entrada de la integración y deja
   `.storage` y `configuration.yaml` intactos.
3. En la consola escribe `core start`. Cuando vuelva Home Assistant, recarga
   la página y abre **Smart LED Manager**. Conserva una captura del inicio
   anterior si lo comparas con la misma ventana y el mismo tema.

Para volver atrás, detén Core, vuelve a poner la carpeta anterior e inicia
Core. Si quieres recuperar también los datos previos a las pruebas, restaura
la copia completa. [Restaurar una copia de HAOS](https://www.home-assistant.io/integrations/backup/#restoring-a-backup).

## Recorrido práctico

Usa una zona o una luz de prueba administrada. En **Iluminación inteligente**
elige los sensores que ya tengas disponibles. Si falta un sensor, deja
pendiente ese caso. Escoge marcas de color que se ajusten a la lectura y la
unidad que muestra el sensor.

| Caso | Qué hacer y qué observar |
| --- | --- |
| Inicio compacto | Revisa las cinco tarjetas en su orden habitual. En pantalla grande hay dos columnas y Configuración ocupa una fila. En móvil hay una columna. Comprueba que puedes llegar a todas las tarjetas con Tab o con el dedo. Abre un formulario de zona para confirmar que conserva su tamaño. |
| Menú y catálogo | Abre Iluminación inteligente y Mis automatizaciones. Comprueba nombre, categoría, destino y estado de tus reglas. Duplica una regla de prueba y verifica que la copia aparece deshabilitada. Habilítala, deshabilítala y elimínala con confirmación. |
| Temperatura y humedad | En cada plantilla elige un sensor, una luz o zona, dos valores de referencia distintos y sus colores. Prueba un valor intermedio en el simulador y cambia de gradual a rangos. Comprueba que la simulación no mueve las luces. Guarda y vuelve a abrir para comprobar los puntos y la unidad. |
| Potencia y energía | Desde Energía entra primero en Potencia instantánea, luego en Energía acumulada. Comprueba que los sensores en W o kW aparecen con potencia y los de Wh o kWh con energía. Si tienes dos sensores de la misma categoría con unidades distintas, cambia el origen y comprueba que te pide recalibrar antes de usar los puntos con la nueva unidad. |
| Seguridad y presencia | Elige una puerta o un sensor de movimiento. Prueba el estado que activa, otro que no activa y el estado no disponible en el simulador. Selecciona un destino, color, brillo y efecto. Comprueba el resultado real por separado con una luz de laboratorio, si la tienes. |
| Espera antes de finalizar | Para una regla de estado, pon 2 s de permanencia en opciones avanzadas y 8 s en **Al finalizar**. Comprueba que se activa tras 2 s. Haz que la condición deje de cumplirse, recupérala antes de 8 s y verifica que la luz mantiene la intención. Deja de cumplirla otra vez durante más de 8 s y comprueba que se aplica la intención vigente, por ejemplo el modo que siga activo. |
| Guardado y regresiones | Espera **Configuración guardada** antes de verificar el catálogo. Cambia un campo y prueba continuar, descartar y guardar al salir. Recarga la integración con un borrador abierto y comprueba que se conserva. Reinicia HAOS y revisa la regla y las luces, zonas y modos anteriores. [Recorrido C.2.2](haos-c22-checks.md#2-recorre-el-centro-de-administración). |

Para la revisión visual, captura el inicio y los formularios a 1280×900 en
claro y 390×844 en oscuro si tu navegador permite esas dimensiones. Anota
la legibilidad, el foco, la navegación táctil y cualquier elemento que se
corte. [Comparación visual](design/c23-evidence/README.md).

Si falla algo, abre **Ajustes → Sistema → Registros** y busca
`smart_led_manager` en Home Assistant Core. Anota el SHA, la versión de
Core, la pantalla y el mensaje. Si había un borrador, indica si se pudo
recuperar. Elimina secretos de los registros que compartas.
[Registros de Home Assistant](https://www.home-assistant.io/integrations/system_log/).

La matriz técnica comprobó 248 casos por versión de Core
(`2026.11.0`, `2026.11.2` y `2026.11.3`) con 85,87 % de cobertura
de ramas. El recorrido de HAOS y su revisión visual quedaron aprobados.
Las comprobaciones físicas conservan su registro separado.
[Matriz Linux del SHA funcional](https://github.com/abel-smart-home/smart-led-manager/actions/runs/45888066752).
[Plan de pruebas](haos-test-plan.md).
