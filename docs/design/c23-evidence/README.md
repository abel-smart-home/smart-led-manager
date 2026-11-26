# Comparación visual de C.2.3

Las capturas del componente en Chromium usan luces y sensores de laboratorio.
Escritorio usa 1280×900 en claro y móvil usa 390×844 en oscuro. Los archivos
`-full.png` muestran la página completa de cada formulario a partir de esas
anchuras. El [HTML v1.0](../prototypes/Smart_LED_Manager_prototipo_v1.0.html)
se conserva íntegro.

El trabajo **browser** de CI también abre la integración instalada en Home
Assistant Core 2026.11.3 con sensores y luces de laboratorio. Publica
`ha-core-panel-c23` con las capturas del panel y la interfaz nativa de HA.
[Ejecuciones de CI](https://github.com/abel-smart-home/smart-led-manager/actions/workflows/ci.yml).

| Pantalla | Referencia | Escritorio claro | Móvil oscuro | Diferencia comprobada |
| --- | --- | --- | --- | --- |
| Inicio | [01](../reference/01-inicio.png) · [23 móvil](../reference/23-movil-inicio.png) · [C.2.2](../c22-evidence/desktop-home.png) | [Inicio compacto](desktop-home.png) | [Inicio compacto](mobile-home.png) | El propietario aprobó centrar y compactar el menú. Conserva las cinco tarjetas, sus textos, iconos, colores y orden. |
| Iluminación inteligente | [07](../reference/07-inteligente.png) | [Menú](desktop-smart.png) | [Menú](mobile-smart.png) | Nueve entradas en el orden de referencia. Las últimas entradas de la pantalla quedan accesibles por desplazamiento. Los tres accesos que se completarán en C.2.4 usan funciones existentes. |
| Mis automatizaciones | [08](../reference/08-automatizaciones.png) | [Catálogo](desktop-automation-list.png) | | El catálogo compartido añade el color, prioridad, destino, estado y acciones de duplicar y eliminar. |
| Temperatura | [09](../reference/09-temperatura.png) | [Formulario](desktop-temperature.png) · [Completo](desktop-temperature-full.png) | [Formulario](mobile-temperature.png) · [Completo](mobile-temperature-full.png) | Origen buscable, destinos, puntos y gráfico. Un valor exacto en la unidad del sensor alimenta la simulación. |
| Humedad | [10](../reference/10-humedad.png) | [Formulario](desktop-humidity.png) · [Completo](desktop-humidity-full.png) | | Comparte el editor de puntos, con etiqueta y origen de humedad. |
| Energía | [11](../reference/11-energia.png) | [Potencia](desktop-power.png) · [Energía](desktop-energy.png) · [Potencia completa](desktop-power-full.png) · [Energía completa](desktop-energy-full.png) | [Energía](mobile-energy.png) · [Completo](mobile-energy-full.png) | La elección de potencia o energía ocurre antes del formulario. Cada plantilla conserva su unidad exacta. |
| Seguridad | [12](../reference/12-seguridad.png) · [25 móvil](../reference/25-movil-seguridad.png) | [Formulario](desktop-security.png) · [Completo](desktop-security-full.png) | [Formulario](mobile-security.png) · [Completo](mobile-security-full.png) | **Al finalizar** está visible. La permanencia se configura por separado. La simulación indica desconexión y el propósito complementario de seguridad. |
| Presencia | [13](../reference/13-presencia.png) | [Formulario](desktop-presence.png) · [Completo](desktop-presence-full.png) | [Formulario](mobile-presence.png) · [Completo](mobile-presence-full.png) | Comparte el editor de estados con opciones propias de ocupación y presencia. |

Los controles mantienen las variables de tema de HA y presentan por separado
zonas y luces autorizadas. Las reglas con destinos o condiciones avanzadas
abren el editor compatible para preservar su configuración. La aprobación
visual definitiva sigue pendiente. [Guía del propietario](../../haos-c23-checks.md).
