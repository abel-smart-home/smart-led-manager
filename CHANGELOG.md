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
- Traducciones previstas en inglés y español, documentación de uso, CI,
  hassfest y validación HACS/Marketplace.
- Auditoría de proyectos comunitarios sin reutilización de código de terceros.

### Seguridad

- Ninguna acción puede resolver una entidad fuera de la lista de luces
  administradas.
- Las órdenes internas conservan contexto para no tratarse como control manual
  externo y la detección directa permanece conservadora y optativa.

### Validación pendiente antes de publicar

- Obtener resultados correctos de Ruff, pytest con cobertura, hassfest y HACS
  Action en el commit candidato.
- Ejecutar y registrar el plan físico en HAOS con el hardware del propietario.
- Recibir aprobación explícita antes de fusionar, etiquetar o crear la
  pre-release.

[0.1.0-alpha.1]: https://github.com/abel-smart-home/smart-led-manager/compare/main...feat/v0.1.0-alpha.1

