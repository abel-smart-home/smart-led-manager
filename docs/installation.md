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
   `controllers/`, `modules/` y `frontend/` estén presentes.
4. Reinicia Home Assistant y revisa los registros.
5. Añade la integración desde la interfaz. No se requiere YAML.

## Actualización manual

Para actualizar desde alpha.2 o desde los Bloques A/B de alpha.3 al Bloque B.1
sin perder la entrada:

1. Crea una copia de seguridad de Home Assistant y conserva una copia de la
   carpeta instalada.
2. **No elimines la entrada** de Smart LED Manager ni sus entidades.
3. Detén Home Assistant Core y reemplaza únicamente
   `custom_components/smart_led_manager/` por la carpeta completa del commit
   candidato; no mezcles archivos de distintos commits.
4. Inicia Core de nuevo. El mismo dominio y ConfigEntry conservan el `entry_id`,
   luces autorizadas, opciones, reglas, zonas, modos y solicitudes del Store.
5. Verifica que el dispositivo central conserve el sensor del motor y que cada
   zona tenga su dispositivo con el mismo selector y switches. Los `entity_id`
   y nombres personalizados deben permanecer iguales.
6. Abre **Configurar > Reglas inteligentes** y confirma que las reglas antiguas
   aparecen habilitadas, conservan sus valores y se pueden editar. Una regla
   duplicada debe usar un identificador nuevo y comenzar deshabilitada.
7. Abre una regla numérica, comprueba sus puntos en el editor visual y descarta
   el flujo sin guardar; no debe producir cambios físicos. Guarda después una
   edición controlada y comprueba la recarga.
8. Abre **Configurar** con el perfil en Español o Español (Latinoamérica). Si el
   navegador conservaba recursos anteriores, recarga la página sin caché o
   cierra y vuelve a abrir la aplicación.
9. Asigna un área opcional desde la edición de la zona. No edites archivos de
   `.storage` ni cambies el área de las luces físicas para completar esta
   prueba.
10. Con una cuenta administradora abre **Configurar > Centro de administración**
    y sigue el enlace interno, usa la barra lateral o entra en
    `/smart-led-manager-editor`. Si el panel no aparece, comprueba
    que copiaste `frontend/`, reinicia Core y recarga el navegador sin caché.
11. Simula un valor antes de guardar: la luz no debe cambiar. Guarda después una
    edición controlada, espera la recarga normal y confirma que la regla
    conserva su identificador y metadatos.

## Acceso al editor gráfico B.1

El panel se registra automáticamente cuando carga la única ConfigEntry y exige
administrador. No requiere añadir un recurso Lovelace ni configuración YAML.
Hay tres referencias de acceso:

1. **Barra lateral > Smart LED Manager**.
2. **Ajustes > Dispositivos y servicios > Smart LED Manager > Configurar >
   Centro de administración**, con enlace interno y el ajuste **Mostrar Smart
   LED Manager en la barra lateral**.
3. **Configurar > Reglas inteligentes > Abrir editor gráfico avanzado**, que
   conserva otro enlace al mismo centro.

Home Assistant 2026.11 no ofrece una API pública estable para redirigir
automáticamente desde un Options Flow; usa el enlace Markdown compatible. Si
se oculta la entrada lateral, `/smart-led-manager-editor` continúa disponible.
El panel sólo edita puntos y modo de reglas
numéricas existentes; para crear una regla o cambiar origen, prioridad,
destinos y otros metadatos usa el editor nativo.

La interfaz `es-419` fue comprobada físicamente; el catálogo `es` tiene
cobertura automatizada, pero no una ejecución física independiente registrada.

La migración alpha.3 añade un campo de área opcional a cada zona, conserva sus
identificadores y no cambia el almacenamiento de solicitudes. Para volver a
alpha.2 restaura la copia de seguridad completa; no sustituyas sólo el código
después de migrar a un `minor_version` más reciente.

El Bloque B no incrementa el esquema: añade un campo opcional `enabled` a las
definiciones que se guarden. Aun así, una reversión de sólo código al Bloque A
no es segura si existen copias o reglas deshabilitadas, porque ese código las
trataría como activas. Restaura la copia completa anterior a Bloque B. Si debes
preparar una reversión manual, elimina primero las copias y reglas
deshabilitadas desde la versión nueva y verifica prioridades y destinos antes
de detener Core.

El Bloque B.1 tampoco cambia ConfigEntry ni Store. Para revertir únicamente el
panel, detén Core, restaura la carpeta completa del commit `f8b9fc9` y reinicia.
Las reglas y los puntos guardados siguen siendo compatibles, pero el rollback
de código no deshace ediciones: restaura la copia de seguridad si también
quieres recuperar los valores anteriores.

## Desinstalación

1. Elimina primero la entrada desde **Dispositivos y servicios** para que se
   cancelen listeners y tareas.
2. Reinicia si Home Assistant lo solicita.
3. Si fue una instalación manual, elimina después
   `custom_components/smart_led_manager/` y reinicia de nuevo.

La descarga no fuerza una restauración ciega de las luces. Comprueba su estado
final y ajústalo con la integración física correspondiente si es necesario.
