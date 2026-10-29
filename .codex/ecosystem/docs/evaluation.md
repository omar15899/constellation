# Evaluación del ecosistema

La evaluación separa tres preguntas: si el paquete conserva sus contratos, si el
cliente ejecuta los mecanismos previstos y si la respuesta sustantiva es correcta.
Un hash, un test de instalación o un quórum de revisión no responden por sí solos
a las otras preguntas.

## Qué se evalúa

| Obligación | Evidencia pertinente |
| --- | --- |
| Distribución | Inventario, hashes, permisos/acceso, proyecciones, reconstrucción y ZIP determinista. |
| Instalación | Caso nuevo, repetición, actualización del formato compatible, conservación de datos, rechazo de alteraciones y recuperación. |
| Ejecución nativa | Catálogo real, confianza efectiva, eventos observados y operaciones permitidas/rechazadas. |
| Ingeniería | Comportamiento y regresiones que puedan refutar la implementación, incluidos fallos de control. |
| Matemáticas | Objetos e hipótesis explícitos, prueba o contraejemplo y evaluación independiente de sus pasos esenciales. |
| Investigación cuantitativa | Datos y tiempos causales, búsqueda completa, validación fuera de muestra y contabilidad pertinente. |
| Escritura | Exactitud, argumento, alcance y lectura humana; la completitud formal no prueba calidad editorial. |

Seleccionar una skill, cargarla y aplicarla correctamente son observaciones
distintas. Un ensayo dirigido comprueba aplicación bajo instrucciones conocidas;
no demuestra selección automática. Cada resultado debe identificar fuentes,
snapshot, cliente, entradas y límites. Un cambio relevante exige revalidar las
afirmaciones que dependan de él.

## Comprobaciones reproducibles

Desde el checkout, con `python3` de versión 3.11+ también en el PATH de los
subprocesos:

```sh
python3 -B -m unittest discover -s .codex/ecosystem/tests -v
python3 -B -m unittest discover -s .codex/tests -v
python3 .codex/ecosystem/validate.py
```

Ejecuta las comprobaciones pertinentes mediante el workflow del dueño para
registrar su snapshot. Las matrices exportadas repiten pruebas para distintos
módulos y destinos; no sumes sus resultados como observaciones independientes.
Un caso omitido o no ejecutado no pasa a ser éxito.

El probe `native_claude_probe.py` conserva su aislamiento macOS y respuestas
HTTP simuladas locales. No se vuelve compatible quitando ese aislamiento.
`windows_acceptance.py` corresponde al backend Windows y requiere ese sistema;
no demuestra por sí solo despacho de eventos del cliente, workflow Git o
round trips de PowerShell. Sigue [la guía Windows](windows.md) para su alcance.

## Evidencia registrada

[Compatibilidad](compatibility.md#baseline-publicado) contiene la matriz acotada
del baseline publicado, anterior a la limpieza final. Los nuevos checks de esta
limpieza se acreditan en el workflow y su traza, no por conservar una tabla
anterior. No se ha realizado una nueva evaluación de modelos por retirar
formatos o documentos.

Los ensayos previos conservan resultados positivos y negativos. En un snapshot,
tres de cuatro casos sustantivos invocaron el método esperado; el editorial no
lo hizo, y dos controles simples evitaron herramientas. Las comprobaciones de
estructura de aquellas respuestas no establecieron verdad exhaustiva.

La generación editorial posterior presentó errores y una repetición autónoma
no los resolvió todos. Una pasada con feedback expresamente autorizado produjo
un artefacto corregido, verificado por dos revisores independientes. Eso acredita
la corrección guiada de ese artefacto, no fiabilidad autónoma general. Los
intentos bloqueados antes de transmitir no tuvieron llamada ni resultado y no
se cuentan como evaluaciones ejecutadas.

La evidencia de proveedor y los hashes completos pueden consultarse en la
[revisión Git del baseline](https://github.com/omar15899/constellation/commit/fd824929a50ad8e2473988107ae0b129213c1be7). Su conservación histórica no requiere
mantener informes retirados en el árbol activo ni habilitar su lectura por el
runtime.

## Revisión y aceptación

El coordinador compara cada requisito con artefactos y checks actuales, registra
autores nativos reales y obtiene revisión independiente por archivo. Todos los
hallazgos abiertos bloquean. Otra persona, distinta de autor y descubridor,
verifica su reparación o descarte con evidencia concreta.

Un éxito operativo no certifica una conclusión científica. Las pruebas, revisión
intelectual y aprobación humana que exija el receptor son obligaciones distintas.
La aceptación pendiente de Windows permanece pendiente hasta su ejecución real;
una edición inglesa o una limpieza estructural no la sustituye.
