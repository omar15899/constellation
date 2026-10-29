# Constellation 1.1: consolidación y verificación

Informe histórico del 2026-10-18, conservado como antecedente de publicación.
Sus versiones, métricas y estados corresponden a aquella entrega; no acreditan
el funcionamiento de una instalación actual. La guía mantenida está en el
[README del paquete](../../README.md).

Fecha: 2026-10-18. El encargo «Constellation 2.0» se implementa como actualización
incremental 1.1. Codex conserva la ejecución nativa; Constellation concentra
coordinación, evidencia, revisión y publicación. Aprendizaje personalizable y
progreso persistente utilizan las capacidades y los almacenes existentes.
Este informe fija implementación y pruebas. Los workflows y el diario de OmarOS
conservan las revisiones, publicaciones y siguientes hitos del cierre.

## Auditoría y responsabilidades

El inventario contiene 21 registros en GitHub: hub, 19 hijos nativos y ruflo
externo. OmarOS es otro dueño Git. Al iniciar había un plugin 1.0 y una migración
1.1 sin publicar. Se continuó ese trabajo autorizado, preservando cambios e
índices ajenos. Conversaciones, credenciales y logs privados no son entregables.

| Responsabilidad | Autoridad |
| --- | --- |
| Modelos, herramientas, agentes, sesiones, permisos y descubrimiento | Codex y las capacidades expuestas por cada cliente |
| Coordinación, reparto, revisión y publicación Git | `.codex/ecosystem/runtime/`, con adaptadores pequeños |
| Selección y composición de skills | Modelo y metadatos nativos, sin clasificador paralelo |
| Evidencia matemática/editorial persistente | Núcleo portable cuando el objetivo requiere esas garantías |
| Dominio, datos y pruebas | Cada proyecto; adaptador especializado de OmarOS |
| Personalización y continuidad | Perfil local privado; estado operativo existente y diario curado |

Los cinco motores del hub tienen una implementación compartida distribuible.
OmarOS consume recursos fijados por hash y conserva privacidad, metadatos,
renombrados, delegados y publicación propia. Sus copias vendorizadas son
artefactos derivados. Claude y sus validadores utilizados permanecen; ruflo no
se modificó. No se introdujo otro runtime de agentes ni base de datos.

Se retiraron 19 TOML que repetían el límite 64 y el TOML del hub que imponía
contexto 1.000.000/900.000. `config/read` resolvió 64 en cada hijo; no se probó
saturación. Los 19 AGENTS pasan de 49.655 a 37.262 bytes conservando sus prefijos
de dominio; 18 PROJECT corrigen referencias. Se eliminaron seis perfiles
heredados, conservando ocho especializados. Los marcadores contra proyección
Claude siguen teniendo consumidor. Las entradas de las tres skills bajan de
11.692 bytes en la migración recibida a 9.355; HEAD tenía 9.421. Sus descripciones
no cambiaron; las referencias extensas se consultan por necesidad.

## Comportamiento y garantías

Investigación, aprendizaje e ingeniería se componen por intención y prioridades
explícitas. Una explicación breve no abre un contrato; una corrección local
pequeña usa comprobación enfocada. Investigación distingue hipótesis, pruebas,
observaciones y aproximaciones. Agentes y hashes no demuestran teoremas,
convergencia ni validez económica.

La revisión mantiene Quick=1, Standard=3 y Deep=3 de corrección más 2 de seguridad,
por archivo y foco, con tres rondas máximas. Código acotado de bajo riesgo puede
usar Quick con justificación anterior a la primera ronda cuando la política lo
permita. Queda ligada al snapshot; cambios la invalidan. No reduce Deep,
mínimos retenidos ni restricciones receptoras.

Se corrigieron registros anidados que desactivaban revisión, rebajas indebidas
de políticas, mínimos receptores ignorados, atribución incorrecta de commits
recibidos al sincronizar y discrepancias entre constructor y validador. OmarOS
reparó actualización de locks, cierre obsoleto al cambiar destino, escrituras
con sincronización bloqueada y reintentos de checkpoints. Su CI incorpora los
dos JSON canónicos que necesitan las pruebas del receptor. Las reparaciones
relevantes tienen regresiones y verificación independiente.

El plugin 1.1 está instalado. El inventario final contiene 57 recursos; SHA-256
de `bundle.json`: `9bf1541317829e0294e3a3fd992d37339d9694f9c6bcdbfe85a9b73dfab8ce78`.
Se verificaron tres exclusiones de fuentes sin nuevas escrituras, configuración
global intacta y cinco hooks nativos habilitados y confiados. Los hooks del hub
se retiraron. El plugin observa contratos activos: no inicia tareas, no hace
fetch por prompt ni publica. El guard de patches no intercepta cualquier
escritura shell/MCP; los commits manuales fuera del workflow no adquieren sus
garantías de revisión.

La sesión abierta conservó una ruta de `SubagentStop` 1.0 retirada durante la
actualización y produjo `Errno 2`. Procesos nuevos ejecutaron correctamente los
hooks 1.1. Abre una sesión nueva tras actualizar; no se reconstruyó la caché
antigua ni se alteró confianza para ocultar esta limitación del cliente.

Se conserva acceso completo/aprobación `never` previamente autorizado. No se
cambiaron permisos, confianza, modelo predeterminado, Memories, feedback ni
telemetría. La configuración local no acredita controles de cuenta.

La primera CI remota detectó una matriz antigua Python 3.9 y la ausencia de
configuración personal en el runner. La matriz del flujo Git pasa a 3.11/3.13;
una configuración temporal explícita permite comprobar herencia y coherencia
sin depender del equipo del usuario. Su nombre identifica que es una fixture,
no una prueba de ejecución de 64 agentes. La reproducción del fallo y los
controles positivos y negativos se verificaron independientemente. Los cuatro
jobs portables originales pasaron en Linux/macOS con Python 3.11/3.13.

## Aprendizaje, investigación y continuidad

`~/.codex/learning/PROFILE.md` es provisional, persistente, editable y privado.
La enseñanza distingue feedback reutilizable intencional de correcciones
puntuales, conserva procedencia y alcance, admite preferencias contextuales y
permite retirarlas. Los ejemplos futuros pueden refinarla; no se afirma un
perfil definitivo ni reentrenamiento. El perfil no forma parte de skills genéricas.

Ocho casos sintéticos pasaron 23 comprobaciones: feedback positivo/negativo,
prioridad actual, contexto, razonamiento propio, eliminación y recuperación en
agentes nuevos. Se observó adaptación del orden expositivo, sin demostrar
causalidad exclusiva o eficacia pedagógica. La revisión independiente contrastó
los artefactos y sus hashes. Las fixtures no se convirtieron en preferencias reales.

Dos procesos nativos nuevos, Astra Ultra y Sol 6.1 Ultra, recuperaron el mismo
perfil real sin modificar los archivos vigilados. Las ventanas efectivas fueron
258.400 y 475.000 tokens. La revisión detectó en Sol un salto de diferenciabilidad
puntual a campo global sin hipótesis adicional; Astra no presentó ese hallazgo.
Portabilidad y lectura del perfil no garantizan corrección matemática.

Los checkpoints guardan objetivos, estado, decisiones, hallazgos, evidencia,
pendientes y siguientes pasos en JSON Git o SQLite existentes. Sobreviven a
replanificaciones y permiten recuperar trabajo sin OmarOS. UUID, identidad de
hitos y revisiones evitan duplicaciones y actualizaciones obsoletas.

La sincronización exige raíz canónica y alias exactos autorizados en
`~/.codex/progress-journal.json`, destino fijado y checkpoint personal. Registrar
proyectos no autoriza exportaciones; fuentes desconocidas o restringidas quedan
excluidas. OmarOS recibe síntesis y referencias, preserva texto manual y recupera
escrituras interrumpidas. `RECEIVED_LOCAL` no significa publicación remota.
El receptor mantiene `17_Dashboards/Constellation.md` y una nota por tarea;
perfiles personales y logs no se copian allí. El agente selecciona los hitos
relevantes, sin un daemon adicional. Conocimiento científico y preferencias
pedagógicas siguen siendo contenidos distintos.

La guía cuantitativa reutiliza los laboratorios existentes. EODHD se investigó
con fuentes oficiales y 62 pruebas offline de adaptadores. No se verificaron
derechos de cuenta, cobertura real ni datos point-in-time; no se hicieron
llamadas pagadas ni órdenes. Un backtest rentable todavía exige causalidad,
costes, control de selección múltiple, OOS y justificación económica.

## Evidencia reproducible

Baseline Git: `86ef3bdb1b5551b50d7f48dac8a7a9a6002576f8`; Codex CLI 0.163.0.
Con Python 3.11 pasaron **281 pruebas del flujo Git** en 357,649 s y **239 del
paquete** en 351,191 s. Estas últimas incluyen construir y ejecutar las cuatro
distribuciones: full/coding/mathematics/writter, 239 casos cada una con 1/10/9/8
omisiones explícitas. Inventarios y bundles permanecieron intactos. No son casos
únicos adicionales. También pasan 30 pruebas de seguridad de proyección.

La matriz encontró tres fixtures que suponían coding en distribuciones que no
lo incluían. Se corrigieron tres líneas de pruebas y se repitió la matriz entera.
El runtime y las instrucciones del ensayo nativo permanecieron byte a byte
idénticos en el bundle final; su única diferencia era `test_core.py`.

| Ensayo | Resultado y alcance |
| --- | --- |
| Corrección Python, plugin 1.0 | Artefacto correcto, 10/10 oracle; 180,047 s sin cierre, 3 subagentes y 26 comandos |
| Misma tarea, plugin 1.1 | Completada en 52,814 s; 0 subagentes, 6 comandos, 10/10 oracle y 2 pruebas propias |
| Verificación independiente Python | 6.560 contrastes por artefacto; mismo harness/modelo, caché distinta |
| Investigación numérica | Oracle exhaustivo, 19 pruebas, 16 mallas, tres revisiones y verificación de reparaciones; no prueba general de convergencia |
| Varios repositorios | Ensayo temporal: proveedor publicado, rechazo del consumidor y reintento sin commit extra; índices parcialmente staged preservados |
| Recuperación y OmarOS | Interrupciones, historia monotónica, autorización, destino y recibos: 29 pruebas de progreso y 57 del loader; cierre integrado registrado en su propio workflow |
| Proyecto mínimo | Descubrimiento sin scaffolding y Git standalone sin leer fuentes del hub |
| Selección | Diez casos con catálogos iguales: nueve inequívocos pertinentes; alternativa ausente ambigua, conservada como tal |
| Integraciones | Lectura web oficial comprobada; ningún navegador gráfico disponible en las superficies ensayadas |

El ensayo candidato observó `UserPromptSubmit`, `PreToolUse` y `Stop` nativos
completados, con 95/95/96 ms. La duración de tarea incluye arranque/cierre del
app-server, no es latencia pura del modelo. La comparación muestra menor
sobrecarga en esa muestra, sin estimar fiabilidad general ni ventaja causal de
velocidad, tokens o calidad. Los fallos y resultados históricos se conservan.

Reproducción principal desde la raíz:

```sh
python3 -B -m unittest discover -s .codex/tests -q
python3 -B -m unittest discover -s .codex/ecosystem/tests -q
python3 -B .codex/ecosystem/validate.py
```

La evidencia experimental reducida permanece local en el directorio Git privado,
bajo `constellation/evidence/01a14c66-0820-7403-aec3-cdb9448c9619/`; no incluye
transcripciones. La evaluación versionada distingue casos ejecutados de futuros
escenarios de regresión.

## Operación y cierre

Describe el objetivo; el catálogo de la sesión orienta las capacidades. Un
proyecto nuevo aporta contexto y validación propios; necesita registro sólo
para coordinación entre repositorios. No copies motores ni perfiles. Consulta
[README](../../README.md), [PROGRESS](../progress.md) y
[QUANT_RESEARCH](../../../QUANT_RESEARCH.md).

Al reanudar, lee el contrato y `progress-show`; no reinicies rondas para ocultar
fallos. Los workflows conservan evidencia vigente, destino congelado y cierre
remoto por dueño Git; el diario muestra hitos y pendientes. Este texto no
certifica publicación por anticipado. Tras actualizar Codex, comprueba esquema,
descubrimiento, hooks y casos reales; retira mecanismos propios cuando una
capacidad nativa suficiente los reemplace.


## Registro de evaluación de las versiones anteriores

Se conserva aquí el contenido histórico que antes acompañaba al runtime en
`ecosystem/EVALUATION.md`. Los ensayos describen sus propias versiones y
condiciones; las rutas históricas del resultado JSON permanecen intactas.
La metodología actual se mantiene en `ecosystem/docs/evaluation.md`.

### Diseño histórico de evaluación 1.2


La implementación elimina el tope universal de tres rondas, mantiene mínimos e
historial e incorpora continuidad justificada y un plazo real de revisión. El
hook estable verifica la instalación bajo el lock compartido con el instalador.
Estas propiedades se comprueban con controles deterministas; no constituyen
evidencia de mayor calidad, menor coste ni menor latencia de agentes.

El arnés nativo y su informe descritos en esta sección pertenecen a una
evaluación local independiente, pendiente de publicación; no se incluyen en
la entrega del runtime 1.2 ni en su bundle. Los comandos siguientes requieren
disponer además de esas fuentes de evaluación. Su descripción no acredita
una serie ejecutada ni constituye un requisito de instalación del runtime.

El harness nativo `evals/native_benchmark.py` separa prerregistro, preflight y
serie. El plan congela escenarios, controles y 25 slots: 18 de la comparación
principal, cuatro de capacidad y tres de recuperación. La comparación distingue
A1 (un agente, plugin desactivado), B4 (delegación nativa, plugin desactivado) y
C4 (Constellation activo), con controles B/C de capacidad 2. Son capacidades
totales del ensayo: B4/C4 permiten coordinador y hasta tres subagentes; los
controles de dos permiten uno, y A1 desactiva delegación. No son un objetivo de
consumo. El modelo y esfuerzo
del producto se siguen heredando; la configuración efectiva del ensayo debe
quedar registrada antes de interpretar sus resultados.

```sh
python3 .codex/ecosystem/evals/native_benchmark.py plan
python3 .codex/ecosystem/evals/native_benchmark.py preflight --output RUTA_NUEVA
python3 .codex/ecosystem/evals/native_benchmark.py run \
  --plan-sha256 SHA_DEL_PLAN --output OTRA_RUTA_NUEVA
```

El canario no sustituye la serie. `run` exige el hash del plan prerregistrado;
cambiar el diseño exige otro prerregistro, sin ocultar intentos anteriores.
La salida conserva metadata por intento y `attempts.jsonl` con métricas y estados
reducidos. No publica prompts, conversaciones, texto de respuestas, argumentos
de herramientas ni sus salidas. La cobertura de observación se declara: un
contador desconocido no se transforma en cero y un fallo de observación no se
confunde con fallo del agente. Se conservan intentos fallidos y resultados
incompletos; no se selecciona sólo el mejor intento.

En este snapshot documental la serie nativa 1.2 sigue pendiente. Los resultados
de integración y despliegue se registran fuera del bundle medido en
`.codex/ADAPTIVE_ORCHESTRATION_REPORT.md`, con el plan, versiones y límites reales.
Los resultados 1.1 y 1.0 siguientes se conservan como historia y no se reutilizan
como mediciones del candidato 1.2.

### Migración histórica 1.1 — controles y experimentos separados

El bloque `migration_1_1` de `ecosystem/evals/results/2026-10-18.json` identifica las observaciones del
18 de octubre de 2026. Conserva íntegra la evaluación histórica 1.0. El baseline
Git es `86ef3bdb1b5551b50d7f48dac8a7a9a6002576f8`; al comenzar, la distribución
instalada era 1.0.0 y existía una migración 1.1 sin publicar. No se atribuyen al
candidato los resultados obtenidos con instrucciones instaladas 1.0.

Las descripciones de las tres skills no cambian entre baseline y candidato.
Dos agentes independientes recibieron diez casos sintéticos y catálogos idénticos:
la selección fue pertinente en los nueve casos inequívocos. Ante una skill
ausente, ambos informaron la ausencia; uno propuso una alternativa y otro la
incluyó en su selección. La rúbrica separa ahora `selected_now` de
`proposed_fallback`, y conjuntos requeridos, opcionales y prohibidos. Esta muestra
es una regresión descriptiva, no una estimación de fiabilidad general.

Una tarea Python real con las instrucciones instaladas 1.0 corrigió una función
sobre iterables: 18 comprobaciones del autor y 6.560 contrastes independientes
pasaron. Leyó 21.062 bytes de instrucciones y necesitó una aclaración sobre un
contrato innecesario. Una definición matemática breve se resolvió sin skills,
herramientas ni agentes adicionales. Estos resultados motivaron una carga
condicional de referencias; el ensayo posterior al despliegue debe comprobar su
efecto, sin inferirlo del texto cambiado.

El baseline nativo usó app-server y un thread efímero: `UserPromptSubmit` y `Stop`
del plugin 1.0 se ejecutaron y terminaron correctamente (96 y 89 ms). Una consulta
CPU terminó en 4,882 s, con 23.004 tokens de entrada y 28 de salida, sin herramientas
ni subagentes. Una ejecución separada con `codex exec --json` no expuso eventos de
hooks; su ausencia en ese canal no prueba ausencia de ejecución. Ningún protocolo
o conversación se conserva en los artefactos de evaluación.

El acceso gráfico también se probó: el subagente recibió `Browser is not available:
iab`; el coordinador recibió `No browser is available`. La consulta web de páginas
públicas funcionó. Se acredita lectura web y diagnóstico de indisponibilidad,
no control de aplicaciones de macOS.

### Extensión: aprendizaje, modelos y continuidad

Se ejecutaron dos pruebas distintas de personalización. La evaluación sintética
usó ocho casos y 23 comprobaciones de artefactos, todas satisfactorias. Verificó
feedback positivo y negativo intencional, conservación de preferencias previas,
alcance contextual, prioridad de la petición actual, distinción entre razonamiento
autodeclarado y objetivo de aprendizaje, eliminación y recuperación posterior.
Un comando incrustado en el ejemplo no produjo su marcador ni se almacenó como preferencia.
Los agentes nuevos no heredaron historial; la prueba permaneció dentro de la
misma sesión de colaboración y empleó exclusivamente perfiles ficticios.

La explicación inicial comenzó con un ejemplo concreto y la posterior con los
objetos generales, según las preferencias sintéticas. Una revisión independiente
no encontró errores matemáticos materiales en ese par. También cambiaron otros
detalles de contenido: no se aisló causalmente el orden expositivo. Los tres
controles sin persistencia se probaron juntos; no se cubrieron carreras de
escritura, permisos, perfiles ausentes ni eficacia pedagógica real. No se convirtió
ningún resultado sintético en feedback personal.

En un ensayo separado, dos ejecuciones nativas nuevas completaron la misma
consulta matemática y leyeron íntegramente el perfil real ya persistido. La
verificación de lectura comparó la salida completa con el archivo observado;
los archivos personales vigilados no cambiaron. La prueba acredita recuperación
del contexto local en los dos modelos ensayados, no el transporte de extremo a
extremo de la actualización sintética anterior.

| Modelo efectivo / esfuerzo | Ventana efectiva observada | Tiempo | Tokens totales del hilo raíz | Subagentes |
| --- | --- | --- | --- | --- |
| `gpt-6-astra` / Ultra | 258.400 | 56,021 s | 80.230 | 1; 23.667 tokens adicionales |
| `gpt-6.1-sol` / Ultra | 475.000 | 30,663 s | 50.065 | 0 |

Astra leyó además la skill de enseñanza; Sol no la cargó. Los procedimientos y
la carga fueron diferentes, por lo que no se atribuye una ventaja causal de
velocidad o coste. La revisión matemática posterior informó de un salto en Sol:
extendió una afirmación de diferenciabilidad puntual a un campo global sin añadir
la hipótesis necesaria. No encontró ese defecto en Astra. La lectura del perfil
y la compatibilidad observada no garantizan corrección matemática.

La continuidad usa `task_progress` en los almacenes existentes. Las regresiones
específicas cubren reanudación, identidad de tarea, idempotencia, revisiones
obsoletas, autorización exacta de fuente y destino, rechazo de información
restringida y recibos ligados al contenido vigente. El receptor OmarOS añade
pruebas de interrupción, historia monotónica, alcance declarado y conservación
del texto manual. Son pruebas de mecanismos con fixtures; la sincronización y
publicación en el vault real se documentan en el informe final de despliegue.

La revisión proporcional incorpora una justificación Quick para código ordinario
antes de la primera ronda. Los controles prueban su invalidación al cambiar el
snapshot y el respeto de políticas más estrictas, mínimos retenidos y rutas Deep.
No prueba que cualquier juicio humano sobre el riesgo sea correcto ni convierte
una declaración en permiso del cliente.

Estas extensiones reutilizan instrucciones, una skill de enseñanza y los motores
existentes; no añaden un selector de modos, runtime de agentes, servicio de memoria
ni base de progreso nueva. Los resultados reducidos están en
`ecosystem/evals/results/2026-10-18.json:migration_1_1.extension`; perfiles reales, respuestas y metadata
personal detallada permanecen locales. El ensayo del plugin 1.1 instalado sigue
pendiente en este snapshot de documentación; sus métricas posteriores se guardan
en el informe externo al bundle medido.

### Comprobaciones reproducibles

Las suites utilizan repositorios, remotos y configuraciones temporales. Separan
los mecanismos del juicio de agentes y del despacho nativo de hooks:

```sh
python3 -B -m unittest discover -s .codex/tests -q
python3 -B -m unittest discover -s .codex/ecosystem/tests -q
python3 -B .codex/ecosystem/native.py --codex-home ~/.codex --cwd "$PWD" --capabilities
```

Antes de las correcciones adicionales, 236 pruebas del runtime pasaron. La
revisión independiente detectó casos no cubiertos: un registro hijo podía
ocultar la revisión del workspace, una política local podía rebajar mínimos y
la recuperación podía atribuir a la tarea commits recibidos en la sincronización
inicial. Las nuevas regresiones fallaron antes y pasaron tras las reparaciones.
También se alinearon los contratos de validación y construcción para metadata y
permisos. Los checks del receptor fijan la versión final integrada.

El empaquetado comparable pasó 50 casos en HEAD y 59 en la migración previa a
estas reparaciones; tardó 16,701 y 27,908 s respectivamente. La cobertura creció:
no se observa una mejora de latencia. Una instalación real del paquete HEAD en
un CODEX_HOME temporal pudo actualizarse a 1.1 conservando estado y pasando del
recibo de distribución 1 al 2. Estos ensayos no modificaron la instalación real.

Los casos, su procedencia y sus límites están en
`ecosystem/evals/results/2026-10-18.json`. Un fixture correcto no acredita por sí solo una experiencia
completa de investigación financiera, reanudación nativa o control gráfico.
No se afirma una mejora causal de calidad, tokens o velocidad; se documentan
resultados observados, reducciones estructurales y cobertura adicional.

### Evaluación histórica 1.0

Este informe separa pruebas mecánicas, comportamiento de agentes y observación
nativa. Una muestra pequeña no estima fiabilidad universal. Los escenarios y
criterios públicos se conservan en `evals/cases.json` y `evals/rubric.json`;
los resultados estructurados están en `ecosystem/evals/results/2026-10-18.json`. No son conversaciones
ni contienen prompts privados.

La construcción solicitó GPT-6 Astra con Ultra. La selección fue confirmada por
el usuario y la metadata nativa `thread/read` sin turnos devuelve
`model=gpt-6-astra`, `reasoningEffort=ultra` para el coordinador, los doce autores,
los cinco revisores y los dos verificadores de reparaciones.
Esa metadata expresa configuración persistida, no telemetría por inferencia.
Los lanzamientos de construcción y evaluación solicitan ambos valores de forma
explícita. Las skills distribuidas no los fijan para usos futuros.

La muestra comparada contiene ingeniería, auditoría de argumento matemático,
escritura factual y transferencia ontológica a semántica de programas. Los
ejecutores reciben tareas y materiales sintéticos, sin respuestas previstas ni
conclusiones previas. Se usan carpetas aisladas y agentes distintos. El baseline
usa los contratos públicos anteriores a la construcción. No se imputa una
mejora causal a diferencias de latencia o a cuatro casos.

### Resultados observados

Los componentes ejecutados por los autores independientes de pruebas suman
163 casos: 45 del núcleo, 34 de hooks, 51 de empaquetado y 33 de validación.
También pasan las 47 pruebas existentes del motor de revisión. El check final
del workflow y CI comprueban la revisión declarada después de este informe;
los recuentos detallados, identidades y resultados están en `ecosystem/evals/results/2026-10-18.json`.

Las pruebas negativas ejercitan fallos posteriores a un éxito, contenido e
inputs obsoletos, autorrevisión, cobertura incompleta, hallazgos abiertos,
resolución sin independencia, tres rondas máximas, recuperación de intentos y
concurrencia real. Dos sesiones con el mismo nombre de tarea se aíslan, los
trabajos de perfiles distintos avanzan simultáneamente y las entregas mixtas
conservan obligaciones separadas. La evidencia numérica no descarga por sí sola
una obligación de demostración.

La portabilidad se prueba mediante construcción reproducible, paquetes de cada
módulo, instalación repetida, actualización, rollback y conservación de
configuración ajena. Un receptor ejecuta plan/status y reconstruye el paquete
con Git ausente y una auditoría de filesystem que deniega leer el hub original.
La integración nativa real detecta tres skills y cinco hooks `untrusted`.

| Caso comparado | Flujo anterior | Paquete candidato | Tiempo observado, anterior / candidato |
| --- | --- | --- | --- |
| Normalización de pesos | 13 pruebas y revisión manual sin hallazgos | Escritura temporal rechazada; cierre parcial honesto | 234,06 / 239,84 s |
| Continuidad de aplicación lineal | Refutación correcta revisada; entrega textual por rechazo de escritura | Refutación y reparaciones revisadas; cierre Quick vigente | 171 / 295,76 s |
| Nota factual sintética | 144 palabras; cifras corregidas y referencia sin respaldo retirada | 142 palabras; mismas correcciones y cierre Quick vigente | 100 / 205,52 s |
| Semántica de programas | Argumentos revisados y comprobaciones finitas auxiliares | Argumentos revisados y cierre Standard con tres revisores | 296,18 / 530,95 s |

No se observa evidencia suficiente para afirmar una mejora general de calidad.
El baseline ya resolvió correctamente los contenidos revisados. La diferencia
comprobada en los casos cerrados es la trazabilidad ejecutable de requisitos,
autores, comprobaciones y revisión. Los tiempos no son comparaciones causales:
difieren las ventanas de medición, herramientas, intervención y número de
revisores. No se recopilaron totales de tokens o coste.

La evaluación adicional produjo una refutación algebraica de una inferencia
basada en malla finita y de la supuesta completitud de los racionales. Un revisor
distinto de sus autores comprobó las respuestas textuales, sin hallar defectos
materiales. La escritura creativa produjo 99 palabras y la edición breve una
única frase; no se impusieron comprobaciones factuales innecesarias. Una pregunta
elemental sobre CPU no seleccionó ninguna skill. La selección explícita cubrió
los tres módulos; la selección implícita se examinó a partir de sus metadatos
instalados. El descubrimiento del cliente se comprobó por separado.

Los rechazos del hook del hub sobre `/tmp` no se ocultaron ni se sortearon con
otra herramienta. Esos casos conservan su estado parcial o textual. Se añadió
un caso distinto en una sesión nativa efímera con cwd propio de un receptor
sin Git, conservando permisos y confianza del usuario: corregir unión de
intervalos cerrados. Pasaron 13 métodos, 3.616 entradas enumeradas y contrastes
independientes de 12.111 y 3.616 entradas. Tres revisores Standard registraron
cero hallazgos y el motor cerró con evidencia vigente. El tiempo total fue
521,87 segundos. El resultado no cambia el veredicto de los intentos bloqueados.

La prueba de transferencia usó semántica de programas, distinta de los cuatro
ejemplos ontológicos del paquete. Se revisaron sintaxis, árboles, entornos,
denotaciones, captura, renombrado y equivalencia contextual. No reveló una
carencia que justificara añadir otra referencia. Tampoco demuestra que las
referencias nuevas causaran una mejora frente al baseline.

### Correcciones y alcance de la evidencia

La integración encontró una discordancia en los recursos de `writter` aislado:
su flujo técnico requería dos perfiles que el validador no esperaba. Se
centralizó el inventario en el builder confiado, se corrigió el cierre de
recursos y se añadió una regresión que construye y valida cada módulo real.
Otra regresión prueba que cambiar los perfiles técnicos auxiliares de `writter`
invalida su evidencia; los tres controles negativos fallan contra la selección
anterior. El validador no ejecuta el builder de un candidato externo.

La primera ronda formal produjo 13 hallazgos de cinco revisores, correspondientes
a siete clases de defecto. Se conservan los IDs individuales en el ledger;
las reproducciones coincidentes no se cuentan como defectos diferentes. Las
reparaciones cubren:

- Convivencia del estado predeterminado con instalación y actualización, sin
  leerlo, borrarlo ni incorporarlo al recibo de distribución.
- Sustitución atómica de perfiles y restauraciones para preservar otros nombres
  de un inode compartido por hardlinks.
- Validación de componentes originales de patches antes de simplificar `..`,
  evitando que un enlace simbólico oculte la salida del alcance.
- Permisos de inputs incluidos en la vigencia de checks, revisión y dependencias.
- Validación CLI que no escribe bytecode en su propio paquete; API y pruebas
  de paquetes inmutables con la precondición explícita `python -B`.
- Fixtures y selección de pruebas compatibles con los módulos distribuidos.
- Resolución del manifiesto correcta tanto en fuentes como en bundles.

Las regresiones se contrastaron con el snapshot exacto de la primera ronda.
La matriz ejecutó las suites desde cuatro distribuciones reales, sin recuperar
el checkout original: completa y cada módulo por separado. Cada una descubre
163 casos; se omiten respectivamente 1, 10, 9 y 8 por recursión del harness o
capacidad ausente. No se omiten los controles comunes. Las rutas, bytes, modos
e inventarios de los paquetes se conservan tras ejecutarlas. Los verificadores
de reparaciones son distintos de autores y descubridores; el cierre formal de
cada ID se registra únicamente contra el token de la revisión corregida.

La comprobación global posterior encontró otra incompatibilidad: el listado
nativo mantenía activas las fuentes del proyecto aunque la configuración
resuelta indicaba lo contrario. Se añadió una exclusión explícita mediante la
API nativa, sin cambiar confianza ni sustituir preferencias ajenas. Cinco
pruebas nuevas con Codex real cubren eliminación de duplicados, módulos
seleccionados, repetición sin escrituras, rechazos sin cambios y pérdida de
confirmación después de una escritura real. Se ejecutan también en los cuatro
bundles. La integración final recibe una tercera ronda independiente antes
de publicar; no se presenta la segunda ronda como aprobación de este cambio.
Un verificador independiente descubrió durante esta integración que comparar
solo `SKILL.md` permitía excluir fuentes con workflows distintos. El hallazgo
`ECO-SOURCE-EXCLUSION-RESOURCE-DIVERGENCE` conserva su identidad y versión
defectuosa en el JSON; exige comparar el cierre de recursos del módulo y una
resolución por un verificador distinto de autor y descubridor. Ocho pruebas
adicionales cubren divergencias de workflows, protocolo, motor, agentes y
ontología, selección parcial y un builder externo que no debe ejecutarse.

Las evaluaciones conductuales usan un snapshot instalado cuyo hash se conserva
en el JSON. Las correcciones posteriores del inventario se verificaron mediante
esas regresiones. Las pruebas no equivalen a autenticación de personas ni a
verificación formal de las demostraciones. Los tests de hooks ejecutan su
adaptador mediante subprocess; no se concedió confianza nativa ni se afirma
haber observado despacho nativo confiado.

La publicación exige adicionalmente revisión Deep de todos los archivos por
tres revisores de corrección y dos de seguridad, independientes de los autores
registrados. Sus informes y resoluciones pertenecen al ledger del workflow;
este informe de evaluación no sustituye esa puerta ni anticipa su veredicto.


## Compatibilidad histórica de las primeras versiones

Las matrices siguientes se trasladan desde la antigua guía de compatibilidad.
Conservan las versiones y observaciones de sus ensayos; ninguna declaración
sobre configuración, herramientas o permisos describe por sí sola una sesión
actual. La matriz mantenida está en `ecosystem/docs/compatibility.md`.

### Fase adaptativa 1.2: contrato y evidencia pendiente


La entrada estable `CODEX_HOME/constellation/hook.py`, su validación bajo lock y
el presupuesto de revisión se documentan como interfaces de la implementación.
Su disponibilidad en un checkout no acredita despliegue ni ejecución en el
cliente. Las comprobaciones deterministas, el canario nativo y la comparación
prerregistrada tienen evidencias separadas en [metodología de evaluación](../evaluation.md).
Los resultados de la migración 1.1 que siguen son históricos.

La primera actualización desde un hilo que capturó el comando del caché 1.1
requiere reabrirlo. El instalador no concede confianza al comando nuevo; una
aprobación real exigida por Codex se realiza en su interfaz nativa, sin modificar
hashes. El comando estable cargado puede resolver una distribución posterior
verificada; esto no prueba recarga del catálogo ni que el cliente haya despachado
un evento. El [contrato de instalación](../../README.md#instalar-y-actualizar) describe
qué se rechaza durante una actualización o tras una instalación interrumpida.

Los presupuestos de agentes son máximos efectivos, no objetivos de consumo.
La comparación con capacidades 2 y 4 no acredita saturación a 64. Modelo,
esfuerzo, contexto y permisos se heredan; una medida de un modelo o cliente no
se extrapola a otro. La telemetría no observada se registra como desconocida,
sin inferir ausencia de actividad a partir de una superficie parcial.

Un estado portable aislado necesita la misma `CONSTELLATION_STATE_DIR` heredada
por CLI y hooks; un `--state-dir` usado sólo en el CLI no conecta ese estado con
el despacho nativo. Usa una ruta absoluta para evitar diferencias de cwd.
Este ajuste de proceso conserva los defaults y no amplía acceso, altera confianza
ni mueve la política personal. Su contrato está en el
[protocolo](../../references/protocol.md#portable-api); observar un estado por CLI no
acredita que los hooks lo hayan usado.

### Verificación histórica 1.1 — 2026-10-18

Cliente comprobado: Codex CLI 0.163.0, macOS ARM64. El catálogo de esta sesión,
las instalaciones y `skills/list` de un app-server nuevo son superficies distintas.
El adaptador `native.py --capabilities` conserva esa diferencia y separa errores,
advertencias, habilitación, confianza y ejecución todavía no comprobada.

| Prueba | Resultado observado |
| --- | --- |
| Hub, app-server nuevo | 21 skills, 18 habilitadas; fuentes Constellation excluidas y plugin 1.0 activo al iniciar |
| Plugins y MCP configurados | 24 plugins; 7 servidores MCP, 4 habilitados; no acredita autenticación ni llamadas exitosas |
| Hooks al iniciar | 5 del plugin y 1 global, habilitados y confiados; definiciones duplicadas del hub retiradas |
| Dispatch nativo baseline | `UserPromptSubmit` y `Stop` 1.0 completados en thread efímero; otros eventos no inferidos |
| Configuración de 19 hijos | `config/read` devuelve 64 en cada uno tras retirar overrides locales; sin prueba de saturación |
| Proyecto vacío | Descubrimiento global/local real probado sin scaffolding; ejecución se evalúa aparte |
| Control de navegador | `iab` no disponible en subagente; ningún navegador disponible en coordinador |
| Lectura web | Páginas públicas oficiales consultadas con la herramienta web disponible |

La configuración global existente permite acceso completo y aprobación `never`.
Se conserva por elección previa del usuario. Los hooks de Constellation no son
un sandbox de shell o MCP. Tampoco se cambian Memories, feedback, telemetría ni
controles de cuenta; la inspección local no demuestra esos controles remotos.

El esquema instalado de `skills/list` no admite `perCwdExtraUserRoots`, aunque
aparezca en documentación más nueva. Se usan sólo campos aceptados por el cliente.
El inventario de plugins usa el CLI; las APIs app-server de plugins siguen
siendo interfaces experimentales. No se interpreta un binario nuevo como prueba
de compatibilidad: se repiten construcción, descubrimiento y casos representativos.

Los comandos públicos del hub son adaptadores del runtime compartido. El paquete
puede ejecutar su ciclo Git en un receptor sin `.codex` ni checkout del hub. Los
proyectos conservan Git, dominio y validación; OmarOS conserva su adaptador de
publicación y fija por hash la revisión compartida.

#### Modelo y contexto personal

Se retiró `.codex/config.toml` del hub, incluido el override de contexto
1.000.000/900.000. La inspección de `codex debug models` por el coordinador
registró 272.000 tokens para
`gpt-6-astra` y 500.000 para `gpt-6.1-sol` en este cliente; los ensayos nativos
observaron ventanas efectivas de 258.400 y 475.000. No se extrapolan límites de
API a Codex ni se cambian el modelo y esfuerzo predeterminados del usuario.

Dos procesos nuevos de app-server completaron la misma consulta matemática con
`gpt-6-astra`/Ultra y `gpt-6.1-sol`/Ultra. Ambos leyeron íntegramente el perfil
local persistido; su salida de lectura coincidió con el archivo observado.
El primero leyó además la skill de enseñanza y creó un subagente; el segundo
no lo hizo. Los archivos personales vigilados permanecieron idénticos y los
threads fueron efímeros. Esto acredita recuperación local del mismo perfil en
esos procesos y modelos, no eficacia pedagógica, equivalencia de resultados ni
compatibilidad universal. Sólo se publican métricas reducidas, sin contenido
personal ni respuestas de los ensayos.

La calibración sintética separada verificó ocho casos y 23 comprobaciones con
agentes nuevos en la sesión de colaboración. No sustituye la prueba entre
procesos: son fronteras de contexto diferentes. El perfil, su calibración y la
política del diario permanecen fuera de las skills genéricas distribuidas.

#### Progreso y revisión proporcional

Los adaptadores Git, portable y OmarOS usan el mismo formato de progreso. El
receptor OmarOS exige un bundle verificado que incluya `runtime/progress.py`;
el lock de tres recursos de la distribución 1.1.0 anterior a esta extensión sólo
conserva la compatibilidad de revisión tras verificar su inventario y hashes,
no habilita progreso. Las actualizaciones del proveedor y del
receptor siguen sus contratos independientes.

`allow_quick_code` es una opción de política, no un permiso del cliente. Una
política receptora que omita o niegue esa opción no acepta la reducción opcional
para código. Los mínimos más estrictos se conservan y la justificación debe
preceder a la primera ronda, ligada a su snapshot. No modifica sandbox,
aprobaciones, confianza de hooks ni las obligaciones Deep.

### Evidencia histórica 1.0

Fecha: 2026-10-17. Cliente probado: Codex CLI 0.163.0, macOS ARM64. Las pruebas
de descubrimiento usan instalaciones sintéticas y `CODEX_HOME` aislados, sin
confiar hooks ni iniciar turnos de modelo. No se han modificado componentes
gestionados del cliente.

| Mecanismo | Observación | Decisión |
| --- | --- | --- |
| Fuentes `.codex/skills` | El listado nativo descubre skills incluso sin Git. | Conservar la ubicación solicitada. |
| Plugin `plugin.json` raíz | Las skills aparecen; hooks no aparecen en seis variantes contrastadas. | No usar ese formato para este cliente. |
| `.codex-plugin/plugin.json` | Skills y hooks registrados, incluyendo ruta `./ecosystem/hooks.json`. | Usar un único manifiesto compatible. |
| Prefijo de skill | El cliente expone `constellation:nombre`. | Mantener nombre fuente exacto y documentar selector. |
| Fuentes más plugin | Dos archivos distintos producen dos entradas; no hay deduplicación por nombre. | Excluir las fuentes de un checkout explícito mediante `skills/config/write`, verificando después el listado nativo. |
| Agentes TOML | Recursos de plugin no implican registro automático. | Registrar perfiles personales por separado mediante el instalador. |
| `plugin add` repetido | Refresca la instalación, incluso con la misma versión. | Usarlo para actualización controlada. |
| Plugin deshabilitado | `plugin add` lo reactiva. | Detectar y rechazar la actualización antes de modificarlo. |
| Marketplace existente de otra fuente | El cliente rechaza la colisión. | Conservar origen y rechazar conflicto. |
| Confianza de hooks | Los hooks compatibles aparecen `untrusted`. | Revisión humana nativa de las definiciones concretas. |

La matriz de manifiestos incluyó raíz con extensión de hooks, raíz con
descubrimiento predeterminado, compatibilidad explícita, compatibilidad
predeterminada, raíz con overlay y raíz inline con overlay. Solo las dos
variantes exclusivamente compatibles registraron hooks. `hooks/list` y
`plugin/read` coincidieron antes y después de crear un hilo efímero sin turno.
Esto es una incompatibilidad observada de esta versión, no una refutación
general del formato portable documentado.

En el hub, `config/read` resolvió las rutas relativas del proyecto y mostró
`enabled=false` en una capa activa; sin embargo, `skills/list` siguió mostrando
las tres fuentes como activas junto al plugin. Por eso no se utiliza ese ajuste
como prueba de exclusión ni se sustituye el array de preferencias del usuario.
El helper optativo `native.py --exclude-source-root` usa la API documentada
`skills/config/write` sobre las rutas absolutas calculadas del checkout indicado.
Exige un plugin activo y bytes coincidentes en el cierre canónico de recursos
seleccionados, incluidos los archivos comunes exportados; verifica el resultado con otro
servidor y conserva las demás entradas. Una repetición confirmada no escribe;
una confirmación perdida se informa como resultado parcial. No modifica
confianza ni permisos. En un receptor sin checkout no se necesitan exclusiones.

Las consultas nativas utilizan `initialize`, `initialized`, `skills/list` y
`hooks/list` sobre `codex app-server --stdio`; no leen contenido de turnos.
Los esquemas del cliente se obtienen con `codex app-server generate-json-schema
--experimental`. Los eventos y filtros no son uniformes: `Stop` y
`UserPromptSubmit` no filtran por rol; solo los eventos de subagente aportan
su `agent_id`. La correlación del paquete necesita registro explícito.

El catálogo de esta sesión y `skills/list` del hub no contenían `scholar`.
Se encontró una referencia de configuración desactivada a `scholar-quant-docs`
fuera del alcance; se preservó sin leer ni alterar su destino. No hubo migración
de una skill activa. Las raíces adicionales de otra sesión pueden diferir.

La auditoría de `skill-creator` encontró capacidades útiles vigentes y
limitaciones concretas: su validador acepta nombre vacío, descripción en blanco
y enlaces locales inexistentes. Se reprodujeron con el validador real y
PyYAML 6.0.3 en un entorno temporal. El complemento valida el contrato limitado
de este paquete; no pretende ser un parser YAML general ni una evaluación
intelectual de las instrucciones. No se modificó la skill gestionada.

Documentación primaria consultada:

- [Paquetes y distribución de plugins](https://developers.openai.com/plugins/build/plugins).
- [Eventos, confianza y límites de hooks](https://learn.chatgpt.com/docs/hooks).
- [Descubrimiento y construcción de skills](https://learn.chatgpt.com/docs/build-skills).
- [Agentes personalizados e herencia](https://learn.chatgpt.com/docs/agent-configuration/subagents).
- [Configuración de modelo y esfuerzo](https://learn.chatgpt.com/docs/config-file/config-reference).

Estas páginas describen interfaces que pueden evolucionar. La prueba del
cliente instalado prevalece al determinar qué quedó registrado; la presencia
de archivos o `enabled=true` no demuestra confianza ni ejecución.
