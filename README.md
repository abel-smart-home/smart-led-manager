# Smart LED Manager

Smart LED Manager es una integración personalizada y completamente local para
Home Assistant. Coordina solicitudes de color, brillo, escenas y avisos sobre
entidades `light` existentes, y decide cuál debe verse en cada luz mediante un
motor de prioridades determinista.

> **Estado:** `0.1.0-alpha.3` en desarrollo. Es un candidato experimental para
> validación física, no una release publicada. Conserva la base alpha.1 probada
> con HAOS/ZHA/GLEDOPTO. La validación consolidada de alpha.2 registra 16 casos
> M completos, 3 parciales y M-06 pendiente con dos controladores Zigbee reales,
> combinando evidencia física y de laboratorio HAOS con luces Demo. No equivale
> a 16 pruebas completas sobre Zigbee ni autoriza la publicación. El propietario
> aprobó 8/8 pruebas del Bloque A y reportó 10/10 del Bloque B en HAOS
> VirtualBox. El Bloque B se ejecutó el 23 de noviembre de 2026 sobre
> `f8b9fc9ec8dc0a31378bb50595d605a2c88a48fe`. La validación manual del nuevo
> editor avanzado B.1 y la repetición física en Raspberry Pi/ZHA/GLEDOPTO
> siguen pendientes.

## Qué hace esta alfa

- Controla únicamente las luces que el usuario autoriza en el flujo gráfico.
- Resuelve cada luz por separado con prioridades `0..100` y desempate
  configurable (`newest`, `oldest` o `lexical`).
- Conserva y actualiza solicitudes de prioridad inferior mientras están
  ocultas, para mostrar la vigente al terminar la solicitud superior.
- Admite reglas de estado y reglas numéricas de color con N puntos,
  interpolación o rangos.
- Administra reglas desde el Options Flow: editar sin cambiar su identificador,
  duplicar como copia inicialmente deshabilitada, activar/desactivar y eliminar.
  Los puntos numéricos se agregan, editan, ordenan y colorean con controles
  nativos, sin escribir cadenas RGB.
- Incluye un centro de administración local y exclusivo para administradores,
  con acceso opcional desde la barra lateral y ruta estable. Permite editar
  puntos con selector de color, ver su
  distribución numérica real y simular exactamente interpolación o rangos sin
  enviar órdenes físicas. El editor nativo del Options Flow continúa
  disponible como alternativa.
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
La clasificación en **Integraciones** y el Options Flow en `es-419` fueron
confirmados por el propietario con `8e21b28`; no se realizó una prueba física
independiente del perfil `es`.

## Compatibilidad objetivo

| Componente | Versión de esta alfa |
|---|---|
| Home Assistant | `2026.11.0` o posterior |
| Versión del manifest/release | `0.1.0-alpha.3` |
| Versión de paquete Python | `0.1.0a3` |
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
Modos de iluminación** o **Configurar > Reglas inteligentes** para crear el
catálogo; no hace falta YAML ni introducir puntos RGB como texto.

Para editar gráficamente una regla numérica existente, abre **Smart LED
Manager** en la barra lateral con una cuenta administradora, visita
`/smart-led-manager-editor` o usa el enlace de **Configurar > Centro de
administración**. La misma pantalla permite mostrar u ocultar el acceso lateral
sin deshabilitar la ruta. **Configurar > Reglas inteligentes > Abrir editor
gráfico avanzado** conserva otro enlace al centro; Home Assistant no ofrece una
API pública para redirigir automáticamente desde el Options Flow. El panel, sus
módulos JavaScript y el backend WebSocket se sirven localmente: no usa CDN,
nube ni un paso de compilación para el usuario.

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
node --test tests/frontend/*.test.mjs
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
