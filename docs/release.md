# Proceso de release

Este documento describe el camino; no autoriza ninguna acción. Fusionar a
`main`, crear una etiqueta, publicar una release o enviar el catálogo de
Marketplace requiere aprobación explícita del propietario.

## Identidad de `0.1.0-alpha.1`

| Lugar | Valor |
|---|---|
| `manifest.json` y changelog | `0.1.0-alpha.1` |
| `pyproject.toml` (PEP 440) | `0.1.0a1` |
| Nombre de archivo opcional | `smart-led-manager-0.1.0-alpha.1.zip` |
| Release | Pre-release, nunca estable |

La etiqueta final debe usar la convención aprobada y comprobarse con HACS
Action/Marketplace. No crees una etiqueta aislada: Marketplace consume una
release de GitHub cuyo contenido corresponde al mismo commit y versión.

## Puertas del candidato

- [x] El diff contiene sólo cambios revisados y preserva trabajo ajeno.
- [x] `ruff format --check .` y `ruff check .` pasan.
- [x] `pytest --cov` pasa con cobertura de ramas configurada.
- [x] La matriz prueba Home Assistant `2026.11.0` y `2026.11.2`.
- [x] hassfest y HACS Action pasan sin `ignore` ni supresiones engañosas.
- [x] Manifest, `hacs.json`, Python, changelog y notas coinciden.
- [x] Traducciones inglesa y española cubren flujos, entidades, acciones y
      excepciones.
- [ ] Instalación, actualización, recarga, descarga y recuperación se prueban.
      La instalación manual, recarga, reinicio de Core y recuperación están
      registradas; eliminar la entrada y verificar su limpieza sigue pendiente.
- [ ] El propietario ejecuta y registra `docs/haos-test-plan.md`. La ejecución
      es parcial: conserva casos pendientes en el propio plan.
- [ ] Se revisan licencia, `THIRD_PARTY_NOTICES.md`, seguridad y privacidad.
- [ ] El propietario aprueba explícitamente la fusión y publicación.

Una comprobación que no pueda ejecutarse se registra como pendiente con su
motivo; no se sustituye por una afirmación de éxito.

## Evaluación del candidato `f283d36`

No se conoce un defecto bloqueante en los recorridos automatizados y físicos
ejecutados. R-01, R-02 y sus antecedentes de recuperación Zigbee quedaron
corregidos y repetidos satisfactoriamente; las advertencias controladas por
dispositivo sin respuesta siguen siendo normales y deben permanecer visibles.

El candidato es técnicamente apto para una **pre-release experimental y
limitada** si sus notas enumeran los escenarios pendientes. No está validado
como versión regular, no está listo para afirmar compatibilidad amplia de
hardware y este estado no autoriza Marketplace. F-08 ya cubre tanto `unknown`
como `unavailable`, y R-05 cubre carga mixta; F-02, eliminación de entrada,
estrés extremo multidispositivo, grupos Zigbee, Alexa/Matter y otros
controladores siguen siendo riesgos de cobertura, no resultados aprobados.

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

## Camino a `0.1.0`

La alfa no equivale a la versión regular. `0.1.0` sólo puede publicarse cuando
el alcance de [requirements.md](requirements.md), la estabilización de la hoja
de ruta, las migraciones y la matriz física estén cerrados y aprobados.
