# Proceso de release

Este documento describe el camino; no autoriza ninguna acción. Fusionar a
`main`, crear una etiqueta, publicar una release o enviar el catálogo de
Marketplace requiere aprobación explícita del propietario.

## Identidad de `0.1.0-alpha.3`

| Lugar | Valor |
|---|---|
| `manifest.json` y changelog | `0.1.0-alpha.3` |
| `pyproject.toml` (PEP 440) | `0.1.0a3` |
| Nombre de archivo opcional | `smart-led-manager-0.1.0-alpha.3.zip` |
| Release | Pre-release, nunca estable |

La etiqueta final debe usar la convención aprobada y comprobarse con HACS
Action/Marketplace. No crees una etiqueta aislada: Marketplace consume una
release de GitHub cuyo contenido corresponde al mismo commit y versión.

## Puertas del candidato

- [x] La rama alpha.3 parte del SHA alpha.2 verificado
      `a14d9afb465c698c0354d18892ecac3537d5f6b4`, no de `main`.
- [x] `ruff format --check .` y `ruff check .` pasan localmente.
- [ ] `pytest --cov` y la matriz Linux de Home Assistant `2026.11.0`/`2026.11.2`
      pasan con la nueva migración y los registros de dispositivos/entidades.
- [ ] Hassfest y HACS/Marketplace Action pasan sin exclusiones engañosas.
- [x] Manifest, Python, changelog y notas coinciden para alpha.3.
- [x] Traducciones inglesa y española cubren flujos, entidades, acciones y
      excepciones.
- [x] Instalación, actualización, recarga, descarga y recuperación se prueban.
      La eliminación completa de la entrada y la ausencia de archivos
      `smart_led_manager.*` se comprobaron en laboratorio HAOS; la evidencia
      física Raspberry/Zigbee se conserva separada.
- [ ] El propietario ejecuta el bloque alpha.3 de `docs/haos-test-plan.md` en
      VirtualBox y Raspberry Pi. Los resultados alpha.2 se conservan como base,
      pero no prueban visualmente los nuevos dispositivos ni su limpieza.
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

Alpha.2 conserva validación física parcial reportada con `8e21b28`: prioridades,
reinicio de Core, recuperación Zigbee, selector/interruptores y exposición
Matter/Alexa funcionaron en Raspberry Pi/ZHA/GLEDOPTO. Las pruebas posteriores
de laboratorio HAOS cerraron M-16, los estados diagnósticos de M-18, la
recuperación semántica de M-19 y la actualización/reversión de M-20. M-06 sólo
se simuló con dos luces Demo y continúa pendiente con dos controladores Zigbee
reales. M-10, M-15 y M-17 permanecen parciales; la entidad residual de M-10 y
la corrupción sintáctica total no probada deben seguir visibles.

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

### Actualización manual segura desde alpha.2

1. Crea una copia de seguridad de Home Assistant y conserva una copia de la
   carpeta alpha.2.
2. Descarga o recarga Smart LED Manager para detener animaciones y tareas.
3. Sustituye únicamente `custom_components/smart_led_manager/` por el contenido
   alpha.3 del commit candidato y reinicia Core; no elimines la entrada.
4. Comprueba que luces, reglas, zonas, modos, selección, `entity_id` y nombres
   personalizados siguen presentes.
5. Asigna áreas desde **Configurar > Zonas** si lo deseas; no edites `.storage`
   ni registros internos.
6. Ejecuta primero el plan VirtualBox y después el plan físico.

Alpha.3 migra el ConfigEntry de `1.1` a `1.2`, pero no cambia el Store. Volver
a alpha.2 requiere restaurar la copia de seguridad completa: una versión
anterior no está obligada a aceptar un `minor_version` futuro. Conserva la
copia hasta verificar las entidades, sus dispositivos y la recuperación.

## Camino a `0.1.0`

La alfa no equivale a la versión regular. `0.1.0` sólo puede publicarse cuando
el alcance de [requirements.md](requirements.md), la estabilización de la hoja
de ruta, las migraciones y la matriz física estén cerrados y aprobados.
