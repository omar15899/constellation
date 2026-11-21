---
name: "ng-diario"
description: "Organiza un diario de OmarOS a partir de audio, transcripción o texto aportado por Omar. Úsala para guardar o actualizar reflexiones y aprendizajes de finanzas, programación u otros temas, o para consultar avances por fecha o tema. Escribe solo cuando Omar pida guardar o corregir una entrada."
---

# Diario de OmarOS

Lee el [perfil de OmarOS](../../../profiles/omaros.md) y usa la plantilla del
vault `18_Templates/Daily_Notes/_template.md`. Cada jornada tiene una entrada en
`01_Daily_Life/Journal/Daily/YYYY-MM-DD.md`. Una consulta de progreso es de lectura.
La captura se realiza en la sesión en la que Omar aporta el material y pide
guardarlo.

## Preparar la entrada

1. Trabaja con el texto, la transcripción o el audio que Omar indique para esa
   entrada. Si entrega audio, usa una transcripción ya accesible o sigue
   `10_Ingestion_and_Transformation/Audio_Local/README.md` para transcribirlo
   sin conexión con el intérprete y modelo locales. Para los archivos de
   trabajo, usa un directorio temporal privado (0700), con ruta real y un
   repositorio local sin remotos cuya regla `/output/` excluya toda la carpeta
   de salida. Pasa esa carpeta como `--output-root`. Revisa las negaciones,
   cifras y términos dudosos. Si el audio no está accesible o la transcripción
   local falla, utiliza el texto aportado que sí puedas leer o pide la
   transcripción. Si falta el relato, espera a recibirlo.
2. Toma la fecha que Omar asigna al registro y resuelve «hoy» y «ayer» según
   la fecha local de la sesión. Para un relato sin referencias temporales usa
   la fecha local de la sesión e indica la suposición al entregar. Si describe
   una jornada distinta que no se puede fechar, aclara la fecha antes de
   escribir. Conserva fechas explícitas de hechos anteriores cuando aporten
   contexto. Usa la fecha de la jornada en el nombre y el título. Conserva
   `created` al editar y usa las fechas reales de creación y actualización
   para `created` y `updated`.
3. Mantén en el diario únicamente el material apto para una ruta que puede
   versionarse. Si la petición incluye guardar aprendizaje profesional de
   ENGIE, pricing, hedging u operativa, aplica el [flujo privado de
   engie-learning](../engie-learning/SKILL.md) a esos pasajes. Las capturas
   privadas siguen sus propias fechas, notas temáticas y registro diario.
   Excluye de las notas personales, índices, trazas y vistas compartidas el
   contenido restringido, incluidos títulos, rutas, enlaces y recuentos.
   Mantén audio, transcripciones, rutas de origen y otros datos brutos en el
   ámbito privado de la sesión. Si todo el contenido es restringido, limita
   la captura al destino privado autorizado.
4. Para el registro personal, busca antecedentes pertinentes con
   `fast-finder` y lee los candidatos antes de redactar. Para teoría
   financiera y programación, busca en los
   ámbitos pertinentes de `06_Knowledge_Base`. Para otras lecturas, aprendizajes
   o reflexiones, aplica las rutas del perfil. Enlaza desde el diario a una
   nota existente cuando su relación con el aprendizaje sea concreta y
   el destino se pueda compartir. Usa enlaces inequívocos comprobados.
   La explicación canónica sigue en su nota temática. Si no encuentras un
   antecedente pertinente, conserva el aprendizaje en el diario.

## Guardar y verificar

1. Lee la entrada de la fecha antes de editar. Usa las convenciones de la
   plantilla y el esquema vigente. Escribe `note_type: daily`,
   `domain: 01_Daily_Life` y `subdomain: Journal`. Completa los demás campos
   requeridos por el perfil. Usa `ai_generated: true` y `ai_reviewed: false`
   para una entrada generada que aún no se haya revisado. Incluye solo
   secciones útiles y enlaces resueltos al crear una nota nueva.
2. Integra el contenido en `## Registro curado`, con las subsecciones
   `### Reflexiones`, `### Aprendizajes` y `### Progreso` en ese orden.
   Omite las que queden vacías. Identifica el tema de cada aprendizaje, por
   ejemplo, finanzas o programación. Conserva el sentido y los matices del
   relato. Atribuye emociones, conclusiones y decisiones solo cuando Omar
   las haya expresado. Distingue qué comprendió, practicó o aplicó de las
   preguntas que siguen abiertas. Describe próximos pasos solo cuando se
   desprendan de la fuente, con su carácter de propuesta o compromiso.
3. Conserva `Narrative` y las demás secciones manuales. Si ya existe
   `Registro curado`, incorpora lo nuevo junto al tema pertinente una
   sola vez. Repetir el mismo aporte deja la nota intacta. Si se pide una
   corrección, cambia solo el pasaje correspondiente y conserva el contexto.
   Si la nota cambia mientras trabajas, relee y concilia la versión actual.
4. Declara los archivos exactos en el encargo de Constellation antes de
   escribir. Guarda las entradas personales en modo local por defecto. Si
   Omar autoriza publicar una entrada apta para Git y su destino, registra
   `mode: "publish"` y `publication_message`. Constellation crea el commit y
   verifica el push al registrar la aprobación independiente con las
   comprobaciones vigentes. Si corresponde una traza
   operativa, descríbela con evidencia apta para su destino. Relee la nota
   guardada y comprueba fecha, metadatos, enlaces y alcance del contenido.
   Entrega el enlace a la entrada, el avance registrado y los puntos que
   requieren aclaración.

## Consultar progreso

Lee las entradas del tema o periodo solicitado y usa las fechas de sus
nombres. Ordena los avances por fecha y enlaza a la entrada que los documenta.
Cuando se repita un tema, explica qué cambió desde su primera aparición
relevante y qué preguntas siguen abiertas en las notas. Muestra el periodo
efectivamente revisado y limita los recuentos a los registros disponibles.
Una jornada sin entrada queda sin evidencia. Para una consulta autorizada
sobre aprendizaje profesional privado, usa la consulta de
[engie-learning](../engie-learning/SKILL.md) y entrega el resultado dentro
del ámbito privado.
