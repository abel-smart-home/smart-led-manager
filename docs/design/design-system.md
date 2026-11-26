# Sistema visual
Usar las reglas CSS del HTML como referencia cuantitativa, no rediseñar a criterio del implementador. La carcasa y controles nativos de HA pueden requerir diferencias: justificar por escrito y acompañar capturas.

| Elemento | Referencia del prototipo |
|---|---|
| Fondo/texto claro | #f8f8f8 / #111 |
| Texto secundario, borde, superficie | #626262 / #ddd / #fff |
| Acento, superficie secundaria | #008eaa / #ececec |
| Oscuro | #161616, #f2f2f2, #b8b8b8, #444, #202020, #252525, #343434, #009fc1 |
| Contenedor | max-width 1600px; padding 34px; carcasa borde 2px, radio 32px, padding 24px |
| Encabezado principal | 38px, peso 650, interlineado 1.25 |
| Inicio | dos columnas, gap 16px; tarjeta min-height 220px, padding 24px, radio 24px, borde 2px |
| Configuración | tarjeta de ancho completo, min-height 150px |
| Panel interior | borde 1px, radio 16px, padding 22px |
| Controles | radio 8–9px, padding 12px, foco visible 3px |
| Responsive | <=800px reducir espaciados y tipografía; <=520px inicio de una columna |

## Inicio compacto aprobado para C.2.3

El menú raíz se centra con un ancho máximo de 1000 px y encabezado de 30 px.
Las tarjetas tienen 145 px de altura mínima en escritorio, con 100 px para
Configuración, margen interno de 18 px, separación de 12 px, radio de 16 px e
iconos de 28 px. Hasta 520 px se usa una columna y las tarjetas principales
tienen al menos 110 px. El ajuste se limita al menú principal.

Colores de los iconos: luces #d5a13b, zonas #438aca, modos #8b5cce, inteligente #299b65, configuración #84909d. Mantener el orden, iconos reconocibles, densidad y alineación. En HA priorizar variables del tema y contrastes accesibles; no forzar tema del sistema operativo. Conservar vista previa de tira sobre fondo oscuro, etiquetas legibles, estados explícitos (no solo color), botones primarios y secundarios diferenciados. Navegación y selección accesibles por teclado, lectores de pantalla y táctil. Español e inglés; usar textos del prototipo como referencia española.
