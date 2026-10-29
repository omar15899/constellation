# constellation

Herramientas compartidas para los repositorios independientes de `~/GitHub/`.
Cada repositorio conserva su historia, sus pruebas y su contrato. El
[registro operativo](.codex/repositories.json) delimita el workspace;
[QUANTOS.md](QUANTOS.md) describe la arquitectura cuantitativa.

Codex empieza en [AGENTS.md](AGENTS.md) y utiliza su
[perfil nativo](.codex/README.md): alcance explícito, pruebas, revisión
independiente y publicación verificada. Sus [ocho perfiles de agente](.codex/ecosystem/agents/)
apoyan el reparto del [workflow](.codex/WORKSPACE.md); el
[plugin portable](.codex/ecosystem/README.md) aporta las skills `coding`,
`mathematics`, `quant-research` y `writter`. El perfil se edita directamente y
`.codex/profile.json` impide que la proyección de Claude lo sustituya.

Claude conserva [CLAUDE.md](CLAUDE.md), su [entrada local](.claude/CLAUDE.md),
contratos, roles, skills y hooks. Los proyectos propios tienen perfiles Codex nativos
con sus reglas técnicas y una referencia al motor común. `ruflo` conserva su
perfil externo. Ninguna operación incluye otros proyectos sin declararlos.

Para trabajar sobre cualquiera de ellos desde la raíz o desde un hijo:

```sh
python3 ~/GitHub/.codex/ecosystem/cli.py workspace route Shared/README.md PricingLab/README.md
```

El [flujo entre repositorios](.codex/WORKSPACE.md) divide los archivos por dueño
Git y coordina plan, pruebas, revisión, commits y pushes. Cada push va al
upstream de su rama; las dependencias se publican en orden y se verifica el
SHA remoto. Los cambios pendientes ajenos y cada índice se preservan.

Para instalar y probar el flujo nativo:

```sh
python3 .codex/install.py
python3 -m unittest discover -s .codex/tests -v
```

Python 3.11+ y Git bastan para este flujo. Las herramientas de proyección de
Claude necesitan Python 3.12+. El [README de Codex](.codex/README.md) detalla las
pruebas específicas, la preservación de cambios previos y los límites de los
controles. Pasar pruebas o instalar hooks de Git no activa automáticamente los
hooks de Codex: sus nuevas definiciones requieren revisión nativa en `/hooks`.
