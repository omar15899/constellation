# Constellation

Una fuente para los ocho agentes, las skills y los encargos de Omar. Codex
selecciona herramientas y ejecuta subagentes nativos; Constellation registra
alcance, evidencia y publicación. Las consultas se responden directamente.

```text
Constellation/
├── constellation.py       # única entrada
├── constellation/         # estado, Git, hooks e instalación
├── agents/                # ocho definiciones heredadas
├── skills/                # métodos y recursos, agrupados por propietario
├── profiles/              # restricciones y destinos de los proyectos
├── instructions/          # contrato común
├── resources/automations/ # automatizaciones conservadas y conectadas
├── git-hooks/             # entradas Git al mismo control
├── tests/                 # pruebas y comprobación nativa
├── resource-inventory.json
└── migration.py           # inventario, protección y retirada explícita
```

## Instalar

Python 3.11+, Git y Codex. Mantén este checkout fuera de `~/.codex`. Ajusta las
raíces de `profiles/projects.json` si cambia el equipo. Desde esta carpeta:

```sh
python3 constellation.py install
python3 constellation.py install --apply
python3 -m unittest discover -s tests -v
```

La primera orden muestra el plan. La segunda conserva recibos privados antes de
cambiar entradas nativas. Los ajustes personales, autenticación, sesiones y
privacidad siguen perteneciendo a Codex. La confianza de hooks se concede por
su interfaz nativa y debe comprobarse en una sesión nueva. Las skills de terceros
siguen instaladas por su proveedor. Cada repositorio conserva su Git y datos.

## Usar

Lee el perfil del dueño. Antes de editar, abre un encargo con rutas **exactas**
y los IDs reales de los autores nativos. Un encargo por dueño Git permite
trabajar en varios repositorios en paralelo sin compartir índices.

```sh
python3 constellation.py begin ejemplo < contrato.json
python3 constellation.py check ejemplo pruebas -- python3 -m unittest discover -s tests
python3 constellation.py status ejemplo
python3 constellation.py review ejemplo < revision.json
python3 constellation.py commit ejemplo 'Describe el cambio'
python3 constellation.py push ejemplo
```

`contrato.json` contiene `root`, `requirement`, `coordinator`, `session_id`,
`assignments` (ruta → ID del autor) y `required_checks` (p. ej. `["pruebas"]`).
Cuando el hook usa un UUID y el catálogo un nombre canónico, `actor_sessions`
asocia ese nombre con el UUID de ejecución dentro del encargo. Es información
de encaminamiento, no una prueba de identidad. `session_id` es la sesión padre;
el UUID del subagente llega como `agent_id`. Registra ambos antes de editar.
La revisión contiene `reviewer`, `evidence`, `verdict` y
`expected_fingerprint`, leído antes de revisar. El revisor es distinto de los
autores y del coordinador. Un cambio de contenido o evidencia invalida la
revisión. Guarda hitos curados mediante `checkpoint` con `{"summary":"..."}`.
Para corregir o transferir una asignación, `assign` recibe `path`, `author` y
`reason`: conserva los autores anteriores e invalida su evidencia. Registra el
ID devuelto por la herramienta nativa; el entorno puede contener el del padre.
Los registros privados viven en `~/.local/state/constellation`; no guardan
conversaciones ni salidas de herramientas.

`PreToolUse` comprueba las rutas de ediciones estructuradas y comandos
destructivos conocidos. No puede aislar todas las escrituras de un shell.
`Stop` señala trabajo local pendiente una vez, sin inventar un cierre. Git
controla el árbol candidato, los commits salientes y el destino exacto. La
publicación preserva el índice ajeno y se confirma consultando el SHA remoto.
Las identidades registradas permiten exigir independencia; no autentican al
proceso ni garantizan la calidad intelectual de una revisión.

El monitor de Notes/Reminders conserva sus tres snapshots locales mediante
recibo, hashes e índice exactos; esa vía automática no autoriza un push.

## Recuperar o revertir

Después de una interrupción: `python3 constellation.py recover ejemplo`.
Consulta primero su resultado; si el remoto ya contiene el commit previsto,
no se crea otro commit. Si cambió el destino o existe divergencia, se bloquea.
Las pruebas y revisiones quedan congeladas durante la publicación. Si el remoto
confirma el commit pero quedan ediciones locales del alcance, el encargo sigue
abierto: repite `check`, `review` y `commit` en él. Conserva la publicación anterior
y las ediciones; `recover` no las descarta.

Para revertir la instalación: `python3 constellation.py install --rollback RECIBO`.
Los recibos se guardan fuera de Git y el rollback rechaza cambios posteriores.
La retirada histórica tiene su manifiesto exacto y copia privada; recupera lo
versionado desde Git y el estado local desde esa copia. No borres los recibos
ni el historial mientras puedas necesitar la reversión.
