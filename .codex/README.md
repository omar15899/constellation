# Operar desde GitHub

El contexto local vive en [AGENTS.md](../AGENTS.md). Los proyectos comparten la instalación verificada de Constellation del equipo. Los ejemplos usan una función de shell para abreviar el comando estable del plugin. El lanzador utiliza el intérprete que registró el instalador del equipo.

```sh
constellation() { "${CODEX_HOME:-$HOME/.codex}/constellation/run" cli "$@"; }
constellation workspace route Shared/README.md PricingLab/README.md
constellation agent-policy show
```

| Operación | Entrada |
| --- | --- |
| Un repositorio Git | `constellation git --root RUTA --session ID OPERACION` |
| Varios dueños Git | `constellation workspace --root HUB --session ID OPERACION` |
| Evidencia portable | `constellation --root RUTA OPERACION` |

Con el perfil OmarOS instalado, `constellation skill-run --help` enumera los auxiliares públicos disponibles. Se ejecutan con el intérprete del equipo. Finder y la captura de aprendizaje requieren la inscripción del vault. Las operaciones del curso siguen su contrato propio.

El [workspace](WORKSPACE.md) agrupa archivos por dueño y respeta las dependencias. `git finish` y `workspace finish` implican publicación verificada en los flujos Git correspondientes. El cierre de consultas locales de OmarOS tiene su propio contrato. Las operaciones portables se describen en el [protocolo](ecosystem/references/protocol.md).

## Desarrollar la fuente

`python3 .codex/ecosystem/cli.py --source …` ejecuta deliberadamente el candidato del checkout para pruebas de desarrollo. Su invocación habitual por un proyecto o un hook Git remite a la instalación verificada. Una instalación incompatible requiere actualizar el equipo antes de operar. La [guía de instalación](ecosystem/docs/migrations.md) detalla el cambio de versión, la recarga de la sesión y la confianza local en los hooks.

```sh
python3 -B -m unittest discover -s .codex/tests -v
```

Comprueba los contratos de los dueños, sus índices, los checks y la revisión independiente antes de publicar. El estado de progreso y las autorizaciones personales se rigen por el [protocolo de progreso](ecosystem/docs/progress.md).


## Primer cambio de versión

Mantén operativa la entrada anterior mientras se construye, se revisa y se comprueba el paquete candidato. Instala ese paquete verificado en el equipo, comprueba que el lanzador puede enrutar un archivo del hub y otro de un hijo y, entonces, activa las entradas nuevas del checkout y sus hooks Git. Las futuras instalaciones se distribuyen por el procedimiento de [actualización](ecosystem/docs/updates.md).

Una distribución extraída en un directorio corriente admite pruebas portables mediante su propio CLI. El nombre reservado `.codex` exige la identidad de la fuente o un inventario coincidente con el del dispositivo. En ese segundo caso ejecuta el lanzador instalado. Un checkout ambiguo se rechaza antes de importar módulos del directorio.
