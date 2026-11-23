# Instalación

## Requisitos

- Home Assistant `2026.11.0` o posterior para el objetivo de esta alfa.
- Al menos una entidad `light` ya configurada y operativa.
- Copia de seguridad reciente de la configuración de Home Assistant.

Smart LED Manager es una capa sobre entidades existentes. No instala firmware,
no se comunica directamente con una tira y no sustituye ZHA, Matter, ESPHome,
WLED u otra integración de dispositivo.

## Marketplace

Marketplace de Home Assistant 2026.11+ es el canal previsto, pero sólo estará
disponible cuando el propietario publique una release y autorice el alta del
repositorio. No interpretes la presencia de `hacs.json` como prueba de que la
versión ya está publicada o aprobada.

Cuando exista una release:

1. Abre **Ajustes > Marketplace**.
2. Busca **Smart LED Manager** e instala la versión compatible.
3. Reinicia Home Assistant si Marketplace lo solicita.
4. Ve a **Ajustes > Dispositivos y servicios > Añadir integración**.
5. Busca **Smart LED Manager** y selecciona las luces autorizadas.

En instalaciones anteriores a Home Assistant 2026.11, HACS sólo será un canal
secundario si la release declara y prueba esa compatibilidad.

## Instalación manual para desarrollo

1. Descarga o clona el commit que vas a probar; no uses una rama desconocida en
   una instalación productiva.
2. Copia la carpeta completa:

   ```text
   custom_components/smart_led_manager/
   ```

   a:

   ```text
   <config>/custom_components/smart_led_manager/
   ```

3. Verifica que `manifest.json`, `services.yaml`, `translations/`, `core/`,
   `controllers/` y `modules/` estén presentes.
4. Reinicia Home Assistant y revisa los registros.
5. Añade la integración desde la interfaz. No se requiere YAML.

## Actualización manual

Para actualizar esta corrección desde un alpha.2 anterior sin perder la entrada:

1. Crea una copia de seguridad de Home Assistant y conserva una copia de la
   carpeta instalada.
2. **No elimines la entrada** de Smart LED Manager ni sus entidades.
3. Detén Home Assistant Core y reemplaza únicamente
   `custom_components/smart_led_manager/` por la carpeta completa del commit
   candidato; no mezcles archivos de distintos commits.
4. Inicia Core de nuevo. El mismo dominio y ConfigEntry conservan el `entry_id`,
   luces autorizadas, opciones, reglas, zonas, modos y solicitudes del Store.
5. Verifica que la entrada existente aparezca en **Ajustes > Dispositivos y
   servicios > Integraciones** y no en **Ayudantes**. El propietario confirmó
   esta clasificación con `8e21b28` en HAOS `2026.11.2`.
6. Abre **Configurar** con el perfil en Español o Español (Latinoamérica). Si el
   navegador conservaba recursos anteriores, recarga la página sin caché o
   cierra y vuelve a abrir la aplicación.

La interfaz `es-419` fue comprobada físicamente; el catálogo `es` tiene
cobertura automatizada, pero no una ejecución física independiente registrada.

El cambio de `integration_type` es metadato del manifest: no requiere una
migración del ConfigEntry ni del almacenamiento persistente.

## Desinstalación

1. Elimina primero la entrada desde **Dispositivos y servicios** para que se
   cancelen listeners y tareas.
2. Reinicia si Home Assistant lo solicita.
3. Si fue una instalación manual, elimina después
   `custom_components/smart_led_manager/` y reinicia de nuevo.

La descarga no fuerza una restauración ciega de las luces. Comprueba su estado
final y ajústalo con la integración física correspondiente si es necesario.
