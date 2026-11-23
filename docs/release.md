# Proceso de release

Este documento describe el camino; no autoriza ninguna acción. Fusionar a
`main`, crear una etiqueta, publicar una release o enviar el catálogo de
Marketplace requiere aprobación explícita del propietario.

## Identidad de `0.1.0-alpha.2`

| Lugar | Valor |
|---|---|
| `manifest.json` y changelog | `0.1.0-alpha.2` |
| `pyproject.toml` (PEP 440) | `0.1.0a2` |
| Nombre de archivo opcional | `smart-led-manager-0.1.0-alpha.2.zip` |
| Release | Pre-release, nunca estable |

La etiqueta final debe usar la convención aprobada y comprobarse con HACS
Action/Marketplace. No crees una etiqueta aislada: Marketplace consume una
release de GitHub cuyo contenido corresponde al mismo commit y versión.

## Puertas del candidato

- [x] El diff local contiene sólo el incremento alpha.2 y preserva la base
      remota verificada de alpha.1.
- [x] `ruff format --check .` y `ruff check .` pasan localmente.
- [x] `pytest --cov` pasa localmente: 123 pruebas y 27 subpruebas, cobertura de
      ramas `85.14 %`; 7 pruebas HA se omiten en Windows y se reservan a CI
      Linux.
- [x] La matriz de CI prueba Home Assistant `2026.11.0` y `2026.11.2`: 130
      pruebas aprobadas en Linux y cobertura total `86.96 %` en ambas.
- [x] Hassfest y HACS/Marketplace Action pasan sin `ignore` ni supresiones
      engañosas en el PR #2.
- [x] Manifest, `hacs.json`, Python, changelog y notas coinciden para alpha.2.
- [x] Traducciones inglesa y española cubren flujos, entidades, acciones y
      excepciones.
- [ ] Instalación, actualización, recarga, descarga y recuperación se prueban.
      La instalación manual, recarga, reinicio de Core y recuperación están
      registradas; eliminar la entrada y verificar su limpieza sigue pendiente.
- [ ] El propietario ejecuta y registra `docs/haos-test-plan.md`. La ejecución
      alpha.2 es parcial: 10 casos M completos, 9 parciales y M-06 pendiente;
      conserva cada subcomprobación faltante en el propio plan.
- [x] El propietario confirmó con `8e21b28` que la entrada reclasificada aparece
      en **Integraciones** y que el perfil `es-419` muestra el Options Flow en
      español. No se atribuye una prueba independiente al perfil `es`.
- [x] Los interruptores de Cine/Lectura funcionaron mediante Matter Hub `2.0.60`
      y Alexa en el entorno registrado; esta evidencia no implica integración
      directa ni compatibilidad general con otros puentes o asistentes.
- [ ] Se revisan licencia, `THIRD_PARTY_NOTICES.md`, seguridad y privacidad.
- [ ] El propietario aprueba explícitamente la fusión y publicación.

Una comprobación que no pueda ejecutarse se registra como pendiente con su
motivo; no se sustituye por una afirmación de éxito.

## Base física heredada de alpha.1

No se conoce un defecto bloqueante en los recorridos automatizados y físicos
ejecutados. R-01, R-02 y sus antecedentes de recuperación Zigbee quedaron
corregidos y repetidos satisfactoriamente; las advertencias controladas por
dispositivo sin respuesta siguen siendo normales y deben permanecer visibles.

Esos resultados protegen la base que alpha.2 debe conservar, pero no prueban
zonas, modos, selectores ni interruptores. Alpha.2 sólo puede llamarse
**candidata experimental para validación** después de sus comprobaciones
automatizadas; no está validada como versión regular ni autoriza Marketplace.
F-08 de alpha.1 sigue aprobada para `unknown` y `unavailable`; no debe volver a
marcarse pendiente.

Alpha.2 tiene validación física parcial reportada con `8e21b28`: prioridades,
reinicio de Core, recuperación Zigbee, selector/interruptores y exposición
Matter/Alexa funcionaron en el entorno registrado. No cierra M-06, la eliminación
completa de M-16, los datos huérfanos de M-19 ni la reversión de M-20. La entidad
residual observada al eliminar un modo en M-10 también debe evaluarse antes de
una revisión final.

La publicación continúa bloqueada administrativamente hasta que el propietario
la autorice de forma explícita; este documento no concede esa autorización.

## Preparación del pull request

1. Actualiza desde el remoto sin reemplazar código más reciente.
2. Trabaja en una rama y ejecuta las puertas locales.
3. Abre un PR con resumen, riesgos, pruebas ejecutadas y pendientes.
4. Espera CI y corrige la causa de cualquier fallo.
5. Solicita revisión del propietario. No combines la aprobación técnica con la
   autorización de release.

## Publicación, sólo tras autorización

1. Fusionar el commit aprobado en `main`.
2. Verificar de nuevo el SHA y la versión en `main`.
3. Crear la etiqueta aprobada sobre ese SHA.
4. Crear una **pre-release** de GitHub con el changelog, requisitos, forma de
   actualización, limitaciones y registro de pruebas.
5. Verificar la instalación del artefacto publicado en una instancia limpia.
6. Sólo con una autorización adicional cuando corresponda, presentar el
   repositorio al catálogo de Marketplace con enlaces a hassfest y HACS Action
   exitosos.

## Reversión

Si la instalación publicada falla, marca el problema de forma visible, detén
la promoción y prepara un nuevo parche; no muevas ni reutilices silenciosamente
una etiqueta existente. Indica cómo volver a la versión anterior y qué datos de
Store/config entry requieren atención.

### Actualización manual segura desde alpha.1

1. Crea una copia de seguridad de Home Assistant y conserva una copia de la
   carpeta alpha.1.
2. Descarga o recarga Smart LED Manager para detener animaciones y tareas.
3. Sustituye únicamente `custom_components/smart_led_manager/` por el contenido
   alpha.2 del commit candidato y reinicia Core.
4. Comprueba que las luces, reglas y ajustes anteriores siguen presentes.
5. Crea zonas y modos desde **Configurar**; no edites `.storage` ni inventes
   identificadores a mano.
6. Ejecuta primero los casos sin animación y después el plan físico de modos.

Alpha.2 no requiere migración de ConfigEntry ni del Store. Si es necesario
volver a alpha.1, desactiva todos los modos o elige **Sin modo**, descarga la
entrada, restaura la carpeta alpha.1 y reinicia Core. Alpha.1 ignora las claves
de opciones `zones`/`modes`; antes de una reversión prolongada conviene eliminar
los modos desde alpha.2 para que no quede una solicitud persistente de módulo
desconocido compitiendo en el Store. Conserva la copia de seguridad hasta
verificar luces, reglas, tareas y almacenamiento.

## Camino a `0.1.0`

La alfa no equivale a la versión regular. `0.1.0` sólo puede publicarse cuando
el alcance de [requirements.md](requirements.md), la estabilización de la hoja
de ruta, las migraciones y la matriz física estén cerrados y aprobados.
