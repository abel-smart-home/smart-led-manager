# Comparación visual de C.2.2

Las capturas muestran el componente del panel en Chromium con respuestas
WebSocket de prueba y datos equivalentes a los del [prototipo HTML v1.0](../prototypes/Smart_LED_Manager_prototipo_v1.0.html).
Se usaron 1280×900 en claro y 390×844 en oscuro. Las capturas de página
completa del editor de modos complementan las del área visible inicial.
Quedan pendientes las capturas con la cabecera, la barra lateral y el tema
activo de una instalación de HAOS. [Validación en VirtualBox](../../haos-c22-checks.md).

| Pantalla | Referencia v1.0 | Escritorio claro | Móvil oscuro | Comparación |
| --- | --- | --- | --- | --- |
| Inicio | [01](../reference/01-inicio.png) · [23 móvil](../reference/23-movil-inicio.png) | [Captura](desktop-home.png) | [Captura](mobile-home.png) | Cinco tarjetas en el orden aprobado, con dos columnas más una fila completa en escritorio y una columna en móvil. A 844 px de alto se desplaza para ver completa la última tarjeta. Los iconos son equivalentes y los colores y fondos se adaptan al tema. El pie indica la versión instalada. |
| Luces administradas | [02](../reference/02-luces.png) | [Captura](desktop-lights.png) | [Captura](mobile-lights.png) | Selector desplegable con búsqueda, nombre amigable, casillas y recuento. Selección inicial basada en las autorizaciones guardadas. La búsqueda tiene un nombre accesible y la lista se limita a luces compatibles e individuales. |
| Zonas | [03](../reference/03-zonas.png) | [Captura](desktop-zones.png) | | Listado de nombre y luces, acceso directo a editar y botón **Crear zona**. |
| Crear y editar zona | [04](../reference/04-editar-zona.png) | [Crear](desktop-create-zone.png) · [Editar](desktop-edit-zone.png) | [Editar](mobile-edit-zone.png) | Nombre, área de HA y selección de luces autorizadas. La edición incluye **Eliminar zona** con confirmación; el servidor protege las dependencias. |
| Modos de iluminación | [05](../reference/05-modos.png) | [Listado](desktop-modes.png) · [Modo activo](desktop-active-mode.png) | [Listado](mobile-modes.png) | Grupos por zona, color, brillo, efecto y control externo cuando está habilitado. El estado activo también distingue si el motor aplica el modo, si otra solicitud lo oculta y si faltan luces disponibles. |
| Crear y editar modo | [06](../reference/06-crear-modo.png) · [24 móvil](../reference/24-movil-modo.png) | [Crear](desktop-create-mode.png) · [Editar](desktop-edit-mode.png) · [Vista completa](desktop-create-mode-full.png) | [Crear](mobile-create-mode.png) · [Vista completa](mobile-create-mode-full.png) | Orden de campos, paleta, tira simulada, control externo y opciones avanzadas. Los efectos se limitan a fija, pulso y parpadeo. El interruptor empieza desmarcado para que la exposición al puente de voz sea explícita. Los ajustes avanzados conservan el subconjunto de luces y otros valores del modo. |
| Iluminación inteligente | [07](../reference/07-inteligente.png) · [08](../reference/08-automatizaciones.png) | [Catálogo actual](desktop-smart.png) | | Abre el catálogo operativo de reglas de C.2.1. Las entradas por plantilla de la referencia corresponden a etapas posteriores. |
| Configuración | [17](../reference/17-configuracion.png) · [22](../reference/22-nativa.png) | [Acceso a la configuración nativa](desktop-settings.png) | | La tarjeta enlaza a los ajustes de la integración que ya existen en Home Assistant. Las vistas específicas General, Prioridades, Recuperación y Diagnóstico quedan según el roadmap. |
| Salida con cambios | [Navegación aprobada](../navigation.md) | [Diálogo](desktop-draft-exit.png) | | El diálogo de C.2.1 conserva las tres opciones. Si se rechaza un guardado, muestra el error y conserva el borrador. |

El panel usa variables de tema de Home Assistant y controles de formulario del
navegador. Las confirmaciones de eliminación usan el diálogo del navegador, igual
que el catálogo de reglas existente. El guardado se habilita al introducir los
datos requeridos. El recorrido de Chromium comprueba el ancho de todas las
capturas y ejercicios de navegación, búsqueda, dependencias, borradores,
activación exclusiva y simulación. La comparación de aspecto en HAOS forma parte
de la comprobación práctica del propietario.
