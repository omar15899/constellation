# Operar y desarrollar Constellation

La fuente canónica de este equipo es `~/.codex`, rama `main` del repositorio
privado `omar15899/constellation`. Su [arquitectura](ecosystem/docs/architecture.md)
separa la fuente, la instalación verificada y los datos propios de cada proyecto.
Las instrucciones globales permanecen en [AGENTS.md](../AGENTS.md); el contexto
específico de desarrollo está en [AGENTS.md](AGENTS.md).

## Usar la instalación del equipo

```sh
constellation() { "${CODEX_HOME:-$HOME/.codex}/constellation/run" cli "$@"; }
constellation git --root "$HOME/.codex" --session ID status
constellation workspace --root "$HOME/GitHub" route Shared/README.md PricingLab/README.md
constellation agent-policy --root "$HOME/.codex" show
```

| Operación | Entrada |
| --- | --- |
| Un repositorio Git | `constellation git --root RUTA --session ID OPERACION` |
| Varios dueños en GitHub | `constellation workspace --root "$HOME/GitHub" --session ID OPERACION` |
| Evidencia portable | `constellation --root RUTA OPERACION` |

El lanzador usa el intérprete registrado por el instalador y verifica el paquete.
Los hooks Git y los adaptadores de OmarOS y del workspace consumen esa misma
instalación. Con el módulo `omaros`, `constellation skill-run --help` enumera los
auxiliares públicos; finder y la captura requieren la inscripción exacta del vault.

El [workspace](WORKSPACE.md) respeta los límites de los dueños Git. `git finish`
y `workspace finish` requieren publicación verificada. Las consultas locales de
OmarOS conservan su propio cierre. La evidencia portable sigue el
[protocolo](ecosystem/references/protocol.md).

## Desarrollar la fuente

Desde `~/.codex`, `python3 .codex/ecosystem/cli.py --source ...` selecciona
explícitamente el candidato. Sin `--source`, la entrada utiliza la instalación
verificada y toma esta raíz como workspace predeterminado; para operar en el
workspace de proyectos proporciona siempre `workspace --root "$HOME/GitHub"`.

```sh
cd "$HOME/.codex"
python3 -B -m unittest discover -s .codex/tests -v
python3 -B -m unittest discover -s .codex/ecosystem/tests -v
```

Construye y comprueba el paquete candidato antes de promoverlo. La
[guía de instalación](ecosystem/docs/migrations.md) distingue las fuentes, la
promoción del paquete y la confianza de hooks del cliente. Las
[actualizaciones](ecosystem/docs/updates.md) siguen el `main` publicado;
`--workspace-root "$HOME/.codex"` selecciona ahora la fuente cuyas skills deben
excluirse del descubrimiento duplicado, no el workspace operativo de proyectos.

Mantén operativa la instalación anterior durante una actualización. Después,
comprueba el lanzador, el enrutado de un archivo del hub y otro de un hijo, y el
adaptador de OmarOS. Una sesión abierta conserva su catálogo cargado; revalida
la ejecución y confianza nativas en una nueva sesión cuando corresponda.

Una distribución extraída puede ejecutar pruebas portables con su propio CLI.
El nombre reservado `.codex` exige identidad de fuente versionada o un inventario
coincidente con la instalación; un checkout ambiguo se rechaza antes de importar
sus módulos. La [política de revisión](../REVIEW.md) y el
[progreso recuperable](ecosystem/docs/progress.md) completan el flujo de entrega.
