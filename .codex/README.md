# Codex nativo: pequeño y verificable

Para coordinar proyectos desde `~/GitHub` o desde cualquier hijo, empieza en
[WORKSPACE.md](WORKSPACE.md). `workspace.py` distribuye rutas y ejecuta este
ciclo por cada dueño Git. El registro operativo está en `repositories.json`;
los proyectos propios usan perfiles nativos y `ruflo` conserva su perfil externo.
La sección de uso siguiente documenta el motor de **un solo repositorio**.

El perfil mantiene instrucciones breves y un único programa de ejecución,
adaptado de OmarOS. Codex trabaja directamente; no necesita proyectar Claude,
cargar agentes especializados ni recorrer una cadena de skills. El modelo,
esfuerzo y permisos se heredan de los ajustes del usuario.

| Aspecto | Proyección anterior | Perfil nativo |
| --- | --- | --- |
| Contrato de Codex | Entrada → kernel Claude → contratos y roles | `AGENTS.md` propio |
| Agentes especializados | 3 | 0 |
| Skills del hub cargadas | 14 | 0; herramientas y skills generales disponibles según la tarea |
| Automatismos Codex | 8 comandos en 4 eventos, con adaptador Claude | 3 comandos en 3 eventos |
| Verificación | Hooks dispersos y evidencia de ejecución | Prueba real, revisión independiente vigente y publicación comprobada |
| Dependencias del flujo | Adaptador y scripts de Claude | Python estándar 3.9+ y Git |

La [guía oficial de modelos](https://developers.openai.com/api/docs/guides/latest-model),
consultada el 2026-09-09, orienta las decisiones sobre autonomía, conflictos entre
instrucciones, delegación selectiva, claridad y pruebas proporcionales. Aplicar
esa guía a las instrucciones no requiere cambiar el modelo que Omar elija.

## Contexto de un millón de tokens

El `config.toml` de este proyecto establece `model_context_window = 1000000`
y `model_auto_compact_token_limit = 900000`. Se conserva el modelo del usuario;
GPT-6 Astra y GPT-5.6 Sol documentan ventanas de 1.050.000 tokens. El ajuste se
aplica al hub y no cambia el archivo global `~/.codex/config.toml`.

Reabre Codex e inicia una tarea nueva en GitHub para cargarlo. La compactación
puede resumir el historial al alcanzar el umbral; no recupera detalle ya
resumido ni aumenta la cuota de uso. Si eliges un modelo de menor ventana,
retira estos dos overrides o ajústalos a su capacidad documentada. Un contexto
más largo puede aumentar consumo y latencia.
[Referencia de configuración](https://learn.chatgpt.com/docs/config-file/config-reference).

## Uso

Desde la raíz del hub, ejecuta `python3 .codex/workflow.py`. El CLI usa
`CODEX_THREAD_ID`; si el hook comunica otra sesión, añade `--session ID` antes
del subcomando. No compartas la sesión `manual` entre trabajos concurrentes.

1. `begin --turn ID` comprueba el upstream si no lo hizo el hook de inicio.
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

Los hooks de Codex están en `hooks.json`: `UserPromptSubmit` comprueba el remoto;
`PreToolUse` valida las rutas de `apply_patch`; `Stop` exige cierre verificado.
Los dos intentos de continuación de Stop son acotados; después informa
`INCOMPLETE` y no finge que el trabajo terminó. Los scripts no crean agentes,
procesos residentes ni commits dentro de Stop.

Para activar las definiciones nuevas, revísalas en `/hooks` y confía cada una
mediante la interfaz nativa. Reabre la sesión para cargar el perfil. Comprueba
que `hooks/list` muestra las tres definiciones del proyecto como `trusted`.
`enabled: true`, instalar los hooks de Git y pasar los tests son hechos distintos
de esa confianza. No edites hashes de confianza ni uses opciones para eludirla.
[Documentación oficial de hooks](https://learn.chatgpt.com/docs/hooks).

## Alcance y límites

La concurrencia se define en [agent-policy.json](agent-policy.json): seis
subagentes por defecto y ocho en el hub. El primario no cuenta. El comando
`python3 .codex/agent_policy.py show` muestra la política efectiva;
`check` detecta divergencias y `apply --repo RUTA` actualiza únicamente las rutas
de configuración declaradas en el plan. Reinicia la sesión para cargar cambios.
No modifica modelo, esfuerzo, permisos, confianza ni configuración global.
[OpenAI Docs: subagentes](https://learn.chatgpt.com/docs/agent-configuration/subagents).

La revisión independiente se aplica a los repositorios nativos registrados
que usan este motor. Comprueba identidad declarada, cobertura, huellas y estados;
no autentica la identidad del proceso revisor ni demuestra la verdad del informe.
La política clasifica rutas, no comprende por sí sola el riesgo semántico: el
coordinador debe aumentar la revisión cuando el comportamiento lo requiera.
Las pruebas CI del hub ejercitan el motor en clones y remotos locales desechables.
No se instala un servicio de revisión AI en GitHub ni se cambian sus protecciones.

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
Los hooks validan el repositorio efectivo y el marcador nativo antes de
crear estado; un evento dirigido a un vecino no ejecuta el flujo del hub ni
le instala nada. Las utilidades de investigación de `.claude/` siguen disponibles
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

El perfil anterior quedó íntegro en `.codex_NOTUSE/`, ignorado por Git. Incluye
los cambios locales previos de su manifest y skill de vídeo. Las versiones
publicadas anteriores también permanecen en la historia de Git. Recupera solo
los archivos que necesites tras revisar el diff; no restaures toda la carpeta
sobre trabajo posterior ni ejecutes una proyección global para deshacer esto.
