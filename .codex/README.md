# Trabajar con Codex y Constellation

## Una instalación para todas las carpetas

Usa el mismo chat para un encargo que abarque OmarOS y código de GitHub. En la
app de escritorio puedes abrir **Editar proyecto** en un proyecto local,
añadir ambas carpetas y elegir una principal. Los chats nuevos, Git por defecto
y el descubrimiento automático de instrucciones, skills y configuración
parten de la principal. Para el trabajo personal de Omar, el proyecto local
usa **OmarOS como principal** y adjunta `~/GitHub`. Mantén **un chat por
encargo**, aunque abarque varios repositorios.
[Proyectos locales de Codex](https://learn.chatgpt.com/docs/projects#use-local-projects-for-folders-and-codebases)

Al trabajar en una carpeta secundaria, lee el `AGENTS.override.md` o
`AGENTS.md` aplicable desde su raíz Git hasta la carpeta afectada, y el
contexto y las restricciones que indique. Cada hijo de `~/GitHub` es una
raíz Git independiente. Para el vault, empieza por su `AGENTS.md` y
`.codex/PROJECT.md`. Para el hub, usa su `AGENTS.md` y
`.codex/WORKSPACE.md` cuando coordines proyectos.
[Descubrimiento de instrucciones](https://learn.chatgpt.com/docs/agent-configuration/agents-md#how-codex-discovers-guidance)

| Necesidad | Fuente |
| --- | --- |
| Preferencias comunes de trabajo y código | [`AGENTS.md`](../AGENTS.md), cargado globalmente desde el directorio de Codex |
| Método de programación | [`coding`](skills/coding/SKILL.md) para el coordinador y [roles nativos](ecosystem/agents/) para delegar |
| Datos, pruebas y publicación del proyecto | Instrucciones del dueño Git y del área afectada |
| Permisos, ajustes y datos de la aplicación | Configuración efectiva del cliente y [rutas nativas](profiles/codex/layout.md) |

Las instrucciones de ingeniería aplican también a agentes sin la skill
`coding`. Los roles especializados añaden el método de implementación, revisión
o verificación y heredan modelo y esfuerzo cuando el cliente lo permite.

## Operar desde cualquier carpeta

El mismo lanzador instalado resuelve las operaciones. Mantén el ID del chat en
los contratos del encargo y selecciona la raíz explícita de cada dueño.

```sh
constellation_entry="${CODEX_HOME:-$HOME/.codex}/constellation/run"
"$constellation_entry" cli workspace --root "$HOME/GitHub" route Shared/README.md
"$constellation_entry" cli git --root "$HOME/.codex" --session ID status
"$constellation_entry" vault --project-root "$HOME/OmarOS" --session ID status
```

Usa [la referencia de publicación](WORKSPACE.md) para un dueño Git o varios
dueños del hub. En OmarOS, su adaptador y su contrato gobiernan el contenido
del vault y los cambios delegados. La [evidencia portable](ecosystem/references/protocol.md)
sirve para trabajos que la requieren fuera de Git. Un contrato independiente
por dueño permite conservar el historial, el índice y el destino de cada
repositorio dentro del mismo chat.

## Mantener la instalación

Desarrolla en la [fuente canónica](AGENTS.md) y prueba explícitamente el
candidato con `python3 .codex/ecosystem/cli.py --source ...` y Python 3.11 o
posterior. Los hooks Git, el hub y el vault consumen la distribución verificada
del equipo.

```sh
cd "$HOME/.codex"
python3 -B -m unittest discover -s .codex/tests
python3 -B -m unittest discover -s .codex/ecosystem/tests
```

Sigue la [guía de instalación y recuperación](ecosystem/docs/migrations.md)
para construir, validar y promover una revisión. Después comprueba el catálogo
de un cliente nuevo, las raíces de destino y el estado de confianza de los
hooks. La evidencia de instalación y la de ejecución nativa se obtienen por
separado.

Consulta los [criterios de revisión](../REVIEW.md), la
[guía de progreso](ecosystem/docs/progress.md) o los
manuales oficiales en `~/.codex/docs/official/INDEX.md` cuando el
trabajo los requiera. En otro equipo prepara primero el
[perfil portable](profiles/README.md).
