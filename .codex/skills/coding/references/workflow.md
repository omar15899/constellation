# Flujo de ingeniería

## Diseñar el cambio

Parte de entradas, resultados, errores y efectos observables. Sigue los
consumidores existentes y las rutas con las que se usa el producto. Identifica
contratos de compatibilidad, formatos históricos, unidades, orden y propiedad de
recursos cuando afecten al resultado. Propón un diseño directo y añade una
abstracción si una variación requerida o una responsabilidad compartida la justifica.
Usa nombres del dominio, tipos claros y control de flujo fácil de seguir.
En operaciones con estado, verifica que fallos parciales y reintentos conserven
las invariantes. Para afirmar una mejora de rendimiento, mide la carga, el
entorno y la base de comparación de forma reproducible.

## Documentar decisiones y datos

Usa [Google Style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
en Python. Describe el propósito de los módulos y clases relevantes. Las
interfaces públicas y funciones de tamaño o lógica no trivial llevan una
docstring con un resumen y el contexto necesario para usarlas. Aplica
`Args:`, `Returns:`, `Yields:`, `Raises:` o `Attributes:` según corresponda.
Explica semántica que la firma no expresa, como precondiciones, efectos, errores
de contrato, unidades, orden, mutación y duración de recursos. Si cuesta
interpretar los datos, incluye un ejemplo breve, sintético y comprobado de la
estructura real. Junto al código, comenta motivos, invariantes y decisiones que
serían difíciles de deducir. Los tests autoexplicativos pueden prescindir de
docstrings que repitan sus nombres.

## Elegir pocas pruebas

1. Reutiliza las comprobaciones que cubren el comportamiento por sus entradas
   normales. Selecciona escenarios que puedan distinguir la solución de una
   implementación defectuosa. Comprueba tanto el caso permitido como el rechazo
   al modificar un control.
2. Añade una prueba si el usuario la pidió, el proyecto la exige o la evidencia
   existente deja una regresión o un riesgo concreto sin cubrir. Para una
   regresión automatizable sin cobertura, demuestra que la prueba falla con el
   defecto y pasa con la corrección cuando sea viable.
3. Da a cada prueba un nombre de escenario y resultado. Prepara datos pequeños,
   ejecuta la conducta y afirma el resultado visible. Controla reloj, azar y
   servicios externos cuando puedan volverla inestable. Agrupa variantes de la
   misma regla si los casos siguen siendo fáciles de distinguir.
4. Conserva la suite existente. Repite o amplía la comprobación por un cambio,
   un fallo o una duda concreta. Registra qué se ejecutó y cualquier límite real.

En código numérico fija dominio y precisión. Busca extremos válidos,
desbordamientos intermedios y cancelación cuando puedan romper el contrato.
Usa una referencia independiente o una cota pertinente. Corrige el cálculo o
declara la obligación pendiente si el dominio requerido queda sin cubrir.

## Revisar y cerrar

Usa el [protocolo común](../../../ecosystem/references/protocol.md) y la política
del proyecto para registro, revisión, resolución de hallazgos y publicación.
Para trabajos sustantivos, conserva decisiones, evidencia y pendientes con el
[progreso del ciclo elegido](../../../ecosystem/docs/progress.md). Protege los
datos privados y el trabajo ajeno durante la integración. Comprueba que cada
requisito tenga artefactos vigentes, evidencia pertinente, autores reales y la
revisión independiente aplicable. Al terminar, comunica el resultado, las
comprobaciones ejecutadas y las obligaciones pendientes que afecten al encargo.
