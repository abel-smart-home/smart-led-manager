# Aceptación C.2 (propuesta)

## Visual y funcional
1. V-01: reproducir inicio de cinco tarjetas, orden, iconos, jerarquía, responsive. Sin menú independiente de escenas.
2. V-02: capturar cada vista a 1280×900 claro y repetir vistas críticas a 390×844 oscuro, con datos equivalentes y tema declarado. Comparar lado a lado contra referencia, sin diferencias injustificadas de estructura, controles, textos o espaciado. Documentar desviaciones necesarias por HA. No imponer pixel-diff bruto al shell nativo; no aprobar con captura de otra vista.
3. V-03: selectores integrados, búsqueda vacía, teclado, foco, filtros, resultados, retirar último destino, móvil sin desbordamiento horizontal. No perder borrador durante actualización de estado.
4. F-01: botones de crear/guardar/editar/eliminar/duplicar (donde corresponda), habilitar/deshabilitar, activar/desactivar, cancelar/volver y los tres caminos del diálogo. Verificar persistencia y resultado backend; fallo conserva datos, no falso éxito.
5. F-02: probar conflicto de revisión, recarga de entrada, permisos administrador/no administrador, error de backend y doble envío. No redirección ni error `entry_not_loaded` sin tratamiento.
6. F-03: editor numérico, unidades, valores inválidos, puntos únicos, extremos, simulación; reglas de estado y horarios nocturnos, desconocido/no disponible; avisos expiran sin recuperar intención vencida. Probar solo las ampliaciones autorizadas, documentar las no implementadas.
7. F-04: migrar reglas y configuraciones sin pérdida, IDs estables, destinos autorizados, conservación de capacidades avanzadas. Reinicio/descarga sin listeners, timers o animaciones residuales. Prioridades y rate limit preservados.

## Recorrido práctico del propietario (HAOS)
| ID | Prueba | Resultado esperado |
|---|---|---|
| U-01 | Crear/editar/guardar y descartar una configuración | Sin errores ni redirecciones; lista correcta |
| U-02 | Crear Cine y Lectura, activar por zona y por Alexa si expuesto | Exclusividad, switch y modo efectivo correctos |
| U-03 | Simular y variar sensor de temperatura | Color esperado, límites seguros |
| U-04 | Disparar aviso desde automatización HA | Aviso temporal, sin comandos fuera de autorización |
| U-05 | Superponer aviso/regla/modo, cambiar modo durante aviso | Recuperar intención vigente, no instantánea vieja |
| U-06 | Reiniciar HAOS | Configuración e IDs conservados, sin reactivar avisos expirados |

## Puertas técnicas
Codex ejecuta Ruff, pytest con branch coverage, frontend, Hassfest y HACS/Marketplace según AGENTS.md; conservar casos A/B/B.1, M y C-01–C-20 con sus estados originales. Repetir C-03/C-07/C-08/C-09/C-19 específicamente; U no sustituye C ni pruebas físicas. Separar resultados automatizados, VirtualBox y Raspberry Pi/ZHA/GLEDOPTO/Matter Hub/Alexa. M-06 sigue pendiente con dos controladores físicos. Informar fallos y no declarar aprobación hasta evidencia real. Capturas del prototipo no equivalen a pruebas HAOS.
