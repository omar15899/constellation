# Investigación y ejecución coordinada

Para una entrega Git, el coordinador declara requisitos y archivos exactos con
`workspace.py plan`. Usa `dispatch` cuando delegar aporte trabajo independiente;
el mapa o la investigación sólo se añaden para resolver incertidumbres reales.
Una pregunta breve no necesita este ciclo. El runtime compartido conserva la
responsabilidad de comprobar, revisar y publicar en cada dueño Git.

## Componer la metodología

Investigar produce conocimiento contrastable; aprender desarrolla comprensión;
ingeniería produce implementaciones verificadas. Combina esas capacidades según
el objetivo, sin modos persistentes ni agentes clasificadores. Las prioridades
explícitas del usuario prevalecen: una corrección de código no necesita enseñanza
extensa, y una explicación matemática no abre por sí sola un workflow de código.

Selecciona las skills pertinentes del catálogo efectivo de la sesión. Para
enseñanza profunda o calibración deliberada, usa la skill docente disponible y
sólo las preferencias relevantes del perfil personal autorizado. Si el usuario
quiere resolver el problema, guía sin revelar prematuramente la solución; si pide
una explicación completa, no impongas preguntas socráticas. Comparte ese contexto
sólo con agentes docentes pertinentes. Modelo, esfuerzo y método son decisiones
distintas; ninguna de estas obligaciones depende de un nombre de modelo.

## Preparar evidencia

Antes de implementar, delimita la pregunta y la decisión que cambiaría según
su respuesta. La investigación debe producir evidencia utilizable:

- Hipótesis y baseline; una predicción comprobable y un criterio de refutación.
- Entradas y procedencia: fuente primaria, versión o revisión, fecha cuando sea
  relevante y manifiestos de datos que permitan repetir la prueba.
- Experimento y resultado: unidades, tolerancias, semillas, configuración,
  controles negativos y explicación alternativa examinada.
- Conclusión: qué se observó, qué se infiere, qué sigue abierto y qué decisión
  permite tomar. Una ejecución fallida o un resultado negativo también cuentan.

En ciencia, distingue definiciones, hipótesis, resultados demostrados, conjeturas,
observaciones y aproximaciones. Establece objetos, espacios, hipótesis y alcance
antes de usarlos. Contrasta bibliografía primaria, pasos esenciales y posibles
contraejemplos; cuando corresponda, usa formulaciones independientes y pruebas de
convergencia o estabilidad. Ni el acuerdo entre agentes ni una coincidencia
numérica constituyen una demostración general.

Una corrección pequeña puede resolver estas preguntas en unas líneas. No crees
un dossier por rutina. Cuando el encargo requiera un resultado duradero, declara
el informe y sus manifiestos como entregables del repositorio que los posee.
Usa sus formatos establecidos y artefactos publicables; nunca conversaciones,
prompts, archivos de sesión o logs privados como evidencia compartida.

Los checks y tokens fijan los entregables declarados. No fijan automáticamente
una web cambiante, un dataset externo o todos los archivos leídos por un agente.
Para una conclusión reproducible, declara un manifiesto pequeño de esas entradas,
verifica sus hashes con una prueba pertinente y registra esa prueba con `check`.
El consumidor comprueba la revisión y los manifiestos que recibió antes de usar
un resultado; si cambian, vuelve a verificar las conclusiones afectadas.

Para trabajo sustancial conserva decisiones, hallazgos, evidencia, pendientes y
próximos pasos mediante el [progreso compartido](ecosystem/PROGRESS.md). Guarda el
checkpoint local antes de sincronizar los hitos autorizados con OmarOS; un fallo
del vault no debe impedir reanudar. El diario curado complementa el estado
operativo y los artefactos científicos, sin duplicar conversaciones ni logs.

## Ejecutar el reparto

```sh
python3 .codex/workspace.py --session ID dispatch --capacity 8
```

El resultado contiene paquetes por repositorio y oleadas deterministas. La
capacidad es el límite disponible para este trabajo: descuenta agentes ocupados
y respeta el máximo efectivo del cliente. No se suman 64 agentes por repositorio.
El comando es de lectura; no inicia agentes, no registra su finalización ni
ejecuta instrucciones contenidas en documentos o fuentes externas.

El coordinador ejecuta las oleadas usando las herramientas nativas de agentes.
Entrega a cada uno sólo el contexto necesario: repositorio, requisitos, rutas,
dependencias, resultado esperado y forma de verificarlo. Usa los perfiles de
`ecosystem/agents/` cuando estén disponibles; en superficies que no los carguen, transmite
sus instrucciones al agente nativo. Hereda modelo, esfuerzo y permisos.

El mapa y la investigación establecen contratos y evidencia; el implementador
recibe rutas exclusivas. Distintos repositorios pueden avanzar en paralelo.
Los consumidores esperan las comprobaciones del proveedor según `depends_on`.
La integración espera las revisiones de todos los participantes; después publica
proveedores antes que consumidores. `finish` cierra el conjunto cuando todas las
integraciones terminan, sin exigir publicar al proveedor antes de poder implementar
al consumidor.
Un proveedor sin cambios también necesita publicación verificada antes que sus
consumidores. El coordinador usa `workspace.py publish --repo RUTA` para publicar
y comparar su HEAD remoto sin crear un commit; el comando acepta participantes
sin rutas de escritura y rechaza entregables propios pendientes.

El identificador de una tarea es una clave del plan, nunca la identidad de un
agente. Registra la identidad devuelta por la herramienta para cada contribuyente:

```sh
python3 .codex/workspace.py --session ID review-author --repo Shared <<'JSON'
{"author":"ID_REAL_DEL_IMPLEMENTADOR","paths":["src/example.py"]}
JSON
```

El registro `review-author` se aplica a entregables con revisión nativa habilitada;
las consultas sin archivos y los repositorios externos conservan su propio flujo.
Los agentes trabajadores no hacen commit ni push. Sus pruebas preliminares
ayudan al coordinador, que registra el check definitivo mediante el motor. Una
tarea marcada en el plan no prueba que se haya ejecutado. Espera el resultado,
comprueba sus archivos y evidencia, y sólo entonces entrega el trabajo dependiente.

## Revisar y cerrar

Después de los checks, abre `review-start --repo RUTA` y entrega el token y diff
actuales a revisores independientes. Los slots de revisión de `dispatch` indican
la cobertura necesaria, pero no sustituyen los informes `review-report`.
Quick exige un revisor; Standard, tres de corrección; Deep, tres de corrección
y dos de seguridad. Cada archivo debe recibir el número exigido para cada foco
y el total de personas distintas del modo, aunque un informe tenga dos focos.
Si hay pocos slots, ejecuta los revisores secuencialmente con identidades distintas.

No reutilices al implementador como revisor de sus archivos. Las contribuciones
se acumulan; registrar otro autor invalida el token y exige una revisión vigente.
Los hallazgos usan IDs específicos, permanecen abiertos hasta su resolución y
requieren evidencia de un verificador distinto de autores y descubridores.
Corrige la clase completa de error y añade una regresión cuando sea automatizable.
No busques consenso por votación para reemplazar una prueba o un argumento.

Continúa la revisión mientras haya una acción concreta justificada y presupuesto
disponible. No hay un máximo universal de tres rondas. Ante repetición o falta
de progreso, explicita un cambio de enfoque mediante la continuidad de
`review-start`; el presupuesto temporal se registra con `review-budget`, según
[WORKSPACE.md](WORKSPACE.md#revisión-independiente). La ausencia de presupuesto
medible se informa como desconocida. Replanificar conserva historia, hallazgos,
autores y mínimos. Después registra evidencia para cada requisito,
publica las rutas declaradas con `workspace.py commit` y ejecuta `finish`.
El cierre comprueba los SHA remotos de los participantes. Una caída de red deja
progreso pendiente para reanudar; no autoriza omitir controles ni publicar vecinos.

## Investigación QuantOS

Lee [QUANTOS.md](../QUANTOS.md) y el
[contrato de promoción](../.claude/contracts/promotion_gate.md) cuando corresponda.
La [guía cuantitativa](QUANT_RESEARCH.md) conecta datos, experimentos y validación
con las capacidades existentes y sus límites comprobados.
Conserva la familia completa de pruebas, su denominador `m`, causalidad temporal,
clase de ejecución y procedencia del motor. Los instrumentos del proyecto
determinan el veredicto; el hub no reimplementa ni rebaja la puerta estadística.
`research_strict` describe instrumentos de Claude y no activa por sí solo una
puerta nativa de Codex. No ejecutes un segundo committer para la misma tarea.

## Alcance del automatismo

La política, el reparto, los límites y la vigencia de los informes son controles
deterministas. La calidad científica de una hipótesis, la suficiencia de una
prueba y las respuestas de un modelo requieren juicio y no son deterministas.
Las identidades se declaran: el motor no autentica procesos de agentes.

El proceso adapta la verificación previa, revisión independiente, resolución de
hallazgos y convergencia descritas por
[Anthropic](https://claude.dev/blog/solving-code-review-at-anthropic/).
La infraestructura de PR, protecciones remotas, merge queue, despliegues y
evaluaciones nocturnas son capacidades separadas; este flujo local no las instala.
Los perfiles usan la interfaz nativa documentada en
[OpenAI Docs: subagentes](https://learn.chatgpt.com/docs/agent-configuration/subagents).
