# Navegación
Una ConfigEntry y un centro de administración. Acceso por Options Flow y barra lateral opcional; conservar identificadores y ruta existente. No duplicar motores ni catálogos.

```text
Smart LED Manager
├─ Luces administradas → selección múltiple autorizada
├─ Zonas → listado → crear / editar
├─ Modos de iluminación → agrupados por zona → crear / editar / activar / desactivar
├─ Iluminación inteligente
│  ├─ Mis automatizaciones → listado unificado → editar / habilitar / deshabilitar / eliminar
│  ├─ Temperatura → editor numérico
│  ├─ Humedad → editor numérico
│  ├─ Energía → potencia / consumo → editor numérico
│  ├─ Seguridad → editor de estados
│  ├─ Presencia → editor de estados
│  ├─ Notificaciones → editor de avisos temporales
│  ├─ Horarios → editor temporal
│  └─ Regla avanzada → condiciones simples + horario opcional
└─ Configuración
   ├─ General
   ├─ Prioridades
   ├─ Recuperación
   ├─ Diagnóstico
   └─ Configuración nativa
```

Guardar correcto vuelve al listado pertinente y muestra confirmación. Atrás/Cancelar con cambios abre diálogo: Continuar editando / Descartar cambios y salir / Guardar y salir. Sin cambios, navegación directa. Error de validación o backend permanece en formulario con borrador intacto. No redirigir a `/home/overview`. En modos, escenas y efectos integrados, sin sexto menú. Eliminación de zona y duplicación de regla están pendientes de completar; véase decisiones.
