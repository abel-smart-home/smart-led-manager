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

### Bloques B, C y D — alcance aprobado pendiente

- Áreas, etiquetas, grupos compatibles y “todas las administradas”, con expansión acíclica y deduplicación.
- Edición y duplicación de reglas con identificadores estables, reconciliación
  de solicitudes activas y ausencia de intenciones obsoletas; condiciones
  compuestas, horarios y duración mínima.
- Histéresis numérica, unidades y políticas por debajo/encima/rango.
- Botones, `event`, `input_button` y device triggers con semántica real de evento.
- Política de reintento y verificación física configurables.
- Política temporal opcional de pausa/reanudación además del vencimiento en tiempo real.
- Editor visual de puntos numéricos con valor, unidad cuando esté disponible,
  selector de color, alta/baja, ordenamiento, validación y vista previa si el
  Options Flow nativo lo permite.
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
- Panel visual dedicado solo si los flujos y dashboards nativos dejan necesidades justificadas.
