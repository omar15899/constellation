# Qué contiene el HOME de Codex

El HOME predeterminado es `~/.codex`; un `CODEX_HOME` explícito puede cambiarlo.
En este equipo también contiene el checkout de Constellation. Por eso conviven
fuente mantenida, configuración personal, instalaciones y estado creado por el
cliente. Esta guía atribuye cada nombre observado; no convierte su mera presencia
en prueba de uso ni recomienda borrar por antigüedad.

Para mantener el sistema, empieza por `README.md`, `config.toml`, `AGENTS.md`,
la fuente `.codex/` y la instalación `constellation/`. El resto tiene dueño y
función específicos. Los nombres internos se comprobaron con Codex CLI 0.166,
el CLI 0.165 y la aplicación de escritorio instalada; pueden
cambiar entre versiones. La evidencia del dispositivo queda en `docs/maintenance/`.

## Fuente e instrucciones

| Entrada en el HOME | Función y tratamiento |
| --- | --- |
| `README.md` | Entrada general del sistema y enlaces de operación. Fuente mantenida. |
| `AGENTS.md` | Instrucciones personales globales que lee Codex. Fuente mantenida. |
| `REVIEW.md` | Contrato de revisión y publicación de Constellation. Fuente mantenida. |
| `.codex/` | Fuente del motor, skills, perfiles y pruebas. Su estructura se detalla más abajo. |
| `.git/` | Historia, índice y evidencia privada del workflow Git. No es una caché. |
| `.github/` | Plantilla de pull requests del repositorio. |
| `.gitignore` | Allowlist que publica únicamente la fuente y excluye datos privados. |
| `docs/` | Documentación oficial descargada, su procedencia y registros locales de mantenimiento. |
| `tools/` | Herramienta documental desplegada desde la fuente versionada. |
| `backups/` | Recuperación local: `configuration`, `profiles`, `recovery`, `releases` y `retired-projects`. No se publica. |

## Configuración, políticas e identidad

| Entrada | Función y tratamiento |
| --- | --- |
| `config.toml` | Configuración efectiva: modelo, herramientas, plugins, permisos y proyectos. Se conserva localmente. |
| `auth.json` | Credenciales si el cliente utiliza almacenamiento en archivo. Privado. |
| `installation_id` | Identificador persistente de esta instalación. No sustituirlo por uno de otro equipo. |
| `keybindings.json` | Atajos de teclado de la aplicación. |
| `hooks.json` | Definiciones globales de hooks. La ejecución y confianza se comprueban por separado. |
| `hooks/` | Código al que remiten los hooks globales, incluido el guard de comandos existente. |
| `.hook-trust/` | Baselines de confianza de hooks; no fabricar ni copiar como aprobación de otro equipo. |
| `rules/` | Reglas de permisos para comandos y aprobaciones recordadas. No fusionar o retirar sin revisar su semántica. |
| `constellation-vault.json` | Inscripción del vault para el enrutado del motor compartido. |
| `constellation-vault-guards/` | Redirectores Git verificados del vault inscrito. |
| `knowledge-sync.json` | Política de sincronización documental consumida por el LaunchAgent configurado. |
| `progress-journal.json` | Autorización exacta de los orígenes cuyos hitos pueden proyectarse al diario. |
| `chrome-native-hosts-v2.json` | Registro y ciclo de vida de la integración con el host nativo de Chrome. |
| `.sandbox_migration` | Marcador de migración de políticas de sandbox. Evita repetir la migración. |
| `.personality_migration` | Marcador histórico sin consumidor localizado en los clientes contrastados. Se archiva conservando su contenido; no se atribuye una función actual demostrada. |

## Instalaciones y coordinación de procesos

| Entrada | Función y tratamiento |
| --- | --- |
| `constellation/` | Lanzador verificado, catálogo, recibo e infraestructura de evidencia portable. No editar las copias instaladas. |
| `agents/` | Roles nativos TOML desplegados por el instalador compartido. |
| `skills/` | Skills suministradas por el cliente, incluidas las de sistema. |
| `plugins/` | Plugins y código realmente ejecutado; incluye un servidor auxiliar de plugins con versión propia. No confundirlo con una descarga abandonada. |
| `packages/standalone/` | Versiones del CLI independiente y selección `current`. El lanzador de usuario consume esta instalación. |
| `packages/app-server-daemon/` | Versiones del servidor persistente y su selección. Es otro propietario de instalación. |
| `app-server-daemon/` | PID, locks, ajustes, socket del actualizador y logs rotados del servidor. |
| `app-server-control/` | Socket de control y exclusión durante el arranque del servidor. |
| `computer-use/` | Aplicación auxiliar, configuración y sesiones de control del ordenador. |
| `browser/` | Configuración y estado de Browser Use. |
| `ipc/` | Comunicación privada entre instancias del cliente. |
| `cross-instance-locks/` | Coordinación entre ventanas para funciones como dictado y atajos globales. |
| `thread-writer-locks/` | Exclusión de escritores de conversaciones. Un archivo de cero bytes puede estar abierto y ser necesario. |
| `node_repl/` | Metadatos de ejecuciones del REPL de Node. Los subdirectorios vacíos pueden recrearse. |
| `tui-thread-reference-capabilities/` | Marcadores de capacidades para referencias entre hilos y tareas de la interfaz de terminal. |
| `tmp/` | Wrappers y enlaces de comandos por proceso, junto a sus locks de vida. Conservar los que sigan en uso o referenciados por el entorno. |
| `process_manager/` | Registro antiguo de procesos de chats sin consumidor localizado en los clientes y herramientas contrastados. Se archiva íntegro como legado, sin borrar sus datos únicos. |

Las dos instalaciones de paquetes pueden contener bytes iguales con destinos
distintos. Eso no basta para eliminar una: `selection-history` registra versión
actual y anterior, y el cliente incluye lógica de poda y validación de selección
anterior. Una copia puede estar ejecutándose o conservar la ruta de recuperación
del propietario. No se sustituyen estos contratos por enlaces artificiales.

## Conversaciones y datos privados

| Entrada | Función y tratamiento |
| --- | --- |
| `sessions/` | Registros persistentes de conversaciones. No son temporales. |
| `history.jsonl` | Historial persistente del cliente. |
| `session_index.jsonl`, `session_index.jsonl.lock` | Índice de sesiones y exclusión de acceso. |
| `external_agent_session_imports.json` | Registro de importaciones de sesiones externas leído por la aplicación. Su fecha antigua no lo vuelve prescindible. |
| `.codex-global-state.json`, `.codex-global-state.json.bak` | Estado global de la aplicación y copia de recuperación. El uso de la copia se atribuye parcialmente por convención y observación. |
| `attachments/` | Adjuntos locales de las conversaciones. Sólo se retiran contenedores vacíos e inactivos. |
| `.chatgpt-projects/` | Recursos e instrucciones descargados para proyectos ChatGPT. Puede haber material único. |
| `dictation-history/` | Audio y transcripciones locales del dictado. |
| `transcription-history.jsonl` | Historial global del dictado; el cliente puede crearlo aunque esté vacío. |
| `visualizations/` | Artefactos de visualización de conversaciones. Los archivos se conservan; las hojas vacías e inactivas se pueden retirar. |
| `shell_snapshots/` | Entornos y configuración de shell capturados para ejecutar comandos. |
| `memories/`, `memories_v2/` | Almacenes de memorias con coexistencia durante migración. No son duplicados demostrados. |
| `memories.lock`, `memories_v2.lock` | Coordinación de los workspaces de memorias; no retirar sólo porque estén vacíos o sin modificación reciente. |
| `learning/` | Perfil personal editable de aprendizaje y recuperación. No forma parte del paquete genérico. |
| `research-sync/` | Estado incremental consumido por el pipeline de ResearchLab. Es distinto de la política `knowledge-sync.json`. |

## Bases de datos

| Archivo o carpeta | Responsabilidad |
| --- | --- |
| `state_5.sqlite` | Estado general reanudable del runtime. |
| `thread_history_1.sqlite` | Historial persistente de hilos. |
| `goals_1.sqlite` | Estado de objetivos. |
| `queue_1.sqlite` | Cola persistente de trabajo. |
| `logs_2.sqlite` | Registros del cliente y su mantenimiento. |
| `memories_1.sqlite`, `memories_v2_1.sqlite` | Almacenes de memoria soportados por el cliente actual. |
| `*-wal`, `*-shm` | Escrituras pendientes y memoria compartida de SQLite; se mantienen junto a su base. |
| `.sqlite-maintenance.lock` | Exclusión del mantenimiento y checkpoints de SQLite. |
| `sqlite/` | Bases propias del escritorio, con variantes de producción/desarrollo. No duplican automáticamente las bases Rust de la raíz. |

Los sufijos numéricos de las bases son versiones de esquema usadas por el cliente
actual, no una lista de archivos antiguos que pueda eliminarse. Se contrastaron
los nombres con sus funciones nativas de apertura y migración y con los archivos
abiertos; no fue necesario consultar el contenido privado.

## Cachés y archivos generados

| Entrada | Función y criterio de limpieza |
| --- | --- |
| `.tmp/` | Git auxiliar, staging y locks de marketplaces. Se eliminan los repositorios que sólo contienen un HEAD inicial y directorios vacíos, tras validar estructura e inactividad. |
| `cache/` | Catálogos, información y herramientas de apps, exclusiones y catálogo remoto de plugins. Las cachés actualizadas durante el uso se conservan. |
| `vendor_imports/` | Caché de recomendaciones de skills y, según instalación, posibles fuentes importadas. Sólo se elimina la caché regenerable comprobada. |
| `models_cache.json` | Catálogo de modelos para un originador del cliente. |
| `models_cache.codex_work_desktop.json` | Catálogo de otro originador. Que sus bytes coincidan no elimina la separación nativa de claves. |
| `version.json` | Estado de consulta de actualizaciones, incluida la versión descartada o última comprobación. |
| `.DS_Store` | Metadatos de presentación de Finder. Se pueden borrar y Finder puede recrearlos. |
| `..codex-global-state.json.tmp-*` | Residuos de escrituras interrumpidas; retirar sólo cuando estén abandonados y sin uso. |

La última pasada usa una hora de margen para los esqueletos Git vacíos. Es una
decisión local conservadora, no una política de retención publicada de OpenAI.
Los wrappers de ejecución requieren además comprobar sus locks y que ninguna
entrada del entorno siga apuntando a ellos. No se vacían cachés activas para
obtener una reducción puramente momentánea del número de archivos.

## La carpeta de fuente `.codex/`

| Entrada | Función |
| --- | --- |
| `AGENTS.md` | Instrucciones para desarrollar esta fuente. |
| `README.md` | Operación, desarrollo y validación del motor. |
| `WORKSPACE.md` | Contrato entre propietarios; hay consumidores que requieren esta ruta. |
| `RESEARCH.md` | Método de investigación y coordinación de evidencia. |
| `QUANT_RESEARCH.md` | Entrada especializada que remite a los contratos del workspace cuantitativo. Es documentación útil, no código muerto. |
| `agent-policy.json` | Política de capacidad de agentes consumida por el runtime. |
| `profile.json` | Marcador del perfil nativo de este dueño. |
| `repositories.json` | Registro de propietarios; esta raíz sólo registra `.`. |
| `install.py` | Instalación de los controles Git de la fuente. |
| `git-hooks/` | Hooks Git activos de este repositorio. |
| `ecosystem/` | Motor, roles, manifiestos, plataformas, documentación y pruebas del paquete. |
| `skills/` | Fuentes canónicas de los métodos y recursos. |
| `profiles/` | Instrucciones, guías e instalador portable de los homes. |
| `tests/` | Pruebas de integración de esta fuente. |
| `ADAPTIVE_ORCHESTRATION_REPORT.md` | Informe local de revisión adaptativa y evaluación nativa. Está sin seguimiento y se conserva como trabajo previo. |
| Archivos locales no versionados | Pueden pertenecer a trabajo ajeno en curso. No se clasifican como basura por estar sin seguimiento. |

Los archivos que ya estaban sin seguimiento se preservan como trabajo ajeno.
Reorganizar el motor o retirar
documentación referenciada sólo para reducir nombres añadiría cambios de
contrato sin eliminar residuos demostrados.

## Cómo se comprobó

La atribución utiliza documentación oficial local, consumidores de la fuente,
la aplicación instalada, nombres de apertura/migración del CLI, enlaces de
selección y archivos abiertos. Las bases, memorias, conversaciones y credenciales
no se leen como contexto incidental. Una coincidencia de nombre sin un consumidor
específico se marca como legado o incertidumbre, no como uso demostrado.

Las guías oficiales de [configuración](https://learn.chatgpt.com/docs/config-file/config-basic)
y [seguridad](https://learn.chatgpt.com/docs/agent-approvals-security) describen las
fronteras públicas. Las rutas internas observadas aquí no son una API pública.
Los inventarios reales, decisiones y recibos de borrado permanecen locales y
separados de este mapa genérico versionado.
