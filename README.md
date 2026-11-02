# Workspace de GitHub

`~/GitHub` contiene los repositorios de software de Omar y su contexto compartido. El repositorio principal del orquestador y la fuente canónica de Constellation están en `~/.codex`. Cada proyecto mantiene su historia, pruebas y contrato. [Registro](.codex/repositories.json) · [QuantOS](QUANTOS.md)

Desde el hub o desde un hijo, la instalación verificada identifica los propietarios y sus instrucciones. Desde otra carpeta, indica la raíz del workspace:

```sh
"${CODEX_HOME:-$HOME/.codex}/constellation/run" cli workspace \
  --root "$HOME/GitHub" route Shared/README.md PricingLab/README.md
```

El [contexto del hub](AGENTS.md) selecciona los contratos de los proyectos. El [flujo entre repositorios](.codex/WORKSPACE.md) coordina dependencias y publicación por dueño Git. La entrada histórica `.codex/ecosystem/cli.py` sigue invocando esa misma instalación; no contiene un motor propio.

Este workspace conserva las herramientas de Claude, el registro y los adaptadores en la rama `codex/workspace` del repositorio privado de Constellation. La rama `main` corresponde a la fuente en `~/.codex`. Las ramas tienen responsabilidades distintas y no se fusionan automáticamente entre sí.

Para modificar Constellation, usa su fuente en `~/.codex` y la [guía de desarrollo e instalación](https://github.com/omar15899/constellation/blob/main/.codex/README.md). Las [entradas locales](.codex/README.md) explican cómo operar este workspace.
