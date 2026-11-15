# Contrato del hub GitHub

La [guía común de publicación](../../.codex/.codex/WORKSPACE.md) contiene el
ciclo y el ejemplo de dos dueños. Usa el lanzador de [README.md](README.md),
con `cli workspace --root "$HOME/GitHub" --session ID OPERACION`.
Las rutas del plan son relativas al hub; conserva el ID del chat.

El [registro](repositories.json) identifica los dueños y la
[política de agentes](agent-policy.json) los límites locales. Sin `--root`,
`workspace` busca el registro más cercano entre los ascendientes; selecciona
la raíz expresamente desde fuera o ante registros solapados. Un proyecto
externo necesita alcance explícito. Lee las instrucciones de cada dueño real.

El hub publica en `codex/workspace`; la fuente Constellation, en `main` del
mismo remoto privado. Mantén ambos árboles separados. Cada hijo conserva su
rama, upstream, contrato, comprobaciones, revisión y publicación. El adaptador
histórico transmite a la instalación y no carga otro motor del hub.

[REVIEW.md](../REVIEW.md), [RESEARCH.md](RESEARCH.md) y [QUANTOS.md](../QUANTOS.md)
añaden los controles del dominio. Para documentación seleccionada de OmarOS
aplica [KNOWLEDGE.md](KNOWLEDGE.md); los hitos personales exigen su autorización
exacta. El registro operativo no concede ninguno de esos permisos.
