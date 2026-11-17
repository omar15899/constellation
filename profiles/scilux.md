# Scilux

Raíz: `/Users/omarkhalil/GitHub/Scilux`. Las rutas de dominio siguientes se
interpretan desde esa raíz. Scilux produce guiones educativos, storyboards TikZ
y documentos intelectuales. Conserva sus contratos pedagógicos y formatos;
Constellation posee los ocho roles nativos, las skills compartidas y el flujo de
alcance, comprobación, revisión y publicación.

## Responsabilidades

- El coordinador aclara el encargo, público, fuentes y entregables; registra
  rutas exactas y los checks pertinentes antes de editar.
- Investigación y extracción usan `ecosystem_researcher`; obligaciones formales,
  `ecosystem_mathematician` y, cuando procede, `ecosystem_counterexample`.
- Redacción y pedagogía usan `ecosystem_editor`; código, TikZ y generación,
  `ecosystem_coder`. La revisión independiente usa `ecosystem_reviewer`,
  `ecosystem_verifier` o `ecosystem_security_reviewer` según el riesgo.
- Los nombres de etapa y antiguos especialistas de skills y registros históricos
  describen responsabilidades del dominio. No son tipos de subagente instalados.
  Ejecuta esas responsabilidades con los ocho roles cargados y el contrato común.
  La antigua secuencia `semantic-kernel`/orchestrator/playbook ya no es una
  condición de despacho ni un segundo runtime. Esta regla de integración rige
  sobre los registros históricos; los métodos actuales no despachan ese sistema.
- Modelos, esfuerzo y permisos se heredan del cliente. Las tablas históricas de
  modelos no son configuración activa. Sólo el coordinador publica mediante
  `constellation.py`; no existe un agente local `git-steward`.

## Maintained methods

Use [scilux-lessons](../skills/Scilux/scilux-lessons/SKILL.md) for lesson creation, revision, sources, storyboards and delivery; use [scilux-documents](../skills/Scilux/scilux-documents/SKILL.md) for governed notes, essays and figures. Natural-language requests do not require a routing command. The fifteen former selectors are consolidated into these two methods.

## Fuentes del dominio

Lee `CLAUDE.md`, `config/context-registry.yaml`, `config/style-canon.yaml`,
`config/document-schema-registry.yaml` y las plantillas de `docs/templates/`.
Las fases P0–P9, artefactos, contratos de entrada/salida y calidad de la enseñanza
siguen vigentes. `config/agent-registry.yaml`, `config/routing-policy.yaml` y los
esquemas de provenance/playbook conservan vocabulario y evidencia histórica;
no constituyen un catálogo de agentes ejecutables. Los documentos históricos
de arquitectura se interpretan con esta distinción.

Scilux está en el perímetro `adjacent`, sin tier QuantOS. No importa Shared.
`reference/` es de consulta; `workspace/` es efímero. No se publican sus archivos.
Conserva el servidor MCP, el estilo de salida, las fuentes y los datos locales.
La recuperación de OmarOS exige evidencia de disponibilidad; una inferencia
propia nunca se presenta como contenido recuperado del vault. `reference/omaros`
conserva su destino histórico, igual que `SCILUX_OMAROS_PATH` en el MCP. Cambiar
esa fuente de datos requiere otro encargo. Comprueba fuentes externas ausentes, como la
ruta histórica de Reflexiones, antes de afirmar acceso.

## Comprobaciones obligatorias según el entregable

Create, change or run tests only when Omar explicitly requests them. The commands below identify existing artifact gates; they are not blanket authorization for tests or behavioral probes. If a required gate needs unauthorized testing, report it as unmet rather than bypassing it.

Declara los checks aplicables en `required_checks` al abrir el encargo. Ejecuta
cada comprobación mediante `constellation.py check TASK ID -- COMANDO` desde
esta raíz. Fija `SCILUX_ROOT` a la raíz real y `SCILUX_LESSON_ID` al identificador
exacto de la lección; no uses la inferencia por archivo más reciente.

| Momento o artefacto | Comando del check |
| --- | --- |
| Antes de P0: brief, fuentes y registros | `env SCILUX_LESSON_ID=LESSON python3 .claude/hooks/start_gate.py` |
| Antes de trabajo intelectual | `python3 .claude/hooks/intellectual_start_gate.py` |
| Recuperación necesaria de OmarOS | `python3 .claude/hooks/mcp_health_probe.py --quiet` |
| P1: fuentes normalizadas | `env SCILUX_LESSON_ID=LESSON python3 .claude/hooks/ingestion_gate.py` |
| P3: notación y preámbulo | `env SCILUX_LESSON_ID=LESSON python3 .claude/hooks/notation_gate.py` |
| Guion ensamblado: duración | `env SCILUX_LESSON_ID=LESSON python3 .claude/hooks/timing_gate.py` |
| Frames TikZ de una lección | `env SCILUX_LESSON_ID=LESSON python3 .claude/hooks/tikz_compile_gate.py` |
| Documento gobernado Markdown | `env SCILUX_HOOK_TASK_ID=TASK python3 .claude/hooks/knowledge_schema_gate.py` |
| TeX/TikZ intelectual | `python3 .claude/hooks/intellectual_compile_gate.py --task-id TASK --require-manifest` |
| Antes de P9 o exportar | `env SCILUX_LESSON_ID=LESSON python3 .claude/hooks/release_gate.py` |
| Infrastructure tests, only when explicitly requested | `python3 tests/run_all.py` |

La publicación añade una comprobación distinta sobre el árbol candidato:
la cadena Git preservada ejecuta `.claude/git-hooks/pre-commit`, que llama a
`pre_commit_gate.py` con el `GIT_INDEX_FILE` aislado de Constellation. Lee los
blobs de ese índice para validar frontmatter de escenas y frames; no sustituye
esos bytes por los del worktree ni modifica el índice ajeno. Las eliminaciones
no requieren contenido inexistente. El guard rechaza contenido no legible o
malformado. La política central excluye además `workspace/**` y `reference/**`
de la publicación, incluidos los commits salientes.

Esta comprobación se ejecuta durante `constellation.py commit TASK MENSAJE`.
Una ejecución manual del script sin el índice candidato no demuestra que se
haya validado el árbol que se va a publicar. Los checks de fase de la tabla y
la revisión independiente siguen siendo obligatorios para sus entregables.

Para Markdown/TeX crea primero el manifiesto exacto
`workspace/intellectual/tasks/TASK/hook_targets.txt`. Comprueba que enumera
todos los entregables actuales y que el resultado del validador cubre esos
archivos. El validador Markdown conserva un fallback histórico por mtime;
un retorno cero sin targets no demuestra cobertura. No uses ese fallback como
evidencia del encargo. La comprobación MCP de inicio es informativa; el check
MCP separado debe pasar cuando el resultado dependa de recuperación.

Los validadores se conservan como checks explícitos. Los antiguos selectores
`SubagentStart`/`SubagentStop` por especialistas ausentes se retiran: terminar un
rol genérico no identifica una fase o un artefacto. Los hooks nativos de registro
y guardia de shell conservan sus responsabilidades. El motor común controla
ediciones y publicación; los hooks no constituyen un sandbox.

## Calidad y entrega

Cada fase necesita evidencia de entrada y salida. Cada objetivo de aprendizaje
(LO) debe quedar cubierto por al menos un beat de definición, ejemplo o
afirmación. Cada concepción errónea debe quedar abordada por al menos un beat
de contraejemplo o puente. Cada afirmación factual debe tener su fuente en
`sources.json`. La revisión debe comprobar estas tres obligaciones para todos
los elementos, además de comprobar la utilidad de cada beat.

Cada beat de definición contiene las tres capas: estructura formal, intuición
rigurosa y visión intelectual. Preserva notación, honestidad visual y paridad
bilingüe. No hay frames sin narración, texto, movimiento y fuente. Cada frame
TikZ debe compilar antes de su commit. Compila también los demás artefactos
TeX antes de entregarlos y revisa visualmente el resultado.

P9 exige un informe independiente con veredicto PASS. Una excepción debe quedar
explícita en el encargo y en el informe; un waiver histórico no es aprobación
nueva. La revisión comprueba matemáticas, pedagogía, accesibilidad, referencias,
coherencia visual y cobertura de los validadores. Los avisos de estilo son
informativos; no sustituyen esa lectura.

Realiza commits por unidades lógicas con rutas exactas y mensajes naturales,
sin atribución de IA. El registro de evidencia y el SHA remoto verificado
pertenecen al flujo común. Las metas históricas de número de commits no obligan
a fabricar actividad.

## Lesson style and artifact conventions

The master lesson script is Markdown at `lessons/LESSON/script/full_script.md`. Frame sheets use `storyboard/frames/frame_NNNN.md`, with corresponding `storyboard/tikz/frame_NNNN.tex`; downstream animation targets Manim Community Edition. Preserve the brief's requested languages and duration; do not introduce a second default or silently change the audience. The lesson skill records the P0–P9 artifact dependencies.

For lessons, retain precise speakable narration and the three-layer definition standard. Avoid “clearly”, “obviously”, “trivially” and “it is easy to see” as substitutes for explanation. Every beat advances a learning objective or addresses a misconception. Hooks begin with a concrete, mathematically honest tension and a precise learning promise.

Analogies map structure, state `breaks_when`, and follow the style canon's preference for physics, geometry and spatial experience rather than cooking, finance, sports or politics. Preserve the lesson convention of at most one strong analogy per two minutes; originality does not excuse distortion. Visual elements must support the beat, use consistent semantic colours and remain readable at the intended 1080p presentation size. Apply the current canon when a brief intentionally changes a presentation convention.

`inputs/briefs/_template.yaml` and `lessons/_template/` own scaffolding. Do not overwrite an existing lesson. Workspace and reference data remain private; lesson reviews and reports contain curated evidence, not raw conversation exports. The start gate currently does not count image-only inputs as a sufficient source set: report this prerequisite honestly rather than inventing a source.
