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
modificado. La revisión recibe un objeto por repositorio, con cada requisito
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

## Instrucciones y agentes

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
