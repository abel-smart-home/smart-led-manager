# Base y respaldo de C.2.0

El 25 de noviembre de 2026 se verificó la base de C.1
`a0df3c48711f8b40fe48f8ded122d5a572906c83` contra GitHub. De ese commit parte
`feat/v0.1.0-alpha.3-c2`. El [informe de auditoría](auditoria-c2.md) conserva
la evidencia de la fase documental y el [roadmap](../roadmap.md) registra la
decisión posterior del propietario sobre el alcance.

## Referencias antes de abrir C.2

| Rama | SHA completo | Dependencia y propuesta |
| --- | --- | --- |
| `main` | `a04e925b9fea426464742644943fd79bb4ed9550` | Rama predeterminada y base de PR #1 y del PR consolidado. Conservar. |
| `feat/v0.1.0-alpha.1` | `163ff8f274d6894ab239ef74ef5ba6a8b545c77a` | Head de #1 y base de #2. Candidata tras resolver ambos. |
| `feat/v0.1.0-alpha.2-modes` | `a14d9afb465c698c0354d18892ecac3537d5f6b4` | Head de #2. Candidata tras resolverlo. |
| `feat/v0.1.0-alpha.3-zone-devices` | `fa9ecd650485e27ee1f1f22654972a1c47379c17` | Candidata, con revisión de enlaces en documentación. |
| `feat/v0.1.0-alpha.3-rules-editor` | `f8b9fc9ec8dc0a31378bb50595d605a2c88a48fe` | Candidata, con revisión de enlaces en documentación. |
| `feat/v0.1.0-alpha.3-visual-editor` | `6ad79e0c3c388f714f08c727ba17f315807310a4` | Candidata, con revisión de enlaces en documentación. |
| `feat/v0.1.0-alpha.3-advanced-rules` | `a0df3c48711f8b40fe48f8ded122d5a572906c83` | Base común; conviene conservarla al validar C.2. |

[PR #1](https://github.com/abel-smart-home/smart-led-manager/pull/1) y
[PR #2](https://github.com/abel-smart-home/smart-led-manager/pull/2) permanecen
abiertos en borrador. Se requiere autorización específica antes de cerrarlos
o eliminar ramas. El inventario local y remoto de etiquetas estaba vacío y
GitHub devolvió cero releases.

El commit exclusivamente documental
`87be81fd745c9a3c9230bde973466d04f54e869f` inició C.2 en GitHub. La rama
contiene íntegramente C.1 y los 46 commits de desarrollo que la separaban de
`main`. [PR consolidado #3, en borrador](https://github.com/abel-smart-home/smart-led-manager/pull/3).

## Hitos funcionales

| Hito | SHA completo |
| --- | --- |
| Alpha.1, recuperación Zigbee validada | `f283d36a4a11834fa812043697a0dead33de3110` |
| Alpha.2, candidato probado | `8e21b2883231adf5ce53fc32faa88434e21c18bd` |
| A, dispositivos por zona | `46ccf94907d43d283d52be9e6c91f941b3f28d3a` |
| B, administración de reglas y copia deshabilitada | `f104e399c640a1d0e173a293893feea5a7d90ca3` |
| B.1, editor numérico estabilizado | `1d8926bcf8307a480d585174cfb7eb8550fb816a` |
| B.1, centro de administración inicial | `ff49295bb5b6ba315eef65d7fd46e769b72d396e` |
| C, reglas avanzadas | `2b9c4dd453c71faf19b5a27d1346d9ef127f49d4` |
| C.1, candidato funcional | `85770cec7143c775dcc2a69853df2a9b0523b07c` |

Los SHA que el propietario instaló y los resultados de cada prueba figuran en
el [registro HAOS](../haos-test-plan.md).

## Respaldo verificado

Se guardó `smart-led-manager-pre-c2-a0df3c4.bundle` fuera del repositorio con
`git bundle create <ruta> --all HEAD`. Git confirmó historial completo y se
compararon las referencias de ramas locales y de seguimiento contra
`git bundle list-heads`. Los cambios de documentación que aún estaban en el
árbol se conservaron al cambiar a la rama C.2.

```text
SHA-256 61776a2caf433940a38d54318b9b96d7743a4eb7156b943d685394a039ad122c
```
