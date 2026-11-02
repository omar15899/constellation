# Perfil OmarOS de Constellation

El módulo `omaros` de la distribución POSIX añade las operaciones del vault,
las skills específicas del proyecto y la recepción del diario al sistema
compartido. Requiere Python 3.11+ con PyYAML. Usa la raíz Git registrada por
el operador y preserva los contratos de sesión bajo el directorio privado de
esa raíz.

Las rutas y ejemplos siguientes se ejecutan desde la raíz de OmarOS.
`.codex/workflow.py` es el punto de entrada del proyecto y delega en el
paquete instalado. Sustituye `~/.venvs/omaros/bin/python` por el intérprete
del perfil en ese equipo. Las convenciones de contenido, metadatos y
privacidad pertenecen a los documentos de contexto del vault.

## Un ciclo local por encargo

Ejecuta desde la raíz con `~/.venvs/omaros/bin/python .codex/workflow.py`.
El perfil requiere Python 3.11+ y PyYAML; el entorno designado ya proporciona
esas dependencias. En las llamadas siguientes, `ID` representa la sesión
comunicada por el hook. Si `CODEX_THREAD_ID` coincide, se puede omitir `--session`.
Fuera de Codex usa una identidad propia; no compartas `manual` entre tareas.

El hook de inicio, cuando esté confiado y activo, comprueba el upstream.
En una sesión sin esos hooks, hazlo explícitamente:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID begin --turn inicio
```

El inicio hace fetch y permite integración fast-forward segura cuando el árbol
está limpio. Divergencia o cambios locales incompatibles dejan un impedimento;
no hace stash, rebase ni sobrescribe archivos. Una consulta puramente local,
con `paths: []` y sin delegados, puede continuar aunque el inicio registre un
error de sincronización o no exista upstream. Su cierre es local, según se
explica abajo. `begin` inicia un encargo nuevo y conserva el estado anterior
en historial privado: no lo uses para reiniciar una tarea pendiente o eludir
hallazgos y rondas. Una corrección del usuario actualiza el plan conservando
el objetivo vigente.

Declara requisitos observables y rutas relativas exactas por stdin. Una
consulta sin entregables usa `paths: []`:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID plan <<'JSON'
{
  "requirements": ["La nota explica el mecanismo y justifica la derivación"],
  "paths": ["06_Knowledge_Base/Mathematics/Calculus/derivada.md"]
}
JSON
```

Las bajas intencionadas de archivos versionados se autorizan por ruta exacta en
`deletions`, como subconjunto de `paths`:

```json
{"requirements":["Retirar un archivo obsoleto"],
 "paths":["ruta/obsoleto.py"],
 "deletions":["ruta/obsoleto.py"]}
```

La revisión y la publicación exigen que las rutas declaradas estén ausentes.
Las bajas conservan las obligaciones de comprobación, revisión independiente,
commit y publicación.
Usa `renames` cuando el archivo se conserve íntegro en otro destino; una baja
real no necesita un renombre archivístico.

Escoge antes de escribir el dominio, si extiendes un archivo existente y qué
estructura, metadatos y enlaces necesita. Las notas respetan los esquemas de
`19_Metadata_and_Schema/`; investigación y conocimiento llevan `latex_pending`
y las hojas de conocimiento exigen subdominio/área/archivo. Un índice de
subdominio puede ocupar `06_Knowledge_Base/<subdominio>/<archivo>.md` solo con
`note_type: moc`, `domain: 06_Knowledge_Base` y `subdomain` idéntico al nombre de
esa carpeta. La excepción depende de su función y coherencia, no del nombre del
archivo; no permite notas en la raíz de `06` ni relaja privacidad, metadatos o
publicación. El trabajo no trivial declara
también una traza breve en `11_Documents_and_Reports/Execution_Traces/YYYY-MM-DD/`.
No crees notas para una explicación pedida solo en conversación.

Si una ruta ya estaba modificada al iniciar, inspecciona la propiedad y el diff.
`adopt_existing` recibe un mapa ruta → justificación explícita por archivo;
no convierte cambios ajenos en propios. `unrelated` justifica archivos nuevos
de otra actividad y los conserva fuera del commit. No permite omitir entregables.
Preserva cambios de daemons y trabajo simultáneo.

Tras implementar, el coordinador registra comprobaciones reales:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID check -- git diff --check
~/.venvs/omaros/bin/python .codex/workflow.py --session ID check --timeout 1200 -- ~/.venvs/omaros/bin/python -m unittest discover -s .codex/tests -v
```

`check` registra resultado y huellas de los archivos; no basta con escribir
«tests passed». El timeout por defecto es 300 segundos y se admite de 1 a 3600.
Un fallo, timeout o error de lanzamiento exige una repetición pertinente con
éxito sobre la versión actual. Los checks no deben cambiar entregables.
Para código prueba el comportamiento y sus rechazos relevantes. Para una nota,
revisa argumentos, fuentes, metadatos y enlaces; no añadas tests que solo
reproduzcan una edición trivial ni repitas suites sin cambio o duda concreta.

Si la invocación era equivocada, `check-resolve` permite vincular ese intento a
otra comprobación equivalente que ya haya terminado con éxito sobre la versión
actual. No borra ni modifica los checks originales. Sólo admite intentos cuyo
proceso terminó con código de salida positivo: no sustituye timeouts, señales,
errores de arranque, mutación de entregables ni ejecuciones incompletas de
resultado incierto.
La equivalencia necesita evidencia explícita de un verificador independiente;
el motor comprueba identidad declarada, cobertura y vigencia, no deduce que dos
comandos prueban lo mismo.

Primero ejecuta el reemplazo mediante `check`, registra autores y completa la
revisión independiente vigente con su cuota normal. El verificador debe tener
un informe `correctness` del token actual que cubra todo el alcance, y no puede
ser el autor principal ni contribuyente de los entregables. Entonces registra:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID check-resolve <<'JSON'
{
  "token": "TOKEN_ACTUAL",
  "failed_check": 0,
  "replacement_check": 1,
  "verifier": "ID_NATIVO_DEL_VERIFICADOR",
  "reason": "La invocación apuntaba a un auxiliar inexistente.",
  "evidence": "El verificador comparó el propósito original con la comprobación equivalente ejecutada y sus resultados."
}
JSON
```

Los índices empiezan en cero y corresponden al array `checks` de `status`;
sustituye los valores del ejemplo por los intentos reales. Ambos deben ser los
últimos de sus comandos respectivos y el reemplazo debe ser posterior, completo,
exitoso, sin cambios durante su ejecución y con las huellas actuales de todo el
alcance. El recibo conserva índices, hashes, token, verificador y justificación.
Un reintento idéntico es idempotente. Cambios de artefactos o permisos, contrato,
autoría, política, destino o checks invalidan la atestación; se conserva el
historial y se requiere nueva evidencia y revisión vigente. `review`, `commit`
y `finish` vuelven a comprobar el recibo. Su registro invalida el cierre semántico
anterior y no concede permisos de publicación ni altera el presupuesto de revisión.

## Reparto y capacidad

Después del plan:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID dispatch --capacity 8
```

Devuelve paquetes y oleadas estables para los requisitos, contratos y rutas
actuales. Solo los paquetes de implementación reciben rutas de escritura;
los delegados conservan su frontera de dueño Git y su propio ciclo. El comando
es de lectura: no inicia agentes, contacta remotos, ejecuta instrucciones de
fuentes externas ni registra trabajo como realizado. Su token identifica las
entradas del reparto; no es el token de revisión. Regenera el reparto cuando
cambien contrato o contenido.

El coordinador asigna los paquetes a agentes nativos reales, espera sus
resultados y comprueba sus dependencias. Cada escritor tiene rutas exclusivas;
los trabajadores conservan cambios ajenos y no alteran índices ni publican.
El coordinador integra, ejecuta checks, registra informes y publica.

Los perfiles provienen del catálogo nativo de la instalación central. Si el
cliente no ofrece un rol, transmite sus instrucciones al agente disponible.
Hereda modelo, esfuerzo, entorno y permisos del usuario.

El máximo configurado es 64 subagentes simultáneos además del coordinador,
compartidos por toda la sesión. No es una cuota que consumir ni se suma por
rol, tarea o repositorio delegado. `--capacity N` debe descontar los agentes
ya ocupados y respetar cualquier límite menor del cliente o sesión; el reparto
respeta también un límite de proyecto más bajo. Cambiar `.codex/config.toml`
no amplía una sesión iniciada: reinicia o abre otra para cargarlo.

## Revisión independiente

[La política del perfil](review-policy.json) selecciona el mínimo por riesgo.
Quick exige un revisor de corrección; Standard, tres; Deep, tres de corrección
y dos de seguridad. Cada archivo requiere esa multiplicidad por foco y el total
de personas distintas del modo. Los archivos sensibles elevan la revisión;
`review-start --risk deep` permite elevar también el riesgo semántico. No se
puede rebajar el mínimo de una tarea en curso. Si hay poca capacidad, usa
revisores sucesivos con identidades distintas. `paths: []` no requiere agentes.

Antes de abrir la ronda, registra todos los autores reales, incluidas
contribuciones de integración. Usa la identidad nativa devuelta por la herramienta,
no el nombre del rol ni un ID de tarea:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID review-author <<'JSON'
{"author":"ID_REAL_DEL_IMPLEMENTADOR","paths":["ruta/entregable.md"]}
JSON
~/.venvs/omaros/bin/python .codex/workflow.py --session ID review-context
~/.venvs/omaros/bin/python .codex/workflow.py --session ID review-start
```

El registro es acumulativo: no se retiran contribuyentes para habilitar
la autorrevisión. Otra contribución o ruta invalida la revisión anterior.
`review-context` no abre una ronda; `review-start` fija requisitos, alcance,
autoría, política, contenido y permisos actuales y devuelve un token.
Entrega ese token, requisitos, diff e invariantes a revisores independientes.
Después de que inspeccionen realmente el resultado, registra sus informes:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID review-report <<'JSON'
{
  "token": "TOKEN_ACTUAL",
  "reviewer": "ID_REAL_DEL_REVISOR",
  "role": "reviewer",
  "focus": ["correctness"],
  "paths": ["ruta/entregable.md"],
  "summary": "0 hallazgos accionables.",
  "evidence": "Comprobados la derivación, las hipótesis y los enlaces del archivo.",
  "findings": []
}
JSON
```

Usa rutas reales del contrato y una evidencia que describa lo comprobado.
Para Standard registra tres revisores de corrección; para Deep añade dos
agentes de seguridad distintos con `focus: ["security"]`. La unión de rutas
sin la cuota por archivo no basta. Ningún autor revisa sus archivos. El motor
comprueba declaraciones y cobertura, pero no autentica procesos: el coordinador
responde de usar identidades reales. No inventes informes ni copies conversaciones.

Cada hallazgo incluye `id` estable, `path`, `line`, `severity` (critical, high,
medium, low), `origin` (introduced, preexisting), `scenario`, `consequence` y
`evidence`. Todos los abiertos bloquean. Corrige la clase completa de error y
prueba la regresión cuando sea automatizable. Abre la siguiente ronda para la
versión corregida y consigue un verificador distinto de autores y descubridor:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID review-resolve <<'JSON'
{
  "token": "TOKEN_ACTUAL",
  "id": "ID_ESTABLE_DEL_HALLAZGO",
  "verifier": "ID_REAL_DEL_VERIFICADOR",
  "disposition": "fixed",
  "evidence": "La reproducción ahora pasa y el caso adverso queda cubierto."
}
JSON
```

`dismissed` exige igualmente evidencia independiente para refutar un falso
positivo o justificar un comportamiento deliberado. Omitir un hallazgo no lo
resuelve. Un cambio posterior exige revalidar su cierre. Contenido, permisos,
requisitos, alcance, autoría o política modificados necesitan revisión vigente.
Replanificar conserva hallazgos, historial, mínimos más estrictos y presupuesto.
La misma versión es idempotente y no consume otra ronda. No hay máximo fijo de
rondas: las nuevas versiones se admiten según presupuesto y señales de repetición.
El historial anterior, incluido un límite antiguo de tres, permanece íntegro.

`review-context` devuelve `budget` (`revision`, `deadline_at`, `status`) y
`adaptation`. Sin plazo declarado, `status` es `unknown`; no se presume un tiempo
restante. Un presupuesto se declara o renueva de forma explícita:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID review-budget <<'JSON'
{"expected_budget_revision": 0, "deadline_at": "2030-01-01T12:00:00Z", "reason": "Plazo declarado para completar las obligaciones pendientes."}
JSON
```

El ejemplo requiere sustituir el plazo por el acordado para el encargo. La revisión
esperada evita sobrescribir decisiones concurrentes. Un plazo agotado impide abrir
una ronda nueva, pero conserva los informes y el cierre ya satisfecho, y permite
resolver hallazgos o entregar informes de una ronda existente. El presupuesto no
modifica el token de revisión. `dispatch` incluye sólo su revisión y plazo estables;
el estado temporal se consulta con `review-context`.

Si se repiten artefactos sin observaciones independientes nuevas, el motor exige
una decisión concreta para continuar:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID review-start \
  --continuation-reason "La reproducción anterior no distinguía las dos causas." \
  --continuation-next-action "Aislar cada causa con una entrada independiente y revisar el resultado."
```

Ambos campos son necesarios. Una declaración idéntica para el mismo ciclo y la
misma evidencia independiente se rechaza. No borres el registro ni cambies de
sesión para ocultar rondas, hallazgos o presupuesto.

Una vez satisfecha la revisión independiente, registra evidencia contra cada
requisito exacto del plan mediante `review`:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID review <<'JSON'
{
  "La nota explica el mecanismo y justifica la derivación": "Comprobados el ejemplo, la prueba y sus hipótesis en la versión actual."
}
JSON
```

Una clave por requisito y texto concreto como valor, no booleanos. El motor
valida existencia, metadatos, comprobaciones y vigencia. El coordinador debe
comparar de verdad el resultado con lo solicitado. Los hashes fijan la versión
revisada; no demuestran claridad editorial, verdad matemática ni suficiencia
científica. el documento `REVIEW.md` del vault detalla las obligaciones de cada entregable.

## Commit, índice y cierre

Una consulta puramente local, con `paths: []` y sin `delegates`, registra la
evidencia por requisito con `review` y ejecuta `finish` para cerrar localmente.
No crea commits, hace push ni verifica un SHA remoto. Este cierre sigue exigiendo
revisión vigente y controles de alcance; `Stop` valida su estado local y no
inventa evidencia de publicación. Un fallo de sincronización del inicio no lo
impide. Este cierre local por defecto no satisface a un padre que lo declare
como proveedor: ese caso requiere `finish --publish-readonly`, descrito en la
sección de delegados. Si existe cualquier entregable o delegado, se exige el
cierre ordinario con publicación y verificación remota completo.

Para encargos con entregables:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID commit -m 'Explica la derivación' ruta/entregable.md
~/.venvs/omaros/bin/python .codex/workflow.py --session ID finish
~/.venvs/omaros/bin/python .codex/workflow.py --session ID status
```

Usa rutas explícitas y commits por unidades lógicas; nunca `git add .` ni
`git add -A`. `commit` valida, crea el commit, intenta push normal y verifica
el SHA con `ls-remote`; cuando hay entregables o delegados, `finish` confirma
los archivos propios comprometidos, revisión vigente, alcance y publicación.
Git dispone de 1200 segundos para el commit y sus hooks, 300 para preparar el
lote o contactar el remoto y 25 para las consultas locales.
Conserva el upstream congelado; no adivines
remotos por nombres de proyectos. Una rama, ref, URL o configuración de push
incompatible bloquea el destino: restaura el contrato o inicia un encargo
separado expresamente autorizado. Un reintento no legitima un destino cambiado.

Si ya hay trabajo ajeno preparado y sus rutas son disjuntas:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID commit --preserve-index -m 'Explica la derivación' ruta/entregable.md
```

La opción usa el commit por rutas de Git y comprueba que entradas ajenas
conserven contenido, modo y estado. No publica esas entradas ni las deshace.
Un solapamiento se rechaza y exige resolver la autoría. El cierre admite cambios
ajenos conservados, pero todos los entregables propios deben estar comprometidos
y publicados. No hagas stash, force-push, rebase, amend, reset duro, clean o
descarte para superar un bloqueo. No inspecciones ni gestiones recuentos de worktrees.

Los commits anteriores pendientes de la rama también salen: revisa su alcance.
Si esa historia requiere autorización pendiente, conserva el resultado revisado
sin enviarla mediante un commit local explícito:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID commit --local-only --preserve-index -m 'Conserva la integración revisada' ruta/entregable.md
```

`--local-only` conserva las validaciones de revisión, alcance, destino, contenido
del commit e índice. Omite la publicación y registra `publication_deferred: true`,
los commits y sus rutas; no registra publicación ni cierre. Puedes acumular otras
unidades con `commit --local-only`. En ese contrato, `publish` ordinario, `finish`,
`commit` sin la opción y `begin` quedan bloqueados para preservar esa intención.
`Stop` informa que la tarea sigue pendiente. La bandera pertenece a la sesión;
no impide que otros clientes o contratos Git publiquen la misma rama.

Solo cuando exista autorización para toda la historia saliente y el destino,
reanuda explícitamente:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID publish --resume-deferred
~/.venvs/omaros/bin/python .codex/workflow.py --session ID finish
```

La reanudación aplica los controles habituales y retira la bandera únicamente
después de verificar el SHA remoto. Un fallo la conserva. La opción no concede
permiso para enviar datos privados ni legitima commits previos sin autorización.

Un fallo de red deja progreso pendiente para reanudar; no deshagas commits ya
publicados ni presentes el cierre como completo. Si un hook crea historia fuera
del alcance, no basta reintentar. Una reparación de historia exige autorización
específica; después `recover SHA_COMPLETO` audita el HEAD reparado y la evidencia
sin mover ramas, modificar índices ni publicar.

## Renombres preservados byte a byte

Un archivo versionado y sin cambios al inicio puede archivarse con un renombre
explícito. Declara ambos extremos y el mapa `renames`:

```json
{"requirements":["El archivo se conserva íntegro en antecedentes"],
 "paths":["ruta/original.tex","antecedentes/original.tex"],
 "renames":{"ruta/original.tex":"antecedentes/original.tex"}}
```

El plan fija el blob regular de `initial_head`. La revisión exige el origen
ausente y un destino regular con exactamente los mismos bytes; las demás rutas
siguen existiendo. Copiar sin retirar el origen, cambiar el destino o recrear
el origen no satisface el contrato. Los dos extremos se comprometen juntos.

El destino no debe figurar en `initial_head`, en `baseline_dirty` ni estar
ignorado al declarar el plan. Esto no reconstruye existencia pasada de archivos
ignorados si después cambian las reglas. El flujo no mueve archivos ni autoriza
sobrescribir destinos: comprueba colisiones antes de mover. Los renombres no
admiten fuentes ya modificadas, cambios de contenido posteriores, cadenas,
ciclos, destinos compartidos ni bajas sin copia íntegra declarada. La igualdad
de bytes no garantiza permisos o enlaces internos. `renames` se conserva al
renovar el plan si se omite; retirarlo exige un contrato nuevo explícito que
conserve el alcance.
Las reglas de metadatos, privacidad, checks e índice siguen aplicándose.

## Tareas entre repositorios

Solo una tarea que incluya expresamente otros repositorios usa `delegates`.
Inicia y declara el contrato en cada dueño y añade al plan de OmarOS una lista
de raíces absolutas canónicas con namespace y sesión:

```json
{"root":"/ruta/al/workspace","namespace":"constellation","session":"ID"}
```

Se admiten `omaros` y `constellation`. Cada raíz debe ser un repositorio
independiente con contrato activo y upstream comprobado. No se admite un árbol
entero por prefijo: declara cada hijo implicado. `paths` sigue conteniendo
solo archivos de OmarOS; los externos pertenecen al plan de su dueño.

El guarda lee los contratos mecánicos sin ejecutar código externo, exige rutas
exactas y rechaza cruces de dueño Git, enlaces ambiguos, datos privados y cambios
de destino. Fija rama, remoto, ref y hash de URL. Restaurar el destino es necesario
ante un cambio durante el encargo; renovar el mismo plan no lo legitima.
No cambia permisos ni confianza del cliente.

La revisión de OmarOS exige que cada delegado cierre su propio ciclo con
archivos revisados, comprometidos y publicación verificada. El cierre comprueba
sus remotos antes y después de publicar OmarOS. Un delegado pendiente o una
revisión obsoleta impiden completar el conjunto. Retirarlo solo procede si
Omar retira o reemplaza esa parte del encargo. El reparto local no sustituye
esas comprobaciones ni publica por otro dueño.

Un proveedor OmarOS puede tener `paths: []` y no tener delegados propios. Su
cierre local por defecto no demuestra publicación y el padre lo rechaza.
Cuando el encargo requiera expresamente publicar ese proveedor, registra su
revisión por requisito y ejecuta desde la raíz del proveedor:

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID_PROVEEDOR finish --publish-readonly
```

La opción solo se admite con `paths: []` y sin delegados; otros contratos se
rechazan. No crea un commit: publica el HEAD actual con upstream válido y
destino congelado, aplica los controles de publicación y verifica el SHA remoto
real. Sin upstream válido falla; no convierte un cierre local en publicación
ficticia. `Stop` revalida el destino y la publicación de esa consulta. El padre
comprueba el cierre publicado y sus demás requisitos antes de aceptarlo.

## Instalación, hooks y confianza

Instala el paquete con los módulos `coding`, `mathematics`, `quant-research`,
`writter` y `omaros`, según la [guía de instalación](../docs/migrations.md).
Desde el vault, ejecuta su instalador con el Python del proyecto:

```sh
~/.venvs/omaros/bin/python -I .codex/install.py
```

El instalador del receptor invoca la entrada estable de la instalación
verificada, registra la raíz local del vault y prepara sus guardas Git.
Respeta otros hooks y preferencias del usuario. La instalación corresponde
al equipo; el registro de un directorio no autoriza otro checkout ni sus
repositorios hijos.

En POSIX, el recibo de esquema 4 vincula el intérprete seleccionado al
lanzador `$CODEX_HOME/constellation/run` (por defecto,
`~/.codex/constellation/run`). El cliente invoca los eventos mediante ese
lanzador y el operador puede usarlo para el CLI. Los guardas Git se preparan
como generaciones inmutables en `$CODEX_HOME/constellation-vault-guards/<hash>`.
Bajo el bloqueo de configuración de Git se vuelven a comprobar la raíz y el
valor esperado de `core.hooksPath`. Un cambio concurrente se conserva y detiene
la activación. Las generaciones anteriores permanecen disponibles para Git.

Las definiciones de eventos nativos pertenecen al plugin. `/hooks` muestra
qué definiciones reconoce y en cuáles confía el cliente. Mantén su confianza
en la interfaz y comprueba la activación tras cargar una nueva versión. La
presencia de una definición en un paquete o su verificación mecánica solo
acredita esa capa. Un operador puede usar el CLI explícito con la raíz y
sesión correctas durante la instalación y las pruebas.

`UserPromptSubmit` inicia o preserva el contrato según su estado.
`PreToolUse` controla las ediciones que reconoce el guarda. `SubagentStart`
entrega contexto a los agentes nativos. `Stop` comprueba la revisión y el
cierre vigente. Los hooks Git añaden controles sobre el índice y los commits
salientes también fuera de Codex. Un rechazo conserva la tarea y la causa
para que el coordinador la resuelva. Los permisos efectivos del cliente
limitan los comandos de shell y las herramientas externas.

## Evidencia y límites

Estado y eventos viven en `git rev-parse --git-path omaros`, aislados por sesión
y protegidos por bloqueos. No se registran prompts ni transcripciones. Las
comprobaciones conservan resultados y hashes; las salidas privadas no se
convierten en artefactos publicables. Las trazas humanas contienen solo objetivo,
cambios, evidencia y límites. No hay exportación de conversaciones ni telemetría
de prompts. Un fallo previo bloquea el commit; un fallo posterior se informa,
pero no puede deshacer un commit que Git ya creó.

Las rutas privadas se bloquean al preparar commits y al revisar todos los
commits pendientes de push, aunque un archivo se borre en otro commit. El control
por rutas no detecta todos los secretos incrustados: inspecciona el diff sin
abrir datos privados como contexto incidental. No se lee ni publica conversación,
manifest de conversación, estado de sincronización o log de daemon sin petición
que nombre datos exactos y destino.

Las comprobaciones se ejecutan localmente en el entorno del proyecto:

```sh
~/.venvs/omaros/bin/python -m unittest discover -s .codex/tests -v
```

La suite de integración del receptor usa repositorios, paquetes y remotos
temporales. La revisión comprueba por separado la ejecución real del cliente,
la calidad del resultado y las autorizaciones que requiera la publicación.

## Progreso curado y diario de Constellation

Los trabajos sustanciales registran hitos deliberados con `progress-update`.
`progress-show` devuelve el comienzo del contrato y el estado actual. El primer
checkpoint exige `expected_task_start` y `expected_revision: 0`; los siguientes
exigen el `task_uid` recibido y la longitud actual de `milestones`. El primero
puede indicar `source_alias` para coincidir con la política local; después es
inmutable y se omite del payload. Repetir un
hito idéntico no crea otro; corregirlo requiere un ID nuevo. Replanificar conserva
su identidad. El progreso vive en el JSON privado de la sesión bajo Git y se
recupera sin depender de OmarOS como diario. No cambia checks, revisión ni cierre.

La entrada de `progress-update` contiene `checkpoint` con `id`, `summary`,
`visibility` y `snapshot`. Este último lleva `objectives`, `current`, `completed`,
`decisions`, `findings`, `verification`, `unresolved`, `next_steps` y `references`.
Excepto `current`, las secciones narrativas son listas de frases breves. Las
referencias tienen `kind` (`repository`, `commit`, `experiment`, `documentation`),
`label` y `value`. No introduzcas conversaciones, secretos, logs ni texto privado.
La visibilidad por defecto es `unknown`; solo un checkpoint `personal` de una
raíz autorizada exactamente puede exportarse.

La política local se lee de `$CODEX_HOME/progress-journal.json` (por defecto
`~/.codex/progress-journal.json`) o de `--policy RUTA`. Declara `schema_version: 1`,
`target: {"root": "/ruta/canónica/OmarOS"}` y `sources`, una lista de objetos
`root`, `alias`, `visibility`. Cada raíz y alias debe ser único; una autorización
para un padre no incluye repositorios hijos. `restricted` y `unknown` no exportan.
Ni el registro de proyectos ni el contenido de un envelope conceden autorización.

```sh
~/.venvs/omaros/bin/python .codex/workflow.py --session ID progress-show
~/.venvs/omaros/bin/python .codex/workflow.py --session ID progress-update < checkpoint.json
~/.venvs/omaros/bin/python .codex/workflow.py --session ID progress-export --task-uid UUID > /ruta/privada/envelope.json
~/.venvs/omaros/bin/python .codex/workflow.py --session ID journal-paths --source-root /raíz/personal < /ruta/privada/envelope.json
```

El coordinador declara las dos rutas devueltas en el plan vigente antes de usar
`journal-import` con los mismos argumentos. Son una traza estable bajo
`11_Documents_and_Reports/Execution_Traces/FECHA/` y
`17_Dashboards/Constellation.md`. El receptor valida el destino, el dueño Git,
los metadatos reales y el contenido gestionado. Conserva las secciones manuales;
rechaza notas ajenas, enlaces simbólicos y cambios manuales dentro del bloque
gestionado. Una repetición idéntica no escribe; tras una interrupción se reenvía
el mismo envelope para completar ambas notas. El pequeño índice privado de
recepción conserva la intención pendiente y la trazabilidad necesaria.

`journal-import` solo devuelve un recibo `RECEIVED_LOCAL`. Para guardarlo en el
origen, `progress-ack` recibe `{"task_uid": "UUID", "expected_revision": N, "receipt": RECIBO}` por stdin y vuelve a calcular el envelope
vigente con la política local. El recibo no acredita publicación remota. Revisión,
commit y `finish` conservan el flujo normal del vault; nunca se ejecutan por la
importación. El estado narrado no sustituye verificación científica ni convierte
un proyecto en completado. El diario solo marca `completed` cuando el adaptador
origen aporta el cierre mecánico del workflow.

El hash del envelope detecta cambios y vincula destino y recibo; no es una firma
que autentique a otra persona. El coordinador proporciona la raíz de origen
confiada. La selección de contenido sigue siendo deliberada y respeta las
fronteras personales/corporativas. La sincronización ocurre al registrar e
importar hitos durante el trabajo autorizado; no instala un daemon ni exporta
automáticamente cada mensaje.
