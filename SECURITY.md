# Política de seguridad

## Versiones con soporte

El proyecto aún está en fase `0.1.0-alpha.1` sin release publicada. Mientras se
prepara la primera versión, las correcciones se realizan en la rama activa y no
se garantiza soporte de versiones anteriores.

| Versión | Estado |
|---|---|
| `0.1.0-alpha.1` en desarrollo | Correcciones durante revisión |
| Cualquier snapshot anterior | Sin soporte |

## Reportar una vulnerabilidad

No publiques credenciales, diagnósticos sin revisar ni detalles explotables en
un issue abierto. Usa **Security > Report a vulnerability** en el repositorio
de GitHub para abrir un aviso privado. Incluye:

- versión o commit afectado;
- escenario y posible impacto;
- pasos mínimos para reproducirlo;
- si requiere una luz administrada o permite alcanzar entidades no
  autorizadas;
- mitigación conocida, si existe.

El mantenedor confirmará recepción y coordinará la divulgación cuando exista
una corrección. Para errores ordinarios sin impacto de seguridad, usa el
seguimiento público de issues.

## Límites del producto

Smart LED Manager controla luces decorativas o informativas mediante Home
Assistant. No es un sistema certificado de alarma, incendio, emergencia,
evacuación ni accesibilidad. Una pérdida de conectividad, reinicio, dispositivo
`unavailable` o integración de luz defectuosa puede impedir una señal visual.

Los diagnósticos intentan excluir información sensible, pero deben revisarse
antes de compartir. Los efectos intermitentes pueden afectar a personas con
fotosensibilidad; usa periodos prudentes y evita emplearlos como única señal de
seguridad.
