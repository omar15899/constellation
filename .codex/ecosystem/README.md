# Constellation

Constellation es un entorno de investigación compartido para Codex y Claude
Code. Una distribución versionada contiene las mismas skills, instrucciones de
agentes y controles de evidencia. Cada cliente descubre y ejecuta sus componentes
nativos; los proyectos conservan datos, permisos, pruebas y propiedad Git.
Describe el resultado que necesitas: el cliente selecciona las capacidades
pertinentes y carga sus instrucciones cuando hacen falta. Constellation añade
contratos, coordinación, evidencia, revisión y publicación sin fijar tu modelo,
esfuerzo, permisos ni confianza de hooks.

El mismo paquete se puede instalar en varios portátiles. Compartir una versión
establece fuentes y criterios comunes, no respuestas idénticas de los modelos
ni acceso automático a los datos o conexiones del otro ordenador. No requiere
un servicio central, otro motor de agentes ni una copia de OmarOS.

## Uso cotidiano

- Una pregunta breve se responde directamente.
- Una tarea Git usa el workflow de su receptor, con pruebas y revisión adecuadas.
- Investigación y documentos sin publicación usan el núcleo portable cuando
  necesitan evidencia persistida. No se crea un repositorio para ellos.
- Una tarea mixta combina skills y dependencias reales. No abre dos contratos
  iguales por haber seleccionado ingeniería y matemática.

Investigación, aprendizaje e ingeniería son comportamientos combinables según
tu intención. Puedes pedir una explicación completa, pistas sin solución o
priorizar la entrega; no necesitas cambiar un modo. La investigación conserva
hipótesis, procedencia y límites de la evidencia.

Para enseñanza, el perfil personal provisional `~/.codex/learning/PROFILE.md`,
cuando está disponible, aporta sólo preferencias pertinentes. Puedes aportar ejemplos positivos,
negativos o de tu razonamiento y pedir que se incorporen para futuros usos.
La skill de enseñanza verifica la persistencia y permite corregir o retirar
preferencias. Una corrección puntual no se convierte automáticamente en memoria.
El perfil queda fuera del paquete, de las publicaciones y de agentes ajenos a
esa enseñanza; cambiar de modelo no requiere copiarlo ni reentrenar nada.

Puedes solicitar expresamente `$constellation:coding`,
`$constellation:mathematics`, `$constellation:quant-research` o
`$constellation:writter` en Codex; en Claude usa `/constellation:coding`,
`/constellation:mathematics`, `/constellation:quant-research` o
`/constellation:writter`. No necesitas conocer esos
nombres para la selección ordinaria. Una skill de documentos, PDF, hojas de
cálculo o una conexión externa sigue perteneciendo a su proveedor; Constellation
no la copia ni presume que está disponible en cualquier cliente.

La skill `quant-research` conecta hipótesis económicas,
datos reproducibles, backtesting causal, evaluación temporal y evidencia hasta
paper. Su recurso `skills/quant-research/references/workflow.md`, cuando el módulo
está incluido, descubre las capacidades del receptor: no instala labs,
datos ni conectores, ni activa órdenes reales. El runner y la persistencia de
campañas pertenecen al proyecto de integración; Constellation conserva la
coordinación nativa y sus controles de evidencia.

El método común es general: delimitar la pregunta, declarar hipótesis y fuentes,
buscar explicaciones rivales y contraejemplos, y ligar cada conclusión a evidencia
vigente. Una demostración, un cálculo y un experimento descargan obligaciones
distintas. Los resultados negativos y los pendientes se conservan. La profundidad,
los especialistas y las pruebas se eligen según el problema; una tarea breve no
activa por defecto una cadena de agentes ni otro ciclo persistente.

## Diagnóstico

Desde este checkout:

```sh
python3 .codex/ecosystem/native.py --codex-home ~/.codex --cwd "$PWD" --capabilities
```

Desde una distribución, usa la misma ruta relativa `ecosystem/native.py`.
El resultado distingue skills descubiertas, activación de plugins, confianza de
hooks, configuración MCP y capacidad declarada. Consulta un **proceso nuevo del
CLI**: el catálogo del cliente actual puede diferir. No acredita autorización,
compatibilidad ni ejecución de lo enumerado. Conserva errores y advertencias
sin volcar comandos, configuración sensible o contenido de conversaciones.

En Claude, comprueba primero la integridad de la instalación:

```sh
python3 /ruta/al/paquete/ecosystem/claude.py verify --claude-home ~/.claude
```

El resultado informa de la instalación y su integridad. La carga, confianza y
ejecución permanecen desconocidas mientras no se observen. En una sesión nueva usa
`/context`, `/skills`, `/agents`, `/hooks` y `/status` para revisar los componentes
efectivos. La configuración personal, local o administrada puede cambiar lo que
carga el cliente. Una definición MCP tampoco prueba autenticación ni acceso real.

Para explicar una selección, el agente identifica el requisito atendido, las
instrucciones realmente consultadas y el resultado comprobado. Una dependencia
no disponible se comunica; no se registra como usada. Esa evidencia se incorpora
al informe de la tarea, sin otro registro de skills ni base de datos.

## Entregas y agentes

En el hub, siguen funcionando `python3 .codex/workspace.py --session SESSION_ID`
y `python3 .codex/workflow.py --session SESSION_ID`. Son entradas al runtime
compartido. Sustituye `SESSION_ID` por la identidad comunicada por el cliente:
en Claude, `claude-<session_id>`; en Codex, el ID nativo de sesión. En una ejecución
independiente usa una identidad propia y única para el trabajo, sin compartir
`manual` entre tareas. Pasa esa misma identidad en todos sus comandos.

En una distribución independiente:

```sh
python3 /ruta/al/paquete/ecosystem/cli.py git --root /ruta/proyecto --session SESSION_ID begin
python3 /ruta/al/paquete/ecosystem/cli.py git --root /ruta/proyecto --session SESSION_ID plan < contrato.json
python3 /ruta/al/paquete/ecosystem/cli.py workspace --root /ruta/workspace --session SESSION_ID route archivo
```

`route` identifica el dueño sin iniciar un contrato. `begin` y `plan` se ejecutan
cuando el trabajo requiere ese ciclo explícito; una consulta breve sigue siendo
una consulta y no abre otro contrato por usar el CLI.

El workflow Git conserva `plan`, `check`, `review-start`, `review-report`,
`review`, `commit` y `finish`; consulta `--help` y la guía del receptor. El
[protocolo portable](references/protocol.md) documenta las operaciones sin Git,
los veredictos matemáticos, las entradas fijadas y los checks declarados.
Las garantías de ambos adaptadores no son equivalentes.

`status` lee una única instantánea JSON y permanece disponible durante checks
largos. Esa lectura puntual no certifica el cierre de la tarea. Los comandos que
cambian estado, revisión, publicación o progreso conservan el bloqueo exclusivo.

Para compartir un estado portable aislado entre CLI y hooks, exporta
`CONSTELLATION_STATE_DIR` con una ruta absoluta antes de iniciar sus procesos,
incluidos Codex o Claude. `--state-dir` sólo afecta a esa invocación del CLI; los defaults
permanecen iguales. El [protocolo](references/protocol.md#portable-api) documenta
precedencia y validación; el ajuste no cambia permisos ni la política personal.

El coordinador delega sólo trabajos independientes útiles, con identidad real,
archivos exclusivos, dependencias y resultados verificables. Usa agentes
nativos y un único presupuesto efectivo de sesión. `dispatch` propone paquetes;
no ejecuta agentes ni certifica su trabajo. La revisión compartida conserva
Quick=1, Standard=3 y Deep=3 de corrección más 2 de seguridad, por archivo y foco.
No hay un máximo universal de rondas: continúa con una acción justificada y
presupuesto real, conservando historia, hallazgos y mínimos. El presupuesto
ausente es desconocido; los límites del cliente siguen vigentes. El
[protocolo](references/protocol.md#review-continuity-and-budget) describe la
continuidad y el plazo explícito. Los hashes fijan versiones; los revisores juzgan
corrección, hipótesis y pertinencia de las pruebas.

Una corrección pequeña de código ordinario puede usar `review-start
--quick-code-reason "JUSTIFICACIÓN CONCRETA"` cuando lo permita la política del
receptor, antes de la primera ronda. La justificación queda ligada a esa versión
y se revisa independientemente; un cambio posterior invalida la elegibilidad.
No rebaja Deep ni mínimos previamente fijados. En el API portable el campo es
`quick_code_reason`.

## Progreso y OmarOS

El trabajo sustancial mantiene checkpoints curados en su workflow existente.
`progress-show` recupera objetivos, decisiones, resultados, evidencia y próximos
pasos aunque el vault no esté disponible. Al guardar hitos significativos, el
coordinador entrega las síntesis personales autorizadas al receptor OmarOS.

La política local `~/.codex/progress-journal.json` permite fuentes exactas y un
destino; el registro de proyectos no concede ese permiso. Fuentes desconocidas,
corporativas o restringidas no se exportan. El diario humano es
`17_Dashboards/Constellation.md` dentro del vault y enlaza las notas curadas.
Los reintentos son idempotentes y el checkpoint fuente sobrevive a un fallo.
Una recepción local no es publicación remota ni prueba de finalización.
Consulta [PROGRESS.md](PROGRESS.md) para las cuatro operaciones `progress-*`,
la importación del receptor y su recuperación. No se copian conversaciones,
logs, resultados brutos ni contenido del perfil personal.

## Proyectos y hooks

Un proyecto nuevo recibe las skills y hooks del plugin instalado sin copiar
motores ni perfiles. Añade `AGENTS.md` para información de dominio cuando sea
útil. `.codex/` es opcional para descubrimiento nativo; un workspace que coordine
varios repositorios necesita su registro declarativo y cada repositorio conserva
su dueño Git. Los marcadores existentes que protegen perfiles frente a la
proyección de Claude se conservan mientras tengan ese consumidor.

El adaptador Codex tiene cinco eventos: `UserPromptSubmit`, `PreToolUse`, `SubagentStart`,
`SubagentStop` y `Stop`. Actúan sobre contratos activos; un prompt no inicia
trabajo ni hace fetch. El guard de patches no cubre todas las escrituras de
shell/MCP. Stop es acotado e idempotente y nunca publica. Las definiciones
antiguas del hub están retiradas; los comandos heredados delegan al mismo
adaptador. Activación, confianza y ejecución se comprueban por separado.

Claude añade `SessionStart` para comunicar la ruta del CLI compartido, la
identidad de sesión y el protocolo de trabajo, y adapta los otros cinco eventos
al mismo motor. Sus herramientas `Write`, `Edit`, `MultiEdit` y `NotebookEdit`
se traducen a rutas estructurales antes de comprobar el alcance. No transmite
prompts, transcripciones ni contenido editado al motor. Una sesión Claude usa
siempre `--session claude-ID`, con el ID nativo comunicado por el hook; no usa
la sesión de reserva `manual`. Los registros de autores y revisores conservan
sus IDs nativos reales, sin ese prefijo de ciclo.

Un receptor con adaptador propio, como OmarOS, declara
`CONSTELLATION_HOOK_OWNER=project` en el entorno de su configuración Claude. El
adaptador global cede los eventos a ese dueño sin ejecutar código del proyecto.
Así se conserva la política especializada y se evita una segunda selección de
ciclo. Los contratos, archivos y requisitos del receptor siguen siendo suyos.
La política nativa `onFailure: "block"` protege los eventos de bloqueo que la
admiten. No protege `Stop` ni convierte sus continuaciones en una garantía de
cierre: la aceptación final depende de los comandos de evidencia y publicación.

Los hooks Git del receptor siguen vigentes. La revisión de Constellation se
exige en su workflow de publicación; los commits y pushes manuales no adquieren
esa garantía automáticamente. OmarOS conserva validación y publicación propias
mientras consume el algoritmo común de revisión.

## Instalar y actualizar

Se necesita Python 3.11+, Git para publicación y el cliente elegido con sus
interfaces compatibles. Los instaladores usan bloqueo POSIX: el objetivo es
macOS/Linux y entornos Linux como WSL, no Windows nativo. La referencia Claude
es 2.1.301; no se promete compatibilidad con versiones anteriores. El uso de WSL
requiere validar allí los clientes y las pruebas pertinentes.

### Preparar otro portátil

1. Construye una distribución en un destino nuevo desde las fuentes publicadas:

   ```sh
   python3 .codex/ecosystem/build.py --output /tmp/constellation-1.3.0 \
     --archive /tmp/constellation-1.3.0.zip
   shasum -a 256 /tmp/constellation-1.3.0.zip
   ```

2. Copia el ZIP y conserva su SHA-256 por un canal autorizado. En el otro
   portátil compara el hash antes de extraerlo. El inventario interno comprueba
   después archivos, hashes y modos. Un hash recibido junto al ZIP detecta
   diferencias, pero no autentica por sí solo a quien lo envió.

3. Instala los clientes que vayas a usar desde el paquete extraído. Para Claude:

   ```sh
   python3 /ruta/constellation-1.3.0/ecosystem/claude.py install \
     --bundle /ruta/constellation-1.3.0 --claude-home ~/.claude --check
   python3 /ruta/constellation-1.3.0/ecosystem/claude.py install \
     --bundle /ruta/constellation-1.3.0 --claude-home ~/.claude
   ```

   Para Codex, conserva el instalador nativo existente:

   ```sh
   python3 /ruta/constellation-1.3.0/ecosystem/install.py \
     --bundle /ruta/constellation-1.3.0 --codex-home ~/.codex --check
   python3 /ruta/constellation-1.3.0/ecosystem/install.py \
     --bundle /ruta/constellation-1.3.0 --codex-home ~/.codex
   ```

4. Verifica la instalación y abre una sesión nueva del cliente. Para Claude:

   ```sh
   python3 /ruta/constellation-1.3.0/ecosystem/claude.py verify --claude-home ~/.claude
   claude plugin validate --strict --json ~/.claude/skills/constellation
   ```

   Después comprueba el catálogo y los hooks efectivos en el cliente. En Codex
   usa el diagnóstico `native.py --capabilities` y `/hooks`. La validación del
   paquete o de su schema no certifica confianza ni ejecución de un evento.

En macOS puedes añadir un ensayo nativo aislado y sin modelo remoto:

```sh
python3 -B /ruta/constellation-1.3.0/ecosystem/tests/native_claude_probe.py \
  --bundle /ruta/constellation-1.3.0
```

Acepta `--claude /ruta/al/binario` para elegir el CLI. Usa un servidor HTTP
local, autenticación sintética y restricciones que bloquean la red exterior,
el HOME real y Keychain. Comprueba carga nativa, rutas permitidas y rechazadas,
cierre pendiente y bloqueo ante el fallo operativo de un hook. No envía datos
a un modelo ni acredita la calidad de su investigación. El ensayo está limitado
a macOS; en otro sistema su indisponibilidad se informa como tal, sin aprobarlo.
Los eventos nativos de subagentes siguen sin verificación: el intento aislado
recibió un rechazo automático de aprobación, que se respetó. Consulta la
[evidencia y sus límites](COMPATIBILITY.md#distribución-dual-13--2026-10-28).

La distribución contiene código e instrucciones expresamente permitidos por
el constructor. No copies `~/.codex` ni `~/.claude`: contienen autenticación,
conversaciones y estado personal. Los perfiles privados, políticas personales,
registros locales de proyectos, datos, proveedores y autorizaciones MCP se
configuran por separado en cada portátil. El paquete no crea cuentas, descarga
datos ni concede nuevos permisos.

### Instalación Claude

El instalador coloca el paquete en `skills/constellation` dentro del directorio
indicado por `--claude-home`, con ambos
manifiestos nativos. Claude descubre ese plugin como `constellation@skills-dir`
en una sesión nueva, salvo que sus políticas lo impidan. No necesita un
marketplace ni editar `settings.json`. Las skills siguen en `skills/`; los
agentes Markdown se generan desde las instrucciones TOML canónicas durante la
construcción. No se mantienen dos cuerpos independientes de cada rol.

La instalación verifica la propiedad e integridad antes de sustituir su
directorio. Conserva las demás skills y ajustes y respeta una desactivación
explícita del plugin. `--check` no modifica los directorios del usuario. Repetir
el mismo paquete devuelve `unchanged`; una actualización usa el nuevo paquete y
el mismo comando. Los cambios ajenos, enlaces o restos de una sustitución
interrumpida se rechazan preservando sus archivos. Un error controlado restaura
la instalación anterior; una terminación abrupta puede requerir resolver la
interrupción antes de reintentar. El estado de investigación queda fuera del
directorio sustituible.

Los hooks instalados validan el inventario antes de cargar el motor compartido
y mantienen un lock compartido durante el despacho, incompatible con la
sustitución de la instalación. Una distribución inmutable cargada expresamente
mediante `--plugin-dir` también comprueba su inventario; esa carga no equivale a
una instalación permanente ni acredita confianza del cliente.

La distribución 1.3.0 no cambia el pin del núcleo derivado 1.2.0 de OmarOS. Ese
receptor verifica sus cuatro recursos existentes y conserva su propio ciclo.
Su actualizador antiguo sólo admite bundles 1.2.0 y rechazará uno 1.3.0; actualizar
ese contrato receptor requiere una migración específica, no copiar el paquete
sobre `.codex/vendor/constellation`.

La carga permanente y sus límites siguen las referencias oficiales de
[plugins Claude](https://code.claude.com/docs/en/plugins/create#make-a-plugin-load-in-every-session),
[hooks](https://code.claude.com/docs/en/hooks) y
[subagentes](https://code.claude.com/docs/en/sub-agents).

### Instalación Codex existente

Desde el checkout también puedes construir e instalar en un destino temporal:

```sh
python3 .codex/ecosystem/build.py --output /tmp/constellation-bundle \
  --archive /tmp/constellation-bundle.zip
python3 /tmp/constellation-bundle/ecosystem/install.py \
  --bundle /tmp/constellation-bundle --codex-home ~/.codex --check
python3 /tmp/constellation-bundle/ecosystem/install.py \
  --bundle /tmp/constellation-bundle --codex-home ~/.codex
```

Repite con un bundle nuevo para actualizar. El instalador verifica inventarios,
recibos y perfiles; conserva configuración ajena, rechaza plugins desactivados y
compensa fallos mediante operaciones nativas. No edites el caché ni el catálogo
como fuentes. Los archivos inesperados necesitan tratamiento explícito que los
preserve; no se ignoran cambios de integridad para completar una actualización.

Los ocho perfiles especializados se registran en `CODEX_HOME/agents` mediante
el instalador. Las fuentes de skills permanecen en `.codex/skills`. Si mantienes
ese checkout y el plugin simultáneamente, evita dos entradas activas mediante
el helper nativo `--exclude-source-root "$PWD/.codex"`, después de verificar que
fuentes y distribución coinciden. Las exclusiones existentes se preservan.

Comprueba `/hooks` al cambiar una definición: instalar no concede confianza.
Una sesión nueva carga perfiles/configuración actualizados; no se presupone que
una sesión abierta recargó su catálogo. Los scripts evitan bytecode incidental;
para importar o probar un bundle inmutable usa `python3 -B`.

Desde 1.2, los cinco eventos usan la misma entrada estable, instalada fuera del
caché versionado:

```sh
python3 -I "${CODEX_HOME:-$HOME/.codex}/constellation/hook.py" EVENTO
```

Su fuente es `ecosystem/hook_entry.py`. Antes de ejecutar el adaptador del catálogo
instalado, valida recibo, inventarios, hashes y modos de la entrada, catálogo y
caché. Conserva un lock compartido no bloqueante sobre
`CODEX_HOME/constellation/.install.lock` durante validación y ejecución; la
instalación toma ese lock en exclusiva. Si encuentra una actualización en curso
o una instalación incoherente, responde de forma controlada: `PreToolUse` deniega;
`Stop` y `SubagentStop` avisan con `INCOMPLETE` sin emitir un bloqueo sobre un
estado todavía no validado. Los demás eventos informan de la indisponibilidad.
Ese aviso no aprueba el cierre. Tras validar el paquete, el adaptador conserva
su política acotada de Stop. La entrada no repara automáticamente una actualización
terminada por `SIGKILL` ni ejecuta el paquete sin verificar.

El recibo de esquema 3 incluye `hook.sha256` y `hook.mode`; los recibos previos
1 y 2 se verifican para actualizar sin importar su código. Una sesión que capturó
el comando antiguo del caché 1.1 necesita reabrirse una vez para cargar la entrada
estable. Un comando estable ya cargado puede seguir resolviendo futuras
instalaciones verificadas. Esto no recarga el resto del catálogo ni concede
confianza: si Codex exige una aprobación nativa por la definición nueva, se usa
su interfaz. Nunca se editan hashes de confianza. La evidencia de despacho real
se registra por separado de los tests de subprocess en
[COMPATIBILITY.md](COMPATIBILITY.md).

El paquete no fija modelo, esfuerzo ni ventana de contexto. Usa los límites
observados del cliente para cada modelo y revalida sus capacidades al actualizar;
la compatibilidad histórica descrita en [COMPATIBILITY.md](COMPATIBILITY.md)
cubre esos ensayos, no cualquier cliente o modelo futuro.

La [arquitectura](ARCHITECTURE.md), el [inventario de migración](MIGRATION.md), la
[compatibilidad observada](COMPATIBILITY.md) y la [evaluación](EVALUATION.md)
detallan las fuentes, evidencias y límites. El estado de trabajo es privado y
no forma parte de los artefactos publicables.
