# Marketplace, compatibilidad y publicación

Fecha de verificación: 20 de noviembre de 2026.

Este documento fija los criterios de distribución de Smart LED Manager como
integración personalizada de Home Assistant. Las decisiones se basan en la
documentación oficial vigente de Home Assistant y en el estado actual del
repositorio. Debe revisarse antes de cada pre-release, porque Marketplace y las
API de Home Assistant evolucionan con rapidez.

## Estado actual de HACS y Marketplace

Home Assistant 2026.11 incorporó Marketplace en Core, bajo **Ajustes >
Marketplace**. Marketplace sustituye a la integración personalizada HACS en
esa versión: migra los repositorios instalados, repositorios personalizados y
entidades de actualización, y elimina los archivos de HACS. Los enlaces HACS
existentes continúan funcionando y abren Marketplace.

Para quienes todavía ejecuten una versión anterior a Home Assistant 2026.11,
HACS conserva utilidad como canal de instalación. Del lado del publicador se
mantienen el catálogo `hacs/default`, el archivo `hacs.json` y HACS Action. Los
blueprints no forman parte de Marketplace; Home Assistant los importa desde
una URL.

Fuentes oficiales:

- [Notas de Home Assistant 2026.11](https://www.home-assistant.io/blog/2026/11/04/release-202611/)
- [Cómo funciona Marketplace](https://contributors.home-assistant.io/marketplace/how-it-works/)
- [Marketplace para usuarios](https://www.home-assistant.io/integrations/marketplace/)

## Decisiones para Smart LED Manager

| Tema | Decisión para `v0.1.0-alpha.2` |
|---|---|
| Tipo de repositorio | Un repositorio público para una integración personalizada. |
| Dominio | `smart_led_manager`; no debe cambiar después de publicar. |
| Tipo de integración | `helper`, porque coordina entidades existentes y ofrece entidades auxiliares. |
| Clase IoT | `calculated`, porque el resultado se calcula dentro de Home Assistant y no se conecta a una nube o dispositivo propio. |
| Instancias | Una sola entrada de configuración mediante `single_config_entry`. |
| Configuración | Exclusivamente gráfica mediante config flow, options flow y, cuando se incorporen, config subentries. |
| Canal principal | Marketplace integrado de Home Assistant 2026.11 o posterior. |
| Versión mínima provisional | Home Assistant `2026.11.0`, por ser la primera versión que incluye Marketplace. Debe validarse en CI antes de publicarla en `hacs.json`. |
| Versión de prueba actual | Home Assistant y `pytest-homeassistant` `2026.11.2`, último parche disponible al redactar este documento. |
| Versión del proyecto | `0.1.0-alpha.2` en manifest y release; `0.1.0a2` es su representación PEP 440 en `pyproject.toml`. |
| Idiomas iniciales | Inglés completo como fallback obligatorio y español completo. |
| Dependencias externas | Ninguna para el funcionamiento inicial; se utilizan únicamente API incluidas en Home Assistant. |

La versión mínima no debe elevarse por comodidad. Si se desea compatibilidad
con instalaciones anteriores mediante HACS, se podrá reducir únicamente tras
probar una matriz contra la versión mínima propuesta. El uso de config
subentries, por sí solo, exige Home Assistant 2025.3 o posterior, porque esa fue
la versión en la que se incorporaron.

Fuentes:

- [Manifest de integraciones](https://contributors.home-assistant.io/core/integrations/manifest/)
- [Categorías de integraciones](https://contributors.home-assistant.io/core/integrations/categories/)
- [Introducción de config subentries en 2025.3](https://www.home-assistant.io/blog/2025/03/05/release-20253/)

## Estructura obligatoria del repositorio

Marketplace instala la primera carpeta que encuentre bajo
`custom_components/`. La estructura mínima esperada es:

```text
custom_components/smart_led_manager/
    __init__.py
    manifest.json
    config_flow.py
    translations/
        en.json
        es.json
    brand/
        icon.png
hacs.json
README.md
```

Todos los archivos que la integración necesite en ejecución deben estar dentro
de `custom_components/smart_led_manager/`. El repositorio debe tener también
descripción, temas de GitHub, Issues habilitados y releases publicadas para
entrar en el catálogo.

El catálogo exige una imagen de marca, ya sea dentro de `brand/` en la
integración o en el repositorio oficial de marcas. La imagen no debe utilizar la
marca de Home Assistant de forma que parezca una integración oficial.

Fuente: [estructura de repositorios de Marketplace](https://contributors.home-assistant.io/marketplace/reference/repository-structure/).

## `manifest.json`

El manifest de una integración personalizada debe contener como mínimo un
dominio válido y coincidente con la carpeta, nombre, documentación HTTPS,
`codeowners`, `issue_tracker` y una versión aceptada por AwesomeVersion. Para
Smart LED Manager se conservan además:

- `config_flow: true`;
- `integration_type: service`, porque una entrada representa el servicio local
  de administración de iluminación y no una entidad auxiliar individual;
- `iot_class: calculated`;
- `single_config_entry: true`;
- `requirements: []` mientras no exista una dependencia externa;
- `after_dependencies: ["light"]` únicamente si el código necesita cargarse
  después de la plataforma `light` cuando esta ya está presente.

El manifest actual conserva `helpers` como categoría de catálogo y
`lighting.led_strips_controllers` como categoría secundaria; estas categorías
no determinan si la entrada aparece en **Integraciones** o **Ayudantes**. Esa
clasificación de ejecución depende de `integration_type`. También identifica al
mantenedor verificado `@Platibolo` en `codeowners` y conserva
`0.1.0-alpha.2` como versión del candidato. Antes de publicar sólo queda
confirmar esas decisiones mediante hassfest/HACS Action y mantener la versión
sincronizada con el commit que eventualmente se etiquete.

Las categorías son opcionales para una integración personalizada, pero HACS
Action avisa cuando faltan y Marketplace las utiliza para presentar el proyecto
en el catálogo.

Fuente: [guía oficial para publicar una integración personalizada](https://contributors.home-assistant.io/marketplace/guides/integrations/).

## `hacs.json`

Marketplace lee `hacs.json` desde la raíz de cada versión que instala. Sin ese
archivo no puede instalar ni actualizar el repositorio.

El archivo actual contiene:

```json
{
  "name": "Smart LED Manager",
  "homeassistant": "2026.11.0"
}
```

No incluye claves obsoletas como `render_readme`. La matriz de CI debe demostrar
que el mínimo declarado `2026.11.0` y el parche fijado funcionan antes de que
esa declaración se use en una release.

No se necesita `zip_release` mientras Marketplace pueda instalar directamente
la carpeta de la integración desde el archivo de la release. Si en el futuro se
genera un ZIP, `zip_release` y `filename` deberán describir exactamente el
asset publicado.

Fuente: [referencia vigente de `hacs.json`](https://contributors.home-assistant.io/marketplace/reference/hacs-json/).

## Versionado y releases

Una etiqueta de Git no basta: Marketplace y el catálogo requieren una release
de GitHub publicada. Para una integración, la versión del `manifest.json` debe
corresponder a la versión de la release.

Flujo de `v0.1.0-alpha.2`:

1. Completar código, documentación y pruebas en una rama de desarrollo.
2. Ejecutar pytest, Ruff, hassfest y HACS Action sin exclusiones.
3. Revisar el diff y fusionar sólo con autorización del propietario.
4. Etiquetar el commit aprobado usando una convención única. Para coincidir de
   forma literal con el manifest, se recomienda `0.1.0-alpha.2`; si se conserva
   `v0.1.0-alpha.2`, debe comprobarse previamente la normalización con HACS
   Action y Marketplace.
5. Crear una **pre-release** de GitHub con notas completas. No publicar sólo la
   etiqueta.

Marketplace ofrece una pre-release únicamente a usuarios que habilitaron el
interruptor de versiones preliminares para el repositorio, y sólo mientras esa
versión sea más reciente que la última release estable.

Fuente: [releases y actualizaciones de Marketplace](https://contributors.home-assistant.io/marketplace/guides/releases/).

## Validación automática

Antes de entrar en el catálogo deben aprobarse dos validaciones independientes:

- **hassfest**, que comprueba manifest, traducciones y convenciones de la
  integración;
- **HACS Action** con `category: integration`, que comprueba los requisitos del
  catálogo y que también utiliza Marketplace.

No se permite usar `ignore` para aparentar que el repositorio es válido. La
revisión de catálogo exige enlaces a ejecuciones exitosas sin exclusiones.

Marketplace vuelve a comprobar durante la instalación:

- presencia de `hacs.json`;
- archivos en las rutas esperadas;
- repositorio no archivado ni retirado;
- versión mínima de Home Assistant;
- dominio válido, coincidente y no ocupado;
- `manifest.json` cargable y con versión reconocida;
- descarga inferior a 100 MiB y 50 000 archivos.

Si una validación posterior a copiar los archivos falla, Marketplace revierte
los archivos a su estado anterior.

### Revisión de los workflows actuales

`actions/checkout@v7` y `actions/setup-python@v7` son versiones vigentes que
ejecutan sobre Node.js 24, por lo que no dependen de los runtimes antiguos que
se desea evitar. El uso de `home-assistant/actions/hassfest@master` y
`hacs/action@main` coincide con los ejemplos oficiales actuales. Dependabot ya
vigila el ecosistema `github-actions`.

Los workflows actuales validan cada `push`, pull request y ejecución manual;
mantienen `contents: read`, desactivan el comentario de HACS Action y prueban
Home Assistant `2026.11.0` y `2026.11.2`. La mejora pendiente no bloqueante es
fijar acciones de terceros a SHA inmutables cuando el flujo de actualización
adoptado lo permita, dejando la versión legible en un comentario. Dependabot
ya vigila esas referencias.

Fuente: [comprobaciones de validación de Marketplace](https://contributors.home-assistant.io/marketplace/reference/validation/).

## Configuración gráfica y subentries

Una config entry representa el único motor central de Smart LED Manager. Los
elementos repetibles encajan de forma natural en config subentries:

- subentry `strip` para una tira autorizada;
- subentry `rule` para una regla configurable;
- tipos adicionales sólo cuando representen elementos independientes que el
  usuario pueda crear, editar y eliminar.

Un subentry flow sólo admite los pasos `user` y `reconfigure`; no admite
discovery ni reautenticación. Los identificadores únicos deben impedir
duplicados dentro de la entrada principal.

Options flow debe reservarse para preferencias globales del motor. Si las
opciones requieren recarga, se debe usar `OptionsFlowWithReload`. No debe
combinarse con un update listener que también recargue: Home Assistant ya
rechaza esa combinación en algunos flujos y endurecerá el comportamiento en
2026.12.

Fuentes:

- [config subentries](https://contributors.home-assistant.io/core/integrations/subentries/)
- [options flow](https://contributors.home-assistant.io/core/integrations/options-flow/)

## Acciones de Home Assistant

La interfaz usa el término **acciones**, aunque las API internas y el archivo
siguen usando `services`. Las acciones de Smart LED Manager deben registrarse
una sola vez desde `async_setup`, preferiblemente mediante
`services.async_setup_services`. No deben registrarse en `async_setup_entry` ni
en una plataforma.

Si existe `async_setup`, la integración debe declarar:

```python
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
```

Todas las acciones deben describirse en `services.yaml` con selectores
visuales. Smart LED Manager admite una sola entrada y por ello sus acciones
resuelven esa única instancia cargada; si en el futuro se permiten varias,
deberán pedir explícitamente `config_entry_id`. Los errores de entrada deben
producir `ServiceValidationError` y los demás fallos `HomeAssistantError`,
ambos con mensajes traducidos.

Fuente: [acciones en integraciones](https://contributors.home-assistant.io/core/integrations/actions/).

## Traducciones

La documentación vigente distingue las integraciones de Core de las
integraciones personalizadas. Smart LED Manager no debe depender de
`strings.json` ni de Lokalise. Debe distribuir directamente:

- `translations/en.json`, completo y obligatorio como fallback;
- `translations/es.json`, completo para Español;
- `translations/es-419.json`, completo para Español (Latinoamérica).

Los tres archivos deben contener los textos de config flow, options flow,
subentries, entidades, errores y acciones que correspondan. Las referencias
`[%key:...%]` no se resuelven en las traducciones de una integración
personalizada y no deben utilizarse. Hassfest valida `translations/en.json`.

Fuente: [traducciones para integraciones](https://contributors.home-assistant.io/core/integrations/translations/).

## Pruebas y dependencias de desarrollo

El paquete de pruebas de primera parte es `pytest-homeassistant`, publicado
desde Home Assistant Core. Debe usarse en la misma versión que Home Assistant y
no debe instalarse junto con `pytest-homeassistant-custom-component`, porque
ambos aportan fixtures solapados.

Revisión de `requirements_test.txt`:

- `homeassistant==2026.11.2` coincide con el parche vigente al redactar este
  documento.
- `pytest-homeassistant==2026.11.2` está fijado para que sus fixtures coincidan
  exactamente con Home Assistant.
- Puede conservarse el pin explícito de ambos paquetes para que la relación sea
  visible, aunque `pytest-homeassistant` ya depende de la versión de Home
  Assistant correspondiente.
- Las restricciones mayores de pytest, pytest-asyncio, pytest-cov y Ruff son
  razonables, pero Dependabot debe mantenerlas actualizadas.

Las pruebas de integración deben atravesar las interfaces públicas de Home
Assistant: configurar mediante config entries, consultar la state machine,
invocar acciones mediante `hass.services`, y revisar los registros de entidades
y dispositivos. Los mocks deben situarse en los límites externos, no sustituir
el coordinador, el motor o helpers internos que se pretende probar.

Se requiere cobertura funcional de config flow, options/subentries, carga,
descarga, migraciones, acciones, persistencia y errores. La cobertura de líneas
no sustituye afirmaciones explícitas sobre comportamiento.

Fuentes:

- [`pytest-homeassistant` en Home Assistant Core](https://github.com/home-assistant/core/blob/dev/packages/pytest-homeassistant/README.md)
- [Cómo escribir pruebas](https://contributors.home-assistant.io/core/development/tests/)
- [Cómo ejecutar pruebas y cobertura](https://contributors.home-assistant.io/core/development/testing/)

## Lista previa a publicación

- [ ] El dominio del manifest coincide con la carpeta.
- [ ] Manifest y release contienen la misma versión lógica.
- [ ] `codeowners` identifica un usuario o equipo válido.
- [ ] `categories` utiliza valores vigentes.
- [ ] Existen `translations/en.json` y `translations/es.json` completos.
- [ ] Existe una imagen válida en `brand/` o en el repositorio de marcas.
- [ ] `hacs.json` sólo contiene claves reconocidas.
- [ ] La versión mínima está probada y declarada en `hacs.json`.
- [ ] `pytest-homeassistant` coincide con la versión de Home Assistant.
- [ ] Ruff, pytest y cobertura terminan correctamente.
- [ ] hassfest termina correctamente.
- [ ] HACS Action termina correctamente, sin `ignore`.
- [ ] La release contiene notas, es una pre-release y no es sólo una etiqueta.
- [ ] No se afirma que las pruebas físicas en HAOS pasaron hasta que el
  propietario las ejecute.
