# Constellation

Constellation coordina requisitos, evidencia, revisión y publicación sobre
Codex y Claude Code. Los clientes ejecutan modelos, herramientas y agentes;
cada proyecto conserva sus archivos, permisos y dueño Git. La distribución
actual `1.4.0` reúne cuatro métodos generales y ocho roles. La edición
personal añade siete skills y el perfil OmarOS al mismo runtime instalado.

El coordinador consulta el catálogo de su sesión y carga las instrucciones
pertinentes. Descubrimiento, habilitación, autorización, ejecución y calidad del
resultado son hechos distintos. La [arquitectura](docs/architecture.md) delimita
esas responsabilidades; la [compatibilidad](docs/compatibility.md) conserva la
evidencia y sus límites.

## Elegir el flujo

| Resultado | Ejecución |
| --- | --- |
| Pregunta breve o edición local pequeña | Respuesta y comprobación proporcional, respetando cualquier contrato receptor activo. |
| Cambio Git | Un contrato del dueño, checks, revisión y publicación con `ecosystem/cli.py git`. |
| Coordinación de repositorios | `ecosystem/cli.py workspace`; contratos separados por dueño Git. |
| Investigación o documento con evidencia persistente | Protocolo portable, incluso sin Git; su cierre no publica. |

Las skills `coding`, `mathematics`, `quant-research` y `writter` cubren ingeniería,
argumentos matemáticos, investigación sistemática y escritura sustantivas. Úsalas
según la tarea y las instrucciones del receptor. Una explicación breve no crea
por sí sola un equipo o contrato. El recordatorio estático de métodos no lee ni
almacena prompts y no prueba selección correcta de una skill.

## Estructura

| Fuente | Responsabilidad |
| --- | --- |
| `.codex/skills/` | Fuentes canónicas de los cuatro métodos generales y las siete skills del módulo OmarOS. |
| `.codex/ecosystem/runtime/` | Git, workspace, reparto, revisión y progreso. |
| `core.py`, `storage.py`, `cli.py` | Contratos portables, persistencia privada y entrada pública. |
| `platform_support.py` | Primitivas de filesystem y acceso por plataforma. |
| `manifests/` y `agents/` | Manifiestos nativos y ocho roles canónicos. |
| `references/` y `docs/` | Método, protocolo y guías vigentes. |
| `tests/` y `evals/` | Pruebas y fixtures de evaluación actuales. |
| `locales/en/` | Traducciones fuente seleccionadas al construir; no otra instalación activa. |

El constructor permite sólo un inventario explícito. Genera los agentes Claude
desde los TOML y el bootstrap autónomo desde las fuentes canónicas; no mantiene
otro cuerpo manual. El historial se consulta en Git, sin informes retirados como
dependencias de la entrega.

## Instalar y actualizar

Se requiere Python 3.11+ y el cliente elegido. El destino `posix` cubre
macOS/Linux; `windows-claude` es el candidato para Claude en Windows nativo, sin
WSL. Su aceptación real allí sigue pendiente. Sigue la
[guía de Windows](docs/windows.md) para ese destino.

Desde las fuentes, usa un destino nuevo:

```sh
python3 .codex/ecosystem/build.py --language en \
  --output /tmp/constellation-1.4.0-en \
  --archive /tmp/constellation-1.4.0-en.zip
shasum -a 256 /tmp/constellation-1.4.0-en.zip
```

La edición predeterminada conserva las fuentes españolas. Ambas ediciones usan
el mismo identificador: instala una por cliente. El paquete no copia cuentas,
credenciales, conversaciones, perfiles personales ni datos de proyectos.

La [guía de instalación](docs/migrations.md#instalar-y-actualizar) describe
preflight, verificación y actualizaciones del formato actual. Los formatos
retirados se rechazan conservando sus archivos; no hay una conversión implícita.
Instalar o conservar una ruta no concede confianza a los hooks.

## Trabajar y comprobar

En un equipo configurado, la entrada estable verifica la distribución instalada
y mantiene el bloqueo mientras utiliza el workspace, el contrato Git del proyecto
o una skill:

```sh
entry="${CODEX_HOME:-$HOME/.codex}/constellation/run"
"$entry" cli workspace route Shared/README.md
"$entry" cli git --root /ruta/proyecto --session ID begin
"$entry" cli skill-read writter
```

La CLI del checkout admite `--source` para desarrollar el motor desde su dueño
Git. La API portátil también funciona desde una distribución extraída y verificada.

El [protocolo](references/protocol.md) separa Git y entrega portable. En Claude,
la identidad de ciclo es `claude-<session_id>`; los autores y revisores conservan
sus IDs nativos. El trabajo sustancial mantiene
[progreso recuperable](docs/progress.md) en el almacén existente.

Las comprobaciones de inventario y revisión vinculan versión y evidencia;
no demuestran por sí solas verdad matemática, calidad editorial o rendimiento.
La [evaluación](docs/evaluation.md) distingue esas obligaciones y conserva los
resultados negativos.
