# Claude: configuración global

| Capa | Ubicación |
| --- | --- |
| Instrucciones personales | `~/.claude/CLAUDE.md` |
| Ajustes del cliente | `~/.claude/settings.json` |
| Plugin Constellation instalado | `~/.claude/skills/constellation/` |
| Documentación oficial local | `~/.claude/docs/official/` |
| Herramienta de documentación | `~/.claude/tools/official_docs.py` |
| Recuperación local | `~/.claude/backups/` |

La fuente mantenible de ambos perfiles está en
[profiles]({{SOURCE_ROOT}}/.codex/profiles/README.md). El motor y los métodos
compartidos pertenecen a la misma fuente de Constellation; cada cliente conserva
su instalación nativa. Los ocho agentes y cuatro skills de Claude vienen en el
plugin: no necesitan copias sueltas adicionales.

```sh
python3 -I -B ~/.claude/skills/constellation/ecosystem/claude.py verify
claude plugin validate ~/.claude/skills/constellation
claude plugin details constellation@skills-dir
python3 -B ~/.claude/tools/official_docs.py --provider all verify
```

El cliente administra también bases de datos, historiales, cachés, locks y
directorios de sesiones y background. Sus nombres y rutas nativas se conservan;
no son archivos de configuración que debamos reorganizar arbitrariamente.
`daemon/` y `jobs/` pueden contener trabajo aunque el supervisor no esté abierto.
Una antigüedad alta no demuestra que un dato sea prescindible.

GitHub guarda el perfil y sus herramientas, no las cuentas, credenciales,
conversaciones ni el estado del dispositivo. Para instalar en otro entorno sigue
la [guía portable]({{SOURCE_ROOT}}/.codex/profiles/README.md). Para actualizar
el motor usa sus instaladores y verifica la nueva copia antes de retirar la anterior.
Los ajustes, modelo, esfuerzo y permisos se eligen localmente en cada cliente.

Después de instalar, abre una sesión nueva y comprueba `/agents`, `/hooks` y
`/context`. Una validación de archivos no acredita confianza ni ejecución de hooks.
El archivo global nativo es `~/.claude/CLAUDE.md`: un `~/CLAUDE.md` adicional
puede cambiar la carga de instrucciones de todos los proyectos situados debajo,
según la [guía de Anthropic](https://code.claude.com/docs/en/memory).

Los repositorios conservan sus instrucciones y especializaciones: GitHub y
OmarOS son propietarios separados. No se globalizan sus permisos o herramientas
por el mero hecho de compartir motor.
