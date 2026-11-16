# Sweeplab

Raíz: `/Users/omarkhalil/GitHub/Sweeplab`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Arquitectura existente

- `src/`: biblioteca Firedrake/PETSc de SDC, restricciones, convergencia,
  sensibilidades, resultados y herramientas de repositorio. Exports lazy:
  los módulos puros no inicializan Firedrake/MPI.
- `labs/`: backends científicos, runners, renderizado y dossiers. Reutilización
  entre labs declarada en `dependencies.cross_lab` de `lab.yaml`, formando un DAG.
  Código reutilizable no importa runners, archivos retirados ni outputs.
- `packages/quant_sweep`: paquete Tier 1 con artefactos y referencia independiente
  de pricing backward-Euler/PSOR. No es el motor SDC; sólo consume su sustrato
  Tier 0. Conserva el contrato de `.importlinter`.
- `src/sweeplab_repo/run_store.py`: creación/finalización canónica. Los documentos
  originales del run conservan autoridad; los CSV son reconstruibles.

Lee [la arquitectura observada](../docs/architecture/lab_architecture.md),
[el contrato de investigación](../docs/scalable_research.md) y los consumidores
afectados. La visión genérica Design/Runner/Aggregator sigue siendo un objetivo.

## Invariantes y límites

Conserva SDC-first: cualquier elección de otro integrador lleva evaluación
explícita de compatibilidad. Los estudios numéricos de publicación usan MPI según
`CLAUDE.md`; pruebas, diagnósticos y baselines seriales conservan su función.
Las derivadas espaciales FE usan operadores FE, nunca diferencias finitas sobre
arrays de DOFs ordenados. Las sensibilidades con conjunto activo o política
congelados mantienen sus hipótesis y límites.

Los dividendos pendientes se aplican mediante un cursor y `dividend_is_due`,
compartido por primal y sensibilidad. No descartes un evento pendiente por una
segunda prueba de ventana con tolerancia distinta.

`RunContext` es una fachada del almacén canónico con IDs explícitos. Los estudios
poseen sus outputs; las funciones Black–Scholes reciben `raw_dir` y no crean runs
persistentes. La salida del contexto coordina writers y fallos antes del sello.
Las reservas simultáneas añaden `__rN`, sin sobrescrituras ni timestamps ficticios.

`finalize_run` es root-only, no colectivo; la creación propaga sus errores MPI.
Revisa todos los consumidores antes de convertir una operación en colectiva.
Los hashes de configuración/artefactos no prueban convergencia, reproducibilidad
del código sucio ni escalabilidad multinodo.

## Entorno y comprobaciones

La instalación local de Firedrake se encuentra en
`/Users/omarkhalil/Documents/Universidad/ImperialCollege/Project/programming/venv-firedrake`.
Verifica existencia y versiones; no copies la ruta a otras máquinas. El proyecto
raíz es virtual: `pip install -e .` no está soportado. `quant_sweep` mantiene su
entorno uv y dependencia local en `../Shared/packages/quant_substrate`.

Desde la raíz, fija threads BLAS/OpenMP a uno, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`,
`OMPI_MCA_sharedfp=individual` y `MPLBACKEND=Agg`. Pytest se ejecuta como
coordinador serial; las regresiones MPI lanzan sus propios procesos.

```sh
python -m pytest tests/ -q --tb=short
python3 tools/repo/check_import_boundaries.py
python3 tools/repo/validate_layout.py
uv run --project packages/quant_sweep pytest packages/quant_sweep/tests -q
uv run --project packages/quant_sweep lint-imports
```

La CI separa serial y MPI. El paquete requiere su sustrato privado en una revisión
fijada. Rechazos, concurrencia y recuperación forman parte del contrato; vuelve
a comprobarlos cuando cambia su comportamiento.

Los hooks Git pueden compartir validadores con Claude. Verifica
`core.hooksPath` antes de afirmar que están activos y respeta su ejecución.
`CONSTELLATION_COMMIT_OWNER=native` deja trazado/publicación al coordinador.
Preserva índice y cambios ajenos; publica sólo las rutas declaradas.
