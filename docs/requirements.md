# Requisitos funcionales y criterios de aceptación

## Alcance del producto `0.1.0`

La versión regular debe satisfacer el alcance aprobado: múltiples tiras/habitaciones/áreas/etiquetas/grupos, reglas sobre entidades y eventos, prioridades `0..100`, sensores numéricos genéricos, seguridad, notificaciones, escenas, horarios, iluminación adaptativa, animaciones, control manual y acciones accesibles desde la interfaz. Las funciones direccionables por píxel/segmento están deliberadamente fuera de `0.1.0`, pero la arquitectura debe admitirlas después.

## Criterios verificables de `0.1.0-alpha.1`

La pre-release solo puede considerarse lista cuando:

1. Se instala como integración personalizada y crea una única entrada por flujo gráfico.
2. El usuario autoriza al menos una entidad `light`; ningún destino no autorizado recibe órdenes.
3. Las acciones `activate`, `deactivate`, `notify`, `set_scene`, `cancel`, `clear_notifications` y `set_manual_override` tienen esquemas y traducciones y pasan por el motor.
4. El motor conserva solicitudes enmascaradas, resuelve cada destino, aplica prioridades `0..100`, tres desempates deterministas y recupera la siguiente solicitud vigente.
5. La expiración usa UTC y tiempo real; cancelar una ganadora cancela también su animación.
6. Una regla de estado y una regla numérica con N puntos pueden crearse/eliminarse por options flow y reaccionan a cambios sin sondeo.
7. Los valores numéricos inválidos (`unknown`, `unavailable`, NaN, infinito) no generan colores.
8. El controlador detecta capacidades, deduplica órdenes, impone un intervalo mínimo por luz y no reintenta sin límite una luz desconectada.
9. Las solicitudes persistentes sobreviven un reinicio simulado, las vencidas no, y la descarga cancela todos los recursos.
10. Hay diagnóstico sin datos sensibles e historial con límite.
11. Pruebas unitarias y de integración cubren las rutas anteriores; Ruff y cobertura configurada pasan.
12. Hassfest y HACS/Marketplace Action pasan en GitHub antes de publicar una pre-release.
13. La documentación distingue de forma explícita pruebas automatizadas de pruebas físicas HAOS/Zigbee/Alexa.

## Criterios verificables de `0.1.0-alpha.2`

1. Una zona contiene al menos una luz autorizada y ninguna luz física puede
   pertenecer a dos zonas.
2. Un modo tiene identificador inmutable, pertenece a una zona y sólo usa un
   subconjunto no vacío de sus luces.
3. Sólo hay una selección de modo por zona; cambiarla reemplaza la solicitud
   anterior bajo un único bloqueo y nunca expone un ganador intermedio.
4. Reactivar el mismo modo conserva antigüedad, tarea de animación, comando
   físico y Store sin escrituras redundantes.
5. **Sin modo** elimina únicamente la solicitud interna y permite que el motor
   muestre la intención vigente de otro módulo.
6. Las definiciones viven en opciones y la selección en el Store existente. Al
   iniciar se eliminan huérfanos/duplicados y el comando se reconstruye desde
   la definición actual.
7. Un selector estable se crea por zona y sólo los modos autorizados por el
   propietario crean un interruptor estable.
8. `activate_mode`, `deactivate_mode` y `set_zone_mode` pasan por el coordinador
   y no permiten apropiarse de solicitudes internas mediante acciones
   genéricas.
9. Las notificaciones y reglas de prioridad superior enmascaran el modo; al
   terminar recuperan sólo el modo vigente, nunca uno reemplazado o borrado.
10. Alpha.1 se carga con listas vacías sin migración destructiva; descarga,
    recarga y reinicio no dejan listeners, animaciones ni órdenes tardías.
11. Ruff, pytest con cobertura de ramas, Hassfest y HACS/Marketplace deben
    aprobar antes de considerar el commit candidato para prueba física.
12. La exposición opcional de interruptores no equivale a validación de Alexa o
    Matter Hub; esa evidencia sólo puede registrarla el propietario en HAOS.

## Criterios verificables de `0.1.0-alpha.3`, Bloque A

1. La integración conserva una ConfigEntry, un coordinador, un motor y la lista
   explícita de luces autorizadas.
2. El dispositivo central conserva el sensor del motor y cada zona obtiene un
   dispositivo virtual estable basado en `entry_id` y `zone_id`.
3. El selector y los switches opcionales de cada modo pertenecen al dispositivo
   de su zona; renombrar una zona no recrea el dispositivo.
4. Una zona puede asociarse a un área existente mediante APIs oficiales sin
   cambiar áreas ni registros de las luces físicas.
5. La migración desde alpha.2 conserva `unique_id`, `entity_id`, nombres
   personalizados, automatizaciones, opciones, selección y Store.
6. Desactivar la exposición conserva el registro del switch. Eliminar una
   definición limpia sólo el registro exacto de esa entrada y nunca entidades
   ajenas o todavía referenciadas al dispositivo.
7. Una descarga temporal no limpia registros y un catálogo inválido desactiva
   la limpieza destructiva.
8. Los nombres predeterminados usan el contrato oficial `has_entity_name`; no
   se crean aliases ni dependencias de Alexa o Matter.
9. Las regresiones de prioridades, sincronización, persistencia e idempotencia
   de alpha.1 y alpha.2 siguen aprobando.
10. Ruff, pytest con cobertura, Hassfest y HACS/Marketplace deben aprobar antes
    de proponer el candidato para prueba física.

## Criterios verificables de `0.1.0-alpha.3`, Bloque B

1. El Options Flow permite agregar, editar, duplicar, activar/desactivar y
   eliminar reglas de estado y numéricas sin YAML.
2. Editar conserva el `id`; duplicar crea otro `id`, conserva la original,
   propone un nombre diferenciable y deja la copia deshabilitada.
3. Una regla heredada sin `enabled` continúa habilitada y editable sin
   recrearse ni cambiar su formato de puntos.
4. Nombre, origen, operador, estado, destinos autorizados, prioridad, color,
   brillo, transición y estado habilitado son editables donde corresponda.
5. El editor numérico nativo muestra puntos y unidad disponible, y permite
   alta, edición y eliminación con valor numérico y selector RGB.
6. Los puntos se ordenan; se rechazan duplicados, números no finitos, canales
   inválidos y el guardado con menos de dos puntos.
7. Los cambios intermedios no envían órdenes. Guardar recarga la ConfigEntry y
   reevalúa la definición vigente; las solicitudes temporales no persistentes
   pueden terminar durante esa recarga.
8. Editar una regla activa reemplaza su intención incluso enmascarada. Cambiar
   destinos libera los anteriores; desactivar o eliminar impide recuperaciones
   tardías de esa regla.
9. La descarga cancela y espera listeners, demoras y evaluaciones antiguas. No
   quedan excepciones de tareas sin recuperar ni catálogos superpuestos.
10. Cualquier regla que incluya un destino no autorizado se rechaza completa;
    nunca se amplía implícitamente a otras luces.
11. Prioridades, desempates, modos, dispositivos del Bloque A, persistencia y
    `unique_id` existentes conservan su comportamiento.
12. Ruff, pytest con cobertura de ramas, matriz Linux para Home Assistant
    `2026.11.0`/`2026.11.2`, Hassfest, HACS/Marketplace, traducciones y JSON
    deben aprobar antes de la validación manual.

## Criterios verificables de `0.1.0-alpha.3`, Bloque B.1

1. El panel usa APIs oficiales de panel personalizado, HTTP estático y
   WebSocket de Home Assistant 2026.11; opera localmente y no exige YAML, CDN,
   nube, Node.js ni compilación al usuario.
2. Panel, lectura, simulación y escritura exigen una sesión administradora. Un
   cliente no autorizado no puede modificar opciones aunque conozca el comando.
3. Se listan sólo reglas numéricas de la ConfigEntry existente y se muestran
   nombre, origen, estado, unidad e información relevante sin recrearlas.
4. El borrador permite alta, edición, eliminación y ordenamiento de puntos con
   valor y selector de color. Barra y gráfica respetan la escala numérica real.
5. El diseño mantiene campos numéricos accesibles, soporte de teclado/táctil,
   datos RGB/hexadecimales y temas claro/oscuro; el color no es la única señal.
6. La simulación reutiliza `core/color.py`, cubre interpolación, rangos y clamp
   y nunca llama servicios de luces ni modifica solicitudes.
7. Antes de guardar, Python valida entrada, regla, `id`, formato, modo, mínimo
   de puntos, finitud, unicidad, RGB y que cada destino siga autorizado.
8. Guardar conserva `id` y todos los campos no editados, usa
   `async_update_entry` y la recarga normal; el formato persistente de puntos y
   los esquemas no cambian.
9. Una revisión de las opciones completas impide que una sesión antigua
   sobrescriba cambios del Options Flow u otra pestaña y devuelve un conflicto
   comprensible.
10. Restaurar, descartar o regresar no cambia ConfigEntry, Store, motor ni
    luces. La navegación interna y la recarga del navegador advierten sobre
    borradores sin guardar cuando el mecanismo disponible lo permite.
11. El editor nativo B continúa funcional. Descargar elimina el panel visible
    y no deja tareas; los recursos de integración registrados una vez no
    conservan estado de reglas.
12. Pruebas Python y frontend cubren lectura, puntos, simulación, guardado,
    preservación, seguridad, concurrencia, reglas heredadas y ciclo de vida; la
    validación visual real se registra sólo cuando el propietario ejecuta
    B1-01 a B1-10 en HAOS.
13. El Options Flow ofrece un enlace interno al centro de administración y una
    opción persistente, activada por defecto, para mostrar u ocultar el acceso
    lateral sin retirar la ruta ni crear un segundo panel o backend.
14. La pantalla inicial identifica producto y versión y sólo enlaza superficies
    reales: reglas numéricas y configuración nativa. Los nombres amigables son
    primarios y los identificadores técnicos quedan bajo detalle avanzado.
15. Actualizaciones ordinarias de `hass` no reconstruyen el formulario; valores
    de simulación vacíos no equivalen a cero, respuestas antiguas no reemplazan
    resultados recientes y un error de carga no se presenta como catálogo vacío.

## Requisitos no funcionales

- Operación completamente local y asíncrona.
- Sin YAML obligatorio ni servidor externo.
- Sin monkey patches ni modificación de servicios globales.
- Complejidad aproximada de resolución `O(solicitudes × destinos)` en el pequeño conjunto local, sin polling constante.
- Historial, reintentos, tareas y colas siempre acotados.
- Errores visibles en log/diagnóstico sin secretos, spam ni supresión engañosa.
- Migraciones explícitas para cambios de config entry y Store.
- Inglés como fallback técnico y español completo desde la primera entrega.

## Matriz de comportamiento prioritaria

| Caso | Resultado esperado |
|---|---|
| Temperatura P40, interruptor P60, notificación P70, alarma P100 | Rojo de alarma; después notificación si sigue vigente; después interruptor; después temperatura actual |
| Se actualiza temperatura mientras manda la alarma | No se ordena la luz, pero el color de P40 queda actualizado y será el que aparezca después |
| Dos reglas P40 en una tira y una sola en otra | Cada tira resuelve su propio conjunto; el empate configurado solo afecta a la primera |
| Misma solicitud llega por destinos superpuestos | Se emite como máximo un comando por entidad física |
| Ganadora temporal vence mientras la luz está offline | No se reproduce al reconectar; se aplica el ganador que esté vigente entonces |
| ZHA marca disponible antes de que el dispositivo responda | Se conserva la ganadora vigente; los envíos usan un límite y espera progresiva, sin excepciones de tareas huérfanas |
| Un envío falla mientras ZHA conserva `on` u `off` en caché | Se invalida la deduplicación, se recupera en segundo plano sin esperar un evento de disponibilidad y sólo se reenvía la ganadora vigente |
| RGB solicitado a luz sin modo de color | Se diagnostica como no representable; no se envían atributos inválidos ni bucles |
| Cambio emitido por Smart LED Manager | No crea control manual externo |
| `unknown` en regla numérica | No se convierte a cero ni activa un umbral |

## Fuera de certificación

Las luces administradas no sustituyen sistemas certificados de incendio, humo, intrusión, emergencia o accesibilidad. Los efectos rápidos deben permanecer desactivados por defecto y la documentación debe advertir sobre fotosensibilidad.
