---
name: "coding"
description: "Implementar, depurar y refactorizar software con requisitos observables, pruebas y revisión independiente. Usar para encargos de ingeniería que cambien o diagnostiquen comportamiento; no para dudas triviales de sintaxis, redacción o teoría matemática por la mera presencia de código."
---

# Coding

Lleva el encargo desde el comportamiento pedido hasta una entrega comprobada,
integrada y, cuando esté autorizado, publicada. El resultado debe permitir seguir
cada requisito hasta sus artefactos, comprobaciones, autores reales y revisión
independiente. Un check aprobado fija evidencia; su pertinencia exige juicio.
En el plugin instalado, el selector es `$constellation:coding`; el nombre interno
de la skill sigue siendo `coding`.

## Elegir el alcance

Identifica el proyecto receptor y sus instrucciones antes de escribir. Lee los
contratos, consumidores e invariantes que puedan cambiar la solución. Delimita
requisitos observables, rutas exactas, dependencias y aceptación; preserva el
trabajo concurrente. Investiga alternativas cuando puedan cambiar una decisión
material, sin convertir una corrección localizada en un rediseño.

Usa [el flujo de ingeniería](references/workflow.md) para implementación,
diagnóstico, refactor y entregas entre agentes. Una corrección pequeña conserva
el mismo rigor con alcance y evidencia breves: reutiliza checks pertinentes y
evita pruebas que solo repitan la edición o ampliaciones rutinarias de la suite.

## Controles esenciales

- Registra cada entrega significativa con el
  [protocolo común](../../ecosystem/references/protocol.md). Su
  [CLI](../../ecosystem/cli.py) mantiene requisitos, evidencia, autoría y revisión;
  consulta allí el formato vigente en vez de inventar operaciones o esquemas.
- Adapta la profundidad al riesgo. Conserva el mínimo vigente: Quick requiere
  un revisor de corrección; Standard, tres; Deep, tres de corrección y dos de
  seguridad, con un máximo de tres rondas. Eleva la revisión ante controles,
  permisos, hooks o fronteras sensibles, aunque el diff sea pequeño.
- Delega cuando ayude, con archivos exclusivos, identidad real y resultado
  verificable. Hereda modelo, esfuerzo y permisos. Usa los perfiles
  [coder](../../ecosystem/agents/coder.toml),
  [researcher](../../ecosystem/agents/researcher.toml),
  [reviewer](../../ecosystem/agents/reviewer.toml),
  [security_reviewer](../../ecosystem/agents/security-reviewer.toml) y
  [verifier](../../ecosystem/agents/verifier.toml) según la necesidad; sus nombres
  nativos llevan el prefijo `ecosystem_`. Si la superficie no los carga, entrega
  sus instrucciones al agente nativo disponible; no afirmes que el perfil está
  activo por haber mencionado su nombre.
- Mantén independientes implementación, revisión y verificación de hallazgos.
  Resuelve las discrepancias con reproducciones o argumentos, no por votación.
  Un gate pendiente exige cierre parcial y explicación concreta del impedimento.
- Integra y publica únicamente mediante el flujo y la autorización del receptor.
  En Constellation, respeta `workspace.py`, sus contratos, hooks y autorizaciones
  existentes; este paquete no crea otro committer ni sustituye controles. Otros
  proyectos necesitan su propio alcance y autorización. Sin Git, entrega archivos
  y evidencia local sin crear un repositorio artificial.

La selección automática de esta skill no concede permisos. El plan y la
evidencia tampoco autorizan nuevos destinos, acceso a datos privados, cambios de
confianza ni acciones externas adicionales.
