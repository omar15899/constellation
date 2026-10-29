# Flujo de ingeniería

Para trabajo sustancial o prolongado, conserva decisiones, hallazgos, evidencia y
siguientes pasos mediante el [progreso del ciclo elegido](../../../ecosystem/docs/progress.md).
Sincroniza hitos personales sólo cuando la política local lo autorice; no abras
otro contrato ni conviertas una tarea pequeña en un procedimiento de seguimiento.

## Contrato y diagnóstico

Localiza el dueño real de los archivos y las instrucciones que gobiernan el
trabajo. En Constellation, usa el enrutado de `workspace.py` y lee el `AGENTS.md`,
`.codex/PROJECT.md` y las instrucciones de las carpetas afectadas. En otro
proyecto, conserva su flujo propio. Trabajar desde una raíz común no autoriza
editar vecinos, dependencias externas o configuración global.

Convierte el encargo en criterios que un tercero pueda comprobar: entradas,
salidas, errores esperados y restricciones de compatibilidad, recursos o datos
que importen. Para un bug, reproduce el fallo y distingue síntoma, causa e
hipótesis pendientes. Para un refactor, identifica el comportamiento que debe
conservarse y sus consumidores. Para una funcionalidad, incluye el trayecto que
la hará utilizable, no solo una función aislada.

Lee el código y los consumidores necesarios para comprobar los contratos.
Identifica invariantes relevantes, por ejemplo tipos, unidades, orden temporal,
propiedad de recursos, transacciones o permisos. No extrapoles la arquitectura
a partir del nombre de un archivo. Si queda una decisión material abierta,
compara las alternativas con un experimento pequeño, una fuente primaria o un
coste concreto. Resuelve las decisiones rutinarias con el contexto disponible.

## Registrar trabajo y repartirlo

Elige el ciclo según el [protocolo común](../../../ecosystem/references/protocol.md).
El flujo Git receptor gobierna cambios y publicación; el CLI portátil conserva
su esquema para entregas que necesitan evidencia semántica sin depender de Git.
Resuelve sus recursos respecto al paquete instalado, no respecto al cwd. La raíz de trabajo es el
proyecto receptor; el estado operativo es privado y queda fuera de la entrega.
No copies prompts, transcripciones, secretos ni salidas sensibles a informes.

Antes de modificar archivos de la entrega, declara el contrato y sus
comprobaciones en el ciclo elegido. Relaciona requisitos, artefactos exactos y
checks que permitan juzgarlos; identifica entradas y dependencias cuya variación
pueda invalidar el resultado. En el protocolo portátil, los requisitos de código
usan aceptación de comportamiento. No atribuyas ese esquema al contrato Git.
Una tarea puramente diagnóstica puede entregar un informe con evidencia y límites
sin modificar el producto. Mantén un contrato breve para cambios pequeños.
Una consulta de solo lectura sin entregables se responde sin crear estado ni un
informe nuevo; no la presentes como certificada por una puerta persistida.

Registra los IDs devueltos por la superficie nativa, incluidos todos los autores
de las rutas editadas, antes de revisar. Un nombre de rol, alias de tarea o slot
planificado no prueba identidad ni ejecución. El registro del motor y la carga
de un perfil de agente son hechos diferentes. Los perfiles de este paquete
heredan modelo, esfuerzo y permisos; si no están cargados, lee sus instrucciones
y pásalas al agente nativo disponible.

Delega investigación, implementación o revisión solo cuando aporten trabajo
independiente útil. Cada escritor recibe rutas exclusivas, requisitos,
dependencias, invariantes, resultado esperado y forma de comprobarlo. Indica las
skills pertinentes y su ubicación accesible; el trabajador debe comprobar su
propio catálogo y leer las instrucciones que necesite. No presupongas que hereda
una conexión, herramienta o perfil por estar disponible para el coordinador.
Advierte que comparte el árbol y debe preservar los cambios ajenos. Descuenta agentes
ocupados del límite efectivo común; no multipliques la capacidad por proyecto.
Espera la evidencia del proveedor antes de integrar un consumidor dependiente.
El coordinador integra y publica; los trabajadores entregan archivos y evidencia.

En un cambio Git ordinario de Constellation, usa la sesión vigente, `workspace.py`
y su reparto cuando corresponda; registra allí autores, checks y revisión sin
abrir un segundo contrato portátil. Si el objetivo también exige una prueba
matemática o un informe con garantías del motor portátil, declara esa obligación,
sus artefactos y la dependencia de la integración Git respecto a su evidencia
vigente. No dupliques todos los requisitos ni supongas una sincronización entre
motores. El protocolo detalla qué controles no son intercambiables. No reemplaces
un contrato activo ni trates un cierre portátil como permiso de publicación.
La ausencia de Git no impide planificar, comprobar y revisar archivos; no
inicialices un repositorio para satisfacer este procedimiento.

## Implementar y comprobar

Elige el diseño según la petición y los contratos observados. Compara la solución
mínima compatible con una abstracción que resuelva variaciones o reutilización
concretas: la brevedad por sí sola no prueba simplicidad ni una capa prueba generalidad.
Si se pide construir sobre abstracciones, explicita sus responsabilidades, contratos
y composición; si se pide una solución directa, no añadas una arquitectura por rutina.
Reutiliza las estructuras existentes y cambia los consumidores afectados dentro del
alcance. Mantén el delta mínimo salvo necesidad demostrada; justifica cambios de
compatibilidad o costes y evita shims, dependencias y refactors preventivos.

La legibilidad exige poder seguir entrada → transformación → salida. Elige nombres
que expresen el dominio, estructuras que hagan visibles las relaciones y pasos que
puedan leerse sin reconstruir estado oculto. Generaliza sobre variaciones requeridas,
no sobre futuros hipotéticos; verifica esas variaciones con casos representativos.
Al valorar eficiencia, identifica qué crece —registros, bytes, llamadas o dimensiones—
y el coste relevante de tiempo, memoria o E/S. Distingue complejidad razonada de
medición: una mejora de rendimiento requiere carga, unidades, entorno y comparación
reproducibles; sin esos datos, conserva la conclusión como hipótesis.

### Documentar decisiones y datos

En Python usa [Google Style para comentarios y docstrings](https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings).
Documenta APIs públicas y código de tamaño o lógica no trivial. Una docstring abre
con un resumen y desarrolla el contexto necesario para usar la interfaz sin leer su
implementación. Desarrolla con amplitud el contexto y los datos que sostienen el
contrato; un getter obvio puede necesitar sólo una línea. Conserva las convenciones aplicables del proyecto
y evita duplicar texto en cada envoltorio.

Explica el propósito y recorrido de los datos en el módulo o clase responsable;
en cada función documenta su parte del contrato. Usa `Args:`, `Returns:` o `Yields:`
y `Raises:` cuando aporten información, y `Attributes:` para atributos públicos
que lo necesiten. Describe significados y restricciones que las anotaciones no
expresan; añade tipos si faltan y puedes establecerlos. En generadores describe los
valores producidos, consumo de entradas y recursos mantenidos durante la iteración.
No rellenes secciones vacías ni repitas literalmente la firma.

Cuando condicionen el uso, declara precondiciones, invariantes, efectos, límites,
propiedad y duración de recursos, mutación y aliasing. Para colecciones, registros,
tablas o tensores, precisa campos, claves, relaciones, esquema, shape, dtype,
unidades, nulos, vacíos, duplicados y orden que importen al contrato. Acompaña las
estructuras difíciles de un ejemplo pequeño de entrada y salida compatible con
la implementación, con valores sintéticos identificados y comprobados; muestra
qué se conserva, transforma o descarta. Usa estructuras reales del programa y
verifica los ejemplos: no inventes tipos, columnas, garantías ni resultados para
completar documentación. Si no puede establecerse un contrato, declara la laguna.

`Raises:` recoge errores que forman parte de la interfaz ofrecida y sus condiciones;
no convierte fallos accidentales fuera de las precondiciones en garantías. El motivo
de una decisión va junto a su dueño: contrato y consecuencias para quien llama en
la docstring, detalles internos no evidentes en comentarios junto al código. Explica
por qué se elige una estructura o algoritmo cuando afecte a su comprensión,
invariantes o costes; evita comentarios que traduzcan cada línea de Python.

### Comprobar comportamiento y documentación

Comprueba comportamiento observable con entradas representativas y límites que
puedan refutar la solución. Ante una regresión automatizable, conserva una prueba
que falle antes del arreglo y pase después. Un cambio en un control necesita
ejercitar tanto el rechazo como un caso permitido para detectar falsos bloqueos.
Incluye consumidores o integración cuando una prueba aislada no alcance el
contrato. Un comando no ejecutado o una prueba omitida no cuentan como éxito.

En código numérico, explicita el rango y la precisión del contrato. Comprueba
extremos válidos, desbordamientos intermedios y cancelación que puedan violarlo,
con una referencia independiente o cotas pertinentes cuando hagan falta. Una
advertencia en la documentación no excusa un incumplimiento ni permite restringir
silenciosamente el dominio pedido; corrige el cálculo o declara la obligación
pendiente. Justifica el coste de la solución elegida sin imponer un algoritmo.

Registra checks definitivos con el ciclo que corresponda, sobre los artefactos
actuales. Las pruebas preliminares de un trabajador ayudan al coordinador, pero
no sustituyen ese registro. Para una edición pequeña, una comprobación existente
y enfocada puede bastar; no inventes tests que solo busquen el texto recién
añadido. Tras pasar los checks pertinentes, repítelos o amplíalos únicamente por
cambios, fallos o una duda concreta. Explica cualquier limitación real de la
verificación, incluidas dependencias o entornos que no estén disponibles.

## Revisar y resolver

Determina el riesgo con la política receptora y el efecto semántico del cambio;
nunca rebajes su mínimo. Usa los umbrales del gate común:

| Modo | Cobertura independiente por archivo |
| --- | --- |
| Quick | Un revisor de corrección para cambios de bajo riesgo admitidos por la política |
| Standard | Tres revisores de corrección para cambios de código ordinarios |
| Deep | Tres revisores de corrección y dos de seguridad para cambios sensibles |

Un ajuste pequeño de hooks, permisos, autenticación, publicación, instalación o
controles puede requerir Deep. La cuota y el total de identidades distintas se
cumplen por archivo; si hay pocos slots, ejecuta las revisiones secuencialmente.
No uses un autor como revisor de sus archivos ni inventes identidades para cubrir
una cuota. Si no puedes obtener la cobertura, conserva el estado parcial.

Abre la revisión después de los checks vigentes. Entrega a los revisores el token
actual, diff, requisitos, invariantes, consumidores relevantes y evidencia.
Pide una evaluación sustantiva de cada requisito, además de corrección,
regresiones y seguridad según el foco. Una lista de tests aprobados o un dictamen
genérico no sustituye la relación requisito–resultado. Los revisores deben
inspeccionar los artefactos; no editen el objeto que están revisando.

Cada hallazgo indica escenario reproducible, ubicación, consecuencia y evidencia;
distingue defectos introducidos de preexistentes. Corrige la clase de error y
encarga la comprobación a un verificador distinto de los autores y descubridores.
El descarte de un falso positivo también necesita justificación independiente.
Registra el resultado mediante el protocolo; no borres ni cierres un hallazgo
por consenso informal.

Un cambio de artefactos, entradas, contrato o checks puede invalidar la evidencia:
consulta el estado vigente y renueva lo necesario. Los controles automáticos de
vigencia difieren entre el contrato Git y el portátil; comprueba expresamente
las dependencias semánticas que el receptor no fija. Las rondas posteriores cubren
el delta y sus consecuencias sin perder hallazgos pendientes. La admisión de
nuevas rondas depende del presupuesto explícito y de las señales de repetición,
sin un máximo universal de tres. Un presupuesto no declarado es desconocido.
Cuando el motor exija continuación, declara el motivo y una acción concreta.
Replanificar conserva el historial, los hallazgos, la autoría y los mínimos;
no permite eludir un plazo agotado. Con obligaciones pendientes, conserva el
estado abierto y explica el impedimento concreto.

## Integrar y entregar

Antes del cierre, comprueba esta cadena para cada requisito significativo:

`requisito → artefactos actuales → checks pertinentes → autores reales → revisión independiente vigente`

Incluye resultados negativos y limitaciones sin convertirlos en aceptación.
Los hashes atan evidencia a una versión; los agentes juzgan si esa evidencia
demuestra el requisito. Si se descubre una obligación necesaria, regístrala en el
contrato y resuélvela dentro del alcance, o conserva el cierre parcial.

Integra dependencias en el orden permitido por el receptor. Antes de publicar,
comprueba alcance, diff, índice ajeno, autorizaciones vigentes y todos sus gates.
Usa exclusivamente el flujo receptor de commit, push, PR o despliegue autorizado;
el motor portátil no publica ni concede permisos. En Constellation, el coordinador
usa `workspace.py`, conserva hooks y verificaciones, y verifica el SHA remoto
antes de declarar publicación completa. No añadas un segundo committer ni
eludas un rechazo. Otros proyectos requieren su propio alcance y autorización;
no traslades la autorización del hub. No vuelvas a pedir una autorización ya
concedida para la misma acción dentro del mismo alcance.

El cierre completo exige todos los requisitos y gates aplicables satisfechos,
incluida la publicación cuando forme parte del encargo. Con obligaciones
pendientes, registra cierre parcial y comunica qué funciona, qué evidencia existe,
qué falta y por qué. Sin Git, la entrega verificada son los archivos autorizados y
su evidencia. Resume el cambio y su comprobación en el idioma del usuario;
no afirmes que una revisión, instalación, activación o publicación ocurrió sin
evidencia de la operación real.
