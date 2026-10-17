# Flujo de ingeniería

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

Usa el [protocolo común](../../../ecosystem/references/protocol.md) como fuente
única de operaciones, campos y semántica de evidencia. Resuelve sus recursos
respecto al paquete instalado, no respecto al cwd. La raíz de trabajo es el
proyecto receptor; el estado operativo es privado y queda fuera de la entrega.
No copies prompts, transcripciones, secretos ni salidas sensibles a informes.

Antes de modificar archivos de la entrega, declara el contrato y sus
comprobaciones. Cada requisito debe enlazar artefactos exactos y checks que
permitan juzgarlo; registra también entradas y dependencias cuya variación pueda
invalidar el resultado. Los requisitos de código usan aceptación de comportamiento.
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
dependencias, invariantes, resultado esperado y forma de comprobarlo. Advierte
que comparte el árbol y debe preservar los cambios ajenos. Descuenta agentes
ocupados del límite efectivo común; no multipliques la capacidad por proyecto.
Espera la evidencia del proveedor antes de integrar un consumidor dependiente.
El coordinador integra y publica; los trabajadores entregan archivos y evidencia.

En Constellation, el contrato del motor portátil acompaña el contrato receptor:
usa la sesión vigente, `workspace.py` y su reparto, registra allí los autores
reales y completa sus comprobaciones y revisión. No reemplaces un contrato activo
ni trates el cierre portátil como aprobación de publicación. En otros entornos,
aplica su autorización y flujo. La ausencia de Git no impide planificar,
comprobar y revisar archivos; no inicialices un repositorio para satisfacer este
procedimiento.

## Implementar y comprobar

Implementa la solución más sencilla que satisfaga los contratos e invariantes.
Reutiliza las abstracciones del proyecto y cambia los consumidores afectados
dentro del alcance autorizado. Justifica las decisiones que alteren compatibilidad
o costes; evita shims, capas o refactors preventivos sin necesidad demostrada.

Comprueba comportamiento observable con entradas representativas y límites que
puedan refutar la solución. Ante una regresión automatizable, conserva una prueba
que falle antes del arreglo y pase después. Un cambio en un control necesita
ejercitar tanto el rechazo como un caso permitido para detectar falsos bloqueos.
Incluye consumidores o integración cuando una prueba aislada no alcance el
contrato. Un comando no ejecutado o una prueba omitida no cuentan como éxito.

Registra checks definitivos con el motor que corresponda, sobre los artefactos
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
consulta el estado vigente y renueva lo necesario. Las rondas posteriores cubren
el delta y sus consecuencias sin perder hallazgos pendientes. El máximo es tres
rondas por tarea; replanificar o cambiar de sesión no permite reiniciarlo. Si no
converge, conserva las obligaciones abiertas y explica el impedimento concreto.

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
