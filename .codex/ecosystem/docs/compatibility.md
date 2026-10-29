# Compatibilidad observada

## Candidato 1.4.0-rc.1: Claude en Windows nativo

El candidato añade una adaptación nativa para Claude Code en Windows, sin WSL.
La ejecución real en Windows permanece pendiente: ni la construcción en macOS
ni la revisión estática acreditan locks, ACL, recuperación o despacho de eventos
en ese sistema. La [guía de Windows](windows.md) separa la aceptación aislada del
backend, los eventos reproducidos directamente y el recorrido en un cliente real.
Codex en Windows no forma parte de ese destino.

Antes de los cambios de plataforma, la base inglesa pasó 368 pruebas y cinco
suites exportadas de 351 pruebas cada una, con omisiones explícitas según módulo.
También pasó instalación inglesa temporal, repetición y actualizaciones entre
idiomas en ambos instaladores. Esa evidencia es del baseline POSIX; no se presenta
como aceptación del candidato Windows ni como una evaluación nueva de modelos.

El instalador informa si la sincronización de directorios está soportada.
Un estado `unsupported` no equivale al `fsync` POSIX ni demuestra durabilidad
ante pérdida de alimentación. Las pruebas Windows que no se hayan ejecutado
permanecen pendientes.

## Aceptación de 1.3.1

Evidencia registrada el 2026-10-29: **código comprobado, con límites de aceptación
explícitos**. La batería anterior a la última corrección del oráculo pasó
353 pruebas directas. Esa ejecución omitió sólo el harness recursivo de cinco
exportaciones, ya superado en la suite integrada anterior de 349 pruebas. El
delta posterior del probe pasó cinco pruebas focales; las 353 no se presentan
como una reevaluación íntegra del código tras ese cambio. Los grupos y reintentos no se suman como casos
independientes. Cada hallazgo conserva por separado su reparación, verificación
independiente y resolución formal contra el token de revisión vigente. Este
checkpoint no anticipa el cierre de hallazgos nuevos o todavía pendientes.
Este documento no acredita publicación: la certifica el cierre del workflow.

| Superficie | Observación del candidato o baseline | Límite |
| --- | --- | --- |
| Predecesor 1.3.0 | Se reconstruyó el paquete original de 78 recursos; su `bundle.json` coincide con SHA-256 `316b0ac84300291a0409776f95c78c140b38bf3e33e30e965e34be1b1540ffce`, sin ejecutar código de la copia anterior. | La coincidencia acredita el artefacto usado en la migración, no su ejecución en un cliente. |
| Paquete 1.3.1 | La distribución contiene 77 recursos, con rutas y contenido distintos de los 78 históricos. El probe ejecutable se distribuye; su prueba de seguridad pertenece sólo al desarrollo. | El tamaño del inventario no certifica comportamiento. Los hashes de los ensayos identifican sus snapshots, no una distribución posterior que incluya esta documentación. |
| Actualización 1.3.0 → 1.3.1 | Ambos instaladores actualizaron hogares temporales; Codex utilizó su CLI nativo real y Claude verificó la sustitución de archivos y su recibo. | La prueba de archivos se distingue del despacho nativo observado después. |
| Baseline Codex | Codex CLI 0.164.0 mostró el paquete 1.3.0, cuatro skills y cinco hooks confiados. | Describe la versión anterior, no la confianza del candidato. |
| Codex 1.3.1 | Tras la aprobación del usuario, la consulta nativa confirmó los cinco hooks `trusted` y habilitados. | La confianza fue aprobada por el usuario; conservar rutas o pasar tests no la concede. |
| Recorrido real Codex | CLI 0.165.0 ejecutó padre e hijo: `apply_patch` declarado permitió los bytes exactos; el no declarado fue bloqueado por `preToolUse` con «outside the registered scope» y dejó el archivo ausente. Se observaron inicio, fin y `observed_agents` final `stop`. | El único contrato registrado del padre permaneció `active` y `closed=false`; no se aprobó un cierre inexistente. El `threadId` del hijo no acredita un payload `session_id`, su rol ni persistencia. |
| Probe Claude | La corrección del oráculo usa una lista permitida explícita y pasó las cinco pruebas focales actuales. Los cinco casos nativos con Claude Code 2.1.301 y respuestas HTTP simuladas locales corresponden al ensayo anterior. | Se distingue la validación del último delta de la ejecución nativa previa. Las respuestas simuladas no miden calidad de un modelo remoto. |
| Subagente real Claude | Un hijo `constellation:ecosystem-coder` escribió los bytes declarados; su `Write` no declarado recibió `PreToolUse` deny y dejó el archivo ausente. Ambas operaciones conservaron la sesión padre; se observaron `SubagentStart`, `SubagentStop` y `observed_agents` final `stop`. | El contrato portable permaneció correctamente `active` después de dos intentos Stop. No se fabricó cierre ni se probó publicación Git o selección autónoma del rol. |
| Concurrencia del motor | Pasaron 132 pruebas enfocadas y un ensayo procesó 64 inicios y 64 cierres en 3,317 segundos. | No representa 64 agentes de modelo ejecutados ni permite extrapolar rendimiento. |
| Selección semántica Claude | En un único candidato, tres de cuatro casos sustantivos invocaron su skill: ingeniería, matemática e investigación cuantitativa. El caso de escritura produjo 179 palabras sin invocarla. | Se conserva la desviación de escritura; no se reemplaza por su éxito con otra variante de la guía. La muestra no establece selección perfecta ni causalidad general. |
| Controles y respuestas | Los dos controles negativos se resolvieron sin herramientas; las seis respuestas fueron completas según sus comprobaciones estructurales. | Completar una respuesta o pasar un oráculo estructural no demuestra su verdad, calidad general ni selección correcta. |

El ensayo semántico corresponde al snapshot de aceptación con SHA-256 de
`bundle.json` `102355132d6bb9831c93faae28306dbd083ea2bed6e8e84e53f3a2385af4a505`.
Sus hooks coinciden con el código evaluado; los cambios posteriores de instrucciones
y documentación no convierten ese hash en el de la distribución final. El resultado
3/4 precede al refuerzo de las instrucciones y no mide la selección automática de
la versión ampliada. Sus [ensayos dirigidos](evaluation.md#ensayos-dirigidos-de-las-instrucciones)
se registran aparte, con el fallo inicial de overflow y los hallazgos matemáticos
preservados; la ampliación no cambia hooks, concede confianza ni publica.
El ensayo real de alcance del hijo Claude usó previamente el snapshot
`0c0ed70f4b2cd31a32d05905d9fd456246d281ea2de21a185c23cdc9db871714`.
Después cambió la guía estática de selección, no el guard de alcance. Son dos
observaciones distintas y no se presentan como una única ejecución.

El recorrido real de Codex corresponde al bundle con SHA-256 de `bundle.json`
`cdab498632f9e4f019840ee27baf8fa2c0872fb523dcd794ecfcbd3b4798ccf1`.
Usó un app-server efímero; el padre heredó `gpt-6-astra` y esfuerzo `max`.
No hubo timeout ni aprobaciones inesperadas. Se observó el `threadId` del hijo,
pero no directamente su payload `session_id`, rol o persistencia; esos campos
no se infieren de la aceptación de las operaciones o del contrato padre.

El ensayo editorial nativo de Claude sobre el snapshot `cdab4986…` usó `--agent`
explícito, invocó `writter` mediante `Skill` y realizó dos `Read` del paquete.
Su texto abrió `NE-ONTO-01` y `NE-PROB-02`; las correcciones de instrucciones no
convierten ese primer resultado en un pase. El primer intento de repetición con
el bundle `1d649b6f77b16523f9a863428696e71527a339022530d9fa03334e1d74ef5fac`,
verificado localmente con 77 recursos, fue rechazado por revisión automática
antes de crear proceso por falta de autorización explícita de transmisión a
Anthropic. En ese intento no hubo modelo, estímulo enviado ni resultado; se
respetó el rechazo sin cambiar de vía.

El usuario autorizó entonces repetir el mismo estímulo. Ese ensayo autónomo,
anterior a la corrección guiada y con rol elegido explícitamente, completó el
proceso con el bundle `1d649b6f…` fijo: cuatro turnos, una invocación de `writter`
mediante `Skill` y un `Read`.
El éxito del proceso no fue aceptación del texto: persistió `NE-ONTO-01` y se
identificaron `NE-PROB-NECESSITY-01` —también registrado como
`NE-ERROR-MODEL-03`— y `NE-PROB-REPETITION-01`. Sus fallos no se sustituyen por
el resultado de la pasada posterior.

Un intento posterior de corrección con texto y hallazgos recibió un segundo
rechazo automático antes de crear proceso: la autorización inicial no cubría
ese nuevo envío a Anthropic. No hubo ejecución ni artefacto nuevo y tampoco se
cambió de vía. El usuario autorizó después expresamente esa corrección del mismo
ensayo con su texto y hallazgos. La llamada real completada en Claude Code 2.1.301, modelo heredado
`sonnet-5-5` y rol explícito mantuvo fijo ese bundle: un turno, cero herramientas,
lecturas o denegaciones, y tres hooks completados con éxito. Es una **revisión
dirigida con feedback**, no una generación ciega ni una prueba nueva de selección
automática. El artefacto íntegro tiene SHA-256
`2ffbd46ca500f63c027e454d15a296a114e93fac6e86e0ba256a7002cdd9a679`.

Verificadores independientes de los autores y descubridores confirmaron las
reparaciones de `NE-ONTO-01`, `NE-PROB-02`, `NE-PROB-NECESSITY-01` y
`NE-PROB-REPETITION-01`, sin nuevos errores materiales en ese texto.
`NE-ERROR-MODEL-03` identifica el mismo fallo que `NE-PROB-NECESSITY-01` y no se
cuenta como otro hallazgo. La revisión dirigida queda aceptada para ese artefacto;
se conservan el bloqueo y los fallos anteriores. No se atribuye una mejora causal
exclusiva a la última pauta editorial ni se afirma perfección general. Código
y hooks de ejecución no cambiaron en esta última pauta. La integración y
publicación se acreditan mediante el workflow, no por la aceptación del texto.

El probe distingue el binario Claude confiado de un CLI candidato. En el primero,
se deniegan HOME, Keychain y red exterior, y las escrituras se limitan al área
temporal del ensayo. El candidato añade un entorno limpio, cwd fijo y una
política de lectura estricta. No se atribuyen las restricciones adicionales del
candidato a la ejecución del binario confiado. Las pruebas focales del probe
comprueban esas fronteras, la lista de herramientas permitidas y los canarios.

La guía estática incluye diagnóstico de ingeniería sin edición y argumentos
matemáticos no triviales; condiciona el uso de las cuatro entradas a su
disponibilidad y a las instrucciones del receptor. Sus tests acreditan que no
consulta campos privados ni abre contratos. Los seis casos reales anteriores
miden por separado su seguimiento y conservan el caso en que no se cargó la skill.

La observación distingue inventario, instalación, catálogo, confianza, evento y
resultado. Un proceso nuevo no representa automáticamente un chat abierto. La
[matriz de aceptación](evaluation.md#aceptación-de-131) conserva esas obligaciones;
los resultados anteriores no constituyen una garantía universal del orquestador.

## Distribución dual 1.3 — 2026-10-28

Esta sección conserva la evidencia de 1.3.0 del 2026-10-28. El ensayo real de
subagentes de 1.3.1 figura arriba; no se atribuye retrospectivamente a este baseline.

El objetivo de esta distribución es instalar las mismas fuentes de investigación
y el mismo núcleo de evidencia en varios portátiles, con entradas nativas para
Codex y Claude Code. La versión del paquete, su integridad, lo cargado por un
cliente y la ejecución de hooks son evidencias distintas. Una equivalencia de
estructura no demuestra igualdad de resultados ni de conectores disponibles.

| Superficie | Evidencia y límite |
| --- | --- |
| Claude Code instalado | El CLI real 2.1.301 ejecutó los ensayos aislados. Es la referencia conservadora de esta integración; no acredita versiones anteriores ni otros portátiles. |
| Validación nativa del bundle | `claude plugin validate --strict --json` terminó con código 0, sin errores ni advertencias. Se observaron cuatro skills con namespace y ocho roles. |
| Plugin permanente en directorio de skills | En un home aislado con espacios, la primera instalación devolvió `installed` y la repetición `unchanged`; la verificación confirmó el recibo 1.3.0. El CLI listó `constellation@skills-dir` habilitado y, sin `--plugin-dir`, cargó las cuatro skills y los ocho roles. |
| Eventos nativos observados | El CLI despachó `SessionStart`, `UserPromptSubmit`, `PreToolUse` y `Stop`. La validación del schema y la ejecución efectiva se comprobaron por separado. |
| Rechazo y permiso de edición | Un `Write` fuera del alcance fue denegado y su archivo quedó ausente. Un `Write` declarado fue permitido y creó el archivo. La carga permanente también rechazó la edición no declarada. |
| Cierre incompleto portable | Un contrato pendiente produjo exactamente dos continuaciones Stop y después `INCOMPLETE`, sin aprobar su cierre. Esto no demuestra corrección de una conclusión científica. |
| Fallo operativo de un hook | Un hook que terminó con código 17 quedó bloqueado mediante la política nativa de fallo. La protección de Stop y SubagentStop sigue siendo distinta. |
| Eventos nativos de subagentes | `SubagentStart` y `SubagentStop` no quedaron verificados en el CLI. La carga de roles y las 17 pruebas enfocadas del adaptador no sustituyen ese despacho. |
| Otro portátil | El ZIP y su hash permiten repetir la instalación. No se ha establecido una prueba en hardware distinto por el hecho de usar dos directorios temporales. |
| Plataformas | Python 3.11+ y bloqueos POSIX. macOS/Linux son el ámbito de implementación; WSL requiere validación en ese entorno. Windows nativo queda fuera de la cobertura. |
| OmarOS | Sus cuatro recursos derivados siguen fijados en 1.2.0. El actualizador receptor no admite bundles 1.3.0 sin una migración explícita. |

Los ensayos nativos utilizaron una respuesta simulada por HTTP exclusivamente
local y una credencial sintética. La red exterior, el HOME real y Keychain
quedaron bloqueados. No hubo llamadas a un modelo remoto. Se comprobó la
integración del cliente y el control de las operaciones, no su capacidad de
investigación ni la calidad de sus respuestas.

El intento de ejercer la herramienta Agent recibió un rechazo de la revisión
automática de aprobación: el clasificador auto-mode no pudo evaluar la acción
con la respuesta simulada local. No se cambiaron permisos ni se reintentó por
otro modo. Por ello aquel ensayo 1.3.0 no estableció la ejecución nativa de los dos eventos
de subagente, aunque sus roles estuvieran cargados y el adaptador tuviera pruebas.

La aceptación de portabilidad también exige construcción repetida, destinos
aislados en rutas distintas, actualización, preservación de configuración ajena,
alteración de archivos y una interrupción de la sustitución. Las comprobaciones
del motor y del paquete se registran aparte del despacho nativo. Las pruebas de
investigación añaden evidencia faltante, agentes fallidos, fuentes cambiadas y
revisión independiente. Ninguna certifica por sí sola la verdad de una
demostración o la validez de una conclusión empírica.

La semántica documentada de `onFailure: "block"` requiere Claude 2.1.295 o
posterior, pero no protege Stop ni SubagentStop. La implementación debe conservar
la aceptación en comandos deterministas. Los settings, políticas administradas
y autorizaciones personales de cada cliente pueden alterar su carga efectiva.
La configuración local no demuestra controles de entrenamiento o retención de
cuenta. No se copian sus datos al bundle.

El [release oficial 2.1.312](https://github.com/anthropics/claude-code/releases/tag/v2.1.312)
se publicó el 2026-10-27; el binario local observado sigue en 2.1.301. Este encargo
no lo actualiza. Las publicaciones y la documentación actuales pueden describir
capacidades posteriores a ese binario. En particular, la
[recuperación de workflows dinámicos](https://code.claude.com/docs/en/workflows#which-agents-run-again)
distingue el comportamiento anterior a 2.1.305; no se atribuyen sus garantías
nuevas a 2.1.301.

La [comparación de diseños publicados](architecture.md#correspondencia-con-diseños-publicados-por-anthropic)
relaciona el método de Constellation con artículos oficiales sobre composición,
investigación multiagente, contexto, skills, recuperación y evaluación. Es una
comparación de mecanismos y obligaciones, no una prueba de sus resultados
experimentales en nuestro sistema. Las evaluaciones nativas de plugins no se
ejecutan como una comprobación inocua: requieren modelos y pueden publicar un
informe. Un ensayo autorizado con datos locales debe conservar el informe local
mediante `--no-publish` y límites explícitos.

Referencias primarias de esta integración:
[carga permanente de plugins Claude](https://code.claude.com/docs/en/plugins/create#make-a-plugin-load-in-every-session),
[schema y componentes](https://code.claude.com/docs/en/plugins/manifest-reference),
[fallos de hooks](https://code.claude.com/docs/en/hooks#block-the-action-when-a-hook-fails)
y [agentes nativos](https://code.claude.com/docs/en/sub-agents).


## Condiciones vigentes de compatibilidad

Las capacidades pertenecen a la superficie y versión observadas. Modelo,
esfuerzo, contexto y permisos se heredan; los máximos de agentes no son un
objetivo de consumo. La telemetría no observada permanece desconocida. Los
clientes deben recargar una sesión cuando lo requiera una actualización; el
instalador no concede confianza ni modifica sus hashes para obtener aprobación.
Los pasos de actualización y recuperación están en la
[guía de instalación](migrations.md#instalar-y-actualizar).

Un estado portable aislado necesita la misma `CONSTELLATION_STATE_DIR` heredada
por CLI y hooks; `--state-dir` afecta sólo a esa invocación. Debe ser una ruta
absoluta. El ajuste no cambia permisos ni la política personal; su contrato está
en el [protocolo](../references/protocol.md#portable-api). Leer un estado por CLI
no acredita que los hooks hayan usado ese mismo estado.

Las matrices y métricas antiguas de 1.0, 1.1 y 1.2 se conservan sólo en las fuentes,
en `ecosystem/docs/history/constellation-1.1.md`, junto a su contexto de evaluación.
No forman parte del bundle instalable ni describen las capacidades actuales.
