# Smart LED Manager

Smart LED Manager es una integración personalizada y completamente local para
Home Assistant. Coordina solicitudes de color, brillo, escenas y avisos sobre
entidades `light` existentes, y decide cuál debe verse en cada luz mediante un
motor de prioridades determinista.

> **Estado:** `0.1.0-alpha.2` en desarrollo. Es un candidato experimental para
> validación física, no una release publicada. Conserva la base alpha.1 probada
> con HAOS/ZHA/GLEDOPTO; las funciones nuevas de modos, Alexa y Matter Hub aún
> no tienen validación física.

## Qué hace esta alfa

- Controla únicamente las luces que el usuario autoriza en el flujo gráfico.
- Resuelve cada luz por separado con prioridades `0..100` y desempate
  configurable (`newest`, `oldest` o `lexical`).
- Conserva y actualiza solicitudes de prioridad inferior mientras están
  ocultas, para mostrar la vigente al terminar la solicitud superior.
- Admite reglas de estado y reglas numéricas de color con N puntos,
  interpolación o rangos.
- Permite crear zonas no superpuestas y modos persistentes por zona. Cada zona
  expone un `select`; un modo puede exponer además un `switch` opcional para
  paneles o puentes, sin depender de Alexa o Matter.
- Expone acciones para activar, desactivar y cancelar solicitudes, enviar
  avisos, fijar escenas, limpiar avisos y establecer control manual explícito.
- Proyecta la intención RGB sobre las capacidades declaradas por cada entidad,
  con deduplicación, límite de frecuencia, cancelación de trabajo obsoleto y
  recuperación al volver de `unavailable`.
- Persiste únicamente las solicitudes marcadas para ello y vuelve a resolver el
  estado actual al iniciar; no restaura snapshots antiguos a ciegas.
- Incluye animaciones iniciales fija, parpadeo y pulsación.

Smart LED Manager no controla hardware directamente: actúa sobre integraciones
de luz ya configuradas, como ZHA, Matter, ESPHome o WLED. Tampoco es un sistema
certificado de alarma, incendio o emergencia.

Home Assistant la clasifica como integración de tipo `service`: una entrada
representa el servicio local de administración de iluminación. No es un
Ayudante individual, aunque proporcione entidades auxiliares para controlarlo.

## Compatibilidad objetivo

| Componente | Versión de esta alfa |
|---|---|
| Home Assistant | `2026.11.0` o posterior |
| Versión del manifest/release | `0.1.0-alpha.2` |
| Versión de paquete Python | `0.1.0a2` |
| Configuración ordinaria | Interfaz gráfica; YAML no requerido |
| Operación | Local, asíncrona y sin servicio externo |

La compatibilidad mínima queda condicionada a que la matriz de CI y las
validaciones de Marketplace terminen correctamente antes de publicar.

## Instalación y primera configuración

Mientras no exista una release autorizada, la instalación manual se reserva a
desarrollo y pruebas. Copia
`custom_components/smart_led_manager` dentro de `config/custom_components/`,
reinicia Home Assistant y agrega **Smart LED Manager** desde **Ajustes >
Dispositivos y servicios > Añadir integración**. Selecciona sólo las luces que
quieras delegar al motor. Después abre **Configurar > Zonas** y **Configurar >
Modos de iluminación** para crear el catálogo; no hace falta YAML.

Cuando haya una release compatible, Marketplace de Home Assistant 2026.11+
será el canal previsto. Consulta la [guía de instalación](docs/installation.md)
y la [guía de configuración](docs/configuration.md) antes de probarla.

## Ejemplo de acción

Las acciones aparecen en el editor visual de Home Assistant. El YAML
equivalente de un aviso temporal es:

```yaml
action: smart_led_manager.notify
data:
  request_id: lavadora_terminada
  targets:
    - light.tira_cocina
  priority: 70
  rgb_color: [0, 255, 0]
  brightness: 180
  duration: 5
  animation: pulse
  period: 1
```

`light.tira_cocina` debe estar incluida en las luces administradas. Reutilizar
`request_id` actualiza la misma intención; omitirlo genera uno nuevo. Todas las
acciones y campos están documentados en [acciones](docs/actions.md).

## Documentación

- [Instalación](docs/installation.md)
- [Configuración y reglas](docs/configuration.md)
- [Acciones](docs/actions.md)
- [Solución de problemas](docs/troubleshooting.md)
- [Arquitectura](docs/architecture.md)
- [Requisitos y aceptación](docs/requirements.md)
- [Hoja de ruta](docs/roadmap.md)
- [Plan de prueba física en HAOS](docs/haos-test-plan.md)
- [Marketplace y compatibilidad](docs/marketplace.md)
- [Proceso de release](docs/release.md)
- [Auditoría comunitaria](docs/community-audit.md)

## Desarrollo y validación

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install -r requirements_test.txt
.venv\Scripts\ruff check .
.venv\Scripts\pytest --cov
```

Además de Ruff y pytest con cobertura de ramas, CI ejecuta hassfest y HACS
Action/Marketplace. Las pruebas automatizadas no sustituyen el plan físico de
HAOS, Zigbee, GLEDOPTO, Alexa o Matter. Consulta [CONTRIBUTING.md](CONTRIBUTING.md)
antes de proponer cambios.

## Seguridad, privacidad y licencias

El proyecto no requiere nube ni telemetría propia. Reporta vulnerabilidades de
forma privada según [SECURITY.md](SECURITY.md). El código se distribuye bajo
Apache License 2.0; los proyectos estudiados y las decisiones de atribución se
registran en [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
