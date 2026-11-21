# Avisos de terceros

## Estado para v0.1.0-alpha.1

Smart LED Manager `v0.1.0-alpha.1` no incorpora, copia, adapta ni distribuye
código fuente, archivos, recursos gráficos o documentación procedentes de los
proyectos comunitarios auditados.

Por tanto, en esta versión **no hay componentes de terceros incorporados que
requieran reproducir avisos de copyright o textos de licencia adicionales**.

Los proyectos enumerados en
[`docs/community-audit.md`](docs/community-audit.md) son referencias de
investigación. Sus conceptos, problemas públicos y casos de uso ayudaron a
definir requisitos y pruebas, pero la implementación de Smart LED Manager es
propia.

## Referencias investigadas, no incorporadas

| Proyecto | Repositorio | Licencia observada |
|---|---|---|
| Color Notify | <https://github.com/cobryan05/ha-color-notify> | Apache-2.0 |
| Signal Lights | <https://github.com/prestomation/ha-signal-lights> | MIT |
| Accent & Signal Light | <https://github.com/arkane-systems/ha-accent-signal-light> | MIT |
| Layers | <https://github.com/lukab-dev/ha-layers> | MIT |
| Adaptive Lighting | <https://github.com/basnijholt/adaptive-lighting> | Apache-2.0 |
| Temperature-based light color | <https://github.com/tobus3000/hass-temperature-based-light-color-blueprint> | MIT |
| Light Blink Pro | <https://github.com/ccpk1/HA-Blueprints> | Sin licencia explícita encontrada |
| Home Assistant blueprints de Markus | <https://github.com/myGithub-Markus/home-assistant_blueprints> | Sin licencia explícita encontrada |

La inclusión en esta tabla no concede derechos ni implica respaldo, afiliación
o incorporación de código.

## Obligaciones si se reutiliza código en el futuro

Antes de copiar o adaptar cualquier código, asset o documentación de terceros
se deberá:

1. Identificar la versión, commit y archivo exactos de procedencia.
2. Confirmar que la licencia permite el uso previsto y es compatible con la
   licencia Apache-2.0 de Smart LED Manager.
3. Registrar qué se reutiliza, por qué representa una ventaja real y qué se
   modificó.
4. Añadir pruebas que cubran el comportamiento incorporado.
5. Actualizar este archivo, la auditoría comunitaria y, cuando corresponda,
   los encabezados de los archivos modificados.
6. Obtener revisión del propietario antes de fusionar la incorporación.

### Código bajo Apache License 2.0

Si se incorpora material bajo Apache-2.0 se deberá, como mínimo:

- conservar una copia de la licencia Apache-2.0;
- conservar avisos de copyright, patentes, marcas y atribución aplicables;
- indicar de forma visible los archivos modificados;
- conservar el contenido atribuible de un archivo `NOTICE`, si la fuente lo
  incluye, de acuerdo con la sección 4 de la licencia;
- no utilizar nombres o marcas de los autores como respaldo del proyecto.

La licencia también contiene una concesión y terminación de patente que debe
revisarse antes de incorporar material.

### Código bajo licencia MIT

Si se incorpora una copia o porción sustancial de código MIT se deberá
conservar, en las copias pertinentes:

- el aviso de copyright original;
- el texto completo de la licencia MIT;
- su exclusión de garantías y limitación de responsabilidad.

### Material sin licencia explícita

La publicación pública de un archivo no concede por sí sola permiso para
copiarlo o crear una obra derivada. No se incorporará material sin licencia
explícita salvo que el titular otorgue permiso escrito compatible con la
distribución del proyecto. Mientras no exista ese permiso, solo podrá usarse
como referencia de requisitos, interoperabilidad o casos de fallo, sin copiar
su expresión concreta.

## Dependencias de ejecución y desarrollo

Este documento se refiere a código incorporado directamente en el repositorio.
Las dependencias declaradas, Home Assistant, herramientas de pruebas y GitHub
Actions conservan sus propias licencias y términos. Antes de cada release se
deberá revisar el conjunto real de dependencias distribuido y añadir aquí los
avisos que resulten obligatorios.
