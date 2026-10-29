# Evaluación del ecosistema

## Qué se evalúa

La evaluación relaciona cada requisito con una entrada controlada, una conducta
esperada y una observación independiente. Se distinguen tres objetos: el motor
que valida contratos, la integración que ejecuta eventos en un cliente concreto
y el agente que decide qué capacidades usar y produce el resultado. El éxito de
uno no certifica los otros. Los recuentos de tests, roles o skills no son una
medida de fiabilidad semántica.

El conjunto de casos debe incluir tareas simples, combinaciones justificadas de
capacidades, ausencia de herramientas y fallos. Para selección se declaran los
conjuntos de capacidades requeridas, opcionales y prohibidas; una alternativa
propuesta se registra aparte de lo realmente seleccionado y ejecutado. Las
variantes deben cambiar la necesidad conceptual, no sólo palabras clave. Un
caso positivo necesita un control negativo que revele activación innecesaria,
aceptación de evidencia ausente o dependencia no comprobada.

La evidencia distingue el catálogo expuesto, las instrucciones consultadas,
la herramienta o agente ejecutados y el artefacto comprobado. Los resultados
incompletos y los rechazos conservan su condición; un éxito posterior no borra
un intento fallido. Un catálogo o una declaración del propio agente no bastan
para certificar el uso. La observación publica únicamente evidencia operativa
curada, sin prompts, transcripciones, credenciales ni datos privados.

## Aceptación de 1.3.1

Esta matriz especifica obligaciones del candidato; su presencia no significa que
los ensayos hayan terminado. La [compatibilidad observada](compatibility.md)
registra el estado y los límites de ejecución de la entrega.

| Obligación | Evidencia necesaria | Rechazo que debe comprobarse |
| --- | --- | --- |
| Fuentes organizadas | Una fuente por manifiesto/rol, enlaces válidos, historial separado y comandos públicos conservados. | Referencia rota, archivo no permitido o dependencia de una ruta retirada. |
| Bundle completo y módulos parciales | Construcción reproducible, inventario exacto y pruebas desde el paquete sin el checkout fuente. | Recurso ausente, extra, alterado, enlazado o módulo no disponible. |
| Actualización 1.3.0 → 1.3.1 | Ambos instaladores verifican la versión anterior y la nueva por separado, conservando datos y ajustes. | Inventario mezclado, cambio ajeno y fallo durante sustitución, con recuperación comprobada. |
| Integración Codex y Claude | Cliente y versión identificados; catálogo, confianza y eventos realmente observados se registran por separado. | Un estado desconocido no se convierte en permiso ni éxito. |
| Alcance y cierre | Edición permitida dentro del plan, denegación fuera del alcance y contrato pendiente que permanece incompleto. | Ausencia/fallo de evidencia, identidad equivocada o cierre obsoleto. |
| Subagentes | Lanzamiento nativo, identidad, resultado y eventos aplicables observados en el cliente ensayado. | Ausencia de resultado, fallo o rechazo de aprobación sin atribuir un trabajo ejecutado. |
| Guía estática sin contrato | El contexto nativo recibe el mismo recordatorio sin consultar prompt/transcripción ni crear estado de tarea. | Creación implícita de contrato, clasificación del contenido privado o permiso añadido. |
| Selección de capacidades | Casos acotados con necesidad, elección, instrucciones leídas y resultado contrastados, incluidos diagnóstico sin edición y argumentos no triviales. | Selección por palabra irrelevante, capacidad ausente presentada como usada o delegación sin utilidad. |
| Revisión y publicación | Autores reales, cobertura independiente vigente y SHA remoto verificado por dueño Git. | Autorrevisión, hallazgo abierto, cambio posterior o destino distinto. |

La instalación puede probarse sin llamadas a modelos. Una evaluación semántica
requiere agentes reales y criterios propios para fuentes, argumentos y calidad;
una respuesta HTTP simulada no sustituye ese ensayo. Las comparaciones entre
clientes o configuraciones fijan casos, versiones, presupuesto, intentos y
métricas antes de interpretar resultados. Más delegación puede aumentar coste
y latencia: no se infiere una mejora del número de agentes. Un recordatorio
estático puede orientar la selección, pero su presencia y sus tests de privacidad
no prueban que un modelo lo siga. Un cambio de guía requiere nuevos casos reales;
una muestra pequeña no establece una garantía universal ni causalidad.

## Resultados acotados del 2026-10-29

La batería anterior a la última corrección del oráculo registró 353 pruebas
directas satisfactorias. Omitió únicamente la ejecución recursiva de cinco
exportaciones, ya superada en la suite integrada anterior de 349 pruebas. Esa
batería no se presenta como una reevaluación íntegra tras el delta posterior. Cada reparación requiere verificación independiente;
ese juicio no sustituye la resolución formal del hallazgo contra el token que
incluya la versión final revisada. Los hallazgos nuevos o pendientes conservan
su estado. La publicación pertenece al workflow.

La última corrección del probe rechaza cualquier herramienta ajena a una lista
permitida explícita y pasó cinco pruebas focales. Los cinco casos nativos con
respuestas simuladas documentan el ensayo anterior; no se confunden con la
validación de ese delta. Sus políticas separan
el binario Claude confiado —HOME, Keychain y red exterior denegados; escrituras
temporales— del CLI candidato, que añade entorno limpio, cwd fijo y lectura
estricta. La prueba registra cada frontera; no generaliza la más estricta a todos
los procesos ni interpreta una respuesta simulada como evaluación de un modelo.

Un ensayo real portable añadió un único hijo Claude: la escritura declarada
produjo los bytes previstos y la no declarada fue denegada sin crear el archivo.
Las operaciones conservaron la sesión padre; los eventos de inicio y fin y el
estado final del agente fueron observados. El contrato permaneció `active`, como
correspondía a sus obligaciones pendientes. Este resultado prueba ese recorrido
de alcance y observación; no prueba publicación Git, delegación autónoma ni cierre.

La selección semántica se midió con seis casos sobre un mismo candidato, cuya
identidad y relación con los demás ensayos están en la
[matriz de compatibilidad](compatibility.md#aceptación-de-131):

| Grupo | Uso observado | Resultado y límite |
| --- | --- | --- |
| Ingeniería, matemática e investigación cuantitativa | Tres de tres invocaron la skill correspondiente. | Evidencia de esos casos y del candidato fijado; no una tasa general de fiabilidad. |
| Escritura sustantiva | No invocó la skill. | Produjo 179 palabras y una respuesta completa; la desviación de método permanece. |
| Dos controles negativos | Ninguno utilizó herramientas. | Cumplieron el criterio de proporcionalidad de esos controles. |

Las seis respuestas pasaron sus comprobaciones de completitud y estructura.
Esos oráculos no demuestran verdad matemática, exactitud factual exhaustiva ni
calidad editorial. No se suma el éxito de escritura en una variante anterior
para construir un resultado artificial de cuatro sobre cuatro. Los cambios de
guía, cliente o versión producen candidatos distintos y conservan sus resultados.

El usuario aprobó los hooks de Codex y la consulta nativa confirmó los cinco
`trusted` y habilitados. En CLI 0.165.0, un recorrido real padre/hijo permitió
el `apply_patch` declarado con bytes exactos y rechazó el no declarado por
`preToolUse`, dejando ausente su archivo. Se observaron inicio y fin del hijo
y `observed_agents` final `stop`, con un único contrato registrado del padre que
permaneció `active` y `closed=false`. El snapshot y los límites de observación
figuran en la [matriz de compatibilidad](compatibility.md#aceptación-de-131).
Se observó `threadId`, no un payload directo de `session_id`, rol o persistencia
del hijo. Este recorrido no demuestra selección semántica universal ni cierre.

### Ensayos dirigidos de las instrucciones

El refuerzo posterior de las instrucciones se comprobó mediante encargos
dirigidos. Estos ensayos evalúan su aplicación, no si un cliente las selecciona
automáticamente; el resultado nativo 3/4 del snapshot `102355…` es anterior y no
se reutiliza como evaluación de estas instrucciones.

| Responsabilidad | Evidencia dirigida y límite |
| --- | --- |
| Escritura | Una muestra extensa sobre funciones, configuraciones y sensores y un control de dos frases fueron revisados sin hallazgos. Acredita esos textos, no toda explicación futura. |
| Ingeniería | Una abstracción pequeña se probó con cantidades y conjuntos, una sola pasada, orden, `None` y aliasing. La implementación directa falló inicialmente por overflow con `1e308`; se corrigió con acumulación racional y conversión final. Código y docstring fueron revisados, con pruebas y un oráculo independiente. El fallo inicial se conserva como fallo. |
| Investigación y revisión | Se detectaron agotamiento y overflow, se ignoró una instrucción incrustada en la entrada y se reprodujeron 28 invocaciones. Son casos observados, no inmunidad universal a instrucciones externas. |
| Auditoría matemática | Detectó tres ambigüedades preexistentes sobre Riesz, el campo y el mapa; el autor las corrigió y un verificador confirmó la corrección matemática. Sus tres hallazgos quedaron resueltos tras la verificación independiente. |

El ensayo editorial nativo inicial sobre `cdab4986…`, con agente elegido mediante
`--agent`, una invocación de `writter` y dos lecturas del paquete, produjo
`NE-ONTO-01` y `NE-PROB-02`. La corrección de instrucciones y los intentos
posteriores se conservan como tales; no hacen pasar la primera respuesta.
El intento preparado con `1d649b6f…` fue rechazado antes de crear proceso por
falta de autorización explícita para transmitir a Anthropic el estímulo y las
instrucciones y referencias del paquete. No hubo modelo, transmisión ni resultado
en ese intento, y no se cambió de vía para eludir el rechazo.

La autorización siguiente permitió repetir el mismo estímulo. La repetición
autónoma, con rol elegido explícitamente y bundle `1d649b6f…` fijo, completó
cuatro turnos, invocó `writter` mediante `Skill` y realizó un `Read`. El proceso terminó con éxito, pero
`NE-ONTO-01` persistió y se detectaron `NE-PROB-NECESSITY-01`
(`NE-ERROR-MODEL-03`, mismo fallo) y `NE-PROB-REPETITION-01`. No fue un pase
editorial y se conserva separado de la corrección guiada.

El intento de enviar después el texto con los hallazgos para corregirlo recibió
un segundo rechazo automático antes de crear proceso: el consentimiento inicial
no cubría ese nuevo envío a Anthropic. No hubo ejecución ni artefacto nuevo y se
respetó la frontera sin cambiar de vía. Tras el segundo consentimiento expreso
del usuario para esa corrección con feedback, se completó una llamada real con Claude Code 2.1.301, modelo heredado
`sonnet-5-5`, rol explícito y el bundle `1d649b6f…` fijo. La pasada registró un
turno, cero herramientas, lecturas o denegaciones y tres hooks satisfactorios.
El resultado íntegro es
`2ffbd46ca500f63c027e454d15a296a114e93fac6e86e0ba256a7002cdd9a679`.
La [matriz de compatibilidad](compatibility.md#aceptación-de-131) fija el hash
completo del bundle. Esta es una **revisión dirigida con feedback**, no generación
ciega ni selección autónoma de método; los seis casos anteriores siguen separados.

| Hallazgo del texto | Verificación independiente del resultado corregido |
| --- | --- |
| `NE-ONTO-01` | Corregida la distinción entre función y punto, y entre tiempo y configuración. |
| `NE-PROB-02` | Corregidas la distinción entre estimador aleatorio y valor observado y las condiciones declaradas de la afirmación. |
| `NE-PROB-NECESSITY-01` / `NE-ERROR-MODEL-03` | Un único fallo, corregido: se admite la cota determinista y no se presentan condiciones suficientes como necesarias. |
| `NE-PROB-REPETITION-01` | Corregida la afirmación sobre repetición con condiciones suficientes explícitas de independencia, distribución común e integrabilidad. |

Los verificadores, distintos de autores y descubridores, no encontraron nuevos
errores materiales en el artefacto íntegro. La aceptación cubre esa revisión
dirigida; no garantiza respuestas futuras ni borra intentos fallidos. La pauta
actual de revisar apertura, desarrollo, conclusión y cuantificadores forma parte
de las instrucciones, pero no se aisló su efecto causal. Esta última pauta no
cambió código ni hooks. La aprobación y ejecución reales de Codex permanecen
acreditadas; la integración y publicación se registran por el workflow y no se
infieren de esta revisión del texto.

La ampliación conserva los hooks y los resultados previos; no suma el fallo
numérico como pase ni sustituye por estos ensayos la desviación de selección en
escritura. La navegación de las guías comunes debe seguir funcionando en cada
paquete parcial, sin exigir enlaces a una skill o referencia opcional ausente.

## Comprobaciones reproducibles

Desde el checkout fuente, las suites usan repositorios, remotos y hogares
temporales. El coordinador registra los comandos pertinentes en su workflow:

```sh
python3 -B .codex/ecosystem/validate.py --root .codex
python3 -B -m unittest discover -s .codex/tests -q
python3 -B -m unittest discover -s .codex/ecosystem/tests -q
```

La distribución se comprueba además desde su propio directorio, sin recuperar
fuentes del hub. Los diagnósticos nativos y ensayos con modelos se registran por
separado: no se deducen de la salida de esas suites. Cambiar código, contenido,
alcance o política obliga a renovar la evidencia afectada antes de publicar.

El diseño de evaluación sigue la distinción entre herramientas, handoffs y
resultado de [Agent evals de OpenAI](https://developers.openai.com/api/docs/guides/agent-evals),
y los casos positivos, negativos y entornos controlados descritos en
[Demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents).
Son criterios públicos para diseñar ensayos, no certificaciones del paquete.

## Registro histórico

Los resultados JSON se conservan íntegros, sólo en las fuentes, en
`ecosystem/evals/results/2026-10-18.json`. El informe
`ecosystem/docs/history/constellation-1.1.md` reúne las evaluaciones anteriores;
`ecosystem/docs/history/omaros-1.2.md` conserva la entrega del runtime al receptor.
Sus rutas, métricas y versiones describen aquellos ensayos, no el árbol actual.
No se distribuyen como dependencias del runtime ni sustituyen las pruebas de 1.3.1.

El arnés adaptativo y su informe de trabajo local fueron excluidos de la entrega
anterior por pertenecer a una evaluación independiente pendiente de publicación.
Esta reorganización no los adopta, borra ni convierte en una serie ejecutada.
