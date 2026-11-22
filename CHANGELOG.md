# Historial de cambios

Este proyecto sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y usa versionado semántico. La versión del manifest conserva la forma de
pre-release (`0.1.0-alpha.2`) y `pyproject.toml` usa su equivalente PEP 440
(`0.1.0a2`).

## [0.1.0-alpha.2] — Sin publicar

### Añadido

- Zonas gráficas con identificador estable, nombre y subconjunto no vacío de
  luces autorizadas; una luz física sólo puede pertenecer a una zona.
- Modos persistentes por zona con prioridad, color, brillo, transición,
  permiso de encendido y animaciones `fixed`, `blink` o `pulse`.
- `ModeManager` que representa la selección como una solicitud persistente del
  motor, reemplaza el modo anterior de la zona en una sola transacción y
  reconcilia datos guardados contra la definición vigente al arrancar.
- Un `select` por zona con la opción **Sin modo**, y un `switch` estable sólo
  para cada modo que el propietario decida exponer.
- Acciones `activate_mode`, `deactivate_mode` y `set_zone_mode`, con esquemas y
  traducciones en inglés y español.
- Flujos gráficos para crear, editar y eliminar zonas y modos sin YAML.

### Seguridad y compatibilidad

- La entrada se clasifica como integración de tipo `service`, no como
  `helper`, para que Home Assistant la muestre en **Integraciones**. Este cambio
  sólo afecta a metadatos del manifest y no recrea ni migra la entrada.
- Se añade el catálogo completo `es-419` para que Español (Latinoamérica) no
  caiga al fallback inglés del Options Flow; `es` continúa disponible.
- Las solicitudes internas de modo usan identificadores protegidos y no pueden
  modificarse con las acciones genéricas.
- Cambiar de modo no muestra estados intermedios de menor prioridad; reactivar
  el mismo modo no altera su antigüedad, no reinicia animaciones, no repite el
  comando físico y no reescribe el almacenamiento.
- **Sin modo** libera únicamente la solicitud de modo y deja que el motor
  calcule la intención vigente; nunca ordena apagar a ciegas.
- No se cambia el esquema de config entry ni el Store de alpha.1: las nuevas
  definiciones son opciones con valores vacíos compatibles y las solicitudes
  conservan el formato persistente existente.

### Validación

- Cobertura automatizada de creación, edición, selección, reemplazo atómico,
  idempotencia, prioridades, reinicio, limpieza de huérfanos, varias zonas y
  entidades `select`/`switch`.
- La validación local aprobó 121 pruebas y 27 subpruebas, con 5 pruebas de
  runtime Home Assistant omitidas en Windows porque requieren Linux. La
  cobertura total de ramas fue `85.13 %`; Ruff y formato aprobaron.
- La matriz de CI aprobó 126 pruebas en Linux, sin omisiones, tanto con Home
  Assistant `2026.11.0` como con `2026.11.2`; la cobertura total fue
  `86.96 %`. Hassfest y HACS/Marketplace también aprobaron en el PR #2.
- La validación física de alpha.2, incluida la exposición opcional mediante
  Alexa/Matter Hub, permanece pendiente y no se deduce de las pruebas de
  alpha.1.

## [0.1.0-alpha.1] — Sin publicar

### Añadido

- Motor puro de solicitudes priorizadas, resolución independiente por luz,
  desempates deterministas, solicitudes enmascaradas y expiración UTC.
- Adaptador RGB consciente de capacidades, deduplicación, limitación de
  frecuencia y resincronización tras indisponibilidad.
- Config flow para la lista explícita de luces autorizadas y options flow para
  ajustes, reglas de estado y reglas numéricas.
- Acciones `activate`, `deactivate`, `notify`, `set_scene`, `cancel`,
  `clear_notifications` y `set_manual_override`.
- Persistencia versionada de solicitudes persistentes, recuperación, historial
  acotado, diagnóstico y sensor de estado del motor.
- Animaciones fija, parpadeo y pulsación con propiedad y cancelación por luz.
- Traducciones en inglés y español, documentación de uso, CI,
  hassfest y validación HACS/Marketplace.
- Auditoría de proyectos comunitarios sin reutilización de código de terceros.

### Seguridad

- Ninguna acción puede resolver una entidad fuera de la lista de luces
  administradas.
- Las órdenes internas conservan contexto para no tratarse como control manual
  externo y la detección directa permanece conservadora y optativa.

### Corregido

- Los temporizadores de vencimiento que se ejecutan con retraso reconstruyen el
  ganador anterior en el límite real de expiración de cada luz. De este modo,
  una notificación temporal libera su animación y sus órdenes obsoletas antes
  de recuperar la solicitud válida de menor prioridad.
- La resincronización tras volver de `unavailable` contiene los fallos
  transitorios del servicio de luz y usa intentos acotados con espera
  progresiva. Cada intento conserva sólo la intención vigente; reemplazarla o
  cancelarla descarta trabajo obsoleto y los fallos quedan diagnosticados sin
  excepciones de tareas no recuperadas.
- Un fallo de envío mientras ZHA conserva la entidad como `on` u `off` agenda
  una recuperación automática de fondo, sin depender de un evento
  `unavailable`. La caché de deduplicación se invalida tras cada fallo y sólo
  la ganadora vigente puede reintentarse; cancelaciones, vencimientos, cambios
  de prioridad y descargas eliminan inmediatamente el trabajo anterior.

### Validación automatizada

- Ruff y la matriz pytest completaron 93 pruebas en Home Assistant `2026.11.0`
  y `2026.11.2`, con cobertura total de ramas igual o superior al `80 %`.
- Hassfest y HACS/Marketplace Action superaron la validación del PR #1.

### Validación física

- El propietario validó `f283d36` en HAOS con ZHA, un coordinador Sonoff
  Dongle-P MG24 Plus y un GLEDOPTO GL-C-007P instalado manualmente. Se aprobaron
  F-01, F-03 a F-10, R-01, R-02, cancelación durante recuperación y R-03.
  F-08 cubrió completamente interpolación y los estados inválidos `unknown` y
  `unavailable`; ambos liberaron la regla sin convertirse en cero.
- La recarga de R-04 detuvo una animación activa y recuperó la solicitud
  persistente sin trabajo tardío. R-05 aprobó una carga mixta de 20 cambios
  numéricos con avisos `pulse` P95 y `blink` P98, recuperación del control
  numérico y estado final correcto; no fue estrés extremo multidispositivo.
- Se repitieron satisfactoriamente los dos fallos encontrados durante la
  validación: la excepción Zigbee sin manejar corregida en `cf57d64` y la falta
  de recuperación con estado ZHA obsoleto corregida en `f283d36`. Los fallos de
  comunicación aún producen advertencias controladas y útiles en el registro.

### Pendiente antes de publicar

- Completar F-02, la eliminación de entrada de R-04, estrés extremo
  multidispositivo, R-06, Alexa/Matter y diversidad de controladores; registrar
  firmware y fecha que siguen pendientes.
- Recibir aprobación explícita antes de fusionar, etiquetar, crear la
  pre-release o enviar la integración al catálogo Marketplace.

[0.1.0-alpha.1]: https://github.com/abel-smart-home/smart-led-manager/compare/main...feat/v0.1.0-alpha.1
[0.1.0-alpha.2]: https://github.com/abel-smart-home/smart-led-manager/compare/feat/v0.1.0-alpha.1...feat/v0.1.0-alpha.2-modes
