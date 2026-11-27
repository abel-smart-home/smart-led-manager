# Solución de problemas

## La integración no aparece

Comprueba que la ruta sea exactamente
`config/custom_components/smart_led_manager/manifest.json`, que no haya una
carpeta adicional creada al descomprimir y que Home Assistant se haya
reiniciado. Revisa **Ajustes > Sistema > Registros** por errores de manifest o
versión mínima.

## La entrada aparece en Ayudantes

Las compilaciones anteriores del candidato alpha.2 usaban por error
`integration_type: helper`. Instala el commit corregido completo y reinicia
Home Assistant Core; no elimines ni vuelvas a crear la entrada. El manifest
actual usa `service`, por lo que la entrada existente debe clasificarse en
**Integraciones**. Registra el resultado real antes de dar la comprobación
visual por aprobada.

## El Options Flow aparece en inglés

Comprueba el idioma del perfil de usuario, no sólo el idioma general de Home
Assistant. La interfaz distingue los códigos `es` y `es-419`; la integración
distribuye `translations/es.json` y `translations/es-419.json` porque el
cargador no sustituye automáticamente una variante regional por `es`. Después
de copiar la carpeta completa, reinicia Core y recarga el frontend sin caché.

## Una acción rechaza los destinos

Sólo pueden usarse entidades elegidas en **Smart LED Manager > Configurar >
Luces administradas**. La selección de un área, un grupo o “todas” no expande
automáticamente permisos en esta alfa. Autoriza la entidad física concreta o
retírala de la acción.

## La luz no cambia de color

1. Confirma que la entidad esté disponible y responda desde sus controles
   nativos.
2. Revisa `supported_color_modes`; una luz sin modo de color no puede
   representar una intención RGB.
3. Busca una solicitud de prioridad superior en el diagnóstico/estado del
   motor.
4. Espera el intervalo mínimo configurado: una orden reciente puede sustituir
   una pendiente antes de enviarse.

El adaptador evita atributos no soportados y no fuerza color mediante llamadas
específicas del fabricante.

## Una regla numérica no se actualiza

El estado debe ser un número finito. `unknown`, `unavailable`, NaN, infinito o
texto se ignoran como valor numérico. Comprueba también **variación mínima** e
**intervalo mínimo**: ambos pueden filtrar cambios pequeños o muy frecuentes.

## El color anterior reaparece

Esto puede ser correcto si una solicitud inferior seguía activa detrás de una
superior. Smart LED Manager no restaura un snapshot: recalcula la ganadora
actual por luz. Revisa los `request_id`, prioridades, duraciones y si una escena
persistente continúa activa.

## Una notificación no reaparece tras desconexión

La duración transcurre en tiempo real. Si venció mientras la luz estaba
`unavailable`, se descarta y al reconectar se aplica sólo la solicitud que siga
vigente. Esto evita reproducir avisos obsoletos.

## El control manual se interpreta de forma inesperada

Usa la política `service_only` y la acción `set_manual_override` para el camino
más predecible. La atribución de cambios directos depende de cómo la integración
física propague `Context` y eco de estado; `respect`/`temporary` requieren
validación específica del dispositivo.

## Animaciones lentas o entrecortadas

El periodo de la animación no puede eludir el intervalo mínimo por luz. Zigbee
y otras redes compartidas pueden añadir latencia. Aumenta el periodo, evita
varias animaciones rápidas simultáneas y no uses parpadeos como señal de
emergencia. No reduzcas protecciones de frecuencia sin medir el dispositivo.

## Diagnósticos e informe útil

Descarga el diagnóstico desde la entrada de la integración, revísalo para
detectar nombres o identificadores que no quieras compartir y adjunta al issue:

- versión exacta de Home Assistant y Smart LED Manager;
- plataforma de la entidad (`zha`, `matter`, `esphome`, etc.);
- pasos mínimos y resultado esperado/real;
- registros relacionados sin secretos;
- resultado de la acción sobre la luz desde sus controles nativos.

No describas una simulación como prueba física. Para vulnerabilidades usa el
canal privado indicado en [SECURITY.md](../SECURITY.md).
