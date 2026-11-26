# Instalar y probar Smart LED Manager C.2.2 en VirtualBox

Usa la máquina de laboratorio con Home Assistant OS y entra como
administrador. La versión sigue siendo **0.1.0-alpha.3**. El código que se
debe instalar es `7a0fc49c2eda8a15e9b0e658e10b6da2efaede29`.
[Descargar el ZIP de C.2.2](https://github.com/abel-smart-home/smart-led-manager/archive/7a0fc49c2eda8a15e9b0e658e10b6da2efaede29.zip).

## 1. Haz una copia e instala

1. En **Ajustes → Sistema → Copias de seguridad**, crea una copia completa y
   descárgala a Windows. Guarda el kit de emergencia si la copia está cifrada.
   [Copias de seguridad de Home Assistant](https://www.home-assistant.io/common-tasks/general/#backups).
2. Abre los archivos de HAOS como de costumbre. Si usas Samba, abre
   `\\IP-DE-LA-VM` desde el Explorador de Windows. Desde la carpeta que contiene
   `configuration.yaml`, copia `custom_components/smart_led_manager` a Windows
   y ponle el nombre `smart_led_manager-anterior`.
   [Acceso a archivos en HAOS](https://www.home-assistant.io/common-tasks/os/#configuring-access-to-files).
3. Descomprime el ZIP en Windows. En la consola de VirtualBox, en el indicador
   `ha >`, escribe `core stop` y espera a que termine. Sustituye **la carpeta
   completa** `custom_components/smart_led_manager` por la del ZIP. Dentro deben
   quedar `manifest.json`, `services.yaml`, `frontend/admin-views.mjs`,
   `translations`, `core`, `controllers` y `modules`. Conserva `configuration.yaml`,
   `.storage`, los demás componentes y la entrada existente de la integración.
4. Escribe `core start` en la misma consola. Cuando vuelva Home Assistant,
   recarga la página del navegador y abre **Smart LED Manager** en la barra
   lateral o añade `/smart-led-manager-editor` al final de la dirección de tu
   VM. Comprueba que sigues viendo las reglas, zonas, modos y luces anteriores.

**Para volver a la versión anterior**, detén Core, vuelve a poner la carpeta
guardada como `custom_components/smart_led_manager` e inicia Core. Si quieres
restaurar también los datos y opciones previos a la prueba, recupera la copia
completa de HAOS. [Restaurar una copia](https://www.home-assistant.io/integrations/backup/#restoring-a-backup).

## 2. Recorre el centro de administración

Usa una luz RGB de laboratorio, por ejemplo **Luz Demo**, que puedas controlar
desde Home Assistant. Usa nombres de prueba para distinguirlos de tu
configuración. Anota el SHA, la versión de Home Assistant y el navegador.

| Prueba | Qué hacer y observar |
| --- | --- |
| Inicio | Comprueba este orden: **Luces administradas**, **Zonas**, **Modos de iluminación**, **Iluminación inteligente**, **Configuración**. Abre **Iluminación inteligente** y comprueba que aparece tu catálogo de reglas. En **Configuración**, comprueba que **Configuración nativa** lleva a los ajustes de la misma integración. |
| Luces | Busca **Luz Demo**, márcala, guarda y espera **Configuración guardada**. Vuelve a entrar y verifica la selección. Si tienes otra luz de laboratorio, prueba la selección múltiple y desmarca después la adicional. Las otras luces deben conservar su selección inicial. |
| Zonas | Crea **Sala C.2.2**, asigna un área existente de HA y selecciona **Luz Demo**. El guardado confirmado vuelve al listado. Edita la zona y cámbiale el nombre. Al volver a abrirla deben conservarse el área y las luces. |
| Dependencia de una luz | Intenta desmarcar **Luz Demo** mientras la zona la use. Si tienes otras luces administradas, mantenlas seleccionadas para poder pulsar **Guardar**. Debe aparecer un error de dependencia y conservarse el borrador. Descarta el cambio y vuelve a abrir para verificar que **Luz Demo** sigue autorizada. |
| Modos y vista previa | Crea **Cine C.2.2** y **Lectura C.2.2** en la misma zona, con colores y brillos distintos. En Cine elige **Pulso**, pulsa **Simular efecto** y comprueba que la tira en pantalla cambia y la luz real conserva su estado. Guarda cada modo y verifica que aparece en el listado. |
| Activación | Activa Cine y luego Lectura. Comprueba que desaparece el estado activo de Cine y queda Lectura. Desactiva Lectura. Si hay otra petición con mayor prioridad, el modo puede aparecer enmascarado. La luz conserva el comportamiento que le corresponde por prioridad. |
| Control externo opcional | Activa **Crear interruptor para Alexa y otros controles** en Cine. En **Ajustes → Dispositivos y servicios → Entidades**, encuentra su interruptor y actívalo. Comprueba su reflejo en el panel. Si ya usas Matter Hub o Alexa, registra esa comprobación por separado. |
| Borrador y recarga | Abre una zona o un modo y cambia el nombre. Pulsa **Volver** y elige **Continuar editando**. En otra pestaña, recarga la integración desde **Ajustes → Dispositivos y servicios → Smart LED Manager → ⋮ → Recargar**. El panel debe quedarse en la misma ruta y conservar el nombre escrito. Tras la recarga, prueba **Guardar y salir**. Vuelve a editar, cambia otro campo y elige **Descartar cambios y salir**. Comprueba que se conserva el valor guardado. Abrir y cancelar sin editar debe salir directamente. |
| Reinicio y eliminación | Reinicia Home Assistant y comprueba que siguen las luces, áreas, zonas, modos, reglas y el interruptor opcional. Intenta eliminar la zona mientras tiene modos. Debe rechazarlo y conservar los datos. Elimina primero los modos de prueba y después la zona. Espera la confirmación en cada paso y verifica que siguen ausentes después de reiniciar. Repite el recorrido de reglas con los [casos P-01–P-06](haos-c21-checks.md#2-pruebas-del-propietario). |

## 3. Guarda evidencia y registra fallos

- Captura el inicio, luces, zonas y modos con los temas claro y oscuro de la
  VM. Usa 1280×900 para escritorio y 390×844 para móvil cuando puedas. Compara con
  las referencias y anota diferencias, problemas de lectura o controles que no
  respondan. [Capturas y comparación de C.2.2](design/c22-evidence/README.md).
- Si algo falla, abre **Ajustes → Sistema → Registros → Home Assistant Core**
  y busca `smart_led_manager`. Si la interfaz no abre, escribe `core logs` en
  la consola `ha >`. Anota la hora, la pantalla, el mensaje completo, si
  apareció la confirmación y si seguía visible el borrador. Quita secretos
  de cualquier registro que compartas.
  [Registros de Home Assistant](https://www.home-assistant.io/integrations/system_log/).
- Comparte los pasos aprobados y los que requieren revisión. Registra por
  separado este recorrido de VirtualBox, los casos C-01–C-20 y U-01–U-06 y las
  pruebas físicas con Zigbee, Matter Hub o Alexa. [Plan de pruebas HAOS](haos-test-plan.md).

## Pruebas técnicas de Codex

El SHA de instalación pasó Ruff y 237 pruebas por cada versión de Home
Assistant en Linux (2026.11.0 y 2026.11.2), con 85,59 % de cobertura de ramas.
También pasaron las 12 pruebas frontend, Hassfest y HACS/Marketplace. Estas
pruebas cubren permisos, autorizaciones, respuestas WebSocket, revisión
concurrente, descarte, recuperación de guardados y persistencia. El recorrido
adicional en Chromium usó datos de prueba. La validación práctica con HAOS
sigue pendiente. [CI Linux y frontend](https://github.com/abel-smart-home/smart-led-manager/actions/runs/45876521527) · [Hassfest y HACS/Marketplace](https://github.com/abel-smart-home/smart-led-manager/actions/runs/45876521637).
