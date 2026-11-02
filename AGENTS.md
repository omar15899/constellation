# GitHub y Constellation

Esta carpeta es el checkout fuente de Constellation y el workspace de proyectos de software de Omar. Cada repositorio hijo tiene su propio Git, rama, contrato y pruebas. El hub conserva el [registro operativo](.codex/repositories.json), los [dominios de QuantOS](QUANTOS.md) y el [contrato documental](.codex/KNOWLEDGE.md). `ruflo` es externo.

Para operar, usa la instalación verificada de Constellation del equipo. El comando histórico del hub, `python3 .codex/ecosystem/cli.py workspace route RUTA`, selecciona esa misma instalación y proporciona la raíz del workspace. Lee las instrucciones que devuelve, el `.codex/PROJECT.md` del propietario si existe y las instrucciones del directorio afectado. La [guía del workspace](.codex/WORKSPACE.md) describe también la invocación desde un hijo o desde otra carpeta.

El método, las skills, los roles, el reparto y la revisión se obtienen del plugin instalado. Crea y modifica las skills propias de Codex exclusivamente en la fuente canónica de Constellation. Cada proyecto conserva los hechos de su dominio y sus restricciones. Las capacidades nativas y de terceros siguen el ciclo de su proveedor. Codex ejecuta las herramientas y los agentes con los permisos de la sesión. El coordinador asigna paquetes a agentes reales, valida las comprobaciones y registra autores e informes independientes. Usa un contrato por dueño Git y declara dependencias entre propietarios cuando existan. Aplica [REVIEW.md](REVIEW.md), [.codex/RESEARCH.md](.codex/RESEARCH.md) y el [contrato de promoción científica](.claude/contracts/promotion_gate.md) cuando correspondan.

Omar autoriza commits y push normales para cerrar el alcance de cada encargo. Conserva los cambios previos, los índices ajenos y el upstream de cada propietario. Confirma el SHA remoto antes de cerrar una publicación. La integración de documentación en OmarOS y los hitos personales requieren la política de recepción correspondiente. Proyectos externos necesitan alcance explícito.

Protege conversaciones, prompts, archivos privados, estados de sincronización y secretos. La autorización para un repositorio no se extiende a los demás ni a comunicaciones con terceros. Conserva la configuración de privacidad y la confianza de hooks del usuario. Preserva las herramientas de Claude que pertenecen a este workspace.

Para desarrollar Constellation se prueban explícitamente las fuentes candidatas antes de construir e instalar la distribución. Los [puntos de entrada](.codex/README.md) distinguen ambas operaciones.
