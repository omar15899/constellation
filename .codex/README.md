# Codex: entrada y ciclo vigentes

Constellation usa una sola entrada: `python3 .codex/ecosystem/cli.py`. Sus
subcomandos `git`, `workspace` y `agent-policy` cargan el runtime de
`ecosystem/runtime/`. No hay lanzadores alternativos en la raíz de `.codex/`.

Lee [AGENTS.md](../AGENTS.md), [WORKSPACE.md](WORKSPACE.md),
[REVIEW.md](../REVIEW.md) y el contrato del repositorio receptor. Cada dueño Git
conserva archivos, índice, pruebas y publicación. El registro no concede acceso
a nuevos datos. Claude conserva sus ajustes y automatizaciones; no es un
prerrequisito para trabajar desde este perfil.

## Elegir la entrada

| Trabajo | Entrada |
| --- | --- |
| Un dueño Git | `cli.py git --root RUTA --session ID OPERACION` |
| Varios dueños o rutas desde el hub | `cli.py workspace --session ID OPERACION` |
| Política efectiva de capacidad | `cli.py agent-policy show` |
| Evidencia sin Git | Operaciones portables documentadas en el [protocolo](ecosystem/references/protocol.md). |

Desde la raíz del checkout se puede omitir `--root`. Coloca `--session ID`
después de `git` o `workspace` y antes de la operación. Usa la identidad
comunicada por el cliente; no compartas `manual` entre tareas concurrentes.
Una corrección del usuario conserva el encargo activo: no lo reinicies para
borrar obligaciones o hallazgos.

El perfil hereda modelo, esfuerzo, permisos y capacidad efectiva del cliente.
Hasta 64 subagentes es un máximo compartido, sujeto a límites menores; no una
cuota. `dispatch --capacity N` propone paquetes y dependencias, pero no inicia
agentes ni acredita trabajo. Da a cada escritor rutas exclusivas; el coordinador
integra y publica.

## Declarar, implementar y comprobar

El ciclo de un solo dueño empieza con upstream y alcance exacto:

```sh
python3 .codex/ecosystem/cli.py git --session ID begin --turn inicio
python3 .codex/ecosystem/cli.py git --session ID plan < plan.json
```

`begin` comprueba el remoto y sólo admite fast-forward seguro con árbol limpio.
No hace stash, rebase ni sobreescribe trabajo. Úsalo para un encargo nuevo,
no para sustituir uno pendiente sin decisión del usuario.

El plan contiene requisitos observables y archivos relativos exactos:

```json
{
  "requirements": ["La función gestiona la entrada vacía"],
  "paths": ["src/example.py", "tests/test_example.py"]
}
```

Sustituye las rutas por las del encargo. Las consultas usan `paths: []`.
`deletions` declara retiradas exactas versionadas; `adopt_existing` justifica
cada cambio previo integrado, sin apropiarse de autoría ajena. `unrelated`
conserva nuevas rutas de otro trabajo fuera de la selección. Un plan no autoriza
editar repositorios o datos externos no incluidos.

Ejecuta checks pertinentes sobre los artefactos actuales:

```sh
python3 .codex/ecosystem/cli.py git --session ID check -- git diff --check
python3 .codex/ecosystem/cli.py git --session ID check --timeout 1200 -- python3 -B -m unittest discover -s tests -v
```

Un fallo posterior invalida el éxito anterior de ese comando. Cambiar los
artefactos requiere evidencia vigente. Un comando omitido, timeout o check que
modificó la entrega no es un pase.

## Revisión independiente

Registra todos los autores reales y sus rutas antes de abrir la ronda:

```sh
python3 .codex/ecosystem/cli.py git --session ID review-author < author.json
python3 .codex/ecosystem/cli.py git --session ID review-context
python3 .codex/ecosystem/cli.py git --session ID review-start
```

`author.json` contiene `{"author":"ID_NATIVO_REAL","paths":["ruta"]}`.
La autoría es acumulativa. Entrega token, requisitos, diff y evidencia a
revisores que hayan inspeccionado realmente los archivos.

| Modo | Mínimo independiente por archivo |
| --- | --- |
| Quick | Una persona de corrección. |
| Standard | Tres personas de corrección. |
| Deep | Tres de corrección y dos de seguridad. |

Cada archivo necesita la cuota por foco y el total de personas distintas.
Respeta la política y cualquier mínimo más estricto del receptor. Autor y
descubridor no verifican el cierre de su propio hallazgo. Todos los hallazgos
abiertos bloquean; el coordinador registra informes reales con `review-report`
y verificaciones independientes con `review-resolve`. El campo `role` del
informe es `reviewer`; `focus` expresa corrección o seguridad.

La política y el ledger actuales usan esquema 2; los formatos retirados se
rechazan conservando su historial. No hay un máximo universal de rondas.
`review-budget` registra un plazo UTC y una razón sin borrar rondas. Sin plazo,
el presupuesto es desconocido. La repetición sin observación independiente nueva
exige una razón y una acción concreta mediante las opciones de continuación de
`review-start`.

Después de los informes, `review` recibe una clave por requisito exacto y
evidencia concreta como valor. Hashes y quórums comprueban versión y cobertura;
no demuestran por sí solos la pertinencia de una prueba o la verdad de un texto.

## Resolver una invocación de check incorrecta

El camino normal es corregir y repetir el mismo check. Si la invocación era
incorrecta, `check-resolve` puede vincularla a un reemplazo equivalente, sin
borrar el fallo. Su payload exacto es:

```json
{
  "token": "TOKEN_ACTUAL",
  "failed_check": 1,
  "replacement_check": 3,
  "verifier": "ID_NATIVO_REAL",
  "reason": "Motivo concreto de la invocación incorrecta",
  "evidence": "Comparación independiente de propósito, escenarios y resultado"
}
```

Los índices son ejemplos; usa los de `status`. El fallo debe haber terminado con
salida positiva y sin mutar artefactos, y el reemplazo debe ser posterior,
satisfactorio y vigente para todo el alcance. Ambos son los últimos intentos
de sus comandos. El verificador necesita un informe de corrección actual que
cubra el alcance completo y ser independiente de los contribuyentes. No se
convalidan timeouts, fallos de arranque, mutaciones ni resultados inciertos.

`review`, `commit` y `finish` revalidan la atestación. Cambios de contrato,
destino, autores, política, artefactos o checks pueden invalidarla. Su registro
no concede publicación ni sustituye revisión sustantiva.

## Publicar y cerrar

```sh
python3 .codex/ecosystem/cli.py git --session ID review < evidence.json
python3 .codex/ecosystem/cli.py git --session ID commit -m 'Mejora el comportamiento' ruta1 ruta2
python3 .codex/ecosystem/cli.py git --session ID finish
```

Selecciona rutas explícitas. `commit --preserve-index` sólo admite trabajo
preparado ajeno disjunto y comprueba su conservación. La publicación normal
incluye los commits salientes de la rama, no sólo los del turno: inspecciónalos
y conserva el upstream congelado. No uses force-push, descartes, amend o rebase
para superar un bloqueo.

El `finish` del ciclo Git compartido es una operación de publicación: tras sus
controles llama a `publish`, sincroniza el upstream, publica el HEAD si hay
commits salientes y verifica el SHA remoto. Conserva esos efectos incluso con
`paths: []`. Requiere revisión vigente y entregables comprometidos.

Para trabajo puramente local sin obligación Git, usa la vía directa o la API
portable; su `close` no publica. El adaptador propio de OmarOS permite un cierre
local de consultas sin entregables ni delegados bajo su contrato especializado;
esa conducta no pertenece a `cli.py git finish`. Si una fase falla, conserva el
progreso y comunica el impedimento; no declares completa una entrega pendiente.

## Instalación, confianza y límites

La [guía del paquete](ecosystem/docs/migrations.md) describe el formato actual,
con recibo Codex 3 y recibo Claude 1. El hub puede instalar sus hooks Git con
`python3 .codex/install.py` sólo sin sustituir hooks ajenos. Los eventos del
cliente pertenecen al plugin, no a un segundo manifiesto del hub.

La confianza de hooks se revisa en `/hooks` y no se concede al instalar. No
edites hashes ni eludas esa aprobación. Un catálogo fresco tampoco representa
necesariamente un chat abierto. Los límites y la aceptación Windows pendiente
están en [compatibilidad](ecosystem/docs/compatibility.md).

El [progreso](ecosystem/docs/progress.md) conserva hitos curados en el almacén
privado existente. La proyección a OmarOS requiere raíz, alias y visibilidad
personal autorizados exactamente. Su adaptador activo de cuatro recursos
fijados en 1.2.0 conserva su contrato; el plugin no lo reemplaza.

No se persisten prompts, transcripciones ni salidas brutas en evidencia
publicable. El guarda de rutas no sustituye el sandbox del cliente ni cubre
todas las escrituras de shell/MCP. Los formatos incompatibles se rechazan,
preservando archivos para una decisión explícita.
