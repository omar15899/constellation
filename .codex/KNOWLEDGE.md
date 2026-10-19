# Documentación e investigación en OmarOS

Constellation coordina la recepción de documentación e informes completos de
los repositorios autorizados de `~/GitHub` en OmarOS. Cada repositorio conserva
la autoridad sobre sus fuentes. OmarOS ofrece una copia documental consultable,
con procedencia verificable y un índice común. La decisión de gobierno está en
`~/OmarOS/20_System_Governance/Decisions/2026-10-19_constellation_document_sync.md`.

La autorización inicial incluye los repositorios propios personales y laborales.
Los proyectos externos, como `ruflo`, necesitan autorización específica. El
registro `repositories.json` identifica proyectos y permite detectar altas
pendientes; pertenecer al registro o tener perfil nativo no concede permiso de
exportación.

## Qué se centraliza

El productor [knowledge_sync.py](knowledge_sync.py) lee blobs del `HEAD` local de
cada fuente autorizada. No modifica el repositorio ni necesita publicarlo para
leer esa revisión. Selecciona documentos de texto `.md`, `.rst`, `.txt`, `.tex`
y `.bib`; admite `.pdf`, `.docx`, `.pptx`, `.png`, `.jpg`, `.jpeg`, `.svg` y
`.webp` en directorios documentales como `docs`, `doc`, `documentation`,
`reports`, `research`, `papers`, `notes` y `figures`.

La selección excluye directorios ocultos, instrucciones activas de agentes,
código, dependencias, datos, logs, conversaciones, prompts y estados privados.
`include_paths` permite autorizar archivos documentales exactos y versionados
en ubicaciones ocultas, como `.codex/RESEARCH.md`; no admite patrones ni abre
el directorio completo. Los vetos de privacidad e instrucciones activas se
mantienen incluso con esa autorización.
Los nombres `AGENTS.md`, `CLAUDE.md`, `SKILL.md` y `REVIEW.md` no se importan como
instrucciones al vault. Los documentos recibidos son contenido de consulta y
nunca se ejecutan ni adquieren autoridad sobre las instrucciones de OmarOS.

Los informes locales fuera de Git requieren `local_paths`: directorios exactos
autorizados por fuente. Allí se admiten únicamente `report.md`,
`diagnostics.md`, `sleeve_diagnostics.md` y `comparison_YYYY-MM-DD.md`. Esta vía
incorpora también sus dependencias inline de imágenes, PDF y `tables/*.md`
cuando están referenciadas y dentro de las mismas raíces locales autorizadas.
No incorpora la carpeta completa ni descarga URLs o recursos externos.
Los cambios locales generales y los archivos sin seguimiento esperan un commit
o una autorización local de ese tipo.

«Completo» significa conservar el contenido íntegro de cada documento
seleccionado, sin sustituirlo por un resumen. No significa copiar todo archivo
del repositorio. `status`, el catálogo por repositorio y las rutas de origen
permiten comprobar la cobertura y distinguirla de una exclusión deliberada.

## Política local y alta de repositorios

La política está fuera de los repositorios, en
`~/.codex/knowledge-sync.json`. Su esquema es independiente de
`progress-journal.json`; autorizar documentos laborales no habilita su envío al
diario personal. Contiene `schema_version: 1`, `hub_root`, `target_root` y
`sources`. Cada fuente declara su raíz Git canónica exacta (`root`), un alias
único en minúsculas (`alias`), `classification: personal|work` y, si procede,
`local_paths` e `include_paths`. Una autorización del hub no se hereda por sus
hijos.

El alta documental forma parte de crear o incorporar un repositorio propio
cuando ese encargo autorice su integración con OmarOS. Tras registrar el
proyecto, clasifícalo y autorízalo expresamente:

```sh
python3 .codex/knowledge_sync.py --policy ~/.codex/knowledge-sync.json \
  enroll --repo PricingLab --classification personal
python3 .codex/knowledge_sync.py --policy ~/.codex/knowledge-sync.json status
```

`--repo` es relativo al hub; `--local-path DIRECTORIO` añade una ubicación local
con la selección restringida anterior. Usa `--classification work` para una
fuente laboral autorizada. No clasifiques un repositorio por inferencia de su
nombre. `--include-path ARCHIVO` es repetible y autoriza una ruta documental
exacta de `HEAD`, por ejemplo `.codex/RESEARCH.md`. Al inicializar una política
ausente, declara también `--hub ~/GitHub --target ~/OmarOS`; ambas rutas deben
ser las raíces Git reales. El alta observa de nuevo el registro y la política
antes de reemplazarlos y rechaza los cambios que detecta. Su bloqueo coordina
este comando, sin garantizar exclusión con editores externos después de la
última observación; evita editar esos archivos simultáneamente con el alta.
Un clon o registro manual sin alta documental
aparecerá en `pending`;
no se exportará hasta resolver su autorización. `status` también distingue
`registered`, `enrolled`, `external` y `missing`.

## Exportación y recepción

```sh
python3 .codex/knowledge_sync.py --policy ~/.codex/knowledge-sync.json \
  export --repo PricingLab
python3 .codex/knowledge_sync.py --policy ~/.codex/knowledge-sync.json \
  sync --repo PricingLab
python3 .codex/knowledge_sync.py --policy ~/.codex/knowledge-sync.json sync
```

`export` produce el paquete documental; `sync` lo entrega al receptor nativo
`~/OmarOS/.codex/knowledge_import.py`. El receptor vuelve a validar la política,
la raíz Git real, la revisión, los modos y bytes fuente, las rutas, colisiones,
enlaces simbólicos y límites. El hub no escribe arbitrariamente en el vault.

La recepción crea estas superficies gestionadas:

| Superficie en OmarOS | Contenido |
| --- | --- |
| `11_Documents_and_Reports/Research_Repositories/<alias>/README.md` | Catálogo y procedencia del repositorio |
| `11_Documents_and_Reports/Research_Repositories/<alias>/files/<ruta>` | Documentos completos y adjuntos seleccionados |
| `90_Attachments/Research_Repositories/<alias>/files/<ruta>.source` | Bytes originales de cada Markdown proyectado |
| `17_Dashboards/Research_Repositories.md` | Índice común de las fuentes recibidas |

Markdown incorpora metadatos de OmarOS y conserva el cuerpo completo. Su copia
`.source` permite recuperar el original exacto; los otros formatos se conservan
byte a byte. La procedencia identifica fuente, ruta, revisión y hash. La
clasificación personal o laboral acompaña al documento; no cambia su origen ni
supone que su contenido se haya validado científicamente.

OmarOS desactiva la conversión de texto y los avisos de espacios de Git
únicamente para `11_Documents_and_Reports/Research_Repositories/**` y
`90_Attachments/Research_Repositories/**`, mediante `-text -filter -working-tree-encoding -whitespace` en
`.gitattributes`. Así conserva los bytes, los finales de línea y los espacios
con significado en Markdown. Los controles del resto del vault se mantienen.
El catálogo advierte de los enlaces cuyo destino quede fuera del paquete;
su presencia en el documento no implica que ese recurso se haya recibido.

El receptor conserva documentos retirados del origen como archivados. Rechaza
sobrescribir cambios manuales observados en material gestionado y comprueba
de nuevo el destino tras preparar el temporal, antes del reemplazo. El bloqueo
coordina receptores; no ofrece exclusión mutua con editores externos. Mantén
las anotaciones propias en notas separadas enlazadas a las proyecciones.
Guarda una intención
durable y recupera una interrupción solo cuando el destino corresponde al
estado anterior o al nuevo previsto; una tercera versión exige resolver el
conflicto. Repetir la misma recepción no vuelve a escribir los archivos.

El recibo `RECEIVED_LOCAL` acredita la recepción local de esa revisión y ese
paquete. No acredita commit, push, revisión científica ni publicación remota.
El proceso automático no hace commits ni push. La publicación inicial y el
mantenimiento editorial conservan el flujo nativo de OmarOS, con alcance,
comprobaciones y revisión propios.

## Automatización y diagnóstico

```sh
python3 .codex/knowledge_sync.py --policy ~/.codex/knowledge-sync.json \
  install --interval 600
```

`install` prepara el LaunchAgent `com.omar.constellation-knowledge-sync` y
devuelve `INSTALLED_NOT_LOADED`: la instalación no lo carga. El coordinador
comprueba la versión revisada, realiza la recepción inicial y activa el
servicio por separado. Una vez cargado, el intervalo de 600 segundos vuelve a
examinar las fuentes autorizadas. Los repositorios nuevos siguen necesitando
el alta documental; el servicio no amplía su propia autorización.

El estado del productor vive bajo
`git rev-parse --git-path constellation/knowledge-sync`, con `sync.lock` y
recibos por alias. El receptor usa
`git rev-parse --git-path omaros-knowledge`, con `manifest.json`, `pending.json`
y `lock`. Son datos operativos privados, fuera de los documentos publicables.
Los bloqueos evitan recepciones concurrentes incompatibles; un error conserva
el progreso recuperable y no se presenta como éxito.

Para diagnosticar, comprueba por separado la política, la cobertura de
`status`, el último recibo, los archivos recibidos, la carga real del
LaunchAgent y, si se publicó, el SHA remoto del flujo nativo. La existencia de
un script o una configuración no demuestra que un servicio esté activo.
