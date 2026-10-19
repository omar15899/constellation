# Constellation

Describe el resultado que necesitas. Codex descubre las capacidades disponibles,
selecciona las skills pertinentes y carga sus instrucciones cuando hacen falta.
Constellation añade contratos, coordinación, evidencia, revisión y publicación.
No cambia tu modelo, esfuerzo, permisos ni confianza de hooks.

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
`$constellation:writter`. No necesitas conocer esos
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

Para explicar una selección, el agente identifica el requisito atendido, las
instrucciones realmente consultadas y el resultado comprobado. Una dependencia
no disponible se comunica; no se registra como usada. Esa evidencia se incorpora
al informe de la tarea, sin otro registro de skills ni base de datos.

## Entregas y agentes

En el hub, siguen funcionando `python3 .codex/workspace.py` y
`python3 .codex/workflow.py`. Son entradas al runtime compartido. En una
distribución independiente:

```sh
python3 /ruta/al/paquete/ecosystem/cli.py git --root /ruta/proyecto begin
python3 /ruta/al/paquete/ecosystem/cli.py git --root /ruta/proyecto plan < contrato.json
python3 /ruta/al/paquete/ecosystem/cli.py workspace --root /ruta/workspace route archivo
```

El workflow Git conserva `plan`, `check`, `review-start`, `review-report`,
`review`, `commit` y `finish`; consulta `--help` y la guía del receptor. El
[protocolo portable](references/protocol.md) documenta las operaciones sin Git,
los veredictos matemáticos, las entradas fijadas y los checks declarados.
Las garantías de ambos adaptadores no son equivalentes.

Para compartir un estado portable aislado entre CLI y hooks, exporta
`CONSTELLATION_STATE_DIR` con una ruta absoluta antes de iniciar sus procesos,
incluido Codex. `--state-dir` sólo afecta a esa invocación del CLI; los defaults
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

El plugin tiene cinco eventos: `UserPromptSubmit`, `PreToolUse`, `SubagentStart`,
`SubagentStop` y `Stop`. Actúan sobre contratos activos; un prompt no inicia
trabajo ni hace fetch. El guard de patches no cubre todas las escrituras de
shell/MCP. Stop es acotado e idempotente y nunca publica. Las definiciones
antiguas del hub están retiradas; los comandos heredados delegan al mismo
adaptador. Activación, confianza y ejecución se comprueban por separado.

Los hooks Git del receptor siguen vigentes. La revisión de Constellation se
exige en su workflow de publicación; los commits y pushes manuales no adquieren
esa garantía automáticamente. OmarOS conserva validación y publicación propias
mientras consume el algoritmo común de revisión.

## Instalar y actualizar

Se necesita Python 3.11+ para el paquete portable, Git para publicación y Codex
con las interfaces verificadas. El instalador usa bloqueo POSIX; la cobertura
actual es macOS/Linux. Construye desde fuentes en un destino nuevo:

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
