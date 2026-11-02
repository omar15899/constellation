# Una instalación de Constellation por equipo

Constellation mantiene los métodos y el código que coordinan el trabajo. Codex
y Claude Code ejecutan los modelos, agentes y herramientas con los permisos
efectivos de cada cliente. Los documentos, los datos y los cambios de software
pertenecen al proyecto que los contiene.

## Fuente, instalación y proyecto

La fuente canónica está en el repositorio de Constellation. En el equipo de Omar,
ese checkout ocupa la raíz de `~/GitHub`, que también contiene repositorios
hijos independientes. Las instrucciones de las skills se mantienen en
`.codex/skills/`. El motor, los ocho roles canónicos, los adaptadores nativos y
las pruebas se mantienen en `.codex/ecosystem/`.

El constructor selecciona los recursos de la edición y genera el inventario de
archivos, huellas y permisos. Las ediciones inglesa y española comparten el motor.
Los roles de Claude se generan desde los mismos TOML que los de Codex. El paquete
guarda las instrucciones y el código. Cada equipo aporta sus propios datos,
cuentas, permisos, configuración del cliente y contexto de proyecto.

En Codex, los proyectos del equipo utilizan una **instalación compartida**.
Los hooks entran por `CODEX_HOME/constellation/run`. El instalador genera ese
lanzador para la ruta absoluta de Python elegida por el equipo, su ejecutable
físico y el contenido esperado de `hook.py`. Así, el arranque puede usar el
entorno virtual elegido aunque el `PATH` del cliente sea diferente. El lanzador
lee y comprueba `hook.py` antes de ejecutar esos mismos bytes. La entrada
comprueba a su vez el recibo y el paquete, y mantiene el bloqueo compartido
durante la operación. La instalación requiere el bloqueo exclusivo. Una
operación que encuentra la instalación ocupada puede reintentarse.

| Se mantiene en | Responsabilidad |
| --- | --- |
| Constellation | Skills, roles, motor Git, enrutado de workspaces, revisión, progreso, hooks y perfil del vault. |
| Proyecto | Identidad, instrucciones locales, documentos de referencia, restricciones y comandos propios. Git determina el dueño de cada archivo. |
| Equipo | Instalación del cliente, selección de módulos, raíz registrada del vault, configuración y confianza de hooks. |
| Sesión | Catálogo cargado, herramientas disponibles, permisos efectivos y agentes realmente ejecutados. |

## GitHub y OmarOS

Desde el hub o desde uno de sus hijos, `workspace route` resuelve el dueño Git,
la rama, el upstream y las instrucciones aplicables. Por ejemplo, un README de
Shared y otro de ResearchLab pueden participar en el mismo encargo y terminar
en ramas distintas. Cada uno pasa por las pruebas, la revisión y la publicación
de su dueño. La entrada de desarrollo del checkout permite trabajar en el propio
motor, mientras que los comandos ordinarios llegan a la instalación del equipo.

La distribución 1.4.0 reúne los cuatro métodos generales `coding`,
`mathematics`, `quant-research` y `writter`. La edición personal completa añade
el módulo `omaros`, con siete skills y el perfil de ejecución del vault. Esto
da once skills en el catálogo de esa edición. La selección de módulos determina
qué recursos y roles incluye un paquete concreto.

El registro del perfil identifica la raíz precisa de OmarOS y su repositorio
Git en el equipo. El adaptador mantiene allí el contrato activo, las reglas de
metadatos y privacidad, los renombres, la revisión y los delegados autorizados.
Los hooks Git se instalan para ese dueño. El programa local del vault envía sus
operaciones al motor verificado. Así, una consulta sin archivos ni delegados
puede cerrar localmente, mientras que una entrega con cambios necesita
publicación y comprobación del remoto de su dueño.

## Actualización y carga nativa

La sincronización toma una revisión publicada del repositorio canónico,
construye el paquete seleccionado y comprueba la instalación. Los proyectos
que usan esa instalación reciben la misma versión en sus siguientes
invocaciones. Cada equipo realiza su propia promoción. Una sesión abierta
puede necesitar una nueva sesión para cargar el catálogo actualizado. La
confianza en las definiciones de hooks se comprueba en el cliente de cada
equipo. La [guía de instalación](migrations.md), las
[actualizaciones](updates.md) y la [matriz de compatibilidad](compatibility.md)
describen los pasos y sus límites.

Los formatos tienen numeración independiente. El inventario del paquete usa
el esquema 1, el recibo de Codex el 4, el de Claude el 1 y la política y el
registro de revisión el 2. El recibo de Codex vincula el intérprete, su destino
físico y la huella y el modo del lanzador a la instalación de ese equipo. El
instalador comprueba el inventario y los archivos que ya administra antes de
promover la edición nueva. Una discrepancia requiere reconciliar los archivos
existentes.

## Evidencia y revisión

Un encargo Git conserva requisitos, rutas autorizadas, resultados de checks,
autoría, revisión y evidencia de publicación por repositorio. El motor portable
guarda evidencia en SQLite cuando la entrega se desarrolla fuera de Git.
El coordinador evalúa qué prueba satisface cada requisito. Registra las
identidades nativas reales y abre la revisión sobre los archivos actuales.

Quick exige un revisor de corrección por archivo. Standard exige tres. Deep
requiere tres de corrección y dos de seguridad. Los hallazgos abiertos impiden
el cierre y su resolución necesita un verificador independiente del autor y de
quien detectó el problema. El [protocolo](../references/protocol.md) define las
condiciones de vigencia. La [evaluación](evaluation.md) distingue la integridad
del paquete, la ejecución observada en el cliente y la calidad del resultado.

Los guardas atienden los eventos y operaciones de edición que expone el cliente.
Las escrituras por terminal o MCP siguen bajo sus permisos efectivos. En el
filesystem, la promoción exclusiva y los controles de acceso dependen de las
primitivas del sistema operativo. La [guía Windows](windows.md) delimita la
evidencia para el destino de Claude Code.

En los flujos Git, workspace y vault, cada `Stop` vuelve a comprobar las
condiciones de cierre vigentes, incluso cuando se repite un evento anterior.
Si el estado sigue incompleto, una identidad ya reconocida evita consumir
otra continuación. Para ello, el historial de reintentos conserva hasta tres
huellas SHA-256 de eventos incompletos identificados. La huella se obtiene de
los metadatos del evento y permite reconocer la repetición sin guardar el
prompt ni la transcripción.

## Progreso y diario personal

El progreso operativo se conserva en el estado Git privado del proyecto o en
SQLite para entregas portables. Un hito del diario necesita una raíz y un alias
autorizados exactamente, un destino permitido y contenido clasificado de forma
expresa como personal. Cada raíz, incluso una anidada, necesita su propia
autorización. El perfil pedagógico y los materiales corporativos permanecen
bajo las reglas de su receptor. El receptor vuelve a comprobar la autorización y emite
un recibo local. La publicación del documento en OmarOS se acredita después
mediante el flujo del vault. La [guía de progreso](progress.md) describe la
recuperación en el origen y el reintento de una entrega interrumpida.
