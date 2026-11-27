# Comparación visual de C.2.4

El trabajo de navegador instaló la integración en Home Assistant Core
2026.11.3 y capturó el panel con el tema claro a 1280×900 y el oscuro a
390×844. Incluye las vistas de C.2.4 y las de regresión de C.2.2 y C.2.3.
[21 capturas de Home Assistant Core](https://github.com/abel-smart-home/smart-led-manager/actions/runs/45897281530/artifacts/15154790784).

Las seis vistas de pantalla de esta carpeta provienen de Home Assistant Core.
Los archivos `-full.png` muestran también el contenido desplazable. Estas
vistas completas se generaron con el mismo componente en Chromium, con luces
y sensores de laboratorio. El HTML original conserva el SHA-256
`35ef9b8ecf4399af4605cd1bbd4687d9ff85770beb24109f62cae8153dd0f62b`.
[Prototipo v1.0](../prototypes/Smart_LED_Manager_prototipo_v1.0.html).

| Pantalla | Referencia | Escritorio claro | Móvil oscuro | Comparación |
| --- | --- | --- | --- | --- |
| Notificaciones | [14](../reference/14-notificaciones.png) | [Vista](desktop-notice.png) · [Completa](desktop-notice-full.png) | [Vista](mobile-notice.png) · [Completa](mobile-notice-full.png) | Conserva nombre, destinos, tira simulada, color, brillo, efecto, duración, habilitación y opciones avanzadas. El catálogo indica el nombre de la acción nativa. Los efectos animados muestran el periodo. La prueba real aparece al abrir una definición guardada y habilitada y requiere confirmación. |
| Horarios | [15](../reference/15-horarios.png) | [Vista](desktop-schedule.png) · [Completa](desktop-schedule-full.png) | [Vista](mobile-schedule.png) · [Completa](mobile-schedule-full.png) | Conserva días, horas, destino y tira de simulación. Explica qué día se usa al cruzar medianoche. La simulación usa una fecha y hora local concreta para poder revisar el cambio de día y de hora local. |
| Regla avanzada | [16](../reference/16-avanzada.png) | [Vista](desktop-advanced.png) · [Completa](desktop-advanced-full.png) | [Vista](mobile-advanced.png) · [Completa](mobile-advanced-full.png) | Conserva todas/cualquiera, bloques de condiciones y horario opcional. El simulador permite probar lecturas concretas. El editor compatible conserva el árbol, las fuentes y los destinos avanzados existentes. |

Los formularios reutilizan los selectores buscables de zonas y luces
autorizadas del panel. Los colores, tamaños de controles de fecha y hora,
y márgenes exteriores se adaptan al tema y a la interfaz de Home Assistant.
La muestra apagada representa la salida de la simulación cuando la regla
queda inactiva. La intención de fondo de una luz depende de las solicitudes
vigentes del motor. El inicio mantiene las dimensiones aprobadas en C.2.3.
[Comparación del inicio](../c23-evidence/README.md).

La comparación automatizada cubre las tres pantallas. El propietario aprobó
la revisión visual en HAOS VirtualBox. Las pruebas físicas conservan su
registro separado. [Resultado en VirtualBox](../../haos-test-plan.md#resultado-de-c24-en-virtualbox).
