# Revisión de la constelación

Una revisión encuentra defectos que cambian el comportamiento: pérdida de
trabajo, publicación equivocada, evidencia caducada, fugas de datos privados,
dependencias invertidas o contratos que mienten. No exige preferencias de estilo
ni refactors que no solucionen el problema del encargo.

El reparto `workspace.py dispatch` asigna revisores por dueño Git y riesgo.
Quick requiere uno de corrección; Standard, tres de corrección; Deep, tres de
corrección y dos de seguridad. La cuota se aplica a cada archivo: revisar otro
archivo no completa su cobertura. Las identidades son las devueltas por las
herramientas de agentes, nunca nombres inventados para llenar un quórum.

Una excepción Quick sobre código necesita permiso de la política efectiva y una
justificación concreta anterior a la primera ronda, fijada al snapshot. Comprueba
que su riesgo y alcance la sostienen. No reduce rutas Deep ni restricciones del
receptor; los cambios posteriores invalidan esa excepción.

Lee el diff, los requisitos, los AGENTS.md aplicables y las invariantes del dueño
Git. Revisa también los consumidores necesarios para probar un fallo; un nombre
de archivo no es evidencia. Para cada hallazgo indica ruta y línea, escenario
reproducible, consecuencia y prueba. Distingue defectos introducidos y preexistentes.
Empieza el informe por el número de hallazgos; di explícitamente cuando sea cero.

El coordinador ejecuta las comprobaciones pertinentes y entrega el diff a un
agente independiente con contexto suficiente. El informe cubre corrección y
regresiones; una segunda revisión de seguridad es obligatoria para las rutas
sensibles de `.codex/ecosystem/runtime/review-policy.json`. El revisor no edita su propio objeto de
revisión. Registra todos los implementadores mediante `review-author` con sus
rutas: tampoco pueden revisar o resolver hallazgos de sus propios archivos.
Otro agente puede verificar hallazgos discutidos o corregidos.
No uses una votación como sustituto de una reproducción o un argumento técnico.

La revisión inicial examina todo el cambio. Las posteriores se concentran en el
delta y sus consecuencias, conservando los hallazgos pendientes. Corrige la clase
de error completa. No repitas hallazgos ya resueltos salvo que reaparezcan con
evidencia nueva. No hay un máximo universal de rondas: continúa autónomamente
cuando la siguiente acción esté justificada y quepa en el presupuesto real.
El motor señala artefactos repetidos sin nuevas observaciones independientes;
el coordinador juzga si existe progreso real. Registra la razón y la acción
siguiente con `review-start` cuando las requiera. Repetir una declaración sin
nueva base no desbloquea un ciclo. Conserva historial, hallazgos y mínimos; no
abras otra sesión para ocultarlos. Un presupuesto agotado detiene nuevas rondas,
sin impedir registrar informes o resolver hallazgos de la ronda vigente.

El plazo de revisión se declara mediante `review-budget`; su ausencia se informa
como desconocida, no como tiempo o tokens ilimitados. Una ampliación explícita
con motivo conserva el historial. Este presupuesto local no modifica los límites
ni permisos nativos del cliente. [WORKSPACE.md](.codex/WORKSPACE.md) contiene el
contrato de los comandos; las reglas del receptor pueden imponer otros límites.

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
