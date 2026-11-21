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
| RGB solicitado a luz sin modo de color | Se diagnostica como no representable; no se envían atributos inválidos ni bucles |
| Cambio emitido por Smart LED Manager | No crea control manual externo |
| `unknown` en regla numérica | No se convierte a cero ni activa un umbral |

## Fuera de certificación

Las luces administradas no sustituyen sistemas certificados de incendio, humo, intrusión, emergencia o accesibilidad. Los efectos rápidos deben permanecer desactivados por defecto y la documentación debe advertir sobre fotosensibilidad.

