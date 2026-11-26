# Validación práctica de C.2.1 en HAOS

Usa una copia de HAOS de laboratorio con una luz Demo autorizada y un ayudante
interruptor. Guarda una copia de seguridad e instala la carpeta completa del
commit C.2.1 que quieras probar. Conserva la entrada existente y registra el
SHA instalado, la versión de HA, el navegador y la fecha. A partir de este
commit el panel usa un identificador de recursos de C.2.1 y el manifiesto
continúa en `0.1.0-alpha.3`.

1. **Guardar.** Abre `/smart-led-manager-editor` como administrador. Crea una
   regla deshabilitada sobre el ayudante y la luz Demo. Guarda y comprueba que,
   tras la recarga, regresa al catálogo en la misma URL. Reabre la regla y
   verifica los datos. Repite al editar su prioridad. En C.1 el paso de
   edición de C-03 permanecía en el formulario. C.2.1 aplica el regreso al
   catálogo previsto en el [diseño de navegación](design/navigation.md).
2. **Borrador.** Cambia el nombre y pulsa **Cancelar**. Elige **Continuar
   editando** y comprueba que sigue el nombre nuevo. Abre el diálogo con
   **Volver**, cancélalo con Escape y verifica que el foco vuelve al botón.
   Repite y prueba **Descartar cambios y salir**. El catálogo debe conservar
   el nombre guardado. Repite con **Guardar y salir** y espera la confirmación
   antes de comprobar el nombre nuevo.
3. **Concurrencia.** Abre la misma regla en dos sesiones de administrador.
   Guarda primero en una y después en la otra. La segunda debe mostrar
   conflicto y conservar su borrador. Repite con Options Flow abierto en una
   sesión. Confirma que sólo el primer cambio se aplicó. Una cuenta sin
   permisos de administración debe quedar fuera del panel y del catálogo.
4. **Recarga nativa.** Con un borrador abierto, desde otra pestaña usa
   **Ajustes → Dispositivos y servicios → Smart LED Manager → Recargar**.
   Comprueba que se conserva `/smart-led-manager-editor` y que el borrador
   permanece. Si no llega la notificación de estado, pulsa **Comprobar
   estado**. Comprueba que **Guardar** vuelve a estar disponible.
5. **Desconexión y reapertura de la conexión.** En la copia de laboratorio,
   interrumpe y restablece la conexión del navegador durante un guardado.
   Confirma que el borrador sigue presente mientras se verifica el resultado y
   que en el catálogo sólo hay una copia. Si se informa de un fallo, conserva
   la hora, el mensaje y el registro de HA antes de volver a enviar.

El diálogo usa `<dialog>` para foco, tabulación y Escape. Conserva los tres
caminos y el orden del prototipo v1.0. El fondo, el borde y el color de foco
usan el tema de Home Assistant. Toma capturas de la edición y del diálogo con
la misma regla a 1280×900 claro y 390×844 oscuro y anota las diferencias del
tema y del marco de HA. La prueba de Edge usa un backend simulado.

Este recorrido se registra aparte, junto al [plan de HAOS](haos-test-plan.md).
Conserva C-01–C-20, U-01–U-06 y las repeticiones sobre Raspberry Pi/ZHA como
pruebas distintas. En Zigbee, M-06 sigue requiriendo dos controladores.
