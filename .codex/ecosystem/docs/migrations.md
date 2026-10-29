# Instalación y mantenimiento

Esta guía describe el formato activo de Constellation `1.4.0-rc.1`. El paquete
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
  --output /tmp/constellation-1.4.0-rc.1-en \
  --archive /tmp/constellation-1.4.0-rc.1-en.zip
shasum -a 256 /tmp/constellation-1.4.0-rc.1-en.zip
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

Codex usa su registro nativo, recibo de esquema 3 y la entrada estable
`CODEX_HOME/constellation/hook.py`. El instalador conserva configuración ajena y
registra los roles que corresponden a los módulos elegidos. Si mantienes fuentes
y plugin activos a la vez, la exclusión nativa de fuentes requiere identidad
exacta entre ambas copias. Las fuentes españolas no son idénticas al paquete
inglés: usa el paquete extraído fuera del checkout en ese caso.

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

Los formatos actuales son inventario de bundle 1, recibo Codex 3, recibo Claude 1
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

El adaptador activo de OmarOS mantiene cuatro recursos verificados fijados en
1.2.0 y su propio ciclo. No es un formato retirado. La instalación del plugin
no autoriza sobrescribir ese receptor ni cambiar su pin.

[Compatibilidad](compatibility.md) separa la evidencia por snapshot y plataforma;
[evaluación](evaluation.md) distingue pruebas de mecanismo y calidad sustantiva.
Los resultados retirados se consultan en Git, no se cargan como dependencias de
instalación. Las referencias nativas son los hooks de
[Codex](https://learn.chatgpt.com/docs/hooks) y
[Claude](https://code.claude.com/docs/en/hooks).
