# Codex nativo: coordinación y publicación verificables

Para coordinar proyectos desde `~/GitHub` o desde cualquier hijo, empieza en
[WORKSPACE.md](WORKSPACE.md). `workspace.py` distribuye rutas y ejecuta este
ciclo por cada dueño Git. El registro operativo está en `repositories.json`;
los proyectos propios usan perfiles nativos y `ruflo` conserva su perfil externo.
La sección de uso siguiente documenta el motor de **un solo repositorio**.

El perfil mantiene instrucciones breves y entradas al runtime compartido de
[Constellation](ecosystem/ARCHITECTURE.md). Codex trabaja directamente; no necesita proyectar Claude,
cargar el sistema de agentes de Claude ni recorrer una cadena de skills. El modelo,
esfuerzo y permisos se heredan de los ajustes del usuario.

El [ecosistema personal portable](ecosystem/README.md) añade `coding`,
`mathematics` y `writter`, recursos de agentes y controles de evidencia para
trabajos con o sin Git. Sus fuentes están en `skills/`; el plugin instalado
las expone con el prefijo `constellation:`. Instala el plugin y aplica la
exclusión explícita de fuentes por ruta descrita en su guía para evitar dos
copias activas. El paquete conserva este flujo como autoridad de publicación:
su `close` no hace commits, push ni sustituye los controles del proyecto.

Cuando la tarea se beneficia de delegación, `workspace.py dispatch` propone
implementación, checks y revisión ordenados por dependencias y capacidad. Una
implementación con un solo dueño puede quedar en el coordinador; mapa e
investigación se añaden cuando resuelven una incertidumbre real.
[RESEARCH.md](RESEARCH.md) explica la ejecución y el
handoff de evidencia. Ocho perfiles compartidos en `ecosystem/agents/` dan instrucciones a los
trabajadores; el coordinador los inicia con las herramientas del cliente.
Un participante sin cambios se publica y verifica con `workspace.py publish
--repo RUTA`, conservando la dependencia del consumidor sin crear commits vacíos.

| Aspecto | Proyección anterior | Perfil nativo |
| --- | --- | --- |
| Contrato de Codex | Entrada → kernel Claude → contratos y roles | `AGENTS.md` propio |
| Agentes especializados | 3 | 8 perfiles compartidos que heredan modelo y esfuerzo |
| Skills del hub cargadas | 14 | 3 módulos mediante el plugin portable; exclusión nativa explícita de fuentes para evitar duplicados |
| Automatismos Codex | 8 comandos en 4 eventos, con adaptador Claude | 5 eventos del plugin; definiciones duplicadas del hub retiradas |
| Verificación | Hooks dispersos y evidencia de ejecución | Prueba real, revisión independiente vigente y publicación comprobada |
| Dependencias del flujo | Adaptador y scripts de Claude | Python estándar y Git; paquete portable y gateway requieren Python 3.11+ |

La [guía oficial de modelos](https://developers.openai.com/api/docs/guides/latest-model),
consultada el 2026-09-09, orienta las decisiones sobre autonomía, conflictos entre
instrucciones, delegación selectiva, claridad y pruebas proporcionales. Aplicar
esa guía a las instrucciones no requiere cambiar el modelo que Omar elija.

## Modelo, contexto y permisos

El hub hereda la configuración nativa del usuario. No fija modelo, esfuerzo,
ventana de contexto ni umbral de compactación: Codex resuelve sus defaults según
el modelo y la superficie. Se retiró el archivo local que imponía un millón de
tokens y 900.000 para compactar, además de repetir hooks y capacidad ya globales.
Cambiar entre modelos compatibles no exige editar proyectos ni skills.

Consulta `model/list` y la configuración efectiva del cliente para disponibilidad
y esfuerzos. La ventana anunciada por una API no sustituye al presupuesto de
contexto del cliente instalado. Las pruebas con modelos concretos constan en
[compatibilidad](ecosystem/COMPATIBILITY.md); no prueban modelos futuros.
[Configuración nativa](https://learn.chatgpt.com/docs/config-file/config-reference).

## Uso

Desde la raíz del hub, ejecuta `python3 .codex/workflow.py`. El CLI usa
`CODEX_THREAD_ID`; si el hook comunica otra sesión, añade `--session ID` antes
del subcomando. No compartas la sesión `manual` entre trabajos concurrentes.

1. `begin --turn ID` comprueba explícitamente el upstream.
   Hace fetch; integra con fast-forward solo con árbol limpio y sin divergencia.
   Un fallo se conserva como impedimento para escritura; permite leer.
2. `plan` recibe por stdin `requirements` y `paths`: criterios observables y
   archivos relativos exactos. Las consultas usan `paths: []`. Para retiradas,
   incluye los archivos también en `deletions`; deben estar versionados.
3. `check -- COMANDO ARGUMENTOS` ejecuta una prueba pertinente y registra su
   resultado y hashes. Rechaza una prueba fallida o que cambie entregables.
4. `review-context` clasifica el alcance; `review-start` abre una ronda y devuelve
   el token que los revisores deben usar en `review-report`. `review-resolve`
   registra la verificación independiente de una corrección o falso positivo.
   Lee [WORKSPACE.md](WORKSPACE.md) y [REVIEW.md](../REVIEW.md) para el protocolo.
   `review` recibe un objeto cuya clave es cada requisito exacto y cuyo valor
   explica la evidencia comprobada. Modificar un archivo invalida la revisión;
   el código y configuración exigen una prueba vigente. Un fallo posterior
   invalida el éxito anterior de ese comando. Las retiradas deben completarse.
5. `commit -m 'Mensaje humano' ruta1 ruta2` prepara solo esas rutas, comprueba
   el contenido del índice, hace commit, push normal y verifica el hash remoto.
   Si el índice ya contiene trabajo, se conserva y se informa del impedimento.
   `commit --preserve-index` permite publicar una selección disjunta mediante
   `git commit --only`, verificando que el índice ajeno permanece intacto.
6. `finish` comprueba revisión, alcance, ausencia de cambios propios pendientes
   y coincidencia con el remoto. `status` consulta el estado privado de la tarea.

Ejemplo de entrada para `plan`:

```json
{"requirements":["La función maneja entradas vacías"],"paths":["src/example.py","tests/test_example.py"]}
```

`adopt_existing` permite justificar por ruta una integración de cambios previos
inspeccionados, sin apropiarse de trabajo ajeno. `unrelated` documenta archivos
nuevos de otra actividad. No se usan para omitir entregables. Una corrección del
usuario conserva la tarea pendiente; actualiza el plan. `begin` inicia otra tarea
solo cuando el objetivo anterior termina, se cancela o se reemplaza.

Un push transmite también los commits anteriores de la rama que falten en su
upstream: revisa ese alcance antes de publicar. El flujo comprueba las rutas
privadas en todos los commits salientes, incluso si después fueron borradas.

## Instalación y confianza

```sh
python3 .codex/install.py
python3 -m unittest discover -s .codex/tests -v
```

El instalador activa tres hooks de Git (`pre-commit`, `post-commit`, `pre-push`)
solo si no sustituye hooks ajenos. Guarda el valor anterior en el directorio
privado de Git. No cambia la configuración global de Codex ni su confianza.

`hooks.json` conserva una declaración vacía de migración. Los cinco eventos del
plugin usan un único adaptador para contratos activos. `UserPromptSubmit` no
crea tareas ni comprueba remotos; `PreToolUse` verifica las rutas declaradas;
los eventos de agentes comunican contexto y `Stop` solicita cierre con intentos
acotados e idempotentes. No se publica desde hooks. Los comandos heredados de
hooks delegan al mismo adaptador para sesiones que todavía los tengan cargados.

La confianza se administra en `/hooks`; instalar no la concede. Comprueba
descubrimiento, habilitación, confianza y ejecución por separado. No edites
hashes de confianza ni uses opciones para eludirla. Una sesión nueva carga las
definiciones actuales sin los eventos duplicados del hub.
[Documentación oficial de hooks](https://learn.chatgpt.com/docs/hooks).

## Alcance y límites

La concurrencia general de Codex se configura en `~/.codex/config.toml` con
`agents.max_concurrent_threads_per_session = 64`. Las instrucciones globales
permiten usar hasta ese máximo cuando haga falta; el primario no cuenta.
La política [agent-policy.json](agent-policy.json) alinea los perfiles nativos
en 64 para que no prevalezcan los anteriores límites de seis u ocho. El comando
`python3 .codex/agent_policy.py show` muestra la política efectiva;
`check` detecta divergencias y `apply --repo RUTA` actualiza únicamente las rutas
de configuración declaradas en el plan. Reinicia la sesión para cargar cambios.
La herramienta de aplicación no modifica modelo, esfuerzo, permisos, confianza
ni configuración global. Esta última se mantiene por separado; el máximo es
capacidad disponible, no una obligación de usar todos los agentes.
[OpenAI Docs: subagentes](https://learn.chatgpt.com/docs/agent-configuration/subagents).

La revisión independiente se aplica a los repositorios nativos registrados
que usan este motor. Comprueba identidad declarada, cobertura, huellas y estados;
no autentica la identidad del proceso revisor ni demuestra la verdad del informe.
La política clasifica rutas, no comprende por sí sola el riesgo semántico: el
coordinador debe aumentar la revisión cuando el comportamiento lo requiera.
Las pruebas CI del hub ejercitan el motor en clones y remotos locales desechables.
No se instala un servicio de revisión AI en GitHub ni se cambian sus protecciones.

Quick exige un revisor; Standard, tres de corrección; Deep, tres de corrección
y dos de seguridad. Cada archivo necesita también el total de identidades
distintas de su modo, aunque un informe cubra ambos focos. `review-author`
registra contribuyentes por rutas e impide su autorrevisión; sus identidades
siguen siendo declaraciones. Los IDs ambiguos de hallazgos se rechazan sin
fusionar problemas distintos. El máximo de tres rondas permanece vigente.

Los datos operativos viven en `git rev-parse --git-path constellation`, separados
por sesión y protegidos con un bloqueo. Se registran estados, hashes y evidencia
operativa; no se guardan prompts, transcripciones, texto de comandos ni salidas.
La revisión escrita debe contener evidencia publicable, nunca conversaciones.

El guarda cubre `apply_patch`, no todas las escrituras posibles de shell o MCP.
La revisión y el cierre verifican los artefactos y detectan archivos nuevos sin
declarar. Los controles no son un sandbox ni un detector universal de secretos.
No certifican la verdad de una explicación o la suficiencia intelectual de una
prueba: esa parte exige revisión del agente.

Los repositorios vecinos conservan su configuración, contratos y pruebas.
Los perfiles propios migrados conservan la doctrina en `.codex/PROJECT.md` y
usan el motor común. Sus proyecciones anteriores se archivaron localmente antes
de retirarlas; `.claude/` se conserva y los validadores Git siguen ejecutándose.
El post-commit de Sweeplab reconoce los commits del coordinador para no crear
commits o pushes secundarios. El generador reconoce
`profile.json` en cualquiera de ellos y nunca lo sobrescribe.
El adaptador usa datos de contratos y código fijo del paquete; un evento dirigido
a un vecino no importa scripts de ese vecino ni le instala nada. Las utilidades de investigación de `.claude/` siguen disponibles
cuando el trabajo las necesita; este perfil no las carga como ritual inicial.

`.codex/profile.json` declara propiedad nativa. `codex_sync.py --repo .` y sus
modos de comprobación respetan el perfil; los repositorios que aún usan proyección
conservan su funcionamiento. El generador y doctor de Claude requieren Python
3.12+, independiente del flujo nativo. Para verificar solo el hub:

```sh
python3.12 .claude/tests/test_codex_sync.py
python3.12 .claude/tests/test_codex_projection_safety.py
python3.12 .claude/scripts/codex_sync.py --repo . --check
python3.12 .claude/scripts/codex_sync.py --repo . --verify
```

La proyección anterior se conserva íntegra en un archivo privado local fuera
del repositorio. Incluye los cambios locales previos de su manifest y skill
de vídeo; no se carga como configuración activa. Las versiones publicadas
anteriores también permanecen en la historia de Git. Recupera solo los archivos
que necesites tras revisar el diff; no restaures toda la carpeta sobre trabajo
posterior ni ejecutes una proyección global para deshacer esto.
