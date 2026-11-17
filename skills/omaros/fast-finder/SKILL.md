---
name: "fast-finder"
description: "Encuentra rápidamente archivos, notas y contenido de OmarOS con búsqueda local por relevancia, filtros de metadatos y extractos verificables. Úsala para localizar, recuperar o averiguar qué contiene el vault."
---

# Fast Finder

Devuelve evidencia local: los archivos relevantes, su ubicación y el fragmento
que responde a la pregunta. Busca primero y lee completos solo los candidatos
que necesitas para responder. La consulta no crea notas.

## Entrada principal

El CLI central selecciona el recurso Python y el intérprete registrado, que
necesita PyYAML. El buscador comprueba la raíz de OmarOS y sus exclusiones;
Git y ripgrep deben estar disponibles. El alcance se expresa respecto a esa
raíz. Desde otro proyecto, añade `--root "$VAULT"` después de `scripts/search.py`
para seleccionar el vault sin cambiar de directorio.

```sh
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py skill-run omaros fast-finder scripts/search.py 'esperanza condicionada' --limit 5
```

El script detecta la raíz real, busca con ripgrep y ordena por cobertura de los
términos, título, ruta, encabezados y contenido. Usa estado canónico y fecha como
señales secundarias. Devuelve JSON con rutas absolutas, líneas reales, extractos,
puntuación, términos encontrados, duración y si la búsqueda fue parcial.
No mantiene un índice que pueda quedar obsoleto.

Escoge el alcance más concreto que sugiera la petición:

```sh
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py skill-run omaros fast-finder scripts/search.py 'martingalas' --path 06_Knowledge_Base --limit 5
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py skill-run omaros fast-finder scripts/search.py --field status=active --field priority=P0 --path 02_Tasks_and_Execution
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py skill-run omaros fast-finder scripts/search.py 'hooks' --config --path .claude
```

Los filtros repetidos tienen semántica AND; una lista de etiquetas admite
pertenencia exacta. La búsqueda textual es literal, por términos, insensible a
mayúsculas y acentos habituales. Traduce términos español/inglés si conviene;
el script no pretende ofrecer comprensión semántica ni traducción automática.

## Consultas exactas

Para contar ocurrencias de un literal o patrón, filtrar metadatos, agrupar notas,
seleccionar rutas por nombre, tamaño o fecha de modificación y resumir archivos
conocidos, usa [query.py](scripts/query.py) y sus
[opciones y ejemplos](references/query.md). El límite de filas mostradas y el
total se calculan por separado. La búsqueda por relevancia sigue usando
`search.py` para contestar preguntas en lenguaje natural con extractos.

## Decisiones de búsqueda

Para un nombre de archivo conocido, `rg --files` y un filtro de ruta suelen
bastar. Para varias ideas o una pregunta, usa el buscador y lee los resultados
mejor situados. Un resultado que coincide con una palabra no demuestra que el
archivo trate la idea completa: comprueba la cobertura y el extracto.

Si los resultados son escasos, prueba una vez términos más cortos, sinónimos o
el equivalente en inglés. Amplía el ámbito cuando esté justificado. Si
`partial: true`, divide la consulta por dominio; no presentes recuentos parciales
como un total. Se limita la lectura de metadatos a 16 KiB por candidato, la
búsqueda de cuerpo a archivos de 2 MiB y el conjunto a 600 candidatos. Para un
archivo grande identificado, usa `rg -n` directamente sobre ese archivo.

Para sintetizar lo que OmarOS sabe de un tema, lee tantos resultados como haga
falta para cubrir la pregunta. No interrumpas a las tres lecturas para pedir
permiso: amplía de forma proporcional y señala lagunas reales.

## Privacidad y fuentes

El inventario conserva archivos regulares con un solo enlace físico, bajo el
dueño Git de OmarOS y sus exclusiones. Los directorios registrados como otros
repositorios se consultan mediante sus propios contratos. Para leer contenido,
el buscador necesita descriptores POSIX sin seguimiento de enlaces y `/dev/fd`.

Por defecto se excluyen raw imports, archivo histórico, configuraciones,
conversaciones, logs de daemons y los dominios de salud y relaciones. Salud o
relaciones requieren un `--path` que los nombre. Usa `--include-archive` o
`--include-raw` solo cuando el encargo los incluya. El área ENGIE/Private se consulta únicamente mediante su skill privada. Las conversaciones permanecen
fuera del buscador general; una petición explícita sobre ellas requiere lectura
local específicamente acotada.

Para la arquitectura compartida, lee el [perfil de OmarOS](../../../profiles/omaros.md)
y la fuente de Constellation. Las carpetas `.codex/` y `.claude/` contienen
entradas y ajustes de sus respectivos clientes. Una búsqueda dentro de OmarOS
no inspecciona la fuente externa de Constellation. Distingue configuración
declarada, confianza nativa y evidencia de ejecución de los hooks.

Una búsqueda sobre el estado de OmarOS no se convierte en búsqueda web cuando
no hay coincidencias. Si el usuario pide información externa o fuentes actuales,
consulta la web con los criterios de la sesión y distingue esas fuentes del vault.

## Entrega

Responde con enlaces a los mejores archivos y una frase sobre lo que aportan.
Usa tabla solo si facilita comparar varios resultados. Cita líneas verificadas
cuando sostengan una afirmación concreta. No vuelques el JSON al usuario salvo
que lo pida. Di claramente cuando la consulta o los límites impiden concluir.
