# Comparación visual de C.2.5

Las catorce capturas de esta carpeta se tomaron con Smart LED Manager
instalado en Home Assistant Core 2026.11.3. Escritorio usa 1280×900 y tema
claro. Móvil usa 390×844 y tema oscuro. El conjunto completo de CI incluye
también las capturas de regresión. [35 capturas de Core](https://github.com/abel-smart-home/smart-led-manager/actions/runs/46033976627/artifacts/15216355518).

| Pantalla | Referencia | Escritorio claro | Móvil oscuro | Comparación |
| --- | --- | --- | --- | --- |
| Configuración | [17](../reference/17-configuracion.png) | [Menú](desktop-settings.png) | [Menú](mobile-settings.png) | Conserva las cinco filas, su orden y el acceso de vuelta al inicio. El panel usa los márgenes del tema y el espacio disponible junto a la barra lateral de HA. |
| General | [18](../reference/18-general.png) | [General](desktop-general.png) | [General](mobile-general.png) | Mantiene la casilla y las acciones de descarte y guardado. Añade versión y acceso al centro, con la ruta alternativa cuando la barra está oculta. |
| Prioridades | [19](../reference/19-prioridades.png) | [Prioridades](desktop-priorities.png) | [Prioridades](mobile-priorities.png) | Conserva el ejemplo de desempate, el selector de control manual, la protección de red plegada y el restablecimiento. Los valores de ejemplo de la captura proceden de preferencias guardadas en Core. El texto largo se puede leer en la lista del selector y en su explicación. |
| Recuperación | [20](../reference/20-recuperacion.png) | [Recuperación](desktop-recovery.png) | [Recuperación](mobile-recovery.png) | Conserva la tira simulada y las tres acciones. El texto describe la reevaluación actual y separa lo pendiente del Bloque D. Los botones se redistribuyen a dos filas en móvil. |
| Diagnóstico | [21](../reference/21-diagnostico.png) | [Resumen](desktop-diagnostics.png) · [Continuación](desktop-diagnostics-activity.png) | [Resumen](mobile-diagnostics.png) · [Continuación](mobile-diagnostics-activity.png) | Mantiene los contadores, modos, estado, actualización y descarga. Los datos de Core añaden las solicitudes, prioridades, órdenes pendientes, ganadoras y enmascaradas por luz. El historial se abre al final de la pantalla. |
| Configuración nativa | [22](../reference/22-nativa.png) | [Acceso](desktop-nativeSettings.png) | [Acceso](mobile-nativeSettings.png) | Mantiene la explicación del recorrido nativo y añade un enlace funcional a los ajustes de la integración instalada. |

El tema de HA determina colores, tipografía y márgenes exteriores. Las seis
pantallas se comprobaron sin desbordamiento horizontal. Las dimensiones del
inicio compacto conservan la aprobación de C.2.3. El HTML v1.0 mantiene su
SHA-256 `35ef9b8ecf4399af4605cd1bbd4687d9ff85770beb24109f62cae8153dd0f62b`.
[Prototipo](../prototypes/Smart_LED_Manager_prototipo_v1.0.html).

El diagnóstico de las capturas usa una luz de laboratorio de Core. La CI
observó la ganadora, la solicitud enmascarada y el JSON descargado. El
recorrido visual en HAOS VirtualBox y la comprobación física corresponden
al propietario. [Guía práctica](../../haos-c25-checks.md).
