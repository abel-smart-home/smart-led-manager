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

Guardar correctamente vuelve al listado pertinente y muestra confirmación. Atrás o Cancelar con cambios abre el diálogo con **Continuar editando**, **Descartar cambios y salir** y **Guardar y salir**. Sin cambios, la navegación es directa. Ante un error de validación o del servidor, el formulario conserva el borrador. La ruta del panel se mantiene. Las escenas y los efectos forman parte de Modos de iluminación.

C.2.2 incorpora la eliminación de zonas con comprobación de dependencias. **Iluminación inteligente** abre el catálogo existente, incluida la duplicación de reglas compatibles. **Configuración** abre **Configuración nativa**. El árbol superior conserva el diseño previsto para las etapas siguientes. [Comparación visual C.2.2](c22-evidence/README.md).
