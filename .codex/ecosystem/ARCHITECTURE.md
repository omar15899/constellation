# Constellation: autoridad compartida, ejecución nativa

Constellation organiza el trabajo; Codex ejecuta modelos, herramientas, agentes,
sesiones, permisos, skills y plugins. Los proyectos conservan sus datos,
invariantes, pruebas y propiedad Git. No hay un segundo runtime de agentes ni
un servicio de selección semántica.

## Responsabilidades y fuentes

| Responsabilidad | Implementación autoritativa | Configuración y estado | Consumidores |
| --- | --- | --- | --- |
| Descubrimiento y carga de skills | Codex; catálogo de la sesión y APIs nativas | Configuración nativa, ámbito y plugin | Coordinador y agentes según su superficie |
| Selección y composición | Modelo, descripciones nativas e instrucciones de las skills | Requisitos de la tarea; sin registro paralelo | Cada tarea |
| Diagnóstico de capacidades | `ecosystem/native.py`, sobre APIs y CLI nativos | Snapshot de lectura; no base de datos | Usuario, instalación y mantenimiento |
| Revisión independiente y continuidad | `ecosystem/runtime/review_gate.py` | Política compartida, historial, presupuesto temporal y extensiones del receptor | Adaptadores Git, portable y OmarOS |
| Entrega y publicación Git | `ecosystem/runtime/workflow.py` | Contrato y evidencia privados en `.git/constellation` | Repositorios Git y coordinador |
| Coordinación entre repositorios | `ecosystem/runtime/workspace.py` y `dispatch.py` | Registro declarativo del workspace y dependencias de la tarea | Hub y otros workspaces explícitos |
| Evidencia matemática/editorial sin publicación | `ecosystem/core.py` | Contratos con hipótesis, checks, evaluaciones y SQLite privado | Trabajos de investigación y documentos |
| Progreso recuperable | `ecosystem/runtime/progress.py`; adaptadores existentes | `task_progress` en el JSON Git o SQLite portable; sin almacén nuevo | Trabajo sustancial y reanudación |
| Diario personal | Receptor `progress_journal.py` de OmarOS y renderizado compartido | Política personal exacta, notas curadas e índice privado mínimo | Sólo fuentes y checkpoints personales autorizados |
| Personalización pedagógica | Skill de enseñanza disponible y perfil explícito del usuario | Perfil local provisional, editable y ajeno al paquete | Explicaciones y feedback intencional reutilizable |
| Eventos Codex | Entrada estable `CODEX_HOME/constellation/hook.py`, fuente `ecosystem/hook_entry.py`; adaptador `ecosystem/hooks.py` | Recibo e inventario verificados bajo lock; activación/confianza nativas; sólo contratos activos | Plugin instalado |
| Distribución | `ecosystem/build.py` e `install.py` | Inventario y recibo de instalación; caché derivado | Codex local y receptores |
| Dominio | `AGENTS.md`, herramientas y validadores del proyecto | Archivos propios del receptor | Su trabajo especializado |

Las entradas históricas `.codex/workflow.py`, `workspace.py`, `dispatch.py`,
`review_gate.py` y `agent_policy.py` son adaptadores de importación y CLI. No
contienen otra implementación. El hub mantiene el registro de sus repositorios;
no determina la propiedad Git de OmarOS ni de un tercero.

## Descubrir, seleccionar y ejecutar

El catálogo de la **sesión actual** es la primera fuente para decidir qué puede
usar el agente. Codex expone metadatos y carga el cuerpo de una skill cuando
resulta pertinente. Una petición explícita tiene prioridad dentro de los
permisos y las instrucciones superiores. El agente explica una selección cuando
ayuda a entender el trabajo; no debe cargar instrucciones irrelevantes para
justificar que conoce el catálogo.

El diagnóstico `native.py --capabilities --cwd RUTA` consulta un app-server nuevo
del CLI instalado. Esa superficie puede diferir del cliente que mantiene la
conversación. Por ejemplo, en 0.163.0 se observaron plugins remotos instalados
que no aparecían en `skills/list` del proceso nuevo aunque sus skills sí estaban
expuestas en esta sesión. La ausencia en ese listado no demuestra ausencia en
otras superficies.

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
clasificador o base de memoria nuevos. [PROGRESS.md](PROGRESS.md) especifica el
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
El [protocolo](references/protocol.md#review-continuity-and-budget) define esos
campos; los receptores mantienen las restricciones que añadan.

Los hooks del plugin observan contratos activos. No convierten cualquier
pregunta en un contrato, no hacen fetch al recibir un prompt y no publican.
Las definiciones del hub quedan retiradas para evitar eventos duplicados.
El comando del plugin apunta a la entrada estable fuera del caché versionado.
Un lock compartido protege validación y ejecución del hook; el instalador usa
el mismo lock en exclusiva para actualizar. Una colisión o instalación incoherente
produce una respuesta controlada, sin ejecutar código parcialmente actualizado.
El contrato de instalación, confianza y primera recarga está en
[README.md](README.md#instalar-y-actualizar).
El guard de patches no intercepta todas las escrituras por shell o MCP.
Un puente acotado de migración reconoce contratos OmarOS activos como datos
para autorizar únicamente sus rutas explícitas en la misma sesión y destino
congelado. No importa código del vault ni certifica su cierre, renombrados o
validación de conocimiento; esas responsabilidades siguen en su adaptador.

Los hooks Git del hub controlan privacidad y consistencia del diff; **un commit
o push manual no exige la revisión de Constellation**. La revisión y el destino
congelado se exigen en el camino de publicación del workflow. Los hooks de
Sweeplab y GasStorage conservan sus responsabilidades propias. No se promete
enforcement fuera de los caminos que realmente lo implementan.

## Referencias nativas

El comportamiento se contrasta con el binario instalado y las interfaces
documentadas de [skills](https://learn.chatgpt.com/docs/build-skills),
[hooks](https://learn.chatgpt.com/docs/hooks) y
[app-server](https://learn.chatgpt.com/docs/app-server). Una documentación más
nueva no convierte sus campos en parámetros admitidos por una versión anterior.
