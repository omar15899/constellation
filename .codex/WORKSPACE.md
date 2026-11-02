# Trabajar desde GitHub o desde un proyecto

Usa la función `constellation` de la [guía de entrada](README.md), que ejecuta la versión instalada y verificada en este equipo. Las rutas de `workspace` son relativas al hub. Desde el hub o cualquier subcarpeta, la instalación busca el registro `.codex/repositories.json` más cercano entre los directorios ascendentes. Desde fuera, o si dos registros se solapan, proporciona la raíz expresamente.

```sh
constellation workspace route Shared/README.md PricingLab/README.md
constellation workspace --root "$HOME/GitHub" route Shared/README.md
```

El comando conserva la rama, el upstream y las instrucciones del propietario real de cada archivo. Un proyecto externo debe identificarse expresamente en el alcance. El [registro](repositories.json) es información del workspace y la [política de agentes](agent-policy.json) fija los límites locales. La [doctrina de revisión](../REVIEW.md) y la [guía de investigación](RESEARCH.md) definen las obligaciones aplicables.

Los proyectos existentes pueden seguir llamando a `.codex/ecosystem/cli.py` del hub. Este adaptador regular proporciona la raíz del hub a la instalación verificada y conserva la precedencia de un `workspace --root RUTA` explícito posterior. No importa código de los antiguos directorios del motor. La opción `--source` se utiliza únicamente desde la fuente canónica en `~/.codex` y se rechaza en el adaptador del hub.

`~/GitHub` conserva su propietario Git y el registro de sus hijos en la rama `codex/workspace`. El repositorio principal de Constellation está en `~/.codex`, en la rama `main` del mismo remoto privado. Cada raíz conserva su contrato y publicación; no fusiones el árbol fuente de nuevo en este workspace.

## Coordinar dos propietarios

`plan` comprueba el upstream de los participantes, fija rutas exactas y prepara un contrato por dueño Git. Declara las dependencias en el mismo plan.

```sh
constellation workspace --session ID plan <<'JSON'
{
  "requirements": ["Ambos proyectos describen el mismo contrato de datos"],
  "paths": ["Shared/README.md", "PricingLab/README.md"],
  "depends_on": {"PricingLab": ["Shared"]}
}
JSON
constellation workspace --session ID dispatch --capacity 4
```

El reparto propone paquetes por dueño. El coordinador asigna agentes nativos según la capacidad real, conserva rutas exclusivas por escritor y comprueba la evidencia de los proveedores antes de integrar consumidores. Los identificadores de los paquetes y los agentes reales son distintos.

```sh
constellation workspace --session ID check --repo Shared -- git diff --check
constellation workspace --session ID check --repo PricingLab -- git diff --check
```

Usa pruebas apropiadas para los cambios reales. Registra autores mediante `review-author --repo RUTA`, abre `review-start --repo RUTA` y registra los informes reales sobre el token vigente. Los hallazgos requieren resolución independiente. `review` recibe evidencia por requisito y propietario. Los commits y sus pushes siguen el orden de dependencias.

```sh
constellation workspace --session ID commit -m 'Aclara el contrato de datos' Shared/README.md PricingLab/README.md
constellation workspace --session ID finish
```

Un proveedor sin archivos propios puede acreditar la publicación de su HEAD con `publish --repo RUTA`. Si falla una fase, `status` conserva el progreso por repositorio. Reanuda el propietario pendiente con su contrato vigente. Publicar en dos remotos son dos operaciones independientes. La documentación seleccionada para OmarOS requiere su [contrato documental](KNOWLEDGE.md) y el progreso personal requiere autorización explícita.

Las operaciones disponibles, incluyendo recuperación de checks y presupuesto de revisión, se consultan con `constellation workspace --help` y la ayuda de cada subcomando. Los hooks compartidos requieren confianza en el cliente. La instalación, ejecución efectiva de un evento y revisión sustantiva se verifican por separado.
