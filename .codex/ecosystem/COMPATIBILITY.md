# Compatibilidad observada

## Verificación de migración — 2026-10-18

Cliente comprobado: Codex CLI 0.163.0, macOS ARM64. El catálogo de esta sesión,
las instalaciones y `skills/list` de un app-server nuevo son superficies distintas.
El adaptador `native.py --capabilities` conserva esa diferencia y separa errores,
advertencias, habilitación, confianza y ejecución todavía no comprobada.

| Prueba | Resultado observado |
| --- | --- |
| Hub, app-server nuevo | 21 skills, 18 habilitadas; fuentes Constellation excluidas y plugin 1.0 activo al iniciar |
| Plugins y MCP configurados | 24 plugins; 7 servidores MCP, 4 habilitados; no acredita autenticación ni llamadas exitosas |
| Hooks al iniciar | 5 del plugin y 1 global, habilitados y confiados; definiciones duplicadas del hub retiradas |
| Dispatch nativo baseline | `UserPromptSubmit` y `Stop` 1.0 completados en thread efímero; otros eventos no inferidos |
| Configuración de 19 hijos | `config/read` devuelve 64 en cada uno tras retirar overrides locales; sin prueba de saturación |
| Proyecto vacío | Descubrimiento global/local real probado sin scaffolding; ejecución se evalúa aparte |
| Control de navegador | `iab` no disponible en subagente; ningún navegador disponible en coordinador |
| Lectura web | Páginas públicas oficiales consultadas con la herramienta web disponible |

La configuración global existente permite acceso completo y aprobación `never`.
Se conserva por elección previa del usuario. Los hooks de Constellation no son
un sandbox de shell o MCP. Tampoco se cambian Memories, feedback, telemetría ni
controles de cuenta; la inspección local no demuestra esos controles remotos.

El esquema instalado de `skills/list` no admite `perCwdExtraUserRoots`, aunque
aparezca en documentación más nueva. Se usan sólo campos aceptados por el cliente.
El inventario de plugins usa el CLI; las APIs app-server de plugins siguen
siendo interfaces experimentales. No se interpreta un binario nuevo como prueba
de compatibilidad: se repiten construcción, descubrimiento y casos representativos.

Los comandos públicos del hub son adaptadores del runtime compartido. El paquete
puede ejecutar su ciclo Git en un receptor sin `.codex` ni checkout del hub. Los
proyectos conservan Git, dominio y validación; OmarOS conserva su adaptador de
publicación y fija por hash la revisión compartida.

### Modelo y contexto personal

Se retiró `.codex/config.toml` del hub, incluido el override de contexto
1.000.000/900.000. La inspección de `codex debug models` por el coordinador
registró 272.000 tokens para
`gpt-6-astra` y 500.000 para `gpt-6.1-sol` en este cliente; los ensayos nativos
observaron ventanas efectivas de 258.400 y 475.000. No se extrapolan límites de
API a Codex ni se cambian el modelo y esfuerzo predeterminados del usuario.

Dos procesos nuevos de app-server completaron la misma consulta matemática con
`gpt-6-astra`/Ultra y `gpt-6.1-sol`/Ultra. Ambos leyeron íntegramente el perfil
local persistido; su salida de lectura coincidió con el archivo observado.
El primero leyó además la skill de enseñanza y creó un subagente; el segundo
no lo hizo. Los archivos personales vigilados permanecieron idénticos y los
threads fueron efímeros. Esto acredita recuperación local del mismo perfil en
esos procesos y modelos, no eficacia pedagógica, equivalencia de resultados ni
compatibilidad universal. Sólo se publican métricas reducidas, sin contenido
personal ni respuestas de los ensayos.

La calibración sintética separada verificó ocho casos y 23 comprobaciones con
agentes nuevos en la sesión de colaboración. No sustituye la prueba entre
procesos: son fronteras de contexto diferentes. El perfil, su calibración y la
política del diario permanecen fuera de las skills genéricas distribuidas.

### Progreso y revisión proporcional

Los adaptadores Git, portable y OmarOS usan el mismo formato de progreso. El
receptor OmarOS exige un bundle verificado que incluya `runtime/progress.py`;
el lock de tres recursos de la distribución 1.1.0 anterior a esta extensión sólo
conserva la compatibilidad de revisión tras verificar su inventario y hashes,
no habilita progreso. Las actualizaciones del proveedor y del
receptor siguen sus contratos independientes.

`allow_quick_code` es una opción de política, no un permiso del cliente. Una
política receptora que omita o niegue esa opción no acepta la reducción opcional
para código. Los mínimos más estrictos se conservan y la justificación debe
preceder a la primera ronda, ligada a su snapshot. No modifica sandbox,
aprobaciones, confianza de hooks ni las obligaciones Deep.

## Evidencia histórica 1.0

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
