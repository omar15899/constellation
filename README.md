# Constellation en la raíz de Codex

`~/.codex` es el repositorio principal del orquestador Constellation, conectado a
[omar15899/constellation](https://github.com/omar15899/constellation) en `main`.
La fuente mantiene su estructura interna en `.codex/ecosystem/`,
`.codex/skills/` y `.codex/tests/`. Esto conserva los contratos de construcción,
identidad del CLI y distribución, separados de la instalación activa del equipo.

| Ruta bajo `~/.codex` | Función |
| --- | --- |
| `.codex/` | Fuente mantenible, skills, pruebas y controles Git. |
| `constellation/` | Lanzador, catálogo y recibo de la instalación verificada. |
| `skills/`, `agents/`, `plugins/` | Recursos instalados por sus proveedores. |
| `config.toml` y demás estado de la aplicación | Configuración efectiva y datos privados locales. |

Git publica únicamente la fuente y las instrucciones permitidas por
[.gitignore](.gitignore). Credenciales, conversaciones, perfiles privados,
memorias, registros y bases de datos permanecen fuera del repositorio.
[AGENTS.md](AGENTS.md) conserva las instrucciones globales del usuario;
[.codex/AGENTS.md](.codex/AGENTS.md) contiene las reglas propias de esta fuente.

`~/GitHub` conserva el workspace de software, sus registros, sus herramientas de
Claude y los repositorios hijos. Su raíz usa la rama `codex/workspace` del mismo
remoto; cada hijo mantiene su propio dueño Git. OmarOS conserva su repositorio y
su adaptador. Ambos consumen la instalación compartida del equipo.

```sh
constellation() { "${CODEX_HOME:-$HOME/.codex}/constellation/run" cli "$@"; }
constellation workspace --root "$HOME/GitHub" route Shared/README.md PricingLab/README.md
constellation git --root "$HOME/.codex" --session ID status
```

La [guía de operación y desarrollo](.codex/README.md), el
[contrato entre propietarios](.codex/WORKSPACE.md) y los
[criterios de revisión](REVIEW.md) describen cómo comprobar y publicar cambios.
