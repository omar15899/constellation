# Evaluación del ecosistema

Este informe separa pruebas mecánicas, comportamiento de agentes y observación
nativa. Una muestra pequeña no estima fiabilidad universal. Los escenarios y
criterios públicos se conservan en `evals/cases.json` y `evals/rubric.json`;
los resultados estructurados están en `evaluation.json`. No son conversaciones
ni contienen prompts privados.

La construcción solicitó GPT-6 Astra con Ultra. La selección fue confirmada por
el usuario y la metadata nativa `thread/read` sin turnos devuelve
`model=gpt-6-astra`, `reasoningEffort=ultra` para el coordinador, los doce autores,
los cinco revisores y los dos verificadores de reparaciones.
Esa metadata expresa configuración persistida, no telemetría por inferencia.
Los lanzamientos de construcción y evaluación solicitan ambos valores de forma
explícita. Las skills distribuidas no los fijan para usos futuros.

La muestra comparada contiene ingeniería, auditoría de argumento matemático,
escritura factual y transferencia ontológica a semántica de programas. Los
ejecutores reciben tareas y materiales sintéticos, sin respuestas previstas ni
conclusiones previas. Se usan carpetas aisladas y agentes distintos. El baseline
usa los contratos públicos anteriores a la construcción. No se imputa una
mejora causal a diferencias de latencia o a cuatro casos.

## Resultados observados

Los componentes ejecutados por los autores independientes de pruebas suman
163 casos: 45 del núcleo, 34 de hooks, 51 de empaquetado y 33 de validación.
También pasan las 47 pruebas existentes del motor de revisión. El check final
del workflow y CI comprueban la revisión declarada después de este informe;
los recuentos detallados, identidades y resultados están en `evaluation.json`.

Las pruebas negativas ejercitan fallos posteriores a un éxito, contenido e
inputs obsoletos, autorrevisión, cobertura incompleta, hallazgos abiertos,
resolución sin independencia, tres rondas máximas, recuperación de intentos y
concurrencia real. Dos sesiones con el mismo nombre de tarea se aíslan, los
trabajos de perfiles distintos avanzan simultáneamente y las entregas mixtas
conservan obligaciones separadas. La evidencia numérica no descarga por sí sola
una obligación de demostración.

La portabilidad se prueba mediante construcción reproducible, paquetes de cada
módulo, instalación repetida, actualización, rollback y conservación de
configuración ajena. Un receptor ejecuta plan/status y reconstruye el paquete
con Git ausente y una auditoría de filesystem que deniega leer el hub original.
La integración nativa real detecta tres skills y cinco hooks `untrusted`.

| Caso comparado | Flujo anterior | Paquete candidato | Tiempo observado, anterior / candidato |
| --- | --- | --- | --- |
| Normalización de pesos | 13 pruebas y revisión manual sin hallazgos | Escritura temporal rechazada; cierre parcial honesto | 234,06 / 239,84 s |
| Continuidad de aplicación lineal | Refutación correcta revisada; entrega textual por rechazo de escritura | Refutación y reparaciones revisadas; cierre Quick vigente | 171 / 295,76 s |
| Nota factual sintética | 144 palabras; cifras corregidas y referencia sin respaldo retirada | 142 palabras; mismas correcciones y cierre Quick vigente | 100 / 205,52 s |
| Semántica de programas | Argumentos revisados y comprobaciones finitas auxiliares | Argumentos revisados y cierre Standard con tres revisores | 296,18 / 530,95 s |

No se observa evidencia suficiente para afirmar una mejora general de calidad.
El baseline ya resolvió correctamente los contenidos revisados. La diferencia
comprobada en los casos cerrados es la trazabilidad ejecutable de requisitos,
autores, comprobaciones y revisión. Los tiempos no son comparaciones causales:
difieren las ventanas de medición, herramientas, intervención y número de
revisores. No se recopilaron totales de tokens o coste.

La evaluación adicional produjo una refutación algebraica de una inferencia
basada en malla finita y de la supuesta completitud de los racionales. Un revisor
distinto de sus autores comprobó las respuestas textuales, sin hallar defectos
materiales. La escritura creativa produjo 99 palabras y la edición breve una
única frase; no se impusieron comprobaciones factuales innecesarias. Una pregunta
elemental sobre CPU no seleccionó ninguna skill. La selección explícita cubrió
los tres módulos; la selección implícita se examinó a partir de sus metadatos
instalados. El descubrimiento del cliente se comprobó por separado.

Los rechazos del hook del hub sobre `/tmp` no se ocultaron ni se sortearon con
otra herramienta. Esos casos conservan su estado parcial o textual. Se añadió
un caso distinto en una sesión nativa efímera con cwd propio de un receptor
sin Git, conservando permisos y confianza del usuario: corregir unión de
intervalos cerrados. Pasaron 13 métodos, 3.616 entradas enumeradas y contrastes
independientes de 12.111 y 3.616 entradas. Tres revisores Standard registraron
cero hallazgos y el motor cerró con evidencia vigente. El tiempo total fue
521,87 segundos. El resultado no cambia el veredicto de los intentos bloqueados.

La prueba de transferencia usó semántica de programas, distinta de los cuatro
ejemplos ontológicos del paquete. Se revisaron sintaxis, árboles, entornos,
denotaciones, captura, renombrado y equivalencia contextual. No reveló una
carencia que justificara añadir otra referencia. Tampoco demuestra que las
referencias nuevas causaran una mejora frente al baseline.

## Correcciones y alcance de la evidencia

La integración encontró una discordancia en los recursos de `writter` aislado:
su flujo técnico requería dos perfiles que el validador no esperaba. Se
centralizó el inventario en el builder confiado, se corrigió el cierre de
recursos y se añadió una regresión que construye y valida cada módulo real.
Otra regresión prueba que cambiar los perfiles técnicos auxiliares de `writter`
invalida su evidencia; los tres controles negativos fallan contra la selección
anterior. El validador no ejecuta el builder de un candidato externo.

La primera ronda formal produjo 13 hallazgos de cinco revisores, correspondientes
a siete clases de defecto. Se conservan los IDs individuales en el ledger;
las reproducciones coincidentes no se cuentan como defectos diferentes. Las
reparaciones cubren:

- Convivencia del estado predeterminado con instalación y actualización, sin
  leerlo, borrarlo ni incorporarlo al recibo de distribución.
- Sustitución atómica de perfiles y restauraciones para preservar otros nombres
  de un inode compartido por hardlinks.
- Validación de componentes originales de patches antes de simplificar `..`,
  evitando que un enlace simbólico oculte la salida del alcance.
- Permisos de inputs incluidos en la vigencia de checks, revisión y dependencias.
- Validación CLI que no escribe bytecode en su propio paquete; API y pruebas
  de paquetes inmutables con la precondición explícita `python -B`.
- Fixtures y selección de pruebas compatibles con los módulos distribuidos.
- Resolución del manifiesto correcta tanto en fuentes como en bundles.

Las regresiones se contrastaron con el snapshot exacto de la primera ronda.
La matriz ejecutó las suites desde cuatro distribuciones reales, sin recuperar
el checkout original: completa y cada módulo por separado. Cada una descubre
163 casos; se omiten respectivamente 1, 10, 9 y 8 por recursión del harness o
capacidad ausente. No se omiten los controles comunes. Las rutas, bytes, modos
e inventarios de los paquetes se conservan tras ejecutarlas. Los verificadores
de reparaciones son distintos de autores y descubridores; el cierre formal de
cada ID se registra únicamente contra el token de la revisión corregida.

La comprobación global posterior encontró otra incompatibilidad: el listado
nativo mantenía activas las fuentes del proyecto aunque la configuración
resuelta indicaba lo contrario. Se añadió una exclusión explícita mediante la
API nativa, sin cambiar confianza ni sustituir preferencias ajenas. Cinco
pruebas nuevas con Codex real cubren eliminación de duplicados, módulos
seleccionados, repetición sin escrituras, rechazos sin cambios y pérdida de
confirmación después de una escritura real. Se ejecutan también en los cuatro
bundles. La integración final recibe una tercera ronda independiente antes
de publicar; no se presenta la segunda ronda como aprobación de este cambio.
Un verificador independiente descubrió durante esta integración que comparar
solo `SKILL.md` permitía excluir fuentes con workflows distintos. El hallazgo
`ECO-SOURCE-EXCLUSION-RESOURCE-DIVERGENCE` conserva su identidad y versión
defectuosa en el JSON; exige comparar el cierre de recursos del módulo y una
resolución por un verificador distinto de autor y descubridor. Ocho pruebas
adicionales cubren divergencias de workflows, protocolo, motor, agentes y
ontología, selección parcial y un builder externo que no debe ejecutarse.

Las evaluaciones conductuales usan un snapshot instalado cuyo hash se conserva
en el JSON. Las correcciones posteriores del inventario se verificaron mediante
esas regresiones. Las pruebas no equivalen a autenticación de personas ni a
verificación formal de las demostraciones. Los tests de hooks ejecutan su
adaptador mediante subprocess; no se concedió confianza nativa ni se afirma
haber observado despacho nativo confiado.

La publicación exige adicionalmente revisión Deep de todos los archivos por
tres revisores de corrección y dos de seguridad, independientes de los autores
registrados. Sus informes y resoluciones pertenecen al ledger del workflow;
este informe de evaluación no sustituye esa puerta ni anticipa su veredicto.
