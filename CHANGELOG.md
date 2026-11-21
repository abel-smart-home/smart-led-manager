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

### Validación automatizada

- Ruff y la matriz pytest completaron 84 pruebas en Home Assistant `2026.11.0`
  y `2026.11.2`, con cobertura total de ramas igual o superior al `80 %`.
- Hassfest y HACS/Marketplace Action superaron la validación del PR #1.

### Pendiente antes de publicar

- Repetir R-02 con ZHA y GLEDOPTO GL-C-007P después de la corrección y completar
  el resto del plan físico en HAOS.
- Recibir aprobación explícita antes de fusionar, etiquetar, crear la
  pre-release o enviar la integración al catálogo Marketplace.

[0.1.0-alpha.1]: https://github.com/abel-smart-home/smart-led-manager/compare/main...feat/v0.1.0-alpha.1
