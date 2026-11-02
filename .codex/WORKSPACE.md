# Propietarios y workspaces

`~/.codex` es el dueño de la fuente de Constellation, en `main`. Su
[registro](repositories.json) contiene sólo `.`. `~/GitHub` conserva otro dueño
Git, en `codex/workspace`, con el registro de los proyectos hijos. El remoto
compartido conserva la historia; cada raíz tiene su contrato, índice y publicación.

Usa la función `constellation` de la [guía de entrada](README.md). Las rutas de
un workspace son relativas a su raíz, que debe ser un repositorio Git real. El
motor rechaza enlaces ambiguos y rutas que salgan de esa raíz; el registro de
Constellation no se usa para incorporar a sus carpetas hermanas.

```sh
constellation git --root "$HOME/.codex" --session ID status
constellation workspace --root "$HOME/GitHub" route Shared/README.md PricingLab/README.md
```

Las entradas históricas en `~/GitHub/.codex/ecosystem/cli.py` conservan el
workspace de GitHub y remiten al lanzador instalado. El CLI de la fuente en
`~/.codex/.codex/ecosystem/cli.py` permite `--source` para desarrollo y selecciona
esta raíz por defecto; proporciona `--root` expresamente al trabajar en GitHub.

## Coordinar dos proyectos de GitHub

`plan` comprueba upstreams, fija rutas y prepara el contrato de cada dueño.
Declara las dependencias en el mismo plan.

```sh
constellation workspace --root "$HOME/GitHub" --session ID plan <<'JSON'
{
  "requirements": ["Ambos proyectos describen el mismo contrato de datos"],
  "paths": ["Shared/README.md", "PricingLab/README.md"],
  "depends_on": {"PricingLab": ["Shared"]}
}
JSON
constellation workspace --root "$HOME/GitHub" --session ID dispatch --capacity 4
constellation workspace --root "$HOME/GitHub" --session ID check --repo Shared -- git diff --check
constellation workspace --root "$HOME/GitHub" --session ID check --repo PricingLab -- git diff --check
```

El reparto entrega paquetes; el coordinador los asigna a agentes nativos reales,
con rutas exclusivas, y comprueba la evidencia de los proveedores antes de integrar
sus consumidores. Los trabajadores preservan cambios ajenos y no publican.

## Revisión independiente

Registra todos los autores con `review-author --repo RUTA`, abre `review-start`
tras los checks y registra los informes reales para el token vigente. Las cuotas
y la independencia se aplican por archivo según [REVIEW.md](../REVIEW.md). Otro
agente verifica cada hallazgo corregido o refutado. `review` documenta la
evidencia por requisito y propietario; los commits siguen las dependencias.

```sh
constellation workspace --root "$HOME/GitHub" --session ID commit -m 'Aclara el contrato de datos' Shared/README.md PricingLab/README.md
constellation workspace --root "$HOME/GitHub" --session ID finish
```

La publicación de `main` y de `codex/workspace` son operaciones distintas. Usa el
flujo Git de la raíz correspondiente y comprueba cada SHA remoto. Las operaciones
se consultan con `constellation workspace --help` y la ayuda de sus subcomandos.
La instalación, la ejecución real de hooks y su confianza se verifican por separado.
El progreso personal y la recepción documental de OmarOS conservan sus políticas;
el registro del workspace no concede esos permisos.
