# Evaluación del ecosistema

## Fase adaptativa 1.2 — diseño y estado de validación

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

## Migración histórica 1.1 — controles y experimentos separados

El bloque `migration_1_1` de `evaluation.json` identifica las observaciones del
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

## Extensión: aprendizaje, modelos y continuidad

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
`evaluation.json:migration_1_1.extension`; perfiles reales, respuestas y metadata
personal detallada permanecen locales. El ensayo del plugin 1.1 instalado sigue
pendiente en este snapshot de documentación; sus métricas posteriores se guardan
en el informe externo al bundle medido.

## Comprobaciones reproducibles

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
`evaluation.json`. Un fixture correcto no acredita por sí solo una experiencia
completa de investigación financiera, reanudación nativa o control gráfico.
No se afirma una mejora causal de calidad, tokens o velocidad; se documentan
resultados observados, reducciones estructurales y cobertura adicional.

## Evaluación histórica 1.0

Este informe separa pruebas mecánicas, comportamiento de agentes y observación
nativa. Una muestra pequeña no estima fiabilidad universal. Los escenarios y
criterios públicos se conservan en `evals/cases.json` y `evals/rubric.json`;
los resultados estructurados están en `evaluation.json`. No son conversaciones
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

## Resultados observados

Los componentes ejecutados por los autores independientes de pruebas suman
163 casos: 45 del núcleo, 34 de hooks, 51 de empaquetado y 33 de validación.
También pasan las 47 pruebas existentes del motor de revisión. El check final
del workflow y CI comprueban la revisión declarada después de este informe;
los recuentos detallados, identidades y resultados están en `evaluation.json`.

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

## Correcciones y alcance de la evidencia

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
