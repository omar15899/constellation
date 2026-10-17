# Compatibilidad observada

Fecha: 2026-10-17. Cliente probado: Codex CLI 0.163.0, macOS ARM64. Las pruebas
de descubrimiento usan instalaciones sintéticas y `CODEX_HOME` aislados, sin
confiar hooks ni iniciar turnos de modelo. No se han modificado componentes
gestionados del cliente.

| Mecanismo | Observación | Decisión |
| --- | --- | --- |
| Fuentes `.codex/skills` | El listado nativo descubre skills incluso sin Git. | Conservar la ubicación solicitada. |
| Plugin `plugin.json` raíz | Las skills aparecen; hooks no aparecen en seis variantes contrastadas. | No usar ese formato para este cliente. |
| `.codex-plugin/plugin.json` | Skills y hooks registrados, incluyendo ruta `./ecosystem/hooks.json`. | Usar un único manifiesto compatible. |
| Prefijo de skill | El cliente expone `constellation:nombre`. | Mantener nombre fuente exacto y documentar selector. |
| Fuentes más plugin | Dos archivos distintos producen dos entradas; no hay deduplicación por nombre. | Excluir las fuentes de un checkout explícito mediante `skills/config/write`, verificando después el listado nativo. |
| Agentes TOML | Recursos de plugin no implican registro automático. | Registrar perfiles personales por separado mediante el instalador. |
| `plugin add` repetido | Refresca la instalación, incluso con la misma versión. | Usarlo para actualización controlada. |
| Plugin deshabilitado | `plugin add` lo reactiva. | Detectar y rechazar la actualización antes de modificarlo. |
| Marketplace existente de otra fuente | El cliente rechaza la colisión. | Conservar origen y rechazar conflicto. |
| Confianza de hooks | Los hooks compatibles aparecen `untrusted`. | Revisión humana nativa de las definiciones concretas. |

La matriz de manifiestos incluyó raíz con extensión de hooks, raíz con
descubrimiento predeterminado, compatibilidad explícita, compatibilidad
predeterminada, raíz con overlay y raíz inline con overlay. Solo las dos
variantes exclusivamente compatibles registraron hooks. `hooks/list` y
`plugin/read` coincidieron antes y después de crear un hilo efímero sin turno.
Esto es una incompatibilidad observada de esta versión, no una refutación
general del formato portable documentado.

En el hub, `config/read` resolvió las rutas relativas del proyecto y mostró
`enabled=false` en una capa activa; sin embargo, `skills/list` siguió mostrando
las tres fuentes como activas junto al plugin. Por eso no se utiliza ese ajuste
como prueba de exclusión ni se sustituye el array de preferencias del usuario.
El helper optativo `native.py --exclude-source-root` usa la API documentada
`skills/config/write` sobre las rutas absolutas calculadas del checkout indicado.
Exige un plugin activo y bytes coincidentes en el cierre canónico de recursos
seleccionados, incluidos los archivos comunes exportados; verifica el resultado con otro
servidor y conserva las demás entradas. Una repetición confirmada no escribe;
una confirmación perdida se informa como resultado parcial. No modifica
confianza ni permisos. En un receptor sin checkout no se necesitan exclusiones.

Las consultas nativas utilizan `initialize`, `initialized`, `skills/list` y
`hooks/list` sobre `codex app-server --stdio`; no leen contenido de turnos.
Los esquemas del cliente se obtienen con `codex app-server generate-json-schema
--experimental`. Los eventos y filtros no son uniformes: `Stop` y
`UserPromptSubmit` no filtran por rol; solo los eventos de subagente aportan
su `agent_id`. La correlación del paquete necesita registro explícito.

El catálogo de esta sesión y `skills/list` del hub no contenían `scholar`.
Se encontró una referencia de configuración desactivada a `scholar-quant-docs`
fuera del alcance; se preservó sin leer ni alterar su destino. No hubo migración
de una skill activa. Las raíces adicionales de otra sesión pueden diferir.

La auditoría de `skill-creator` encontró capacidades útiles vigentes y
limitaciones concretas: su validador acepta nombre vacío, descripción en blanco
y enlaces locales inexistentes. Se reprodujeron con el validador real y
PyYAML 6.0.3 en un entorno temporal. El complemento valida el contrato limitado
de este paquete; no pretende ser un parser YAML general ni una evaluación
intelectual de las instrucciones. No se modificó la skill gestionada.

Documentación primaria consultada:

- [Paquetes y distribución de plugins](https://developers.openai.com/plugins/build/plugins).
- [Eventos, confianza y límites de hooks](https://learn.chatgpt.com/docs/hooks).
- [Descubrimiento y construcción de skills](https://learn.chatgpt.com/docs/build-skills).
- [Agentes personalizados e herencia](https://learn.chatgpt.com/docs/agent-configuration/subagents).
- [Configuración de modelo y esfuerzo](https://learn.chatgpt.com/docs/config-file/config-reference).

Estas páginas describen interfaces que pueden evolucionar. La prueba del
cliente instalado prevalece al determinar qué quedó registrado; la presencia
de archivos o `enabled=true` no demuestra confianza ni ejecución.
