---
name: claude-api
description: "Construir, depurar y migrar integraciones de Claude API, SDK oficial y Agent SDK. Verifica documentación vigente y conserva proveedor, modelo y alcance del proyecto."
license: Complete terms in LICENSE.txt
---

# Integraciones de Claude

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

Parte de la aplicación real y conserva su proveedor, lenguaje, modelo elegido
y contratos. No conviertas código de otro proveedor ni añadas una integración
remota por una tarea de configuración local. La configuración de `.claude/`
usa Claude Code y no necesita por sí misma una aplicación basada en API.

## Elegir la superficie

| Necesidad | Superficie que evaluar |
|---|---|
| Trabajo interactivo en archivos de un proyecto | Claude Code |
| Llamadas directas y bucle de herramientas controlado por la aplicación | Messages API y SDK oficial del lenguaje |
| Integrar el harness existente de Claude Code en un proceso propio | Claude Agent SDK |
| Agente con ciclo y entorno gestionados por Anthropic | Managed Agents, si su despliegue satisface el alcance autorizado |

Compara primero la opción más sencilla que cumpla el comportamiento pedido.
No construyas otro bucle de agentes si el harness existente cubre la necesidad.
Una skill local, una skill subida por API y un workspace gestionado tienen
fronteras de despliegue, datos y permisos distintas.

## Verificar contratos actuales

Antes de cambiar código, consulta la [documentación oficial de la plataforma](https://platform.claude.com/docs/en/home)
y la referencia del SDK instalado. Los modelos disponibles, sus IDs exactos,
precios, límites de contexto, parámetros de thinking y effort, funcionalidades
beta y firmas de SDK cambian. Las referencias locales son snapshots históricos:
no imponen ningún modelo o migración y sus ejemplos no prueban disponibilidad
actual. No existe una obligación de cambiar a una familia Opus, Sonnet o Haiku.

Conserva la selección explícita o ya configurada. Para una integración nueva,
comprueba las opciones actuales y elige según la necesidad, coste y límites
relevantes. Si el modelo elegido ya no está disponible, explica la evidencia y
resuelve la elección material antes de sustituirlo. No construyas IDs por analogía.
Distingue la configuración del modelo de Claude Code del parámetro de una API.

Usa el SDK oficial ya presente cuando encaje con el proyecto. HTTP directo es
apropiado si el usuario lo pide o no hay SDK adecuado. No inventes bindings a
partir de otro lenguaje. Caching, streaming, thinking, compaction, herramientas
y procesamiento por lotes son decisiones que necesitan una función concreta,
compatibilidad verificada y manejo explícito de errores y cancelación.

## Cargar solo las referencias pertinentes

Identifica el lenguaje y lee su carpeta: `python/`, `typescript/`, `java/`, `go/`,
`ruby/`, `csharp/`, `php/` o `curl/`. Conserva los recursos y scripts existentes;
resuelve los enlaces de esas referencias respecto a su propia ubicación.
[shared/live-sources.md](shared/live-sources.md) reúne las fuentes oficiales para
actualizar un binding o una capacidad. Para el harness consulta también
[Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview).

Si hace falta migrar, lee la referencia local correspondiente como antecedente y
contrástala con la guía oficial vigente. Identifica cambios incompatibles y
prueba el consumidor real. No migres dependencias o modelos como efecto lateral
de una edición ajena a esa integración.

## Verificar sin ampliar el acceso

Prueba respuestas, errores, rechazos de herramientas, cancelación y límites que
formen parte del contrato. Usa fixtures y mocks para mecánica determinista;
distingue esas pruebas de una llamada real al proveedor. Nunca expongas claves,
transcripciones ni datos privados en ejemplos, tests o trazas.

No subas contenido del vault ni invoques una API de pago como comprobación
incidental. Las llamadas reales deben pertenecer al alcance autorizado. Una
respuesta aceptada no demuestra la entrega de un mensaje ni la persistencia de
un resultado. En OmarOS conserva el ciclo existente de checks, revisión y
publicación, sin activar otro servicio, telemetría o exportador.
