# Operar desde GitHub

[AGENTS.md](../AGENTS.md) define los permisos y dueños del hub.
La [guía común](../../.codex/.codex/README.md) y la
[referencia de publicación](../../.codex/.codex/WORKSPACE.md) mantienen el método.
El mismo lanzador sirve desde cualquier carpeta:

```sh
"${CODEX_HOME:-$HOME/.codex}/constellation/run" cli workspace --root "$HOME/GitHub" route Shared/README.md PricingLab/README.md
"${CODEX_HOME:-$HOME/.codex}/constellation/run" cli agent-policy --root "$HOME/GitHub" show
```

[WORKSPACE.md](WORKSPACE.md) conserva las particularidades del hub:
registro, rama, coordinación y contratos de recepción. Cada hijo mantiene
sus instrucciones, pruebas, índice y publicación.

## Entrada histórica

`python3 .codex/ecosystem/cli.py …` comprueba el transporte instalado bajo
bloqueo y conserva el directorio del llamante. Para `workspace` y `agent-policy`
añade la raíz de este hub; un `--root` explícito posterior tiene precedencia.
Rechaza `--source`: desarrolla Constellation desde `~/.codex`, mediante
`python3 .codex/ecosystem/cli.py --source …`. Una instalación incompatible se
recupera con la [guía común](../../.codex/.codex/ecosystem/docs/migrations.md).

## Comprobaciones del adaptador

```sh
python3 -B -m unittest discover -s .codex/tests -v
```

Las pruebas del motor y su distribución pertenecen a la fuente canónica.
La confianza de hooks es del cliente; verifica su estado efectivo tras instalar.
