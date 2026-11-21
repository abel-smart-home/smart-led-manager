# Contribuir a Smart LED Manager

Gracias por ayudar. El proyecto prioriza comportamiento predecible: ninguna luz
no autorizada debe recibir órdenes y una solicitud oculta debe conservar su
estado actual para recuperarse cuando termine la superior.

## Antes de comenzar

1. Lee [AGENTS.md](AGENTS.md), [arquitectura](docs/architecture.md),
   [requisitos](docs/requirements.md) y [hoja de ruta](docs/roadmap.md).
2. Abre o enlaza un issue para cambios de alcance o comportamiento observable.
3. Parte del `main` remoto más reciente y trabaja en una rama; no desarrolles
   directamente sobre `main`.
4. Mantén separado el motor puro de la orquestación de Home Assistant.

No fusiones, etiquetes, publiques una release ni envíes el proyecto al catálogo
de Marketplace sin autorización expresa del propietario.

## Entorno local

Se requiere Python `3.14.2` o posterior para esta línea de Home Assistant.

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements_test.txt
```

En Linux/macOS sustituye `.venv\Scripts\python` por `.venv/bin/python`.

## Reglas de implementación

- Usa APIs asíncronas oficiales; no interceptes ni modifiques servicios
  globales de Home Assistant.
- Conserva la lista explícita de luces permitidas en todas las rutas.
- Mantén rate limit, deduplicación, cancelación de trabajo obsoleto y reintentos
  acotados en cada camino que produzca una orden.
- No conviertas `unknown` o `unavailable` en valores numéricos.
- Persiste UTC de pared; usa tiempo monotónico sólo para demoras del proceso.
- Agrega pruebas enfocadas al cambio. Prueba el motor exhaustivamente sin Home
  Assistant y el comportamiento visible a través de APIs públicas cuando sea
  práctico.
- Añade módulos sólo cuando posean comportamiento real.

## Puertas locales

```powershell
.venv\Scripts\ruff format --check .
.venv\Scripts\ruff check .
.venv\Scripts\pytest --cov
```

En Windows, la carga completa del paquete oficial de pruebas de Home Assistant
puede depender de componentes POSIX. Si una prueba no puede ejecutarse por la
plataforma, registra el motivo y deja que la matriz Linux de CI la ejecute; no
la marques como aprobada ni ocultes la falla.

El pull request también debe superar hassfest y HACS Action sin exclusiones.
Una prueba o simulación no cuenta como resultado físico de HAOS, Zigbee,
GLEDOPTO, Alexa o Matter Hub.

## Documentación, versiones y terceros

- Documenta primero en español y conserva los textos de interfaz en inglés y
  español.
- Actualiza `CHANGELOG.md` y la hoja de ruta ante cambios visibles o alcance
  aprobado diferido.
- Mantén sincronizados `0.1.0-alpha.1` en manifest/changelog/release y
  `0.1.0a1` en el paquete Python.
- Revisa [docs/community-audit.md](docs/community-audit.md) antes de reutilizar
  material y conserva todas las obligaciones en `THIRD_PARTY_NOTICES.md`.

## Pull request

Describe el problema, la solución, riesgos, pruebas ejecutadas y pruebas no
ejecutadas con su motivo. Incluye capturas sólo cuando la interfaz cambie. No
mezcles refactors no relacionados. La aprobación del PR no autoriza por sí sola
una release ni una prueba física no registrada.

