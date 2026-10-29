# Instalación y migraciones

Esta guía describe los comandos y las condiciones de actualización. La
[compatibilidad observada](compatibility.md) registra por separado lo que se ha
probado en cada versión y cliente. Los ejemplos no acreditan por sí solos
que el paquete esté instalado, confiado o ejecutándose en una sesión existente.

## Instalar y actualizar

Se necesita Python 3.11+, Git para publicación y el cliente elegido con sus
interfaces compatibles. Esta sección conserva el destino POSIX para macOS/Linux
y entornos Linux como WSL. Para Claude en Windows nativo, el candidato
1.4.0-rc.1 se construye con `--language en --target windows-claude` y tiene
[una guía específica](windows.md); su aceptación en Windows sigue pendiente.
La referencia Claude del baseline POSIX es 2.1.301; no acredita esa versión en
Windows ni compatibilidad con versiones anteriores. El uso de WSL
requiere validar allí los clientes y las pruebas pertinentes.

### Preparar otro portátil

1. Construye una distribución en un destino nuevo desde las fuentes publicadas:

   ```sh
   python3 .codex/ecosystem/build.py --output /tmp/constellation-1.4.0-rc.1 \
     --archive /tmp/constellation-1.4.0-rc.1.zip
   shasum -a 256 /tmp/constellation-1.4.0-rc.1.zip
   ```

2. Copia el ZIP y conserva su SHA-256 por un canal autorizado. En el otro
   portátil compara el hash antes de extraerlo. El inventario interno comprueba
   después archivos, hashes y modos. Un hash recibido junto al ZIP detecta
   diferencias, pero no autentica por sí solo a quien lo envió.

3. Instala los clientes que vayas a usar desde el paquete extraído. Para Claude:

   ```sh
   python3 /ruta/constellation-1.4.0-rc.1/ecosystem/claude.py install \
     --bundle /ruta/constellation-1.4.0-rc.1 --claude-home ~/.claude --check
   python3 /ruta/constellation-1.4.0-rc.1/ecosystem/claude.py install \
     --bundle /ruta/constellation-1.4.0-rc.1 --claude-home ~/.claude
   ```

   Para Codex, conserva el instalador nativo existente:

   ```sh
   python3 /ruta/constellation-1.4.0-rc.1/ecosystem/install.py \
     --bundle /ruta/constellation-1.4.0-rc.1 --codex-home ~/.codex --check
   python3 /ruta/constellation-1.4.0-rc.1/ecosystem/install.py \
     --bundle /ruta/constellation-1.4.0-rc.1 --codex-home ~/.codex
   ```

4. Verifica la instalación y abre una sesión nueva del cliente. Para Claude:

   ```sh
   python3 /ruta/constellation-1.4.0-rc.1/ecosystem/claude.py verify --claude-home ~/.claude
   claude plugin validate --strict --json ~/.claude/skills/constellation
   ```

   Después comprueba el catálogo y los hooks efectivos en el cliente. En Codex
   usa el [diagnóstico completo](#diagnóstico-de-codex) y revisa `/hooks`.
   La validación del paquete o de su schema no certifica confianza ni ejecución.

### Diagnóstico de Codex

Sustituye las rutas del paquete y del proyecto por sus directorios reales y
asegúrate de que `python3` sea Python 3.11 o posterior:

```sh
python3 /ruta/al/paquete/ecosystem/native.py --codex-home ~/.codex --cwd /ruta/proyecto --capabilities
```

`--codex-home` es obligatorio; `--cwd` fija el proyecto observado. El comando
consulta metadatos en un proceso nuevo del CLI. No instala ni habilita componentes,
no cambia la confianza y no ejecuta skills o herramientas para certificar su
funcionamiento. Sus resultados no representan automáticamente un chat abierto.
Un hook marcado `modified` requiere revisión y aprobación mediante la interfaz
nativa de Codex antes de atribuirle ejecución. Conservar su ruta no sustituye esa
aprobación; nunca se editan hashes de confianza para completarla.

### Ensayo aislado Claude

En macOS puedes añadir un ensayo nativo aislado y sin modelo remoto:

```sh
python3 -B /ruta/constellation-1.4.0-rc.1/ecosystem/tests/native_claude_probe.py \
  --bundle /ruta/constellation-1.4.0-rc.1
```

Acepta `--claude /ruta/al/binario` para elegir el CLI. Usa un servidor HTTP
local, autenticación sintética y restricciones que bloquean la red exterior,
el HOME real y Keychain. Comprueba carga nativa, rutas permitidas y rechazadas,
cierre pendiente y bloqueo ante el fallo operativo de un hook. No envía datos
a un modelo ni acredita la calidad de su investigación. El ensayo está limitado
a macOS; en otro sistema su indisponibilidad se informa como tal, sin aprobarlo.
La ejecución de subagentes exige su propia observación nativa. La prueba de
1.3.0 no la estableció; consulta la [matriz de evidencia vigente](compatibility.md)
antes de atribuir esa capacidad a una versión.

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
interrumpida se rechazan preservando sus archivos. Ante un error controlado se
restaura el payload anterior cuando su identidad y el destino de retorno siguen
verificados. Los datos parciales, cambiados o ajenos y las colisiones de retorno
se conservan para inspección explícita. Una terminación abrupta puede requerir
resolver la interrupción antes de reintentar. El estado de investigación queda fuera del
directorio sustituible.

Los hooks instalados validan el inventario antes de cargar el motor compartido
y mantienen un lock compartido durante el despacho, incompatible con la
sustitución de la instalación. Una distribución inmutable cargada expresamente
mediante `--plugin-dir` también comprueba su inventario; esa carga no equivale a
una instalación permanente ni acredita confianza del cliente.

La distribución 1.3.1 no cambia el pin del núcleo derivado 1.2.0 de OmarOS. Ese
receptor verifica sus cuatro recursos existentes y conserva su propio ciclo.
Su actualizador sólo admite bundles 1.2.0 y rechaza el paquete dual; actualizar
ese contrato receptor requiere una migración específica, no copiar el paquete
sobre `.codex/vendor/constellation`.

La carga permanente y sus límites siguen las referencias oficiales de
[plugins Claude](https://code.claude.com/docs/en/plugins/create#make-a-plugin-load-in-every-session),
[hooks](https://code.claude.com/docs/en/hooks) y
[subagentes](https://code.claude.com/docs/en/sub-agents).

### Instalación Codex

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
[compatibilidad observada](compatibility.md).

El paquete no fija modelo, esfuerzo ni ventana de contexto. Usa los límites
observados del cliente para cada modelo y revalida sus capacidades al actualizar;
la compatibilidad histórica descrita en [compatibilidad observada](compatibility.md)
cubre esos ensayos, no cualquier cliente o modelo futuro.


## Organización 1.3.1 y actualización desde 1.3.0

Las fuentes de manifiestos viven en `ecosystem/manifests/`; las guías mantenidas,
en `ecosystem/docs/`. El constructor proyecta los dos manifiestos de plugin a
las ubicaciones nativas `.codex-plugin/plugin.json` y `.claude-plugin/plugin.json`.
Los destinos distribuidos `ecosystem/hooks.json` y `ecosystem/claude-hooks.json`
se conservan porque participan en la identidad nativa de los hooks. Sus fuentes
no se duplican ni se modifica la confianza del usuario para reorganizarlas.

La evidencia de evaluaciones pasadas vive sólo en el checkout:
`ecosystem/evals/results/2026-10-18.json` y `ecosystem/docs/history/`. No se instala
como dependencia operativa ni sustituye las comprobaciones del candidato actual.
Los valores y las rutas históricas del JSON se conservan como evidencia fechada.

Una actualización debe verificar el inventario de la versión que sustituye y
el de la nueva versión por separado. La desaparición intencional de un documento
no autoriza archivos desconocidos, mezclas de versiones ni cambios ajenos.
La migración requiere pruebas en ambos clientes con un paquete 1.3.0 anterior,
conservación de datos y ajustes, rechazo de alteraciones y recuperación tras un
fallo controlado. La matriz de [aceptación](evaluation.md#aceptación-de-131)
indica las obligaciones; sólo los resultados registrados acreditan su ejecución.

## Antecedentes de migración

Las secciones siguientes describen las transiciones anteriores. Sus versiones,
recuentos y observaciones no son inventarios de la sesión actual.

### Fase adaptativa 1.2

La revisión mantiene el algoritmo común, sus pisos de riesgo, independencia y
hallazgos acumulados. Sustituye el máximo universal de tres rondas por continuidad
justificada y presupuesto temporal explícito. Las políticas de esquema 1 siguen
siendo legibles y se normalizan sin `max_rounds`; el esquema 2 rechaza ese campo.
Replanificar o cambiar de política conserva los mínimos de riesgo y cobertura,
incluidos los más estrictos del receptor. `review-budget` registra cada plazo y ampliación;
`review-start` recibe una razón y acción siguiente cuando la detección de ciclos
o falta de progreso las exige. No se inventa un presupuesto de tokens a partir
del contexto disponible. Consulta el
[contrato compartido](../references/protocol.md#review-continuity-and-budget).

El hook pasa del comando de un caché versionado a
`CODEX_HOME/constellation/hook.py`. El instalador mantiene la entrada y el recibo
de esquema 3; el hook verifica la distribución bajo un lock compartido, mientras
el instalador usa el mismo lock en exclusiva. El
[contrato de instalación](../README.md#instalar-y-actualizar) especifica rechazos,
actualización desde recibos anteriores y límites de recuperación.

La primera transición requiere reabrir los hilos que retengan el comando antiguo.
No se editan hashes de confianza: si la nueva definición requiere una aprobación
del cliente, se realiza mediante su interfaz nativa. La entrada estable evita
depender de la ruta de un caché retirado en actualizaciones posteriores, pero no
demuestra recarga de skills ni despacho exitoso por sí sola.

El experimento nativo se prerregistra separando baseline de un agente, delegación
nativa y Constellation, con controles de capacidad y recuperación. Su diseño y
estado están en [metodología de evaluación](evaluation.md). Las pruebas deterministas del
motor y del instalador no sustituyen esa comparación. No se atribuyen mejoras de
calidad, latencia o coste antes de obtener y analizar los resultados.

### Inventario histórico 1.1

Auditoría inicial: 2026-10-18, Codex CLI 0.163.0. Se examinó la infraestructura
de los 21 repositorios registrados, OmarOS, configuración nativa y distribución
Constellation. No se usaron conversaciones, secretos o contenido personal como
contexto. Los resultados históricos de 1.0 no certifican esta migración.

| Componente previo | Evidencia inicial | Decisión |
| --- | --- | --- |
| Cinco módulos del hub | Implementaciones de workflow, workspace, dispatch, review y agent policy | Consolidar en `ecosystem/runtime`; conservar entradas pequeñas compatibles |
| Revisión portable | Ya importaba el mismo algoritmo del hub | Mantener un algoritmo y una política compartida en el paquete |
| Registro Git + registro portable obligatorio | La skill de ingeniería exigía ambos ciclos | Eliminar la obligación ritual; elegir ciclo por sus garantías y objetivo |
| Skills globales, locales y plugins | Descubrimiento nativo real, carga progresiva documentada | Retener mecanismos nativos, sin copiarlas todas a Constellation |
| Diagnóstico del plugin | Filtraba sólo Constellation e ignoraba `warnings` | Ampliar el adaptador nativo con estados y superficie explícitos |
| Hooks del hub | Cuatro eventos; Stop confiado pero deshabilitado | Retirar definiciones duplicadas; un adaptador del plugin para contratos activos |
| Hooks del plugin | Cinco eventos confiados y habilitados; sólo veían contratos portables | Integrar selección explícita del contrato activo sin autoiniciar trabajo |
| OmarOS | Motor especializado y copia casi idéntica del algoritmo de revisión | Consumir revisión compartida; retener semántica de dominio y publicación independiente |
| 19 hijos nativos | Cuatro archivos `.codex`, sin copias de motores/agentes/hooks | Conservar dominio y protección contra proyección; reducir overrides redundantes cuando se verifica herencia |
| `.claude` | Infraestructura paralela con consumidores reales, incluidos validadores Git | Aislar por cliente; no borrar validadores de dominio que siguen ejecutándose |
| `ruflo` externo | Hooks rechazados por `_generated_by`; timeouts obsoletos y auto-memory | Diagnosticar incompatibilidad; conservar propiedad externa y no ejecutar automatismos |
| Caché y catálogo instalado | Caché 1.0 válido; catálogo con cinco `.DS_Store` adicionales | Tratar como derivados; actualización validada desde fuentes, preservando extras |
| Contexto y agentes locales | Override de contexto 1.000.000/900.000 en el hub y seis perfiles heredados | Retirar override y perfiles duplicados; conservar ocho perfiles especializados y límites nativos por modelo |
| Aprendizaje personalizado | Preferencias explícitas del usuario; sin ejemplos suficientes para un perfil definitivo | Perfil local provisional y calibración en la skill de enseñanza; no datos personales en el paquete |
| Continuidad y diario | Estado operativo existente, Git y mecanismos propios de OmarOS | Añadir checkpoints al almacén existente y una proyección curada con autorización exacta; sin otro motor ni base de datos |
| Código pequeño | Clasificación ordinaria Standard aunque el cambio fuera acotado | Permitir Quick justificado antes de la primera ronda cuando ambas políticas lo admitan; conservar Deep y pisos de riesgo |

El inventario inicial del app-server encontró 21 skills/18 habilitadas en el
hub, 18/18 en Sweeplab, 120/22 en OmarOS y 191/191 en ruflo. OmarOS conserva
cuatro skills locales habilitadas y 98 exclusiones deliberadas. El listado de
plugins tenía 24 instalados y 23 habilitados; no equivale al catálogo de skills
de un proceso nuevo ni al de esta sesión.

Un directorio vacío sin Git descubrió 18 skills habilitadas, incluidas las tres
de Constellation, y seis hooks (uno global y cinco del plugin), sin crear
archivos en el directorio. Esto prueba integración nativa sin scaffolding para
descubrimiento; las pruebas de ejecución se registran por separado.

### Actualización reversible

La fuente es este checkout. El builder genera un bundle con inventario explícito;
el instalador verifica la distribución anterior y conserva configuración ajena.
No se edita el caché como fuente ni se modifica confianza para hacer pasar una
prueba. Una distribución nueva se instala usando las operaciones nativas.

Los estados de tareas existentes conservan sus formatos y ubicación privada.
Los adaptadores públicos preservan las invocaciones habituales. Los cambios de
evidencia o política invalidan la revisión correspondiente; una actualización
no concede aprobación a trabajo anterior. La recuperación de un intento
interrumpido es explícita y nunca fabrica un check exitoso.

`task_progress` se crea al primer hito sustancial, sin migración masiva de tareas
anteriores. Mantiene UUID y cronología al replanificar. La política personal del
diario no se genera desde el registro de repositorios: sólo permite raíces y
aliases explícitos. El receptor OmarOS actualiza su bundle fijado para consumir
progreso y revisión; la nota y el dashboard se crean mediante su propio workflow.
Su recibo local no acredita publicación. Consulta [progreso recuperable](progress.md).

El perfil de aprendizaje y las instrucciones locales de calibración se conservan
fuera del bundle y de Git. La base inicial es provisional, derivada de requisitos
explícitos; los futuros ejemplos pueden refinarla o corregirla. Los ensayos
sintéticos usan perfiles ficticios aislados y no añaden preferencias reales.
Investigación, aprendizaje e ingeniería se componen por intención sin crear
motores independientes o selectores persistentes.

El instalador admite inventarios anteriores verificados al añadir recursos del
paquete, preservando estado privado y configuración ajena. Las pruebas cubren
actualizaciones desde recibos de esquemas 1 y 2 en hogares temporales. Esa
compatibilidad no autoriza archivos desconocidos ni demuestra por sí sola que
la instalación personal haya sido actualizada.

La restauración consiste en desplegar una distribución anterior verificada y
restaurar exclusivamente los archivos de configuración modificados, con revisión
del estado de tareas que corresponda. No requiere reset de historia, borrar
trabajo, habilitar plugins desactivados ni conceder confianza a hooks.

### Validación

La matriz vigente y sus límites se describen en [metodología de evaluación](evaluation.md).
Las suites automatizadas prueban controles y rechazos en repositorios y remotos
temporales. La selección real de skills y la ejecución de agentes se evalúan
como experimentos separados: los fixtures deterministas no las sustituyen.
