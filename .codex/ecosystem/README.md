# Constellation personal

Tres módulos para encargos de ingeniería, matemáticas y escritura, con un
núcleo de evidencia compartido. Describe el resultado directamente o selecciona
la skill instalada:

```text
$constellation:coding Corrige este defecto, verifica sus consumidores y cierra el cambio.
$constellation:mathematics Examina estas hipótesis y construye una prueba o un contraejemplo.
$constellation:writter Revisa este informe para esta audiencia y comprueba sus fuentes.
```

La selección automática está habilitada. Los nombres de las skills son
`coding`, `mathematics` y exactamente `writter`; Codex añade el espacio de nombres
del plugin. Las tareas mixtas aplican los perfiles pertinentes por entregable.
El modelo, esfuerzo, permisos y presupuesto de agentes se heredan del trabajo
futuro: el paquete no los fija.

## Instalar y actualizar

Necesitas Python 3.11 o posterior, con `python3` resolviendo esa versión también
en el directorio receptor, y un cliente Codex
con plugins locales y agentes TOML. Se comprobó la interfaz nativa de Codex
0.163.0 en macOS. El instalador usa bloqueo POSIX; se cubren macOS y Linux,
sin afirmar compatibilidad con Windows. El núcleo, instalador y validadores usan la biblioteca estándar;
`requirements-dev.txt` declara la dependencia opcional del validador oficial de
`skill-creator`. Git es necesario solamente para los flujos de publicación de
repositorios que lo utilicen. No se crea un repositorio para un trabajo sin Git.

Desde el checkout, crea una distribución en un destino nuevo fuera de las fuentes:

```sh
python3 .codex/ecosystem/build.py --output /tmp/constellation-bundle \
  --archive /tmp/constellation-bundle.zip
python3 /tmp/constellation-bundle/ecosystem/install.py \
  --bundle /tmp/constellation-bundle --codex-home "${CODEX_HOME:-$HOME/.codex}" --check
python3 /tmp/constellation-bundle/ecosystem/install.py \
  --bundle /tmp/constellation-bundle --codex-home "${CODEX_HOME:-$HOME/.codex}"
```

Para un único módulo añade, por ejemplo, `--modules mathematics` al build.
Recibirá su núcleo, referencias, perfiles y pruebas necesarios. Para otro
ordenador, copia el ZIP, extráelo en una carpeta nueva y ejecuta desde ella el
instalador con los dos argumentos anteriores. El checkout original no interviene
en la instalación ni en la ejecución. Un bundle parcial no puede reconstruir
módulos que no contiene: usa el bundle completo para ampliar la selección.

Actualizar consiste en construir un bundle nuevo y repetir el instalador. El
catálogo administrado conserva una ubicación estable dentro de `CODEX_HOME`.
El instalador comprueba sus recibos y hashes, detecta cambios manuales y conflictos,
y usa los comandos nativos para refrescar el plugin. Un plugin deshabilitado
provoca un rechazo previo: la actualización no lo reactiva. Se preservan las
configuraciones y perfiles ajenos. No edites las copias administradas del caché;
mantén los cambios en las fuentes y reconstruye.

Si trabajas en el checkout que mantiene estas mismas skills, excluye sus
entradas fuente después de instalar para evitar duplicarlas con las del plugin:

```sh
python3 /tmp/constellation-bundle/ecosystem/native.py \
  --codex-home "${CODEX_HOME:-$HOME/.codex}" --cwd "$PWD" \
  --exclude-source-root "$PWD/.codex"
```

Ejecuta ese comando desde la raíz del checkout. El helper comprueba el cierre
canónico de recursos de los módulos seleccionados: skills, referencias,
agentes, motor, política, hooks y archivos comunes exportados, incluidas
documentación y pruebas. Si difieren, reconstruye y actualiza antes de excluir.
El helper escribe únicamente sus flags
nativos por ruta; después confirma el descubrimiento con un servidor nuevo.
Es idempotente, conserva las demás preferencias y muestra cualquier resultado
parcial. No cambies confianza para resolver un rechazo. Esta integración es
explícita y no hace falta en un proyecto receptor sin las fuentes duplicadas.

El plugin incluye los TOML de agentes como recursos. El instalador los registra
por separado en `CODEX_HOME/agents` con archivos `constellation-*.toml`; incluirlos
en una skill no basta. Abre una sesión nueva para cargar los perfiles. Si la
superficie no expone uno, el coordinador puede pasar sus instrucciones a un
agente nativo disponible, conservando su identidad real y sin fingir registro.

## Hooks y confianza

El manifiesto compatible reside en `.codex-plugin/plugin.json` dentro del
bundle. Declara cinco eventos: `UserPromptSubmit`, `PreToolUse`, `SubagentStart`,
`SubagentStop` y `Stop`. Todos ejecutan código fijo del paquete instalado:

```text
python3 -I "${PLUGIN_ROOT}/ecosystem/hooks.py" EVENTO
```

Cada definición concreta está en `ecosystem/hooks.json`. La instalación registra
el plugin; no concede confianza. Revisa las cinco definiciones en `/hooks` y
confía únicamente las que quieras activar. Una definición nueva o modificada
puede volver a requerir revisión. No se alteran hashes de confianza ni se usan
opciones para omitirla. Comprueba mediante el cliente qué está incluido,
registrado, confiado y observado en ejecución; son estados diferentes.

Los hooks se aplican a tareas registradas y activas. `PreToolUse` comprueba
las rutas de patches, incluidas retiradas y renombrados; no intercepta todas
las escrituras de shell o MCP. Los eventos sin identidad de agente no atribuyen
autoría. Si hay varias tareas activas y el evento es ambiguo, se exige cierre
explícito mediante el CLI, sin adivinar cuál lo emitió. Las capas de hooks se
acumulan: los controles del receptor siguen aplicándose.

`Stop` pide como máximo dos continuaciones por tarea. Después informa que el
trabajo está incompleto; no aprueba el resultado ni inicia agentes, checks,
commits o procesos residentes. `close complete` y `close partial` retiran la tarea
del alcance activo de los hooks. Una modificación posterior invalida su evidencia
al consultar o reutilizar el certificado; para continuar la tarea se replantea
explícitamente. Un cierre parcial conserva obligaciones pendientes.

Un error o timeout del cliente puede dejar un hook sin aplicar. El adaptador
emite diagnósticos acotados, pero no constituye un sandbox. La aceptación
controlada se decide en el núcleo, que rechaza evidencia incompleta o caducada.

## Trabajo cotidiano y controles

La skill recoge requisitos observables, entregables y responsables. Para una
entrega significativa, el coordinador abre un contrato, registra los UUID reales
devueltos por los agentes, ejecuta las comprobaciones pertinentes y obtiene
revisión independiente. El [protocolo](references/protocol.md) contiene el schema
y las operaciones exactas; se carga cuando haga falta, sin duplicar ese manual
en los tres `SKILL.md`.

La revisión reutiliza la política vigente: Quick exige un revisor; Standard,
tres de corrección; Deep, tres de corrección y dos de seguridad. La cobertura
es por archivo y foco, con un máximo de tres rondas. Un autor no revisa sus
archivos; los hallazgos necesitan verificación distinta del autor y descubridor.
Los cambios relevantes de contenido, hipótesis, dependencias, política o
comprobaciones invalidan la evidencia afectada. Un fallo posterior no queda
oculto tras un éxito anterior.

Las comprobaciones mecánicas verifican estructura, cobertura, hashes, vigencia,
independencia declarada y obligaciones. Los revisores deben juzgar la validez
de los argumentos, la pertinencia de las pruebas, las fuentes y la calidad
editorial. Ni hashes ni quórums autentican personas o demuestran teoremas.

El estado SQLite vive fuera de los entregables, separado por sesión, tarea y
agente. Los checks ejecutan comandos explícitos sin shell y guardan hashes,
estados y códigos de salida; no se guardan argv, stdout, stderr, prompts ni
transcripciones. Las transacciones cortas permiten trabajos concurrentes y los
intentos interrumpidos necesitan recuperación explícita.

Los CLI y hooks ejecutados directamente por su ruta evitan escribir bytecode
en el paquete. Para importar su API desde Python o ejecutar las pruebas de una
distribución, inicia el intérprete con `-B` o establece
`PYTHONDONTWRITEBYTECODE=1` antes de la primera importación. El inventario del
bundle es inmutable: no se ignoran ni se borran cachés inesperados para darlo
por válido. La validación CLI directa funciona sin exigir ese flag adicional.

En Constellation, declara también los archivos en `workspace.py` y publica con
sus checks, revisión, commit y finish. El `close` del paquete no publica ni
sustituye ese contrato. En otro proyecto se conservan sus `AGENTS.md`, hooks,
aprobaciones y procedimiento de publicación. Para escritura breve o creativa
se usa una revisión adecuada a su propósito; no se inicia investigación factual
sin necesidad.

## Fuentes, pruebas y límites

Las skills se mantienen únicamente en `.codex/skills`. El núcleo y los recursos
de este paquete se mantienen junto a este archivo. El builder selecciona rutas
explícitas; copia el motor de revisión y su política desde su fuente única.
Las distribuciones generadas son artefactos, no ramas de mantenimiento.

El validador complementario admite el formato mantenido de estas skills:
frontmatter con `name` y `description` como strings entre comillas JSON, y
metadata UI como objeto JSON o mappings YAML de dos espacios con strings y
booleanos. No es un validador YAML general. Su lista de archivos y restricciones
de rutas tampoco detectan secretos arbitrarios incrustados en archivos permitidos;
la inspección sustantiva antes de publicar sigue siendo necesaria.

```sh
python3 .codex/ecosystem/validate.py --root .codex
python3 -B -m unittest discover -s .codex/ecosystem/tests -v
```

La suite distribuida ejecuta los controles comunes con cualquiera de los
módulos instalados. Omite explícitamente los casos que necesitan módulos
excluidos. La matriz que construye y ejecuta los cuatro paquetes corre desde
las fuentes; dentro de un bundle se omite para evitar recursión. La prueba
nativa se omite cuando el ejecutable Codex no está disponible, sin presentarla
como ejecutada.

Consulta [compatibilidad](COMPATIBILITY.md) y [evaluación](EVALUATION.md) para
conocer la evidencia, los casos probados y sus límites. No se encontró una
`scholar` activa en las superficies comprobadas: se creó `writter` sin retirar
una entrada activa ni tocar el candidato desactivado fuera del alcance.
