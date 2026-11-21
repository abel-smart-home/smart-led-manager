# Historial de cambios

Este proyecto sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y usa versionado semántico. La versión del manifest conserva la forma de
pre-release (`0.1.0-alpha.1`) y `pyproject.toml` usa su equivalente PEP 440
(`0.1.0a1`).

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
