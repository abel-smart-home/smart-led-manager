# Instalar y probar Smart LED Manager C.2.5 en VirtualBox

Usa la máquina de laboratorio con HAOS y Home Assistant Core 2026.11.3.
La versión visible es **0.1.0-alpha.3**. El SHA para este recorrido es
`e9ac4753680f03a541483ddab43277039bb0d39e`.
[Descargar el ZIP de ese SHA](https://github.com/abel-smart-home/smart-led-manager/archive/e9ac4753680f03a541483ddab43277039bb0d39e.zip).

## Copia e instalación

1. En **Ajustes → Sistema → Copias de seguridad**, crea una copia completa,
   comprueba que terminó y descárgala a Windows. Guarda el kit de emergencia
   si la copia está cifrada. Guarda también en Windows una copia de
   `custom_components/smart_led_manager` con el nombre
   `smart_led_manager-anterior`. [Copias de seguridad de HAOS](https://www.home-assistant.io/common-tasks/os/#backup).
2. Descomprime el ZIP. En la consola de VirtualBox, en `ha >`, escribe
   `core stop`. Con tu acceso habitual a los archivos de la VM, sustituye
   **la carpeta completa** `custom_components/smart_led_manager` por la del
   ZIP. Comprueba que contiene `manifest.json`, `diagnostics.py` y
   `frontend/settings-views.mjs`. Conserva la integración ya instalada y
   deja `.storage` y `configuration.yaml` intactos.
3. Escribe `core start` en la consola. Cuando vuelva Home Assistant, recarga
   la página. Abre Smart LED Manager y comprueba que siguen tus luces, zonas,
   modos, reglas y avisos.

Para volver a C.2.4, detén Core, repón la carpeta guardada y vuelve a
iniciarlo. Para restaurar también las preferencias y la configuración
anteriores a las pruebas, usa la copia completa.
[Restaurar una copia de seguridad](https://www.home-assistant.io/integrations/backup/#restoring-a-backup).

## Recorrido práctico

Empieza en **Smart LED Manager → Configuración**. Anota las preferencias
actuales para poder volver a ellas al terminar. Usa solo una luz autorizada
de laboratorio para los casos con iluminación real.

| Caso | Qué hacer y qué observar |
| --- | --- |
| T-01 · General y barra lateral | Comprueba que aparece la versión y que el interruptor refleja tu ajuste guardado. Oculta el acceso, pulsa **Guardar** y espera **Configuración guardada**. El panel sigue disponible en la misma ruta. Entra desde **Ajustes → Dispositivos y servicios → Integraciones → Smart LED Manager → Configurar → Centro de administración**. Pulsa **Abrir el Centro de administración** y vuelve a habilitar la barra si así la usabas. |
| T-02 · Prioridades | Comprueba los valores actuales. Abre **Protección de la red (avanzado)** y prueba `0,53` s. El formulario debe indicar que solo admite pasos de `0,05`. Prueba un valor válido, por ejemplo `0,80` s, guarda y confirma que el valor se conserva al volver. Comprueba que las prioridades de tus reglas, avisos y modos siguen siendo las que configuraste. |
| T-03 · Restablecer y descartar | Pulsa **Restablecer valores iniciales** y comprueba que cambia el borrador a solicitud más reciente, control explícito y `0,75` s. Pulsa **Cancelar → Continuar editando** y confirma que el borrador sigue ahí. Después usa **Descartar cambios y salir** y verifica el valor anterior en Prioridades. |
| T-04 · Configuración nativa | Desde **Configuración nativa**, abre el ajuste de la integración en HA. En **Configurar → Ajustes avanzados**, cambia el desempate. Regresa a Prioridades y comprueba que muestra el valor guardado. Repite en sentido inverso y revisa que los catálogos siguen completos. |
| T-05 · Recuperación | Pulsa **Simular desconexión**, luego **Simular reconexión** y finalmente **Reiniciar demostración**. Observa el estado de ejemplo y el cambio de color de la tira en pantalla. Comprueba que tus luces reales y modos guardados siguen igual. |
| T-06 · Diagnóstico | Comprueba el número de luces, zonas y reglas habilitadas. Usa un modo y un aviso de prueba sobre la misma luz, con el aviso a mayor prioridad. Pulsa **Actualizar** antes de que termine el aviso. La lista debe mostrar el aviso ganador y el modo enmascarado en esa luz. Descarga el diagnóstico, abre el JSON y comprueba que contiene el estado. Registra por separado si el dispositivo físico respondió. |
| T-07 · Reinicio y revisión visual | Guarda una preferencia, reinicia HAOS y comprueba su persistencia junto con una regla anterior y un aviso guardado. Revisa las seis pantallas de Configuración en claro y oscuro, con teclado o pantalla táctil. [Capturas y diferencias](design/c25-evidence/README.md). |

La matriz de Codex comprueba los tres desempates con solicitudes reales del
motor, el control de revisiones, los permisos y la redacción. Si quieres
observar un empate en la VM, usa un modo de laboratorio y un aviso con la
misma prioridad. Aplica el desempate primero e inicia el modo y el aviso
después. Repite el orden de activación tras cambiar la preferencia. Una
recarga de opciones finaliza los avisos temporales activos.

## Si aparece un error

Abre **Ajustes → Sistema → Registros** y busca `smart_led_manager` en el
registro de Core. En `ha >` también puedes escribir `core logs`. Anota
SHA, versión de Core, caso, hora local, mensaje y si se conservó el borrador.
El diagnóstico redacta credenciales. Revisa los nombres de entidades y zonas
antes de compartir el archivo. [Registros de Home Assistant](https://www.home-assistant.io/integrations/system_log/).

La comprobación visual del propietario, el recorrido T-01–T-07 y las pruebas
físicas se registran cuando se confirmen en su entorno.
