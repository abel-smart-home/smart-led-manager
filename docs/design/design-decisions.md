# Decisiones y pendientes de alcance

## Validadas preliminarmente en el prototipo
Cinco menús; modos como función central, escenas/efectos dentro de modos; catálogo unificado; plantillas numéricas y de estado; selección buscable integrada; avisos, horarios, condiciones simples, configuración. Diálogo de borrador y navegación sin guardado obligatorio. Los comentarios del propietario validan el diseño en general, no cada valor predeterminado ni pruebas físicas.

## Propuestas que requieren confirmación o comprobación
- C.2 priorizar estabilidad y fidelidad, corregir `entry_not_loaded`. El roadmap actual reserva módulos gráficos para beta.1; adelantar plantillas a C.2 requiere aprobación explícita y actualizar roadmap. Proponer C.2a estabilidad/centro de administración, C.2b adaptación de plantillas compatibles y ampliaciones acordadas, sin cambiar la versión oficial todavía.
- Catálogo persistente de avisos por nombre y acción seleccionable: ampliación del backend, no confundir con `notify` existente. Resolver selección dinámica compatible con HA antes de comprometer UX exacta.
- Eliminar zonas: confirmar y bloquear si referencias activas o exigir reasignación explícita; preservar identificadores. Duplicar reglas: ID nuevo, deshabilitada por defecto (plan C-03).
- Destinos por área, etiqueta y grupo: controles avanzados y vista previa de exclusiones; conservar capacidades existentes. Histéresis, permanencia, condiciones anidadas y disparadores avanzados no representados por completo: no eliminar ni aplanar datos. Definir diseño complementario antes de exponerlos.
- Prioridades de ejemplo (modo 60, numérico 40, seguridad 80, presencia 50, avisos 70, horario/avanzada 45) no son migraciones ni sustituyen prioridades reales; revisar colisiones. General: motor existente default newest, intervalo 0.75 s, manual service_only. La política temporal actual usa 15 min.
- Bloque D queda separado: reintentos/verificación física configurables, pausa/reanudación temporal, aliases de voz. Escenas por luz y efectos avanzados requieren diseño futuro; sin sexto menú.

## No autorizado
No modificar main, publicar release, etiquetar, cerrar PR, borrar ramas ni enviar a Marketplace sin permiso expreso. No elevar resultados simulados a HAOS o Zigbee. No declarar C.1 ni C.2 aprobados por la maqueta.
