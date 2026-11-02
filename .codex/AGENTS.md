# Fuente de Constellation

Esta carpeta contiene la fuente canónica del orquestador en `~/.codex`, rama
`main` de `omar15899/constellation`. Las instrucciones globales del usuario en
[AGENTS.md](../AGENTS.md) se conservan como tales. El contrato de desarrollo está
en [README.md](README.md); aplica también [REVIEW.md](../REVIEW.md) y
[RESEARCH.md](RESEARCH.md) cuando corresponda.

Mantén los métodos y las skills en `skills/`, el motor y los roles en
`ecosystem/`, y las pruebas de integración de la fuente en `tests/`. Prueba el
candidato con `python3 .codex/ecosystem/cli.py --source ...`; las operaciones
ordinarias usan el lanzador verificado `~/.codex/constellation/run`. No edites
las copias instaladas como fuente ni alteres recibos para superar comprobaciones.

`~/GitHub` es otro dueño Git, con su registro de proyectos y herramientas de
Claude en la rama `codex/workspace`. Proporciona `workspace --root ~/GitHub` para
operar allí. El registro de esta raíz sólo incluye `.`; no amplíes sus límites
para enrutar carpetas hermanas. OmarOS y cada proyecto conservan sus contratos.

Preserva cambios e índices ajenos. Registra requisitos, checks y autores reales,
obtén revisión independiente y publica únicamente el alcance declarado. La
allowlist de la raíz excluye configuración efectiva, credenciales, conversaciones,
estado de aplicación, perfiles privados y recursos instalados. No leas ni
publiques esos datos como contexto incidental de desarrollo.
