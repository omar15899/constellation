# Revisión de la constelación

Una revisión encuentra defectos que cambian el comportamiento: pérdida de
trabajo, publicación equivocada, evidencia caducada, fugas de datos privados,
dependencias invertidas o contratos que mienten. No exige preferencias de estilo
ni refactors que no solucionen el problema del encargo.

Lee el diff, los requisitos, los AGENTS.md aplicables y las invariantes del dueño
Git. Revisa también los consumidores necesarios para probar un fallo; un nombre
de archivo no es evidencia. Para cada hallazgo indica ruta y línea, escenario
reproducible, consecuencia y prueba. Distingue defectos introducidos y preexistentes.
Empieza el informe por el número de hallazgos; di explícitamente cuando sea cero.

El coordinador ejecuta las comprobaciones pertinentes y entrega el diff a un
agente independiente con contexto suficiente. El informe cubre corrección y
regresiones; una segunda revisión de seguridad es obligatoria para las rutas
sensibles de `.codex/review-policy.json`. El revisor no edita su propio objeto de
revisión. Un tercer agente puede verificar hallazgos discutidos o corregidos.
No uses una votación como sustituto de una reproducción o un argumento técnico.

La revisión inicial examina todo el cambio. Las posteriores se concentran en el
delta y sus consecuencias, conservando los hallazgos pendientes. Corrige la clase
de error completa. No repitas hallazgos ya resueltos salvo que reaparezcan con
evidencia nueva. El máximo de tres rondas exige reconsiderar el enfoque si no se
converge; no autoriza rebajar el riesgo, borrar el estado ni abrir otra sesión
para eludirlo.

En este hub, revisa especialmente:

- Propiedad real de Git, rutas literales, enlaces simbólicos, índice ajeno,
  upstream congelado y commits salientes.
- Invalidación de pruebas y revisiones ante cambios de contenido, permisos,
  requisitos o política; fallos posteriores no borrados por éxitos antiguos.
- Rechazos seguros ante configuración ambigua, estados parciales y fallos de red.
- Ausencia de prompts, transcripciones, secretos y datos privados en artefactos
  publicables. No abras archivos privados como contexto de revisión.
- Configuración de agentes que conserva modelo, esfuerzo, permisos y confianza.

En hijos, añade su REVIEW.md si existe y sus invariantes de PROJECT.md. Para
QuantOS comprueba causalidad temporal, determinismo, procedencia y dependencias
de tiers cuando el cambio las afecte. No audites todos los proyectos por rutina.

Cada regresión corregida debe dejar una prueba que falle antes de la corrección
y pase después, cuando sea automatizable. Las pruebas del motor incluyen casos
limpios para detectar falsos bloqueos. Esto evalúa controles deterministas; no
es una medición de la precisión de un modelo ni un historial de incidentes reales.

La guía [WORKSPACE.md](.codex/WORKSPACE.md) explica los comandos. La inspiración
es el [proceso de Anthropic](https://claude.dev/blog/solving-code-review-at-anthropic/):
verificar, revisar de forma independiente y hacer converger las correcciones.
La política local no configura por sí sola protecciones de ramas, revisores de
GitHub, merge queues, despliegues graduales ni aprobaciones humanas.
