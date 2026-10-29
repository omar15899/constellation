# Trabajar desde GitHub o desde un proyecto

El hub es un repositorio y sus carpetas de proyecto son otros repositorios.
Un archivo pertenece a la raíz que devuelve Git para su directorio; su posición
en una carpeta no lo convierte en parte del índice del padre. El coordinador
usa esa propiedad real y mantiene un contrato, revisión y publicación por dueño.

Ejecuta `python3 ~/GitHub/.codex/workspace.py` desde cualquier carpeta. Sus rutas
son siempre relativas a `~/GitHub`, no al directorio de la terminal. Para un hub
clonado en otra ubicación, invoca su script; la raíz por defecto es la que contiene
ese script. `--root` permite seleccionar explícitamente otro hub compatible.

## Localizar y declarar

```sh
python3 ~/GitHub/.codex/workspace.py route Shared/README.md PricingLab/README.md
```

`route` es de solo lectura: muestra dueño, ruta interna, rama, upstream e
instrucciones aplicables. Lee esas instrucciones antes de escribir. El registro
`repositories.json` distingue perfiles nativos de proyectos externos; nunca
se usa una tabla de nombres para adivinar el remoto. Un repositorio nuevo se
registra explícitamente; las dependencias descargadas dentro de builds quedan
fuera. Un proyecto registrado que no esté clonado no necesita inicializarse.

Usa la sesión comunicada por el hook, o `CODEX_THREAD_ID`. Fuera de Codex elige
un identificador propio con `--session ID`; no compartas `manual` entre tareas.
Este ejemplo declara una actualización documental en dos proyectos:

```sh
python3 ~/GitHub/.codex/workspace.py --session ejemplo plan <<'JSON'
{
  "requirements": ["Ambos README describen el mismo contrato de datos"],
  "paths": ["Shared/README.md", "PricingLab/README.md"],
  "depends_on": {"PricingLab": ["Shared"]}
}
JSON
```

El plan comprueba el upstream de los participantes, integra solo fast-forward
seguro y divide las rutas por dueño. No sincroniza proyectos ajenos a la tarea.
Un archivo modificado antes del inicio exige `adopt_existing` con justificación
por ruta. `deletions` enumera retiradas exactas. `unrelated` explica archivos
nuevos producidos por otra actividad; nunca permite omitir un entregable.
`extend_existing: true` integra un contrato anterior explícitamente y conserva
sus requisitos. Los ciclos de dependencias y los repositorios no registrados
se rechazan. `external_repositories` debe enumerar los externos expresamente
incluidos en una tarea; clasificarlos no autoriza modificarlos.

## Distribuir el trabajo

Tras el plan, `workspace.py --session ID dispatch --capacity N` devuelve un
grafo de tareas y oleadas estables para los participantes. Respeta `depends_on`,
el presupuesto común y los límites por repositorio. Elige N según la capacidad
real disponible del cliente, descontando agentes ya activos. El comando no
inicia procesos, no contacta remotos ni altera el estado del ciclo.

Los paquetes incluyen requisitos, contratos, rutas, destino congelado sin URL
y cobertura de revisión. Sólo implementación recibe rutas de escritura. El
coordinador lanza agentes nativos para las tareas de agentes y ejecuta los checks
y la integración. Los perfiles de `ecosystem/agents/` conservan modelo y esfuerzo; si la
superficie no los carga, usa sus instrucciones con los agentes disponibles.
Consulta [RESEARCH.md](RESEARCH.md) para hipótesis, fuentes, refutación y handoffs.

El token de reparto identifica sus entradas; no es un informe de ejecución ni
el token de `review-start`. Regenera el reparto si cambia el contrato o su
contenido, y abre la revisión sólo después de implementar y comprobar.
Registra los autores reales antes de revisar:

```sh
python3 .codex/workspace.py --session ejemplo review-author --repo Shared <<'JSON'
{"author":"ID_REAL_DEL_SUBAGENTE","paths":["README.md"]}
JSON
```

Este registro se aplica cuando hay archivos y revisión nativa habilitada; las
consultas y los repositorios externos no invocan una puerta nativa deshabilitada.
La implementación consumidora espera los checks de sus proveedores. La integración
espera la revisión de todo el conjunto, publica en orden y reserva `finish` para
después de todos los commits; así no crea una espera circular entre implementación
del consumidor y publicación del proveedor.
Si un participante no tiene cambios propios que comprometer, usa
`workspace.py --session ID publish --repo RUTA`: verifica y publica su HEAD
actual sin crear un commit. También sirve para un proveedor con `paths: []`.
Esta comprobación establece la publicación que necesita su consumidor; omitirla
dejaría la dependencia pendiente. Se rechaza si hay entregables propios sin commit,
revisión incompleta, destino cambiado o un proveedor todavía sin publicar.

Las contribuciones se acumulan y no pueden retirarse para habilitar autorrevisión.
Otro autor o ruta invalida la revisión previa sin borrar hallazgos ni rondas.
Un ID de tarea del reparto no sustituye la identidad real de la herramienta.
Los trabajadores entregan resultados al coordinador, que realiza las operaciones
de publicación. Las tareas de reparación se abren sólo ante hallazgos reales.

## Verificar y publicar

Tras implementar, registra comprobaciones pertinentes con el cwd del dueño:

```sh
python3 ~/GitHub/.codex/workspace.py --session ejemplo check --repo Shared -- git diff --check
python3 ~/GitHub/.codex/workspace.py --session ejemplo check --repo PricingLab -- git diff --check
```

Para código, sustituye esas comprobaciones por las pruebas del comportamiento
modificado. `check --timeout 1200 -- COMANDO` permite pruebas largas; el valor
por defecto es 300 segundos y el máximo 3600. Los timeouts y fallos de lanzamiento
quedan registrados como fallos y exigen repetir con éxito el mismo comando.
La revisión recibe un objeto por repositorio, con cada requisito
exacto como clave y evidencia concreta como valor:

```sh
python3 ~/GitHub/.codex/workspace.py --session ejemplo review <<'JSON'
{
  "Shared": {"Ambos README describen el mismo contrato de datos": "Comparados los campos y tipos con su definición en Shared y su uso en PricingLab."},
  "PricingLab": {"Ambos README describen el mismo contrato de datos": "Comprobado que el ejemplo consumidor usa los campos y tipos documentados por Shared."}
}
JSON
python3 ~/GitHub/.codex/workspace.py --session ejemplo commit -m 'Aclara el contrato de datos' Shared/README.md PricingLab/README.md
python3 ~/GitHub/.codex/workspace.py --session ejemplo finish
```

Un lote crea un commit por repositorio y respeta las dependencias. También puedes
crear varias unidades lógicas usando subconjuntos explícitos de rutas. Se valida
el lote antes de empezar; los commits Git y los pushes siguen siendo operaciones
independientes, sin transacción atómica entre servidores. Si un push falla,
`status` muestra el progreso y el cierre permanece pendiente. Corrige la causa
y reanuda: no deshagas los commits ya publicados ni cambies de rama para ocultar
el fallo. `finish` puede publicar y verificar un commit que quedó pendiente.

Cada publicación usa el SHA revisado y el upstream de la rama vigente; verifica
el SHA con `ls-remote`. Si cambia la rama, remoto, ref o URL, restaura el destino
del contrato o inicia explícitamente una tarea separada para el nuevo destino.
No basta con renovar el mismo plan. Se rechaza un `pushurl` distinto o múltiple para evitar publicar
en un destino y verificar otro. Un índice ocupado se conserva. No se usa
`git add -A`, `--no-verify`, force-push, stash, rebase ni borrado de trabajo.
Los commits previos pendientes de esa rama también salen: revisa su alcance.

Si ya hay trabajo ajeno preparado en el índice y ninguna de sus rutas coincide
con la selección, usa `commit --preserve-index -m 'Mensaje' RUTAS`. Esta opción
emplea el commit por rutas de Git y comprueba que las entradas ajenas conservan
su contenido, modo y estado. No publica esas entradas ni las deshace. Un
solapamiento se rechaza y exige separar la autoría; no se resuelve por fuerza.
El cierre admite trabajo ajeno conservado, pero sigue exigiendo que todos los
archivos del encargo estén comprometidos y su publicación verificada.

Los commits del motor exponen `CONSTELLATION_COMMIT_OWNER=native` únicamente
al subproceso de Git. Los hooks que generan commits o pushes secundarios deben
reconocer ese dueño; los validadores siguen ejecutándose. Sweeplab conserva sus
cinco validadores previos y su comprobación posterior, y delega trazado y push
al coordinador durante estos commits. Fuera de ese contexto mantiene su flujo.

Si un hook crea un commit fuera del alcance, la publicación queda bloqueada
también al reintentar. No basta con volver a ejecutar `commit` o `finish`. La
reparación de historia requiere autorización específica; después, el motor
local ofrece `workflow.py --root RAÍZ --session ID recover SHA_COMPLETO` para
auditar el HEAD reparado, su árbol, revisión, destino y todos los commits desde
el inicio. `recover` no mueve ramas, no modifica archivos ni índices y no hace
push. Solo retira el bloqueo cuando esa evidencia vuelve a ser válida.

## Instrucciones y agentes

### Presupuesto por repositorio

La configuración general `~/.codex/config.toml` declara hasta 64 subagentes.
Los hijos heredan ese ajuste: se retiraron sus 19 archivos que repetían sólo
el valor. Un proyecto necesita configuración local únicamente para una excepción.
`agent-policy.json` expresa el presupuesto de coordinación de la constelación:
`defaults.max_concurrent_threads_per_session` vale 64 y `repositories` permite
sobrescribirlo por dueño Git. El hub y los hijos nativos usan el mismo máximo,
sin excepciones iniciales. Las instrucciones globales permiten decidir cuántos
agentes hacen falta según la tarea.
Son máximos de subagentes simultáneos, excluido el coordinador, no un objetivo de
consumo. El cliente puede imponer un límite menor. Una sesión que coordina varios
repositorios conserva un único límite de ejecución; no suma los presupuestos.
Al delegar aplica también el presupuesto del repositorio afectado. La política
no puede cambiar el límite de una sesión ya iniciada.

```sh
python3 .codex/agent_policy.py show
python3 .codex/agent_policy.py check --repo Shared
python3 .codex/agent_policy.py --session ejemplo apply --repo Shared
```

Para cambiar el límite, declara la política y los `.codex/config.toml` afectados
en un plan, edita el JSON y aplica los repositorios seleccionados explícitamente.
`check` compara declaraciones locales o heredadas del archivo global; no evalúa
overrides de CLI, perfiles o administración ni acredita ejecución. El diagnóstico
`ecosystem/native.py --capabilities` consulta la configuración efectiva de un
proceso nativo nuevo. `apply` conserva los demás ajustes y rechaza configuración
ambigua, destinos externos y rutas sin declarar. Reinicia Codex o abre una sesión
nueva para cargar el resultado. El registro de repositorios y Git delimitan
destinos; no se modifica `~/.codex/config.toml`. La clave nativa documentada es
`agents.max_concurrent_threads_per_session`.

### Revisión independiente

La política [review-policy.json](ecosystem/runtime/review-policy.json) selecciona Quick para
documentación, Standard para cambios ordinarios y Deep para rutas sensibles,
incluidos el motor y CI. Cuando la política efectiva permite `allow_quick_code`,
un cambio de código acotado puede usar `review-start --quick-code-reason TEXTO`
antes de la primera ronda. La justificación queda ligada al snapshot completo;
un cambio posterior la invalida. No reduce Deep, mínimos locales ni quórums.
El revisor comprueba también que la clasificación sea adecuada.
El coordinador puede elevar el riesgo semántico con
`review-start --risk deep`; no puede reducir el mínimo durante la tarea.
Quick exige un revisor independiente de corrección; Standard exige tres.
Deep exige cinco: tres de corrección y dos de seguridad. Cada archivo necesita
el número exigido de revisores por foco y el total de personas distintas del modo.
Se pueden ejecutar sucesivamente
cuando no haya capacidad paralela. Consulta [REVIEW.md](../REVIEW.md) y las
invariantes locales antes de revisar.

```sh
python3 .codex/workspace.py --session ejemplo review-context --repo Shared
python3 .codex/workspace.py --session ejemplo review-start --repo Shared
```

`review-context` no abre una ronda. `review-start` devuelve un token de los
requisitos, alcance, política y contenido/permisos actuales. Entrega ese token
y el diff al revisor. Tras inspeccionar realmente los archivos, registra su
informe mediante `review-report --repo Shared`, con JSON por stdin:

```json
{
  "token": "TOKEN_DEVUELTO_POR_REVIEW_START",
  "reviewer": "identificador-real-del-subagente",
  "role": "reviewer",
  "focus": ["correctness"],
  "paths": ["README.md"],
  "summary": "0 hallazgos accionables.",
  "evidence": "Comprobado el ejemplo contra la interfaz y las pruebas del proyecto.",
  "findings": []
}
```

Usa las rutas reales del contrato; cada foco obligatorio debe cubrirlas todas
con su cuota por archivo. La unión de rutas sin esa multiplicidad no basta.
Para Standard registra tres informes de corrección; para Deep añade dos informes
de agentes de seguridad distintos con `focus: ["security"]`. Los IDs
son declaraciones verificables por el coordinador, no identidades autenticadas
por este programa. Nunca inventes un revisor ni copies su conversación al estado.

Cada hallazgo incluye `id` estable, `path`, `line`, `severity` (critical, high,
medium, low), `origin` (introduced, preexisting), `scenario`, `consequence` y
`evidence`. Todos los hallazgos abiertos bloquean. Para corregir, modifica y
prueba los archivos, abre la siguiente ronda y consigue una verificación distinta
del autor y del descubridor. `review-resolve --repo Shared` recibe:

```json
{
  "token": "TOKEN_ACTUAL",
  "id": "identificador-del-hallazgo",
  "verifier": "identificador-real-del-verificador",
  "disposition": "fixed",
  "evidence": "La reproducción ahora pasa y el caso adverso queda cubierto."
}
```

`dismissed` requiere igualmente evidencia independiente para un falso positivo
o comportamiento deliberado. Omitir un hallazgo en el siguiente informe no lo
resuelve. Una modificación posterior exige revalidar su cierre. Replanificar
conserva el contador, los hallazgos, los autores y los mínimos. Abrir la misma
versión es idempotente. No hay un máximo universal de tres rondas: continúa
autónomamente cuando la siguiente acción tenga fundamento y respete el presupuesto
real. Ante repetición o falta de progreso, registra una razón y una acción
concreta; el motor rechaza reutilizar la misma declaración para el mismo ciclo
y la misma base de observaciones independientes. `review-context.adaptation`
expone la señal observada y `continuation_required`. Un archivo distinto no
demuestra progreso semántico: ese juicio sigue correspondiendo al coordinador.

```sh
python3 .codex/workspace.py --session ejemplo review-start --repo Shared \
  --continuation-reason 'El nuevo contraejemplo permite aislar la causa' \
  --continuation-next-action 'Contrastar la reparación con ese caso y su límite'
```

Ambas opciones se suministran juntas. Una continuación no resuelve hallazgos ni
reduce la cobertura. Si falta una decisión material del usuario o un permiso
nativo, informa del impedimento; cambiar de sesión no evita ese requisito.

El presupuesto de revisión usa un plazo UTC explícito, no una estimación de
tokens. El coordinador lo declara o amplía con revisión esperada y motivo:

```sh
python3 .codex/workspace.py --session ejemplo review-budget --repo Shared <<'JSON'
{"expected_budget_revision":0,"deadline_at":"2026-10-19T12:00:00Z","reason":"Plazo explícito asignado a esta revisión"}
JSON
```

Adapta el plazo al presupuesto realmente autorizado. `deadline_at` admite UTC
ISO 8601 con segundos y `Z` o `+00:00`; no admite quitarlo con `null`.
Sin presupuesto previo, su revisión es cero; cada actualización nueva añade
una entrada al historial. `review-context` expone `budget.revision`,
`budget.deadline_at` y `budget.status`: `unknown` si no se declaró, `available`
antes del plazo y `exhausted` al alcanzarlo. Desconocido no significa ilimitado.
Un plazo agotado impide abrir una versión nueva; permite consultar o repetir la
ronda vigente, registrar informes, resolver hallazgos y validar evidencia.
Una ampliación requiere la revisión actual y un motivo explícito; no borra
rondas ni historial. Este control no mide tokens ni cambia límites del cliente.

Cambiar la política invalida la evidencia: abre otra ronda, conservando los
hallazgos y los mínimos más estrictos de riesgo y cobertura. La migración de
políticas de esquema 1 elimina el antiguo `max_rounds`; el esquema 2 ya no lo
admite. Los demás mínimos se conservan, incluidos los más estrictos del receptor.

Después registra la evidencia de cada requisito con `review` y publica con el
flujo habitual. `commit` y `finish` comprueban también esta puerta. Los comandos
equivalentes de `workflow.py` no necesitan `--repo`. Una consulta con `paths: []`
no requiere subagentes. Esta puerta es local: la CI del hub prueba los controles,
pero GitHub sólo los exige para fusionar si sus reglas remotas lo configuran.

El hub mantiene el motor; cada proyecto nativo mantiene una entrada breve y sus
reglas técnicas en `.codex/PROJECT.md`. Claude conserva su sistema. Codex hereda
modelo, esfuerzo, entorno y permisos del usuario. El reparto fija fases y dependencias para la tarea; no
inicia una infraestructura paralela de agentes. Una delegación
útil tiene repositorio, archivos, resultado y verificación definidos; el agente
principal coordina los commits para evitar competencia sobre un mismo índice.

La carga automática de AGENTS.md recorre raíz a cwd al iniciar la sesión; por
eso una sesión iniciada en el hub debe leer los contratos hijos al seleccionarlos.
[OpenAI Docs: instrucciones por directorio](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
La configuración local y la confianza son conceptos distintos; no se editan
hashes de confianza. [OpenAI Docs: configuración de proyecto](https://learn.chatgpt.com/docs/config-file/config-advanced).

Los hooks del plugin, cuando están habilitados y confiados, reconocen contratos
activos de workspace, Git o entregas portables. Un prompt no crea un contrato ni
sincroniza remotos. `SubagentStart` transmite contexto sin modificar el estado.
Las sesiones sin esos hooks usan el mismo CLI explícitamente; los hijos heredan
el plugin y conservan sus hooks Git. El guarda de patches no cubre todas las
escrituras de shell o MCP y no sustituye los permisos del cliente.
La entrada estable, el lock de actualización y la recarga única al migrar desde
un comando antiguo están descritos en
[la instalación del plugin](ecosystem/README.md#instalar-y-actualizar).

El estado mecánico vive bajo el directorio privado de Git, con bloqueos por
workspace y por repositorio. No registra prompts, transcripciones, comandos
ni salidas. Ninguna comprobación de hashes demuestra por sí sola que una
revisión intelectual sea suficiente.

Para trabajos sustanciales, conserva objetivos, decisiones, evidencia y pendientes
mediante [progreso persistente](ecosystem/docs/progress.md). El estado fuente permite
reanudar sin OmarOS; el receptor recibe únicamente hitos personales autorizados
y no convierte una recepción local en publicación remota.
