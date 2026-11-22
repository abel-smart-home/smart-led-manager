# Acciones de Home Assistant

El dominio es `smart_led_manager`. Todas las acciones se registran una sola vez
y pasan por el mismo motor de prioridades; ninguna envía directamente una
orden fuera de las luces administradas. Admiten respuesta opcional cuando la
invocación de Home Assistant la solicita.

## Campos comunes

| Campo | Tipo | Significado |
|---|---|---|
| `request_id` | texto | Identificador estable. Si se reutiliza, actualiza la misma solicitud. |
| `name` | texto | Nombre legible; por defecto usa `request_id`. |
| `targets` | lista de `light` | Destinos obligatorios y previamente autorizados. |
| `priority` | entero `0..100` | Prioridad; normalmente `50`. |
| `rgb_color` | RGB | Color `[R, G, B]`, canales `0..255`. |
| `brightness` | entero `1..255` | Brillo opcional. |
| `transition` | segundos `>=0` | Transición si la entidad la soporta. |
| `duration` | segundos `>0` | Vencimiento en tiempo real. |
| `allow_turn_on` | booleano | Permite que la intención encienda una luz apagada. |
| `persistent` | booleano | Guarda la solicitud para recuperación tras reinicio. |

## `smart_led_manager.activate`

Crea o actualiza una solicitud genérica. `targets` es obligatorio; `priority`
por defecto es `50`. Si omites `request_id` se genera uno, por lo que conviene
proporcionarlo en automatizaciones que deban actualizar o cancelar la misma
intención. La respuesta contiene `request_id` y los destinos resueltos.

```yaml
action: smart_led_manager.activate
data:
  request_id: modo_cine
  name: Modo cine
  targets: [light.tira_sala]
  priority: 40
  rgb_color: [40, 5, 0]
  brightness: 80
  transition: 2
  persistent: true
```

## `smart_led_manager.deactivate`

Marca inactiva una solicitud pero conserva su definición. Requiere
`request_id`; la respuesta devuelve ese identificador. Para eliminarla por
completo usa `cancel`.

## `smart_led_manager.notify`

Crea o actualiza un aviso temporal. Requiere `targets` y `rgb_color`. Sus
valores por defecto son prioridad `70`, brillo `255`, duración `5` segundos,
animación `fixed` y periodo `1` segundo. `animation` admite `fixed`, `blink` o
`pulse`; `period` admite `0.5..60` segundos.

```yaml
action: smart_led_manager.notify
data:
  request_id: puerta_abierta
  targets: [light.tira_pasillo]
  rgb_color: [255, 128, 0]
  duration: 10
  animation: blink
  period: 1.5
```

Usa efectos intermitentes con prudencia por fotosensibilidad.

## `smart_led_manager.set_scene`

Crea o actualiza una intención de escena mediante el motor. Usa prioridad `50`
y transición `1` segundo por defecto, y la solicitud se marca persistente. No
captura ni restaura snapshots de Home Assistant: describe el estado deseado de
las luces indicadas.

## `smart_led_manager.cancel`

Elimina la solicitud indicada y cancela el trabajo/animación que le pertenezca
antes de aplicar la siguiente ganadora vigente. Requiere `request_id`.

## `smart_led_manager.clear_notifications`

Elimina solicitudes del módulo de notificaciones. `targets` es opcional: si se
indica, limita la limpieza a esos destinos; si se omite, limpia todas las
notificaciones. La respuesta incluye `cleared: true`.

## `smart_led_manager.set_manual_override`

Activa o desactiva una solicitud manual explícita para `targets`. Requiere
`enabled` y luces administradas; acepta `rgb_color`, `brightness` y prioridad
(`60` por defecto). Al desactivar, el motor muestra la solicitud vigente que
siga en la cola. La respuesta devuelve el estado y los destinos.

## Acciones de modos persistentes

`smart_led_manager.activate_mode` requiere `mode_id` y selecciona ese modo en
su zona. Si había otro modo seleccionado, ambos se reemplazan en una sola
transacción. Su respuesta contiene `mode_id` y `active: true`.

`smart_led_manager.deactivate_mode` requiere `mode_id`. Sólo libera la
solicitud cuando ese modo continúa seleccionado; desactivar un modo ya
reemplazado es idempotente y no afecta al modo nuevo.

`smart_led_manager.set_zone_mode` requiere `zone_id` y acepta `mode_id`. Si se
omite `mode_id`, equivale a **Sin modo**: elimina la intención de modo sin
ordenar apagar y deja que el motor recalcule la solicitud vigente.

```yaml
action: smart_led_manager.set_zone_mode
data:
  zone_id: sala
  mode_id: lectura
```

Los identificadores aparecen en diagnósticos y permanecen estables aunque se
cambie el nombre visible. Las solicitudes internas `smart_led_manager:mode:*` están
reservadas: no uses `activate`, `deactivate` ni `cancel` para modificarlas.

## Errores esperados

Si no hay una entrada cargada, la acción devuelve un error traducido. Si algún
destino no está administrado, la llamada completa se rechaza y enumera las
entidades no autorizadas; no se ejecuta parcialmente. Los límites del esquema
se validan antes de llegar al motor. Las acciones de modo también rechazan
zonas/modos inexistentes y un modo que no pertenezca a la zona indicada.
