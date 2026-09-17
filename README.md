# constellation

Herramientas compartidas para los repositorios independientes de `~/GitHub/`.
Cada repositorio conserva su historia, sus pruebas y su contrato. El
[registro operativo](.codex/repositories.json) delimita el workspace;
[QUANTOS.md](QUANTOS.md) describe la arquitectura cuantitativa.

Codex empieza en [AGENTS.md](AGENTS.md) y utiliza su
[perfil nativo mínimo](.codex/README.md): autonomía, alcance explícito, pruebas
pertinentes y cierre con Git verificado. Se edita directamente y no carga
agentes especializados ni cadenas de skills. El marcador `.codex/profile.json`
impide que la proyección de Claude lo sustituya.

Claude conserva [CLAUDE.md](CLAUDE.md), su [kernel](.claude/CLAUDE.md), contratos,
roles, skills y hooks. Los 19 proyectos propios tienen perfiles Codex nativos
con sus reglas técnicas y una referencia al motor común. `ruflo` conserva su
perfil externo. Ninguna operación incluye otros proyectos sin declararlos.

Para trabajar sobre cualquiera de ellos desde la raíz o desde un hijo:

```sh
python3 ~/GitHub/.codex/workspace.py route Shared/README.md PricingLab/README.md
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

Python 3.9+ y Git bastan para este flujo. Las herramientas de proyección de
Claude necesitan Python 3.12+. El [README de Codex](.codex/README.md) detalla las
pruebas específicas, la preservación de cambios previos y los límites de los
controles. Pasar pruebas o instalar hooks de Git no activa automáticamente los
hooks de Codex: sus nuevas definiciones requieren revisión nativa en `/hooks`.
