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
- [x] El Bloque B parte del HEAD aprobado del Bloque A
      `fa9ecd650485e27ee1f1f22654972a1c47379c17` y conserva sus cambios.
- [x] El Bloque B.1 parte exactamente del HEAD del Bloque B
      `f8b9fc9ec8dc0a31378bb50595d605a2c88a48fe`; el conjunto funcional del panel,
      la compatibilidad con runtime sin frontend, la cobertura frontend y el
      rechazo de campos numéricos vacíos quedan en
      `1d8926bcf8307a480d585174cfb7eb8550fb816a`.
- [x] El Bloque C parte del HEAD B.1
      `6ad79e0c3c388f714f08c727ba17f315807310a4`; la implementación inicial es
      `6ea6eca`, el endurecimiento de ciclo de vida `88862a5`, el seguimiento de
      grupos anidados `6a74106`, el ajuste de pruebas `8903be0` y el SHA
      funcional final, que conserva restauración, barra y gráfica B.1, es
      `2b9c4dd` en `feat/v0.1.0-alpha.3-advanced-rules`. No cambia la versión,
      ConfigEntry ni Store.
- [x] `ruff format --check .` y `ruff check .` pasan localmente.
- [x] `pytest --cov` y la matriz Linux de Home Assistant `2026.11.0`/`2026.11.2`
      pasan para B.1: 157 pruebas y cobertura de ramas `87.21 %` en ambas
      variantes; el job frontend aprueba 6 pruebas Node.
- [x] El SHA funcional C `2b9c4dd` aprueba Ruff y 185 pruebas Python con
      cobertura de ramas `80.72 %` tanto en Home Assistant `2026.11.0` como en
      `2026.11.2`; el job frontend aprueba 6/6 pruebas Node.
- [x] Hassfest y HACS/Marketplace Action pasan sin exclusiones engañosas.
- [x] Manifest, Python, changelog y notas coinciden para alpha.3.
- [x] Traducciones `en`, `es` y `es-419` cubren flujos, entidades, acciones y
      excepciones, incluido el administrador y editor de reglas.
- [x] Instalación, actualización, recarga, descarga y recuperación se prueban.
      La eliminación completa de la entrada y la ausencia de archivos
      `smart_led_manager.*` se comprobaron en laboratorio HAOS; la evidencia
      física Raspberry/Zigbee se conserva separada.
- [x] El propietario aprobó 8/8 pruebas del Bloque A en HAOS VirtualBox con
      `fa9ecd650485e27ee1f1f22654972a1c47379c17`, reportadas el 23 de noviembre
      de 2026. No se atribuyen logs o métricas no entregados.
- [x] El propietario reportó B-01 a B-10, 10/10 en HAOS VirtualBox con
      `f8b9fc9`, el 23 de noviembre de 2026; no se atribuyen evidencias no
      entregadas.
- [x] El propietario reportó B1-01 a B1-10 aprobadas, 10/10, en HAOS VirtualBox
      con `6ad79e0c3c388f714f08c727ba17f315807310a4`. Se conserva el primer fallo
      `MappingProxyType`, su corrección manual en `9ba3b0c` y el endurecimiento
      posterior. A/B/B.1 suman 28/28 reportadas; no son resultados de Codex ni
      de CI.
- [ ] Se repiten B-02, B-04, B-07, B-08, B1-05, B1-06, B1-07 y B1-10 sobre el
      hardware físico señalado en el plan, además de los pendientes heredados.
- [ ] El propietario ejecuta C-01 a C-20. Ningún caso C se considera aprobado
      por compilación, pytest, CI, HAOS anterior o presencia del formulario.
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

El pytest completo no se marca como aprobado en Windows: la dependencia
`pytest-homeassistant` importa `fcntl`, disponible sólo en POSIX. Ruff, la
compilación sintáctica y las seis pruebas Node del modelo/panel sí se ejecutaron
localmente; la evidencia Python completa corresponde a la matriz Linux indicada
arriba. El repositorio no incorpora un runner de navegador real; Node valida el
modelo y el contrato del componente, mientras el recorrido visual, teclado,
táctil y temas permanece en C-01 a C-20 para HAOS VirtualBox.

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
5. Abre **Configurar > Reglas inteligentes**, edita una regla sin cambiar su
   identidad y revisa el editor visual de puntos. Las copias empiezan
   deshabilitadas; no las actives hasta comprobar destinos y prioridad.
6. Con una cuenta administradora abre **Configurar > Centro de administración**
   y usa su enlace, la barra lateral o `/smart-led-manager-editor`. Decide si
   deseas mantener visible el acceso lateral. Simula antes de guardar y
   verifica que no se envíen órdenes físicas durante el borrador.
7. Asigna áreas desde **Configurar > Zonas** si lo deseas; no edites `.storage`
   ni registros internos.
8. Ejecuta primero B1-01 a B1-10 en VirtualBox y después el plan físico.

Alpha.3 migra el ConfigEntry de `1.1` a `1.2`, pero no cambia el Store. Volver
a alpha.2 requiere restaurar la copia de seguridad completa: una versión
anterior no está obligada a aceptar un `minor_version` futuro. Conserva la
copia hasta verificar las entidades, sus dispositivos y la recuperación.

Volver del Bloque B al código del Bloque A sin restaurar datos puede activar
copias o reglas que estaban deshabilitadas, porque el código anterior no conoce
`enabled`. La reversión segura es restaurar la copia de seguridad completa. Si
no existe, elimina antes todas las copias y reglas deshabilitadas desde Bloque B
y documenta una revisión manual; no se recomienda sustituir sólo el código.

Volver de B.1 al commit del Bloque B sí conserva el esquema y el formato de
puntos: detén Core, restaura la carpeta completa de `f8b9fc9` y reinicia. El
panel lateral desaparecerá y las reglas guardadas seguirán disponibles en el
editor nativo. Restaura la copia de seguridad si el objetivo es deshacer
también los cambios de puntos, porque sustituir código no revierte opciones.

### Actualización y reversión del Bloque C

1. Crea una copia completa y conserva la carpeta B.1.
2. Detén Core y sustituye la carpeta completa de la integración por la rama C;
   no elimines la entrada ni modifiques `.storage`.
3. Inicia Core y verifica primero luces autorizadas, zonas, modos, entidades y
   reglas heredadas. Después abre el catálogo unificado con un administrador.
4. Previsualiza destinos y simulaciones antes de guardar. Ejecuta C-01 a C-20
   en la instancia aislada y separa los casos que exigen Zigbee real.

El esquema de entrada y Store no aumenta, pero B.1 desconoce reglas de evento y
campos avanzados. Para revertir, deshabilita o elimina desde C las reglas que los
usen, detén Core y restaura la copia completa. Volver sólo al código B.1 no
deshace opciones y puede ignorar definiciones C; no se declara compatible como
reversión general sin esa limpieza o restauración.

El Bloque D conserva sin adelantos la política configurable de reintentos y
verificación física, pausa/reanudación temporal y aliases de voz.

## Camino a `0.1.0`

La alfa no equivale a la versión regular. `0.1.0` sólo puede publicarse cuando
el alcance de [requirements.md](requirements.md), la estabilización de la hoja
de ruta, las migraciones y la matriz física estén cerrados y aprobados.
