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

Haz una copia de seguridad, detén Home Assistant, reemplaza únicamente la
carpeta de esta integración por la versión completa nueva y vuelve a iniciar.
No mezcles archivos de versiones. Revisa `CHANGELOG.md` y las instrucciones de
migración de la versión destino antes de actualizar.

## Desinstalación

1. Elimina primero la entrada desde **Dispositivos y servicios** para que se
   cancelen listeners y tareas.
2. Reinicia si Home Assistant lo solicita.
3. Si fue una instalación manual, elimina después
   `custom_components/smart_led_manager/` y reinicia de nuevo.

La descarga no fuerza una restauración ciega de las luces. Comprueba su estado
final y ajústalo con la integración física correspondiente si es necesario.
