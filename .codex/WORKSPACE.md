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

`agent-policy.json` es la fuente común. `defaults.max_concurrent_threads_per_session`
vale 6 y `repositories` permite sobrescribirlo por dueño Git; el hub usa 8.
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
`check` detecta desvíos. `apply` conserva los demás ajustes y rechaza configuración
ambigua, destinos externos y rutas sin declarar. Reinicia Codex o abre una sesión
nueva para cargar el resultado. El registro de repositorios y Git delimitan
destinos; no se modifica `~/.codex/config.toml`. La clave nativa documentada es
`agents.max_concurrent_threads_per_session`.

### Revisión independiente

La política [review-policy.json](review-policy.json) selecciona Quick para
documentación, Standard para cambios ordinarios y Deep para rutas sensibles,
incluidos el motor y CI. El coordinador puede elevar el riesgo semántico con
`review-start --risk deep`; no puede reducir el mínimo durante la tarea.
Quick y Standard exigen un revisor independiente de corrección. Deep exige dos
revisores distintos y cobertura de seguridad. Se pueden ejecutar sucesivamente
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

Usa las rutas reales del contrato; cada foco obligatorio debe cubrirlas todas,
individualmente o entre sus revisores.
Para Deep añade un informe de otro agente con `focus: ["security"]`. Los IDs
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
conserva el contador y los hallazgos. Abrir la misma versión es idempotente;
hay un máximo de tres versiones revisadas por tarea. Si no converge, replantea
el enfoque con Omar; no borres el registro ni finjas aprobación.

Cambiar la política invalida la evidencia: abre otra ronda, conservando los
hallazgos y los mínimos más estrictos de la tarea. Un cambio de política nunca
reduce su revisión vigente ni amplía retroactivamente el máximo de rondas.

Después registra la evidencia de cada requisito con `review` y publica con el
flujo habitual. `commit` y `finish` comprueban también esta puerta. Los comandos
equivalentes de `workflow.py` no necesitan `--repo`. Una consulta con `paths: []`
no requiere subagentes. Esta puerta es local: la CI del hub prueba los controles,
pero GitHub sólo los exige para fusionar si sus reglas remotas lo configuran.

El hub mantiene el motor; cada proyecto nativo mantiene una entrada breve y sus
reglas técnicas en `.codex/PROJECT.md`. Claude conserva su sistema. Codex hereda
modelo, esfuerzo, entorno y permisos del usuario, salvo los ajustes expresamente
conservados en el hub. No necesita una cadena fija de agentes. Una delegación
útil tiene repositorio, archivos, resultado y verificación definidos; el agente
principal coordina los commits para evitar competencia sobre un mismo índice.

La carga automática de AGENTS.md recorre raíz a cwd al iniciar la sesión; por
eso una sesión iniciada en el hub debe leer los contratos hijos al seleccionarlos.
[OpenAI Docs: instrucciones por directorio](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
La configuración local y la confianza son conceptos distintos; no se editan
hashes de confianza. [OpenAI Docs: configuración de proyecto](https://learn.chatgpt.com/docs/config-file/config-advanced).

Los hooks del hub, cuando están confiados, usan el contrato de workspace para
comprobar patches y cierre de todos sus participantes. Las sesiones sin esos
hooks ejecutan el mismo CLI explícitamente. Los hijos no reciben nuevos hooks
Codex; sus hooks Git siguen aplicándose. El guarda de patches no cubre todas
las escrituras de shell o MCP y no sustituye los permisos del cliente.

El estado mecánico vive bajo el directorio privado de Git, con bloqueos por
workspace y por repositorio. No registra prompts, transcripciones, comandos
ni salidas. Ninguna comprobación de hashes demuestra por sí sola que una
revisión intelectual sea suficiente.
