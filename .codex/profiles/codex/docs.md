# Codex: mapa y documentación local

| Capa | Ubicación |
| --- | --- |
| Instrucciones globales | `~/.codex/AGENTS.md` |
| Ajustes del cliente | `~/.codex/config.toml` |
| Instalación verificada de Constellation | `~/.codex/constellation/` |
| Recursos nativos instalados | `~/.codex/{agents,skills,plugins}/` |
| Documentación oficial local | `~/.codex/docs/official/` |
| Herramienta de documentación | `~/.codex/tools/official_docs.py` |
| Recuperación local | `~/.codex/backups/` |

La [fuente común]({{SOURCE_ROOT}}/README.md) contiene el motor y los perfiles
portables de ambos clientes. El estado privado y las rutas nativas pertenecen
a Codex: no se trasladan bases de datos, historiales, locks o paquetes para
reducir visualmente el número de archivos en la raíz.

[INDEX.md](official/INDEX.md) da acceso a las copias oficiales de OpenAI,
incluidos el manual condensado, el índice, el export completo y las páginas
seleccionadas. [manifest.json](official/manifest.json) guarda fuentes, fechas UTC,
tamaños y SHA-256.

```sh
python3 -B ~/.codex/tools/official_docs.py --provider codex search 'AGENTS.md'
python3 -B ~/.codex/tools/official_docs.py --provider codex verify
python3 -B ~/.codex/tools/official_docs.py --provider codex refresh
```

Las descargas son explícitas y conservan una copia anterior. La búsqueda y
verificación no usan red ni modelos. Consulta la fecha y la fuente cuando un
ajuste pueda haber cambiado. Lee páginas concretas; no cargues el export entero
sin necesidad ni ejecutes ejemplos por el hecho de descargarlos.

Las [instrucciones para otros entornos]({{SOURCE_ROOT}}/.codex/profiles/README.md)
explican qué se publica y qué se regenera. El registro local del perfil está en
`docs/maintenance/profiles.json`; los registros locales de limpieza también
permanecen bajo `docs/maintenance/`. Cada proyecto conserva sus propios contratos.
