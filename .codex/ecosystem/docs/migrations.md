# Instalación y mantenimiento

Esta guía describe el formato activo de Constellation `1.4.0`. El paquete
tiene una sola estructura permitida. Los formatos retirados se rechazan sin
ejecutar ni sustituir sus archivos; no se convierten silenciosamente.

## Instalar y actualizar

Necesitas Python 3.11+ y el cliente elegido. `python3` debe resolver ese
intérprete en el entorno que inicia el cliente POSIX. Git se usa para publicación,
no para una entrega portable sin Git.

| Destino | Uso |
| --- | --- |
| `posix` | Codex y Claude Code en macOS/Linux. |
| `windows-claude` | Candidato para Claude Code en Windows nativo; aceptación real pendiente. |

Para Windows sigue [la guía específica](windows.md). No uses allí el instalador
Codex ni interpretes las pruebas de empaquetado como ejecución nativa Windows.

Desde las fuentes, elige rutas nuevas:

```sh
python3 .codex/ecosystem/build.py --language en \
  --output /tmp/constellation-1.4.0-en \
  --archive /tmp/constellation-1.4.0-en.zip
shasum -a 256 /tmp/constellation-1.4.0-en.zip
```

`--language en --target windows-claude` selecciona el paquete inglés para Claude
Windows. Un paquete portable ya construido conserva idioma y destino al
reconstruirse sin esas opciones; no realiza conversión. El ZIP es autocontenido.
Comprueba su hash por el canal de entrega y extrae en un destino nuevo. El hash
detecta diferencias, pero no autentica por sí solo al remitente.

### Instalación Claude

Con un paquete POSIX extraído:

```sh
python3 /ruta/paquete/ecosystem/claude.py install \
  --bundle /ruta/paquete --claude-home ~/.claude --check
python3 /ruta/paquete/ecosystem/claude.py install \
  --bundle /ruta/paquete --claude-home ~/.claude
python3 /ruta/paquete/ecosystem/claude.py verify --claude-home ~/.claude
claude plugin validate --strict --json ~/.claude/skills/constellation
```

El instalador gestiona `skills/constellation` con recibo Claude de esquema 1.
Conserva skills y ajustes ajenos y respeta una desactivación explícita. No copia
cuentas ni concede confianza. Abre una sesión nueva y comprueba catálogo, roles
y eventos reales del cliente: la validación estructural no prueba su despacho.

### Instalación Codex

```sh
python3 /ruta/paquete/ecosystem/install.py \
  --bundle /ruta/paquete --codex-home ~/.codex --check
python3 /ruta/paquete/ecosystem/install.py \
  --bundle /ruta/paquete --codex-home ~/.codex
```

Codex utiliza un recibo de esquema 4. La entrada estable
`$CODEX_HOME/constellation/run` tiene modo 0700 y un hash registrado en el
recibo. Invoca `hook.py` con el Python absoluto empleado al instalar, incluida
la ruta del entorno virtual. El instalador comprueba el recibo de la versión
anterior antes de migrarlo. El instalador conserva configuración ajena y
registra los roles que corresponden a los módulos elegidos. Si mantienes fuentes
y plugin activos a la vez, la exclusión nativa de fuentes requiere identidad
exacta entre ambas copias. Las fuentes españolas no son idénticas al paquete
inglés: usa el paquete extraído fuera del checkout en ese caso.

### Instalar una revisión publicada en varios equipos

Constellation publica su código en `main` de `omar15899/constellation`. Desde
un checkout de confianza o un paquete verificado, ejecuta este comando una vez
por dispositivo para seleccionar y promover el último commit publicado:

```sh
python3 -I -B .codex/ecosystem/sync.py --latest --vault-root "$RUTA_ABSOLUTA_OMAROS" \
  --workspace-root "$RUTA_ABSOLUTA_CONSTELLATION"
```

En una instalación existente, el mismo comando está disponible en
`~/.codex/constellation/catalog/plugins/constellation/ecosystem/sync.py`.
`--vault-root` instala los cuatro métodos generales y el módulo opcional
`omaros`. Su ejecución requiere Python 3.11+ con PyYAML y la ruta absoluta del
repositorio OmarOS de ese equipo. Las herramientas de búsqueda del vault usan
`rg`; las tareas de compilación de Brainteasers usan la distribución TeX del
proyecto. `--general` selecciona expresamente los
cuatro métodos generales. El idioma predeterminado es español. `--language en`
selecciona los textos ingleses disponibles. `--codex-home` y `--codex` permiten
usar la instalación y el ejecutable nativos del equipo.

`--latest` confía en la rama principal del único repositorio canónico, fija su
SHA en la copia temporal y construye exactamente esa revisión. Para exigir un
SHA aprobado independientemente, usa `--revision "$REVISION_APROBADA"` en
lugar de `--latest`. Si ha avanzado `main`, la comprobación del SHA fijado sale
antes de instalar. `--check` verifica el paquete y la
preinstalación sin cambiar la instalación ni registrar el vault. Git consulta la URL HTTPS canónica en un directorio temporal ajeno a los
proyectos, rechaza reescrituras de esa URL y fija configuración independiente
con verificación TLS y sin redirecciones. Se admiten helpers de credenciales
estándar o la integración nativa de GitHub CLI expresamente configurados para
GitHub. Al promover, el instalador comprueba bajo bloqueo que el recibo sigue
siendo el que se observó antes de la descarga. Si otro proceso ya cambió la
instalación, se obtiene el nuevo estado repitiendo la sincronización. El resultado
incluye el SHA de Git, el hash del inventario y los módulos. La instalación
utiliza el bloqueo, las comprobaciones y la recuperación del instalador. Repetir
la misma revisión y selección ya instalada devuelve `current` después de
verificar el contenido y el registro nativo.

Desde una instalación verificada, `"$HOME/.codex/constellation/run" install-vault --project-root "$RUTA_ABSOLUTA_OMAROS"` prepara el perfil personal
con el mismo ejecutable de Codex. Esta operación instala los controles Git
gestionados, configura las exclusiones nativas aplicables y registra la raíz
exacta al terminar. Un fallo en la preparación del vault identifica por
separado el paquete ya instalado. Corrige la condición indicada y repite el
comando con el mismo SHA. Las carpetas de ese dispositivo
comparten el paquete instalado. Abre una sesión nueva cuando la interfaz
necesite recargar su catálogo y comprueba la confianza de hooks en `/hooks`.
Para pasar de una revisión a otra en varios equipos, ejecuta el comando con un
mismo SHA aprobado en cada uno. La recepción del paquete y la activación nativa
se comprueban por dispositivo. El [actualizador periódico](updates.md) se activa
por dispositivo y `updates plan` muestra la definición que se instalará.

El argumento opcional `--workspace-root` aplica las exclusiones en el checkout
fuente real al final de la instalación. Requiere que sus fuentes correspondan
al paquete seleccionado. Si la carpeta falta, contiene cambios locales en los
recursos relevantes o está en otra revisión, el comando indica qué paso quedó
pendiente y distingue el paquete ya instalado. Conserva los cambios locales,
compara esa revisión y reintenta. `--check` omite la escritura de exclusiones.

También puedes completar ese paso por separado mediante el diagnóstico nativo.
`RUTA_CONSTELLATION` identifica el checkout permanente del equipo:

```sh
python3 -I -B "$HOME/.codex/constellation/catalog/plugins/constellation/ecosystem/native.py" \
  --codex-home "$HOME/.codex" --cwd "$RUTA_CONSTELLATION" \
  --exclude-source-root "$RUTA_CONSTELLATION/.codex"
```

La operación comprueba identidad de contenido y permisos de los recursos de
origen e instalación, actúa sobre las rutas seleccionadas y verifica el
resultado con un cliente nuevo. Las exclusiones corresponden al checkout
descubierto por el cliente del equipo.

### Diagnóstico de Codex

```sh
python3 /ruta/paquete/ecosystem/native.py \
  --codex-home ~/.codex --cwd /ruta/proyecto --capabilities
```

La consulta describe un proceso CLI nuevo; no instala componentes, carga skills
ni representa automáticamente una sesión abierta. La evidencia registrada del
CLI corresponde a 0.165.0. Revalida las capacidades si cambian cliente o versión.

Revisa `/hooks` para la habilitación y confianza efectivas. No edites hashes ni
uses opciones para eludir aprobación. Instalar, estar descubierto, estar
habilitado, estar confiado y haber ejecutado un evento son estados distintos.

## Integridad, actualización y recuperación

Los formatos actuales son inventario de bundle 1, recibo Codex 4, recibo Claude 1
y política/ledger de revisión 2. Un número de versión no sustituye la comprobación
del esquema, inventario, hashes, permisos e identidad. Un formato incompatible,
un archivo desconocido o una copia modificada bloquean la operación preservando
sus archivos para inspección explícita.

Una actualización entre versiones del formato compatible usa el mismo comando
con un paquete nuevo y verificado. Repetir el paquete instalado es idempotente.
El preflight no cambia el home indicado. Los hooks mantienen un lock compartido
durante verificación y ejecución; la sustitución necesita el lock exclusivo.

La promoción de directorios es exclusiva. Si un filesystem no ofrece la primitiva
necesaria, la operación falla sin sustituir datos ajenos. Ante un fallo controlado,
la copia anterior se restaura cuando su identidad y el destino de retorno siguen
verificados. Los datos parciales, cambiados o ajenos y las colisiones se conservan;
no se borran para aparentar recuperación. Inspecciona una interrupción antes
de reintentar.

El resultado del instalador Claude incluye `directory_sync`: `supported`, `unsupported` o `not_measured`. Un flush
de archivo no demuestra durabilidad de los metadatos del directorio ante cualquier
pérdida de alimentación. Windows usa DACL verificable para acceso privado;
un modo Unix lógico no sustituye esa protección.

No copies homes completos de Codex o Claude, credenciales, conversaciones,
perfiles personales o estados de proyectos. El estado operativo permanece fuera
del directorio de plugin sustituible. Las importaciones de un paquete inmutable
usan `python3 -B` para no introducir bytecode fuera del inventario.

## Receptores y evidencia

El perfil opcional de OmarOS ejecuta el ciclo del vault desde el paquete
verificado de Constellation. El registro de la raíz exacta es local al equipo y
los archivos de contexto, los datos y los permisos de publicación pertenecen
al repositorio correspondiente.

[Compatibilidad](compatibility.md) separa la evidencia por snapshot y plataforma;
[evaluación](evaluation.md) distingue pruebas de mecanismo y calidad sustantiva.
Los resultados retirados se consultan en Git, no se cargan como dependencias de
instalación. Las referencias nativas son los hooks de
[Codex](https://learn.chatgpt.com/docs/hooks) y
[Claude](https://code.claude.com/docs/en/hooks).
