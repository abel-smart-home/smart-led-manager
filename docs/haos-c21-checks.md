# Instalar y probar Smart LED Manager C.2.1 en HAOS VirtualBox

Usa tu máquina de laboratorio de VirtualBox con Home Assistant OS. El código
que se va a probar es **0.1.0-alpha.3**, commit
`cf2f371353dc6321baaef67c0ca8858e6d564110`. Descarga y descomprime el ZIP en
Windows. El nombre de la carpeta extraída incluye ese SHA.
[Descargar el ZIP de C.2.1](https://github.com/abel-smart-home/smart-led-manager/archive/cf2f371353dc6321baaef67c0ca8858e6d564110.zip).

## 1. Respalda e instala

1. En la VM abre **Ajustes → Sistema → Copias de seguridad** y crea una copia
   completa. Descárgala a Windows y guarda también el kit de emergencia si la
   copia está cifrada. Conserva una copia de la carpeta instalada
   `custom_components/smart_led_manager` en Windows, con el nombre
   `smart_led_manager-anterior`. Si usas instantáneas de VirtualBox, puedes
   tomar una con la VM apagada antes de volver a arrancarla.
   [Copias de seguridad de Home Assistant](https://www.home-assistant.io/common-tasks/general/#backups).
2. En el Explorador de Windows, abre tu acceso habitual a los archivos de la
   VM. Con Samba, escribe `\\IP-DE-LA-VM` y abre la carpeta donde ves
   `configuration.yaml`. Dentro está `custom_components`.
   [Acceder a los archivos de HAOS](https://www.home-assistant.io/common-tasks/os/#configuring-access-to-files).
3. Abre la ventana de la VM en VirtualBox. En la consola que muestra
   `ha >`, escribe `core stop` y espera a que termine. La página de Home
   Assistant dejará de responder hasta que inicies Core de nuevo.
4. Confirma que tienes la copia de la carpeta anterior en Windows. Quita la
   carpeta instalada `smart_led_manager` de `custom_components` y pega ahí
   **la carpeta completa** del ZIP. Comprueba que
   `manifest.json`, `services.yaml` y las carpetas `frontend`, `translations`,
   `core`, `controllers` y `modules` queden dentro de una sola carpeta
   `smart_led_manager`. Conserva la entrada existente de la integración y
   deja intactos `configuration.yaml`, `.storage` y los demás componentes.
5. En la misma consola escribe `core start`. Cuando vuelva la interfaz,
   recarga la página del navegador. Abre **Smart LED Manager** desde la barra
   lateral o escribe `/smart-led-manager-editor` al final de la dirección de
   la VM. Comprueba que la entrada existente conserva sus luces autorizadas,
   reglas, zonas y modos.

**Para volver atrás.** Detén Core, vuelve a poner la carpeta anterior bajo
`custom_components/smart_led_manager` e inicia Core. Esto revierte el código.
Para recuperar también las opciones anteriores, restaura la copia completa
desde **Ajustes → Sistema → Copias de seguridad** o la instantánea de la VM.
Si la interfaz no vuelve a abrir, usa la consola de VirtualBox para consultar
el registro antes de restaurar. [Restaurar una copia de HAOS](https://www.home-assistant.io/integrations/backup/#restoring-a-backup).

## 2. Pruebas del propietario

Usa una luz Demo autorizada y un ayudante interruptor. Anota el SHA, la versión
de HA y el navegador. Guarda el resultado de cada prueba.

| Prueba | Qué hacer y qué observar |
| --- | --- |
| Crear y guardar | En **Reglas inteligentes → Crear regla** elige **Estado**, ponle el nombre **C.2.1 Lab**, usa el interruptor como origen y la luz Demo como destino. Déjala deshabilitada para empezar. Pulsa **Guardar**. Espera **Configuración guardada** y verifica que vuelves al catálogo en `/smart-led-manager-editor`. Abre la regla para comprobar los valores. |
| Editar y cancelar | Cambia el nombre y pulsa **Cancelar**. Elige **Continuar editando** y comprueba que el nombre nuevo sigue escrito. Abre el diálogo otra vez y pulsa **Descartar cambios y salir**. El catálogo debe conservar el nombre guardado. |
| Guardar y salir | Cambia la prioridad y pulsa **Volver**. Elige **Guardar y salir**. Al confirmarse el guardado, abre la regla y comprueba la prioridad nueva. |
| Recarga y borrador | Deja un cambio sin guardar. En otra pestaña abre **Ajustes → Dispositivos y servicios → Smart LED Manager → ⋮ → Recargar**. La pestaña del editor debe conservar su URL y el borrador. Si el estado tarda en actualizarse, pulsa **Comprobar estado**. Guarda o descarta el cambio al terminar. |
| Persistencia | Desde **Ajustes → Sistema**, usa **Reiniciar Home Assistant**. Abre de nuevo el panel. Comprueba que la regla de prueba, su prioridad y las reglas anteriores siguen guardadas. Un borrador que descartaste no debe aparecer. |
| Eliminar | Elimina **C.2.1 Lab** desde el catálogo y confirma. Espera el aviso de guardado y comprueba que la regla desapareció. Reinicia Home Assistant y verifica que sigue ausente. |

Para la comparación visual, captura el editor y el diálogo de salida con la
misma regla a 1280×900 claro y 390×844 oscuro. En C.2.1 una edición guardada
regresa al catálogo, conforme al prototipo. [Navegación de diseño](design/navigation.md).

## 3. Si falla algo

- En **Ajustes → Sistema → Registros**, revisa **Home Assistant Core** y
  busca `smart_led_manager`. Desde la consola de VirtualBox puedes escribir
  `core logs` en `ha >` si el navegador no carga.
- Anota la hora del fallo, el mensaje exacto, si el catálogo muestra el cambio
  y si seguía visible el borrador. Conserva la parte del registro que coincide
  con esa hora. Omite tokens, contraseñas y claves al compartirla.
- Si el panel dice que las opciones se recibieron pero falta aplicarlas,
  comprueba el catálogo y el registro antes de intentar guardar otra vez.
  [Registros de Home Assistant](https://www.home-assistant.io/integrations/system_log/).

## Pruebas técnicas de Codex

La matriz Linux del SHA de instalación aprobó 233 pruebas por variante de
Home Assistant (2026.11.0 y 2026.11.2) y 85,54 % de cobertura con ramas.
Pasaron Ruff, las 12 pruebas frontend, Hassfest y HACS/Marketplace.
[CI Linux y frontend](https://github.com/abel-smart-home/smart-led-manager/actions/runs/45731820881) · [Hassfest y HACS](https://github.com/abel-smart-home/smart-led-manager/actions/runs/45731820902).

Las pruebas técnicas cubren revisiones obsoletas, accesos de administrador,
recargas correctas y fallidas, pérdida de eventos o de respuesta WebSocket y
reenvíos. El recorrido automatizado de navegador usa un backend simulado.
Registra por separado los resultados de esta guía en VirtualBox, los casos
C-01–C-20 y U-01–U-06, y las repeticiones con Zigbee.
[Plan de pruebas HAOS](haos-test-plan.md).
