# Constellation: autoridad compartida, ejecución nativa

Constellation organiza el trabajo; Codex y Claude Code ejecutan modelos,
herramientas, agentes, sesiones, permisos, skills y plugins mediante sus interfaces
nativas. Los proyectos conservan sus datos,
invariantes, pruebas y propiedad Git. No hay un segundo runtime de agentes ni
un servicio de selección semántica.

## Responsabilidades y fuentes

| Responsabilidad | Implementación autoritativa | Configuración y estado | Consumidores |
| --- | --- | --- | --- |
| Descubrimiento y carga de skills | Cliente nativo; catálogo de la sesión y sus APIs | Configuración nativa, ámbito y plugin | Coordinador y agentes según su superficie |
| Selección y composición | Modelo, descripciones nativas e instrucciones de las skills | Requisitos de la tarea; sin registro paralelo | Cada tarea |
| Diagnóstico de capacidades | `ecosystem/native.py` para Codex; `ecosystem/claude.py verify` y comandos nativos para Claude | Snapshot de lectura e integridad; sin catálogo paralelo | Usuario, instalación y mantenimiento |
| Revisión independiente y continuidad | `ecosystem/runtime/review_gate.py` | Política compartida, historial, presupuesto temporal y extensiones del receptor | Adaptadores Git, portable y OmarOS |
| Entrega y publicación Git | `ecosystem/runtime/workflow.py` | Contrato y evidencia privados en `.git/constellation` | Repositorios Git y coordinador |
| Coordinación entre repositorios | `ecosystem/runtime/workspace.py` y `ecosystem/runtime/dispatch.py` | Registro declarativo del workspace y dependencias de la tarea | Hub y otros workspaces explícitos |
| Evidencia matemática/editorial sin publicación | `ecosystem/core.py` | Contratos con hipótesis, checks, evaluaciones y SQLite privado | Trabajos de investigación y documentos |
| Progreso recuperable | `ecosystem/runtime/progress.py`; adaptadores existentes | `task_progress` en el JSON Git o SQLite portable; sin almacén nuevo | Trabajo sustancial y reanudación |
| Diario personal | Receptor `progress_journal.py` de OmarOS y renderizado compartido | Política personal exacta, notas curadas e índice privado mínimo | Sólo fuentes y checkpoints personales autorizados |
| Personalización pedagógica | Skill de enseñanza disponible y perfil explícito del usuario | Perfil local provisional, editable y ajeno al paquete | Explicaciones y feedback intencional reutilizable |
| Eventos Codex | Entrada estable `CODEX_HOME/constellation/hook.py`, fuente `ecosystem/hook_entry.py`; adaptador `ecosystem/hooks.py` | Recibo e inventario verificados bajo lock; guía estática y controles sobre contratos activos; confianza nativa | Plugin instalado |
| Eventos Claude | `ecosystem/claude_hooks.py`, traducción al mismo `ecosystem/hooks.py` | Identidad `claude-<session_id>`, metadata estructural y dueño de hooks explícito | Plugin Claude o adaptador receptor |
| Distribución | `ecosystem/build.py`; instaladores `install.py` y `claude.py` | Un bundle permitido, hashes, recibos y proyecciones nativas | Codex, Claude y receptores autorizados |
| Dominio | `AGENTS.md`, herramientas y validadores del proyecto | Archivos propios del receptor | Su trabajo especializado |

El CLI `ecosystem/cli.py` es la entrada común a `git`, `workspace` y
`agent-policy`; desde el checkout se invoca en `.codex/ecosystem/cli.py`.
Importa los módulos de `ecosystem/runtime/` directamente, sin lanzadores de
compatibilidad en la raíz de `.codex/`. El hub mantiene el registro de sus
repositorios; no determina la propiedad Git de OmarOS ni de un tercero.

## Organización de fuentes y distribución

La estructura separa cuatro responsabilidades: runtime, adaptación al cliente,
documentación mantenida y evaluación. `runtime/` conserva los algoritmos comunes;
los módulos públicos de instalación y hooks adaptan sus interfaces. `manifests/`
contiene sus fuentes declarativas y `docs/` las guías operativas. `references/`
conserva el método que consumen las skills; no duplica la documentación de operación.

Los informes fechados en `docs/history/` y los resultados en `evals/results/`
permanecen fuera del paquete instalable. Se conservan para auditar afirmaciones
históricas; no son entradas del motor. Los fixtures y pruebas pertinentes sí
acompañan al paquete para comprobarlo sin recuperar el checkout original.

El constructor ya es la frontera entre fuente y distribución. Proyecta los
manifiestos de plugin a las rutas exigidas por cada cliente y las instrucciones
TOML de roles al Markdown de Claude. Los manifiestos distribuidos de hooks
mantienen `ecosystem/hooks.json` y `ecosystem/claude-hooks.json`: esas rutas forman
parte de la identidad nativa y no se cambian por estética. Conservarlas no
mantiene ni concede confianza: una instalación o definición modificada puede
requerir una nueva aprobación del cliente. Cada proyección procede de una fuente
única en `manifests/`; no hay otro registro ni generador de arquitectura.

Los recibos y las verificaciones de instalaciones anteriores conservan la
propiedad, integridad y recuperación necesarias para actualizar. Son datos y
controles del instalador vigente; no mantienen otra estructura activa ni otro
runtime. El adaptador de OmarOS y su copia derivada verificada pertenecen al
contrato receptor actual.

## Una distribución para varios portátiles

La línea 1.3 distribuye un núcleo y dos entradas nativas; 1.3.1 reorganiza
sus fuentes y guías sin reemplazar esas responsabilidades. Las skills conservan
un único cuerpo canónico en `skills/`. Las instrucciones de roles permanecen en
`ecosystem/agents/*.toml`; el constructor genera el Markdown que Claude requiere.
Los manifiestos `.codex-plugin/plugin.json` y `.claude-plugin/plugin.json`
identifican la misma versión y apuntan a recursos permitidos dentro del paquete.
La construcción y el ZIP son deterministas para unas mismas entradas y módulos.

Cada adaptador traduce eventos y registro nativos. Ambos consumen los contratos,
checks, revisión y progreso existentes; no coordinan modelos mediante otro
runtime. Los agentes siguen siendo procesos del cliente, con su modelo, esfuerzo,
permisos y capacidad efectiva. La distribución completa incluye los ocho papeles;
una selección de módulos conserva los papeles necesarios para esa selección.

Claude admite un plugin permanente en `~/.claude/skills/constellation`, sin
marketplace ni cambios de settings. Su instalador protege ese directorio por
propiedad e integridad; el estado operativo vive fuera de él y sobrevive a una
actualización. Codex conserva su registro nativo, recibo y entrada estable.
Las diferencias de instalación reflejan las interfaces reales de los clientes,
sin imponer un formato único que ninguno de ellos garantice.

Los portátiles comparten versión, fuentes metodológicas y controles de evidencia.
Las cuentas, datos, políticas locales, registros de proyectos y conectores
permanecen separados. El paquete no transporta transcripciones, credenciales,
perfiles privados ni estados de investigación. Una instalación igual no garantiza
respuestas iguales ni que un proveedor esté disponible en ambos ordenadores.
Los proyectos conservan sus fuentes originales y el dueño Git de cada entrega.

OmarOS mantiene su adaptador y sus cuatro recursos derivados fijados en 1.2.0.
La versión 1.3 identifica la distribución dual, no una actualización implícita
del pin receptor. Su actualizador actual sólo admite bundles 1.2.0 y debe rechazar
el nuevo hasta que se migre expresamente ese contrato. La distribución no se
copia sobre los recursos derivados del vault.

## Descubrir, seleccionar y ejecutar

El catálogo de la **sesión actual** es la primera fuente para decidir qué puede
usar el agente. El cliente expone metadatos y carga el cuerpo de una skill cuando
resulta pertinente. Una petición explícita tiene prioridad dentro de los
permisos y las instrucciones superiores. El agente explica una selección cuando
ayuda a entender el trabajo; no debe cargar instrucciones irrelevantes para
justificar que conoce el catálogo.

La selección se revisa al cambiar la tarea o aparecer nueva evidencia. El
coordinador identifica primero las obligaciones del resultado: implementar,
demostrar, contrastar fuentes, presentar un artefacto o usar un servicio externo.
Después distingue capacidades necesarias, opcionales e improcedentes según el
catálogo realmente expuesto. Lee las instrucciones elegidas antes de usarlas y
comprueba dependencias, permisos y entradas en la superficie donde se ejecutarán.
Un subagente recibe un alcance concreto y verifica sus propias capacidades;
no se presupone que dispone de las conexiones del coordinador.

Esta disciplina debe producir decisiones observables: una definición elemental
puede no requerir ninguna skill; un algoritmo con una justificación matemática
puede requerir ingeniería y matemática; un informe basado en datos ajenos exige
proveniencia y acceso autorizado. Si falta una capacidad, se conserva la carencia
y se prueba una alternativa antes de atribuirle resultados. Cargar todas las
skills o lanzar todos los roles no satisface mejor esas obligaciones.

Los controles negativos contrastan precisamente esas decisiones: una referencia
irrelevante no debe activar otro flujo, una herramienta descubierta pero sin
acceso no cuenta como usada y una salida incompleta de un agente no aprueba la
entrega. La [metodología de evaluación](evaluation.md) separa pertinencia de
selección, ejecución efectiva y corrección del resultado. Los hooks observan
fronteras concretas; no pueden demostrar que cada decisión semántica futura del
modelo será correcta.

El [diagnóstico completo de Codex](migrations.md#diagnóstico-de-codex) consulta un app-server nuevo
del CLI instalado. Esa superficie puede diferir del cliente que mantiene la
conversación. Por ejemplo, en 0.163.0 se observaron plugins remotos instalados
que no aparecían en `skills/list` del proceso nuevo aunque sus skills sí estaban
expuestas en esta sesión. La ausencia en ese listado no demuestra ausencia en
otras superficies.

En Claude, `claude.py verify` comprueba la instalación y deja desconocidos carga,
confianza y ejecución. `/context`, `/skills`, `/agents`, `/hooks` y `/status`
permiten inspeccionar una sesión concreta. Su validación de manifiesto tampoco
ejecuta un experimento de investigación. Las comprobaciones y ensayos realmente
observados quedan separados en [compatibilidad observada](compatibility.md).

Instalación, descubrimiento, habilitación, autorización, compatibilidad y
ejecución son hechos diferentes. Una lista de herramientas MCP demuestra
descubrimiento, no una llamada exitosa. Un hook habilitado y confiado todavía
necesita un evento ejecutado para acreditar su comportamiento. Los estados sin
evidencia se mantienen desconocidos. Un error de dependencia se comunica y se
resuelve con una alternativa disponible o una limitación concreta.

Para un solver con análisis e informe, se pueden combinar ingeniería,
matemática y la skill del formato solicitado. Las dependencias reales ordenan
la ejecución; los trabajos independientes reciben archivos exclusivos. Una
definición breve se responde directamente. Una corrección pequeña usa un cambio
y una comprobación pertinentes, sin investigación ni delegación ceremoniales.

Investigación, aprendizaje e ingeniería se combinan según el objetivo y la
prioridad explícita del usuario; no son modos persistentes ni motores distintos.
La investigación distingue hipótesis, pruebas, aproximaciones y observaciones.
El aprendizaje aplica sólo el contexto personal pertinente y respeta la elección
entre explicación completa y guía sin revelar la solución. Los procedimientos
genéricos nunca incorporan el perfil personal. Su calibración conserva alcance y
procedencia del feedback intencional; ejemplos sintéticos no crean preferencias
reales. Persistir significa escribir y recuperar contexto, no entrenar el modelo.

Modelo, esfuerzo y metodología son decisiones separadas. El paquete no fija un
modelo ni una ventana de contexto global. Se retiró el override del hub que
imponía 1.000.000/900.000 tokens; cada cliente y modelo conserva sus límites
nativos observados. Cambiar de modelo no modifica contratos ni perfiles locales,
pero tampoco garantiza igualdad de herramientas, comportamiento o capacidad.

## Criterios de trabajo por responsabilidad

La escritura establece objetos, espacios, hipótesis y relaciones antes de usar
notación; distingue una función de sus argumentos y valores y construye la
explicación hasta el rigor necesario. Una edición acotada conserva voz y estructura
con el mínimo cambio suficiente. El referente financiero autorizado se consultó
como criterio editorial: ni su contenido ni el perfil personal se redistribuyen.

La ingeniería elige el diseño y el nivel de abstracción que pide el encargo,
reutiliza las estructuras reales del proyecto y aplica Google Style cuando sea
pertinente al lenguaje y sus convenciones. Explicita precisión y rango, comprueba
los casos límite y corrige los fallos: documentar una limitación no convierte un
resultado incorrecto en aceptable.

La investigación y la revisión usan fuentes primarias, búsqueda adversarial y
hallazgos reproducibles. Sus handoffs separan resultados, evidencia y pendientes;
antes de esperar a un agente, comprueban su estado real. Este refuerzo cambia
instrucciones, no hooks de ejecución, formatos nativos ni contratos. No introduce
un clasificador por palabras ni garantiza el cumplimiento semántico del modelo.

## Un ciclo suficiente por objetivo

El trabajo Git ordinario utiliza el ciclo Git. Una entrega matemática o
editorial que no requiere publicar usa el núcleo portable. No se exige abrir
dos contratos idénticos sólo porque se haya seleccionado una skill.
La presencia de `.git` no decide por sí sola: publicar requiere un upstream
autorizado; una entrega local puede usar portable dentro de una carpeta Git.

Los dos adaptadores tienen garantías diferentes. El núcleo portable conserva
inputs fijados, checks declarados, dependencias de evidencia y evaluaciones
por requisito que distinguen una prueba de un experimento. La revisión Git
base no certifica esas obligaciones automáticamente. Un trabajo mixto debe
declarar sus obligaciones semánticas y cómo se verifican antes de publicar;
cuando requiere un certificado portable, éste es un resultado concreto de
investigación consumido por la entrega Git, no un cierre duplicado de la misma
tarea. Ningún hash demuestra un teorema o la pertinencia de una prueba.

OmarOS conserva el adaptador especializado que protege renombrados, delegados,
datos privados y publicación durable. Consume el algoritmo común de revisión
con su política y validación de rutas. No se sustituye ese adaptador por el
motor Git ordinario: sus obligaciones adicionales siguen siendo necesarias.

Para código ordinario pequeño, la política puede admitir una justificación
`quick_code_reason` antes de la primera ronda. Queda ligada al snapshot completo
y la evalúa un revisor independiente. Una modificación de contenido, alcance,
autores o política la invalida; no reduce los mínimos ya fijados ni la revisión
Deep de rutas sensibles. Las políticas receptoras más estrictas prevalecen.

## Continuidad y conocimiento personal

Los checkpoints registran objetivo, estado, resultados, decisiones, hallazgos,
evidencia y pendientes en el almacén operativo existente. Mantienen identidad y
cronología durante la replanificación. El trabajo puede recuperarse sin OmarOS;
una entrega fallida no borra su estado ni lo convierte en completado.

El coordinador sincroniza los hitos significativos permitidos por la política
local: raíz canónica y alias exactos, destino fijado y checkpoint personal.
Registrar un proyecto o autorizar su padre no concede permiso de exportación.
El receptor OmarOS escribe una nota curada y el dashboard por su propio workflow,
con replay idempotente, rechazo de historia obsoleta y recuperación de escrituras
interrumpidas. `RECEIVED_LOCAL` acredita recepción local, no publicación remota.

El estado operativo, la historia Git y las notas científicas son responsabilidades
distintas. El diario no copia logs, conversaciones ni perfiles de aprendizaje.
La selección de hitos sigue siendo responsabilidad del agente; no hay daemon,
clasificador o base de memoria nuevos. [progreso recuperable](progress.md) especifica el
protocolo, los permisos y la recuperación.

## Fronteras verificables

El coordinador usa agentes nativos, conserva sus identidades reales y asigna
propiedad exclusiva. La capacidad efectiva pertenece a la sesión: los máximos
por proyecto no se suman. Un reparto describe dependencias; no demuestra que
sus agentes se hayan lanzado. Las pruebas con identidades sintéticas verifican
el mecanismo, no la calidad de una revisión realizada por un modelo.

La revisión adapta su continuidad a progreso observable y presupuesto real,
sin tope universal de tres rondas. El algoritmo común conserva independencia,
historia, hallazgos y mínimos; las ampliaciones de presupuesto y continuaciones
quedan explícitas. No incorpora otro clasificador ni planificador de agentes.
El [protocolo](../references/protocol.md#review-continuity-and-budget) define esos
campos; los receptores mantienen las restricciones que añadan.

Los controles de alcance, revisión y cierre del plugin observan contratos
activos. Además, `UserPromptSubmit` aporta una guía estática para consultar el
catálogo y cargar las instrucciones pertinentes, también cuando no hay contrato.
El texto común `METHOD_GUIDANCE` vive en `hooks.py`; Claude lo reutiliza en su
inicio y contexto nativos. El adaptador procesa el JSON del evento, pero no
consulta los campos de prompt o transcripción, no clasifica su contenido y no
los almacena. El recordatorio no inicia, sincroniza ni publica tareas.

La guía identifica `constellation:coding`, `constellation:mathematics`,
`constellation:quant-research` y `constellation:writter` como opciones que deben
usarse sólo si existen y las instrucciones del receptor lo permiten. Incluye el diagnóstico
de ingeniería sin edición y los argumentos matemáticos no triviales; conserva
la respuesta directa para consultas breves, traducciones cortas y aritmética
simple. Un equivalente seleccionado por el proyecto prevalece cuando corresponde.
La existencia del texto no demuestra que el modelo haya cargado una skill:
la selección y su resultado se evalúan por separado.

Las definiciones del hub quedan retiradas para evitar eventos duplicados.
El comando del plugin apunta a la entrada estable fuera del caché versionado.
Un lock compartido protege validación y ejecución del hook; el instalador usa
el mismo lock en exclusiva para actualizar. Una colisión o instalación incoherente
produce una respuesta controlada, sin ejecutar código parcialmente actualizado.
El contrato de instalación, confianza y primera recarga está en
[instalación y actualización](migrations.md#instalar-y-actualizar).
El guard de patches no intercepta todas las escrituras por shell o MCP.
El adaptador de OmarOS reconoce sus contratos activos como datos
para autorizar únicamente sus rutas explícitas en la misma sesión y destino
congelado. No importa código del vault ni certifica su cierre, renombrados o
validación de conocimiento; esas responsabilidades siguen en su adaptador.

El adaptador Claude comunica el CLI y la identidad prefijada en `SessionStart`,
sin iniciar un contrato. Traduce sólo identidad, evento, cwd y rutas de edición;
no transmite prompts, transcripciones, contenido de herramientas ni resultados
de agentes. Claude no documenta un `turn_id` equivalente: la correlación usa
metadata estructural deliberada y no fabrica una identidad a partir del texto
privado. Las observaciones de agentes conservan los IDs nativos reales.

Un receptor que declara `CONSTELLATION_HOOK_OWNER=project` conserva la autoridad
de su adaptador y evita un segundo tratamiento global de eventos. La traducción
no ejecuta scripts del proyecto. `onFailure: "block"` protege los eventos
nativos que lo admiten; `Stop` y `SubagentStop` quedan fuera de esa protección.
El cierre requiere evidencia y aceptación explícitas del motor, incluso si el
cliente deja de pedir continuaciones. Los hooks de archivos tampoco confinan
escrituras arbitrarias por shell o MCP.

Los hooks Git del hub controlan privacidad y consistencia del diff; **un commit
o push manual no exige la revisión de Constellation**. La revisión y el destino
congelado se exigen en el camino de publicación del workflow. Los hooks de
Sweeplab y GasStorage conservan sus responsabilidades propias. No se promete
enforcement fuera de los caminos que realmente lo implementan.

## Criterios publicados por OpenAI y Anthropic

Esta comparación usa documentación y experiencias públicas, consultadas el
2026-10-29. No describe una arquitectura interna universal de los laboratorios
ni transfiere a Constellation sus métricas experimentales. Las decisiones del
paquete se contrastan con sus consumidores y pruebas locales.

OpenAI describe en [Harness engineering](https://openai.com/index/harness-engineering/)
un mapa de instrucciones breve, documentación estructurada e invariantes
comprobadas mecánicamente. Constellation aplica esa separación: README orienta,
las guías explican responsabilidades y los controles validan alcance, evidencia
y publicación. Una organización de carpetas facilita mantener el sistema; no
prueba que sus agentes produzcan mejores resultados.

La [personalización de Codex](https://learn.chatgpt.com/docs/customization/overview)
y las [skills de Claude](https://code.claude.com/docs/en/skills) distinguen
metadatos disponibles e instrucciones cargadas cuando hacen falta. La
[ingeniería de contexto de Anthropic](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)
apoya recuperar contexto pertinente progresivamente. Por eso la selección usa
el catálogo de la sesión y las obligaciones de la tarea, sin cargar todos los
cuerpos ni construir otro selector persistente.

Las interfaces de [subagentes Codex](https://learn.chatgpt.com/docs/agent-configuration/subagents)
y [subagentes Claude](https://code.claude.com/docs/en/sub-agents) requieren
respetar su contexto, herramientas y permisos efectivos. La delegación de
Constellation asigna alcance y resultados verificables, pero no presupone que
el hijo herede las conexiones o las skills ya leídas por el coordinador.
La evidencia publicada sobre multiagentes no elimina la necesidad de comprobar
si una división concreta del trabajo mejora esa tarea.

## Correspondencia con diseños publicados por Anthropic

La comparación del 2026-10-28 se refiere a principios y mecanismos observables,
no a igualdad de productos ni a reproducir resultados internos de Anthropic.
Sus publicaciones respaldan una estructura pequeña que compone capacidades y
exige evidencia. Incorporar cada servicio, proceso o modo anunciado añadiría
dependencias sin demostrar que mejora este centro de investigación.

| Diseño publicado | Correspondencia y límite de Constellation |
| --- | --- |
| [Agentes efectivos](https://www.anthropic.com/research/building-effective-agents) | Skills y especialistas se componen según dependencias reales. Una tarea simple no necesita un equipo o workflow persistente. El cliente ejecuta los agentes. |
| [Sistema de investigación multiagente](https://www.anthropic.com/research/multi-agent-research-system) | El coordinador acota trabajos, asigna archivos y exige resultados, fuentes y revisión independiente. Más agentes no prueban mejores conclusiones; amplitud, exactitud de citas y calidad de síntesis necesitan evaluación propia. |
| [Ingeniería de contexto](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) | El catálogo permite cargar instrucciones pertinentes y los handoffs conservan alcance, evidencia y pendientes. El progreso curado es recuperable sin distribuir conversaciones completas. Los límites efectivos siguen perteneciendo al cliente. |
| [Agent Skills](https://www.anthropic.com/research/equipping-agents-for-the-real-world-with-agent-skills) | Instrucciones y referencias viven en archivos canónicos, se distribuyen modularmente y se cargan cuando hacen falta. La presencia de una skill no demuestra selección ni uso correcto. |
| [Harnesses para tareas largas](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents) | Requisitos explícitos, progreso durable, checks y revisión actuales permiten reanudar y decidir qué falta. Un estado mecánico completo no sustituye una prueba real del comportamiento o argumento. |
| [Evaluación de agentes](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) | Se distinguen afirmaciones del agente, resultado observado y evidencia independiente. Los checks deterministas conviven con revisión intelectual. Los ensayos repetidos deben separar conseguir algún éxito de mantener el éxito en todos los intentos; las diferencias entre modelos requieren casos representativos. |
| [Diseño adaptable del harness](https://www.anthropic.com/research/harness-design-long-running-apps) | La ejecución nativa y los adaptadores pequeños permiten cambiar de cliente sin duplicar el núcleo. La separación autor/revisor se conserva, y cada componente añadido debe justificar su función con evidencia. |
| [Managed Agents](https://www.anthropic.com/research/managed-agents) | Se separan estado recuperable, contratos y ejecución. Aquí el estado es local y cada proyecto conserva su autoridad; distribuir el paquete no instala un servicio cloud ni ofrece sus garantías operativas. |

Los [plugins Claude](https://claude.com/resources/articles/claude-code-plugins)
aportan distribución nativa de skills, agentes y hooks. La versión 1.3 usa ese
mecanismo para entregar el mismo núcleo. Los
[workflows dinámicos](https://claude.com/resources/articles/introducing-dynamic-workflows-in-claude-code)
pueden ejecutar tareas dentro del cliente, pero su adopción no reemplaza el
contrato durable ni la aceptación independiente. Las
[evaluaciones nativas de plugins](https://code.claude.com/docs/en/plugin-evals)
permiten contrastar casos con una baseline sin plugin; son una herramienta
adicional que requiere disponibilidad y llamadas a modelos, no una condición
para instalar o verificar el paquete sin conexión.

La comparación deja abierta la medición de resultados entre Codex y Claude:
ejecutar la misma pregunta acotada, comprobar fuentes y contraejemplos, provocar
una ausencia o fallo de evidencia y verificar que ninguna síntesis lo convierte
en aprobación. Los porcentajes y mejoras publicados por Anthropic no son
mediciones de Constellation.

La [medición publicada de cobertura interna de acciones](https://www.anthropic.com/institute/measuring-pace-of-ai-development)
tampoco se transfiere a este paquete. Sus hooks observan eventos concretos y
protegen las herramientas de archivos declaradas; no interceptan universalmente
shell, MCP ni toda acción del cliente. La revisión y publicación vuelven a
comprobar el alcance por su propio camino.

## Referencias nativas

El comportamiento se contrasta con el binario instalado y las interfaces
documentadas de [skills](https://learn.chatgpt.com/docs/build-skills),
[hooks](https://learn.chatgpt.com/docs/hooks) y
[app-server](https://learn.chatgpt.com/docs/app-server), y con las interfaces
Claude de [plugins](https://code.claude.com/docs/en/plugins/create),
[hooks](https://code.claude.com/docs/en/hooks) y
[subagentes](https://code.claude.com/docs/en/sub-agents). Una documentación más
nueva no convierte sus campos en parámetros admitidos por una versión anterior.
