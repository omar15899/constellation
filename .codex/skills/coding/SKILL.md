---
name: "coding"
description: "Implementar, depurar y refactorizar software con requisitos observables, pruebas y revisión independiente. Usar para encargos de ingeniería que cambien o diagnostiquen comportamiento; no para dudas triviales de sintaxis, redacción o teoría matemática por la mera presencia de código."
---

# Coding

Lleva el comportamiento pedido hasta una entrega comprobada e integrada, y
publicada cuando forme parte del encargo autorizado. Identifica el receptor,
sus instrucciones, los consumidores e invariantes que puedan cambiar la solución;
preserva el trabajo ajeno.

## Elegir el trabajo necesario

Una corrección local pequeña puede resolverse leyendo el código pertinente,
editando y ejecutando una comprobación enfocada. Si no hay un contrato activo
ni una política receptora que lo exija, no crees un contrato persistente, token,
repositorio Git o equipo de agentes para esa edición. Explica el cambio y su
comprobación; no cargues las referencias del flujo extendido por rutina.

En un proyecto Git, cumple el flujo receptor y su mínimo de revisión; no abras
además una tarea portátil por haber seleccionado esta skill. Para implementación
sustantiva, diagnóstico complejo o trabajo coordinado, consulta el
[flujo de ingeniería](references/workflow.md). Usa el
[protocolo común](../../ecosystem/references/protocol.md) cuando necesites elegir
o enlazar ciclos de evidencia; el [CLI portátil](../../ecosystem/cli.py) permite
entregas con evidencia persistente sin Git. Conserva los contratos ya activos.

## Implementar y verificar

Define el comportamiento observable y comprueba la causa antes de corregir.
Implementa la solución más sencilla que satisfaga el encargo; verifica entradas,
límites y consumidores pertinentes. Para controles, prueba tanto el rechazo como
el caso permitido. Reutiliza checks útiles; no añadas pruebas que solo repitan la
edición ni amplíes la suite tras aprobarla sin cambios, fallos o dudas concretas.

Requisitos, artefactos actuales y evidencia deben corresponderse. Adapta la
revisión al riesgo sin rebajar el mínimo receptor; permisos, hooks y fronteras
sensibles pueden exigir revisión profunda con un diff pequeño. Mantén la revisión
y verificación de hallazgos independientes de sus autores. Un gate aprobado
comprueba trazabilidad y vigencia, no la pertinencia de una prueba.

Delega trabajo separable cuando aporte valor, con archivos exclusivos, identidad
real y resultado comprobable. Los perfiles disponibles son
[coder](../../ecosystem/agents/coder.toml),
[researcher](../../ecosystem/agents/researcher.toml),
[reviewer](../../ecosystem/agents/reviewer.toml),
[security_reviewer](../../ecosystem/agents/security-reviewer.toml) y
[verifier](../../ecosystem/agents/verifier.toml). Usa los nombres que anuncie el
catálogo del cliente nativo.
Si un perfil no está cargado, transmite sus instrucciones al agente disponible;
hereda modelo, esfuerzo y permisos sin afirmar una activación inexistente.

Un solver con análisis de convergencia e informe puede necesitar además
`mathematics` y una capacidad editorial o de formato: verifica cada obligación
con su evidencia propia. Integra y publica mediante el flujo autorizado del
receptor; en Constellation, respeta `workspace.py`, contratos y hooks. La skill
no autoriza nuevos destinos, datos privados ni acciones externas. Con requisitos
o gates pendientes, entrega el resultado parcial y el impedimento concreto.
