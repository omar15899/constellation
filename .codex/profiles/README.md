# Perfiles portables de Codex y Claude

Este directorio es la fuente única de las instrucciones y herramientas personales
de ambos clientes. Constellation conserva su motor en `../ecosystem/` y sus
métodos en `../skills/`. El perfil añade las entradas globales de cada cliente,
las guías de navegación y una herramienta de documentación oficial; no introduce
otro motor de agentes.

| Fuente versionada | Destino local |
| --- | --- |
| `../../AGENTS.md` | `~/.codex/AGENTS.md` |
| `claude/CLAUDE.md` | `~/.claude/CLAUDE.md` |
| `claude/README.md` | `~/.claude/README.md` |
| `{codex,claude}/docs.md` | `~/.{codex,claude}/docs/README.md` |
| `official_docs.py` | `~/.{codex,claude}/tools/official_docs.py` |

Las dos copias instaladas de la herramienta proceden del mismo archivo fuente.
El instalador deja hashes y procedencia en `~/.codex/docs/maintenance/profiles.json`.
Los marcadores `{{SOURCE_ROOT}}` de las plantillas se sustituyen por la ubicación
del checkout; las plantillas no contienen rutas absolutas de un dispositivo.

## Preparar otro equipo

El perfil está probado en macOS/Linux con Python 3.11+ y Git. Instala los clientes
por sus canales oficiales y autentica cada uno en ese equipo. Este perfil no
transporta cuentas ni permisos. La herramienta de documentación utiliza `fcntl`;
este bootstrap no acredita compatibilidad con Windows nativo. Para el paquete
Claude Windows consulta [su guía](../ecosystem/docs/windows.md).

Clona el repositorio en una carpeta nueva, fuera de los homes nativos si ya
contienen estado. No ejecutes `git clone` encima de una configuración existente.

```sh
git clone https://github.com/omar15899/constellation.git "$HOME/src/constellation"
AI_SOURCE_ROOT="$HOME/src/constellation"

# Inspección: no escribe.
python3 -B "$AI_SOURCE_ROOT/.codex/profiles/install.py" --home "$HOME"

# Instalación de instrucciones, guías y herramienta.
python3 -B "$AI_SOURCE_ROOT/.codex/profiles/install.py" --home "$HOME" --apply
```

El instalador conserva archivos idénticos y rechaza conflictos antes de escribir.
Para sustituir deliberadamente un perfil previo usa `--backup-existing --apply`;
la copia anterior se conserva bajo `~/.codex/backups/profiles/`. Nunca aplica esa
opción a settings, credenciales, historiales o archivos ajenos al inventario.
No sigas editando copias desplegadas sin decidir si el cambio debe incorporarse
a la fuente: la siguiente instalación protege esas modificaciones como conflictos.

Al reemplazar un archivo, conserva el original desplazado bajo
`backups/profiles/<transacción>/captured/` y crea el nuevo destino sin sobrescribir
uno que aparezca entretanto. El nombre puede faltar brevemente entre captura y
promoción; este mecanismo conserva cambios concurrentes, no ofrece una operación
CAS frente a cualquier editor. Las capturas retienen su inode para conservar
también escrituras tardías mediante un descriptor abierto. El destino y su copia
de recuperación deben estar en el mismo sistema de archivos.

## Instalar el motor nativo

Construye un paquete general en un destino nuevo. El argumento `--source-root`
del constructor recibe la carpeta `.codex` de la fuente, no el HOME del cliente.

```sh
AI_BUNDLE_ROOT="$(mktemp -d)/constellation"
python3 -B "$AI_SOURCE_ROOT/.codex/ecosystem/build.py" \
  --source-root "$AI_SOURCE_ROOT/.codex" \
  --modules coding mathematics quant-research writter --output "$AI_BUNDLE_ROOT"

python3 -B "$AI_BUNDLE_ROOT/ecosystem/claude.py" install \
  --bundle "$AI_BUNDLE_ROOT" --claude-home "$HOME/.claude" --check
python3 -B "$AI_BUNDLE_ROOT/ecosystem/claude.py" install \
  --bundle "$AI_BUNDLE_ROOT" --claude-home "$HOME/.claude"

python3 -B "$AI_BUNDLE_ROOT/ecosystem/install.py" \
  --bundle "$AI_BUNDLE_ROOT" --codex-home "$HOME/.codex" --check
python3 -B "$AI_BUNDLE_ROOT/ecosystem/install.py" \
  --bundle "$AI_BUNDLE_ROOT" --codex-home "$HOME/.codex"

python3 -B "$HOME/.codex/tools/official_docs.py" --provider all refresh
```

La [guía de instalación del motor](../ecosystem/docs/migrations.md) gobierna
actualizaciones, formatos anteriores, recuperación y el módulo personal opcional
OmarOS. Conserva una instalación anterior hasta verificar su reemplazo. Comprueba
el catálogo y la confianza en cada sesión nativa nueva; copiar archivos no basta.

## Qué va a GitHub

Se publican código, instrucciones, plantillas, guías y pruebas. La allowlist del
repositorio excluye los homes efectivos: credenciales, conversaciones, memoria,
logs, bases de datos, configuraciones del dispositivo, recibos y backups.
Las copias oficiales de documentación se descargan localmente con URL, fecha y
hash; su lista de fuentes y la herramienta sí están versionadas. Los proyectos
conservan su configuración y Git propios.

## Mantener el orden

El perfil mantenido tiene cuatro responsabilidades visibles: instrucciones,
instalación nativa, documentación y recuperación. Los clientes añaden sus propios
archivos en raíz. No los escondas mediante enlaces ni traslados que contradigan
sus contratos. Las bases SQLite abiertas y sus WAL/SHM se mantienen juntas.

Elimina temporales y cachés sólo con evidencia de que son generados y están
inactivos. Antes de retirar un duplicado, comprueba nombres y bytes contra la copia
conservada. Conserva material único bajo `backups/`, agrupado por configuración,
versiones y recuperación. Registra rutas, motivo, tamaño y resultado en un recibo
local de `docs/maintenance/`; no publiques ese inventario del equipo.

```sh
python3 -B -m unittest discover -s .codex/tests -p 'test_home_profiles.py' -v
python3 -B -m unittest discover -s .codex/tests -p 'test_official_docs.py' -v
```
