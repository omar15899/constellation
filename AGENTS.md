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

El agente principal resuelve el trabajo. Delega solo una subtarea independiente
cuando ahorre tiempo o aporte una revisión útil, con alcance y archivos claros.
No se exige una secuencia de agentes, auditorías recursivas, puntuaciones
semánticas ni procesos persistentes. Hereda el modelo y esfuerzo elegidos por
Omar; no fuerces otro modelo para compensar instrucciones innecesarias.

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
