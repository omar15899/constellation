# Constellation: autoridad compartida y ejecución nativa

Constellation coordina contratos, evidencia, revisión y publicación. Codex y
Claude Code ejecutan modelos, herramientas, agentes, sesiones y permisos. Los
archivos reales y su dueño Git conservan autoridad; un índice o recibo describe
su estado, no crea otra fuente de verdad.

## Responsabilidades y fuentes

| Responsabilidad | Implementación y límite |
| --- | --- |
| Descubrimiento y ejecución de capacidades | Cliente nativo, catálogo de la sesión y permisos efectivos. |
| Selección y composición | Modelo e instrucciones pertinentes; no existe otro selector de skills. |
| Entrada pública | `ecosystem/cli.py` con `git`, `workspace`, `agent-policy` y operaciones portables. |
| Publicación Git | `runtime/workflow.py` y `workspace.py`; contrato, revisión y upstream por dueño. |
| Evidencia portable | `core.py` y `storage.py`; SQLite privado y entrega sin requisito de Git. |
| Revisión independiente | `runtime/review_gate.py` y política actual de esquema 2. |
| Progreso | `runtime/progress.py` y almacenes existentes; receptor OmarOS sólo con autorización exacta. |
| Filesystem | `platform_support.py`; locks reales, identidad, acceso y promoción exclusiva por SO. |
| Adaptación nativa | `hooks.py`, `hook_entry.py`, `claude_hooks.py` e instaladores. |
| Método | Cuatro skills, referencias y ocho roles que heredan modelo, esfuerzo y permisos. |

Los formatos actuales son inventario de bundle 1, recibo Codex 3, recibo Claude 1
y política/ledger de revisión 2. Sus números pertenecen a contratos diferentes.
Los formatos retirados se rechazan sin ejecutar ni sobrescribir sus copias;
no hay motores o inventarios alternativos cargados por compatibilidad.

## Organización de fuentes y distribución

`.codex/ecosystem/` contiene el runtime, adaptadores, manifiestos, roles, método,
guías y pruebas; `.codex/skills/` contiene las instrucciones de las skills.
`ecosystem/cli.py` es la entrada única. El constructor distribuye sólo sus rutas
permitidas y genera las proyecciones requeridas por los clientes.

Los roles Claude Markdown proceden de los TOML canónicos. El bootstrap Claude
incorpora mecánicamente las primitivas de plataforma, de modo que puede verificar
el inventario antes de importar código del paquete. El resto del runtime usa el
mismo helper de la distribución verificada. No se mantienen dos implementaciones
manuales ni se importa código de un proyecto a partir de un evento.

Las traducciones inglesas son fuentes seleccionadas al construir. Para el mismo
destino, el motor se comparte; el renderizador de progreso permite sólo las
constantes de presentación declaradas. Un paquete extraído conserva idioma y
destino al reconstruirse sin opciones de conversión. El historial se consulta
mediante revisiones Git, sin informes retirados dentro de la estructura activa.

## Una distribución para varios portátiles

La entrega actual `1.4.0-rc.1` conserva cuatro skills, ocho roles y un inventario
completo de 82 recursos. Las variantes de módulos conservan sólo los roles que
necesitan. `posix` cubre macOS/Linux; `windows-claude` adapta Claude Code para
Windows nativo. La ejecución real de este último sigue pendiente, según
[compatibilidad](compatibility.md) y [su guía](windows.md).

Los equipos comparten fuentes metodológicas y contratos, no cuentas, datos,
conectores, registros personales ni autorizaciones. Los instaladores conservan
datos ajenos y trabajan bajo locks de instalación; los hooks mantienen el lock
compartido durante verificación y despacho. La confianza corresponde al cliente.

## Criterios de trabajo por responsabilidad

Una explicación establece sus objetos, estructuras e hipótesis antes de usarlos;
distingue una función de su valor y una representación del objeto. La notación
debe aclarar una relación y los pasos esenciales deben poder reconstruirse.

La ingeniería parte del comportamiento pedido, el código y sus consumidores.
Compara la intervención suficiente con una abstracción justificada, hace visible
el recorrido de los datos y comprueba casos válidos y rechazos pertinentes.
Coste razonado y rendimiento medido son afirmaciones distintas.

La investigación declara fuentes, hipótesis refutables, evidencia contraria y
límites. Los handoffs contienen lo necesario para una tarea autónoma; un agente
fallido o una evidencia ausente no se convierten en una dependencia completada.
La revisión independiente busca defectos y exige evidencia, no votos.

## Un ciclo suficiente por objetivo

Una tarea Git usa el contrato del receptor. Una entrega portable conserva
evidencia semántica sin publicar. Un trabajo mixto declara la dependencia entre
ambos resultados, sin duplicar toda la tarea ni atribuir a un cierre portable
permiso de publicación. Las consultas breves siguen siendo breves, salvo las
obligaciones que ya imponga un contrato activo.

El coordinador registra autores reales antes de revisar. Quick exige una persona
de corrección; Standard, tres; Deep, tres de corrección y dos de seguridad,
con cobertura y personas distintas por archivo. Los hallazgos abiertos bloquean;
su cierre requiere un verificador distinto del autor y del descubridor.
El [protocolo](../references/protocol.md) define los datos y la vigencia.

## Continuidad y conocimiento personal

El progreso vive en el JSON privado de Git o SQLite portable. El historial de
fuentes permanece en Git. OmarOS recibe sólo síntesis personales autorizadas
por raíz y alias exactos; una recepción local no demuestra publicación ni cierre.
El perfil pedagógico y los datos corporativos no se exportan por asociación.

El adaptador activo de OmarOS conserva su pin 1.2.0 de cuatro recursos verificados.
Es una especialización vigente del receptor, no una estructura retirada.
Actualizar el plugin no sustituye ni sobrescribe ese adaptador.

## Fronteras verificables

Los controles vinculan alcance, bytes, identidad, acceso y evidencia a una versión.
En Windows, se verifican DACL y reparse points; un modo Unix lógico no sustituye
una ACL. La promoción de directorios es exclusiva; un filesystem sin la primitiva
necesaria se rechaza. El estado de sincronización de directorios es explícito y
no acredita durabilidad ante cualquier pérdida de alimentación.

El guarda observa rutas de edición declaradas, no todas las escrituras de shell
o MCP. No sustituye los permisos del cliente. Los hashes y los quórums tampoco
demuestran calidad editorial, verdad matemática, validez empírica o selección
universal de skills. Esas obligaciones necesitan evidencia sustantiva.

## Correspondencia con diseños publicados por Anthropic

La composición, los handoffs autosuficientes y las pruebas de resultado son
comparables con los mecanismos publicados de
[agentes componibles](https://www.anthropic.com/research/building-effective-agents)
e [investigación multiagente](https://www.anthropic.com/research/multi-agent-research-system).
Esta correspondencia no revela una arquitectura interna de proveedor ni acredita
en Constellation sus resultados experimentales.

Las referencias operativas son los hooks de
[Codex](https://learn.chatgpt.com/docs/hooks) y
[Claude](https://code.claude.com/docs/en/hooks).
