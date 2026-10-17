# AGENTS.md — constellation en Codex

Este repositorio mantiene las herramientas compartidas de `~/GitHub/`.
Las carpetas hijas son repositorios independientes, con sus propios contratos,
historias y pruebas. El hub no tiene un tier de QuantOS. Abrir Codex en esta
raíz permite coordinar todos los proyectos registrados sin mezclar sus índices.

## Resultado y autonomía

Completa el trabajo pedido: identifica el resultado, el alcance y la evidencia
que permitirá comprobarlo; implementa, verifica y corrige dentro de ese alcance.
Resuelve decisiones rutinarias con el contexto. Pregunta cuando una elección
faltante cambie materialmente el resultado o una acción irreversible carezca de
autorización. Una corrección o pregunta de estado conserva el objetivo vigente.

La petición actual del usuario prevalece sobre las guías locales. Si una regla
obliga a detenerte, cita su archivo e instrucción exactos. Respeta los permisos,
las revisiones de aprobación y la confianza de hooks del cliente.

Codex usa este contrato y el perfil nativo de [.codex/README.md](.codex/README.md).
`.claude/` mantiene el sistema de Claude; sus routers, agentes, comandos y loops
no son un prerrequisito de Codex. `.codex/profile.json` impide que el generador
sustituya este perfil. El archivo local `.codex_NOTUSE/` conserva la proyección
anterior, fuera de la carga activa y de Git.

## Contexto que aporta información

Localiza primero el repositorio pertinente mediante `python3 .codex/workspace.py
route RUTA` y lee su `AGENTS.md`, sus invariantes en `.codex/PROJECT.md` y las
instrucciones de las carpetas afectadas. Abrir la raíz no carga automáticamente
los contratos de todos los hijos. Consulta su
`CLAUDE.md` si contiene información del proyecto que falte, sin importar cadenas
de ejecución de otro agente. Usa el [registro](.claude/registry/repos.yaml) para
identificar repositorios; verifica los hechos que vayan a determinar cambios.
El [registro operativo](.codex/repositories.json) delimita proyectos propios
y externos; Git determina el dueño real de cada archivo. El registro de Claude
aporta contexto de dominio, no autoridad para elegir remotos. Los proyectos
externos o vendorizados mantienen sus reglas y necesitan alcance explícito.

Busca con `rg --files` y `rg -n` dentro de las raíces seleccionadas. Devuelve
rutas y líneas verificadas. Amplía la búsqueda cuando la evidencia lo requiera;
no ejecutes inventarios o auditorías de toda la constelación por rutina.
Para arquitectura QuantOS consulta [QUANTOS.md](QUANTOS.md); los cambios de
investigación respetan el [contrato de promoción](.claude/contracts/promotion_gate.md)
y las dependencias de tiers. Estas restricciones de dominio siguen vigentes.

El agente principal resuelve el trabajo. Puede usar hasta 64 subagentes cuando
subtareas independientes ahorren tiempo o aporten una revisión útil, con alcance
y archivos claros. Decide cuántos necesita según la tarea; es capacidad máxima,
no una cantidad que deba agotar.
Consulta `.codex/agent_policy.py show` para el presupuesto por repositorio;
el límite del cliente y de la sesión prevalece y se comparte entre sus tareas.
No ocupes todos los agentes por obligación ni crees pools por repositorio dentro
de una misma sesión. Hereda modelo y esfuerzo; el coordinador integra y publica.

Tras declarar el plan, usa `workspace.py dispatch --capacity N` para obtener
paquetes y oleadas por dueño Git. Ejecuta los paquetes con agentes nativos,
descuenta los agentes ya ocupados y conserva archivos exclusivos por escritor.
Para investigar aplica [.codex/RESEARCH.md](.codex/RESEARCH.md): hipótesis,
fuentes, contraejemplos y evidencia reproducible. Registra los implementadores
reales con `review-author` y sus rutas antes de revisar; un ID de tarea no es
una identidad. El reparto no ejecuta ni certifica tareas por sí mismo.

Antes de publicar, aplica [REVIEW.md](REVIEW.md) y la revisión independiente del
motor común. Abre una ronda con `workspace.py review-start --repo RUTA`, entrega
su token y el diff a revisores distintos del autor, registra sus informes y
resuelve cada hallazgo con evidencia independiente. Quick requiere un revisor;
Standard, tres de corrección; Deep, tres de corrección y dos de seguridad.
Cada archivo necesita esa cobertura por foco. El máximo son tres rondas;
replanificar no borra hallazgos ni reinicia el contador. Una revisión de agente
no sustituye una aprobación humana exigida por el proyecto o el servidor.

## Ejecución y evidencia

Para trabajar desde esta raíz sobre uno o varios repositorios, usa
[workspace.py](.codex/WORKSPACE.md): rutas exactas relativas al hub, un contrato
por dueño Git, pruebas y revisión por repositorio, commits granulares y push al
upstream congelado de cada rama. Declara `depends_on` cuando un cambio necesite
otro: proveedores primero, consumidores después. Un fallo deja el conjunto
pendiente con su progreso; nunca publiques todos los repos por rutina.

Para trabajo exclusivamente local del hub también sirve `.codex/README.md`: comprobación segura
del upstream, alcance explícito, comprobaciones pertinentes, revisión del
resultado, commits granulares y cierre con remoto verificado. Las consultas
usan `paths: []`. Los perfiles nativos hijos usan el motor común y conservan
su doctrina y hooks Git. No instales ni regeneres perfiles incidentalmente.

Python estándar es suficiente para el flujo nativo (3.9+). Las utilidades de
proyección de Claude requieren Python 3.12+. Reutiliza el código existente y
prueba comportamiento real, incluidos rechazos cuando cambies un control.
No añadas pruebas que reproduzcan una edición trivial. Tras pasar las pruebas
pertinentes, amplíalas o repítelas solo por cambios, fallos o dudas concretas.
La revisión confirma cada requisito contra el resultado real; los hashes
certifican la versión revisada, no la verdad de un argumento.

## Preservación y privacidad

Omar autoriza commits y push normales para cerrar sus encargos. Revisa el diff,
incluye rutas explícitas y preserva el índice y cambios ajenos. No hagas
force-push, rebase, amend, reset duro, clean o descartes sin petición exacta.
No inspecciones ni gestiones recuentos de worktrees. El vault OmarOS se modifica
solo mediante su propio flujo y cuando el encargo lo autorice.

Prompts, transcripciones, archivos de conversación, sus manifests, estados de
sincronización y logs de daemons son privados locales. No los leas como contexto
incidental ni los stages, publiques o transmitas sin que Omar nombre los datos
y el destino. No leas secretos ni actives Memories, feedback, telemetría de
prompts u OTel sin petición explícita. No envíes mensajes a terceros sin
autorización. La configuración local no demuestra los controles de cuenta.

## Comunicación

Escribe en el idioma de la petición, con prosa natural, precisa y conectada.
Explica primero el resultado y después la evidencia necesaria para evaluarlo.
La longitud depende de la dificultad; evita jerga decorativa, plantillas rígidas
y conclusiones repetidas. En matemáticas establece objetos, espacios e hipótesis
y justifica los pasos esenciales. Distingue hechos, inferencias y aproximaciones.
Informa qué cambió, cómo se verificó y cualquier limitación real pendiente.
