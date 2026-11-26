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
│  ├─ Notificaciones → catálogo de avisos → crear / editar / duplicar / eliminar / simular / probar
│  ├─ Horarios → editor temporal
│  └─ Regla avanzada → condiciones simples + horario opcional
└─ Configuración
   ├─ General
   ├─ Prioridades
   ├─ Recuperación
   ├─ Diagnóstico
   └─ Configuración nativa
```

Guardar correctamente vuelve al listado pertinente y muestra confirmación. Atrás o Cancelar con cambios abre el diálogo con **Continuar editando**, **Descartar cambios y salir** y **Guardar y salir**. Sin cambios, la navegación es directa. Ante un error de validación o del servidor, el formulario conserva el borrador. La ruta del panel se mantiene. Las escenas y los efectos forman parte de Modos de iluminación.

C.2.3 abre **Iluminación inteligente** con las nueve entradas del árbol.
**Energía** ofrece potencia instantánea y energía acumulada por separado.
**Mis automatizaciones** usa el catálogo común. Desde C.2.4,
**Notificaciones** muestra los avisos guardados de ese catálogo, **Horarios**
abre el formulario sin fuente y **Regla avanzada** abre el editor de
condiciones. El editor compatible sigue disponible para árboles anidados y
configuraciones avanzadas. **Configuración** conserva el acceso a
**Configuración nativa**.
