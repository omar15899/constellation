# Operar desde GitHub

El contexto local vive en [AGENTS.md](../AGENTS.md). Los proyectos comparten la instalación verificada de Constellation del equipo. El lanzador utiliza el intérprete que registró el instalador. La fuente canónica y el repositorio principal del orquestador están en `~/.codex`.

```sh
constellation() { "${CODEX_HOME:-$HOME/.codex}/constellation/run" cli "$@"; }
constellation workspace --root "$HOME/GitHub" route Shared/README.md PricingLab/README.md
constellation agent-policy --root "$HOME/GitHub" show
```

| Operación | Entrada |
| --- | --- |
| Un repositorio Git | `constellation git --root RUTA --session ID OPERACION` |
| Varios dueños Git | `constellation workspace --root "$HOME/GitHub" --session ID OPERACION` |
| Evidencia portable | `constellation --root RUTA OPERACION` |

El [workspace](WORKSPACE.md) agrupa archivos por dueño y respeta las dependencias. `git finish` y `workspace finish` implican publicación verificada en sus flujos Git. El cierre de consultas locales de OmarOS tiene su propio contrato. El [protocolo portable](https://github.com/omar15899/constellation/blob/main/.codex/ecosystem/references/protocol.md) describe las operaciones fuera de Git.

Con el perfil OmarOS instalado, `constellation skill-run --help` enumera sus auxiliares públicos, ejecutados con el intérprete del equipo. Finder y la captura de aprendizaje requieren la inscripción del vault. Las operaciones del curso siguen su contrato propio.

## Entrada histórica

`python3 .codex/ecosystem/cli.py …` conserva una entrada regular para los proyectos existentes. El adaptador pasa `workspace` y `agent-policy` a la instalación del equipo con la raíz de este hub, aunque se invoque desde otra carpeta. Un `--root` explícito posterior conserva precedencia. Otros comandos mantienen sus argumentos y el directorio de trabajo del llamante. `CODEX_HOME` conserva su significado habitual.

El adaptador comprueba el recibo, los bytes y los modos del transporte bajo el bloqueo de instalación antes de ejecutar el lanzador verificado. Rechaza una instalación incompleta o alterada.

El adaptador rechaza `--source`: el desarrollo se realiza desde `~/.codex`, mediante `python3 .codex/ecosystem/cli.py --source …`. No carga un motor del workspace ni sustituye la instalación verificada por una copia local. Una instalación ausente o incompatible se repara mediante la [guía de instalación](https://github.com/omar15899/constellation/blob/main/.codex/ecosystem/docs/migrations.md).

Las regresiones propias de esta entrada se ejecutan desde el hub:

```sh
python3 -B -m unittest discover -s .codex/tests -v
```

Las pruebas del motor y la construcción de la distribución pertenecen a la fuente canónica en `~/.codex`. Su [guía](https://github.com/omar15899/constellation/blob/main/.codex/README.md) describe los controles de desarrollo, instalación y actualización.

Comprueba los contratos de los dueños, sus índices, los checks y la revisión independiente antes de publicar. Este hub mantiene `codex/workspace`; la fuente mantiene `main`. La configuración de privacidad y la confianza de hooks pertenecen al equipo. Una declaración de hooks no acredita su ejecución efectiva.
