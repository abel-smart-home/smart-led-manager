# Hoja de ruta

La hoja de ruta mantiene todo el alcance aprobado para `0.1.0`; distribuirlo en incrementos no lo elimina. Una casilla solo se marca cuando existe implementación y evidencia de prueba.

## `0.1.0-alpha.1` — base utilizable

- [x] Motor puro: prioridades, desempates, actualización enmascarada, vencimiento y cancelación por destino.
- [x] Adaptador RGB según capacidades, deduplicación y rate limit por entidad.
- [x] Config flow para luces autorizadas y options flow para reglas de estado/numéricas.
- [x] Acciones de activación, cancelación, notificación, escena y control manual explícito.
- [x] Persistencia versionada de solicitudes persistentes y recuperación.
- [x] Animaciones iniciales fija, parpadeo y pulsación con cancelación.
- [x] Diagnóstico, sensor de motor e historial acotado.
- [x] Recuperación acotada tras indisponibilidad o fallo de envío con estado
  ZHA obsoleto, con espera progresiva, invalidación de caché y cancelación de
  intención obsoleta.
- [x] Traducciones inglés/español, documentación, CI y validadores Marketplace.
- [x] Pruebas automatizadas del criterio de aceptación de alpha.1.
- [ ] Ejecución física documentada por el propietario en HAOS con GLEDOPTO/ZHA.

## `0.1.0-alpha.2` — zonas y modos persistentes

- [x] Zonas no superpuestas sobre la lista explícita de luces administradas.
- [x] Catálogo gráfico de modos con prioridad, estilo y animación inicial.
- [x] Selección exclusiva y reemplazo atómico por zona, sin estado intermedio.
- [x] Persistencia y reconciliación de selección contra definiciones vigentes.
- [x] Un `select` por zona e interruptores opcionales por modo.
- [x] Acciones de activar, desactivar y establecer modo de zona.
- [x] Compatibilidad de carga con entradas y Store de alpha.1 sin migración de
  esquema.
- [x] Pruebas automatizadas de los casos M-01 a M-20 aplicables al software.
- [ ] Validación consolidada **parcial en hardware físico**: 16 casos M están
  completos sumando la evidencia Raspberry/Zigbee y el laboratorio HAOS, M-10,
  M-15 y M-17 permanecen parciales, y M-06 sigue pendiente con dos
  controladores Zigbee reales aunque aprobó la simulación con dos luces Demo.
  `docs/haos-test-plan.md` separa explícitamente cada origen de evidencia.

## `0.1.0-alpha.3` — destinos y disparadores completos

### Bloque A — dispositivos por zona

- [x] Un dispositivo virtual por zona bajo una sola integración, entrada y
  motor, con asociación opcional a un área y migración que conserva
  `unique_id`, `entity_id` y nombres personalizados.
- [x] Ciclo de vida selectivo del Entity Registry: elimina definiciones
  permanentes de la entrada correcta, conserva switches sólo ocultos y no
  ejecuta limpieza durante la descarga.
- [x] Nombres naturales mediante nombre de dispositivo y `has_entity_name`, sin
  aliases ni dependencias de servicios de voz.
- [x] Validación del propietario 8/8 en HAOS VirtualBox (A-01 a A-08) con
  `fa9ecd650485e27ee1f1f22654972a1c47379c17`, reportada el 23 de noviembre de
  2026. La repetición física Raspberry Pi/ZHA/GLEDOPTO y los nombres mediante
  Alexa/Matter siguen pendientes.

### Bloque B — administración de reglas

- [x] Alta, edición con `id` estable, duplicación con `id` nuevo y copia
  deshabilitada, activación/desactivación y eliminación de reglas.
- [x] Editor numérico multipaso con valor, unidad disponible, selector RGB,
  alta/baja, ordenamiento y validación mediante controles nativos.
- [x] Reconciliación por recarga: tareas/listeners antiguos cancelados y
  esperados, destinos reemplazados y reglas deshabilitadas/eliminadas sin
  intención tardía.
- [x] Compatibilidad de reglas alpha.1/alpha.2 sin migración de esquema y
  rechazo completo de cualquier catálogo con destinos no autorizados.
- [x] Validación manual del Bloque B reportada por el propietario: B-01 a B-10,
  10/10 en HAOS VirtualBox con `f8b9fc9`, el 23 de noviembre de 2026. No se
  atribuyen logs ni métricas no entregados.
- [ ] Repetición separada del Bloque B con Raspberry Pi/ZHA/GLEDOPTO.

### Bloque B.1 — editor gráfico especializado

- [x] Panel local de administrador mediante mecanismos oficiales de Home
  Assistant 2026.11, WebSocket autenticado y recursos incluidos sin compilación
  para el usuario.
- [x] Borrador visual de puntos, posiciones numéricas no uniformes, modos por
  interpolación/rangos y simulación exacta delegada a `core/color.py`.
- [x] Guardado mínimo con validación Python, destinos autorizados, conservación
  de `id`/campos y rechazo explícito de concurrencia obsoleta.
- [x] Editor nativo del Bloque B conservado como alternativa.
- [x] Centro de administración inicial, enlace desde Options Flow y visibilidad
  lateral persistente sin duplicar ruta ni backend.
- [x] Estabilidad del formulario ante actualizaciones globales, simulaciones
  concurrentes, valor vacío y ConfigEntry descargada.
- [x] B1-01 a B1-10 reportadas por el propietario como aprobadas, 10/10, en
  HAOS VirtualBox sobre `6ad79e0c3c388f714f08c727ba17f315807310a4`.
  Se conserva el incidente inicial `MappingProxyType`, la corrección manual en
  `9ba3b0c` y el endurecimiento posterior. A/B/B.1 suman 28/28 reportadas.
- [ ] Repetición física B1-05, B1-06, B1-07 y B1-10 en
  Raspberry Pi/ZHA/GLEDOPTO.

El Bloque B.1 cerró la superficie especializada. No absorbe el dashboard
operativo; el Bloque C amplía el mismo panel sin crear otro.

### Bloque C — reglas avanzadas

- [x] Áreas, etiquetas, grupos transparentes, zonas y “todas las
  administradas”, con expansión segura, acíclica y deduplicada.
- [x] Condiciones AND/OR/NOT, horarios locales, días y permanencia mínima.
- [x] Histéresis numérica y activación por encima/debajo/dentro/fuera,
  separadas del color fijo, interpolado o por rangos.
- [x] Triggers oficiales de Home Assistant para estado, bus, `event`,
  `input_button` y device triggers compatibles, con solicitud temporal única.
- [x] Panel unificado de reglas y backend compartido con Options Flow.
- [ ] C-01 a C-20 en HAOS VirtualBox y pruebas Zigbee señaladas por separado.

### Bloque C.1 — correcciones del panel y destinos

- [x] Mantener la ruta y el contexto de edición durante el guardado.
- [x] Selectores de origen, destinos, tiempo y disparadores, y constructor
  de condiciones. Usar el contrato común de reglas en los dos editores.
- [x] Volver a comprobar luces autorizadas, membresía de grupos y plazo de
  eventos antes de despachar. Reconstruir suscripciones al cambiar un grupo.
- [ ] Ejecutar el [recorrido de laboratorio](haos-block-c-walkthrough.md)
  con C.1 y repetir las variantes Zigbee indicadas en el plan.

### Bloque D — alcance aprobado pendiente

- Política de reintento y verificación física configurables.
- Política temporal opcional de pausa/reanudación además del vencimiento en
  tiempo real.
- Nombres y aliases naturales para voz, breves y opcionalmente cualificados por
  zona, sin cambiar los `unique_id` existentes; el Bloque A cubre los nombres
  nativos y deja pendiente la gestión explícita de aliases.

## `0.1.0-beta.1` — módulos funcionales

- Módulos gráficos para temperatura, humedad, energía, seguridad, presencia, escenas/ambientes y horarios reutilizando reglas genéricas.
- Alternancia multicolor, respiración, transiciones graduales y secuencias personalizadas accesibles.
- Entidades virtuales necesarias para control manual, dashboard y exposición opcional a Matter Hub/Alexa.
- Detección conservadora de cambios directos mediante `Context`, tolerancias y ventana anti-eco; políticas temporal/permanente/retorno automático.
- Iluminación adaptativa local sin dependencia obligatoria de otra integración.
- Rate limit global y estrategia explícita para grupos Zigbee/multicast.

## `0.1.0-rc.1` — estabilización

- Migraciones reales desde todas las pre-releases.
- Pruebas de carga, carreras, reinicio, descarga, actualización y datos corruptos.
- Matriz de versiones de Home Assistant compatible y mínimo revisado según API/pruebas.
- Plan HAOS ejecutado en varias tiras, habitaciones y desconexiones Zigbee.
- Revisión de accesibilidad, traducciones, seguridad, privacidad y documentación.
- Hassfest, HACS/Marketplace Action, Ruff, pytest y cobertura en verde.

## `0.1.0` — versión regular

Se publica únicamente tras cerrar los requisitos aprobados de la versión regular, registrar la prueba física y recibir autorización expresa para fusionar, etiquetar y crear la release.

## Después de `0.1.0`

- Controladores WLED y ESPHome Addressable Light.
- WS2812B, WS2815, SK6812 y otras tiras direccionables.
- Segmentos, píxeles individuales y señales simultáneas por segmento.
- Dashboard operativo general sólo si las superficies nativas dejan necesidades
  adicionales justificadas; el editor especializado B.1 no adelanta ese alcance.
