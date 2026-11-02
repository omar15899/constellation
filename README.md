# Constellation

Este checkout mantiene la fuente de Constellation y el catálogo de repositorios de `~/GitHub`. Cada proyecto conserva su historia, pruebas y contrato. El registro y el mapa de QuantOS describen el ámbito de trabajo. [Registro](.codex/repositories.json) · [QuantOS](QUANTOS.md)

Instala una versión verificada en cada equipo siguiendo la [guía de instalación](.codex/ecosystem/docs/migrations.md). Desde el hub o desde un hijo, este comando identifica los propietarios y sus instrucciones. Usa Python 3.11 o posterior.

```sh
"${CODEX_HOME:-$HOME/.codex}/constellation/run" cli workspace route Shared/README.md PricingLab/README.md
```

El [contexto del hub](AGENTS.md) selecciona los contratos de los proyectos. El [flujo entre repositorios](.codex/WORKSPACE.md) coordina dependencias y publicación por dueño Git. Los puntos de entrada anteriores de los proyectos llaman a la misma instalación del equipo.

Para modificar Constellation, ejecuta las pruebas de la fuente y construye el paquete desde este checkout. Las instrucciones de [desarrollo e instalación](.codex/README.md) describen la separación entre la fuente candidata, la distribución y una sesión que ya está abierta.
