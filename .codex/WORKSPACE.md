# Publicación entre repositorios

[La guía común](README.md#operar-desde-cualquier-carpeta) define la función
`constellation`. Conserva el ID del chat y elige la raíz del propietario en
cada operación. La fuente de Constellation publica en `main`. El hub de GitHub
publica en `codex/workspace` y mantiene el registro y la coordinación de los
hijos. Los hijos y OmarOS publican desde sus propias raíces.

Usa `git --root RUTA --session ID` para un solo dueño con contrato Constellation
y `workspace --root "$HOME/GitHub" --session ID` para coordinar los dueños
registrados en el hub. El vault tiene su adaptador y contrato de delegación.
El adaptador histórico del hub sigue resolviendo al mismo lanzador instalado.

## Coordinar dos proyectos de GitHub

Declara rutas relativas al hub y dependencias entre dueños. El motor determina
cada raíz Git real y comprueba el upstream. El coordinador asigna rutas
exclusivas a agentes nativos y valida la evidencia en orden de dependencia.

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

## Revisión independiente

Registra a los autores con `review-author --repo RUTA`, abre `review-start`
tras las comprobaciones y registra los informes del token vigente. Usa
[REVIEW.md](../REVIEW.md) y la política del dueño para la cobertura de revisión.
`review` documenta el resultado por requisito y propietario.

```sh
constellation workspace --root "$HOME/GitHub" --session ID commit -m 'Aclara el contrato de datos' Shared/README.md PricingLab/README.md
constellation workspace --root "$HOME/GitHub" --session ID finish
```

Comprueba el SHA remoto de cada dueño. El registro de repositorios describe
el enrutado. Para el acceso a datos y la recepción documental de OmarOS rige
el alcance autorizado del encargo.
