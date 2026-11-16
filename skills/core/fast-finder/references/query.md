# Consultas exactas del vault

Usa la búsqueda por relevancia para encontrar la mejor nota sobre una idea.
Usa `scripts/query.py` para una pregunta con criterio verificable, por ejemplo
cuántas veces aparece una expresión, qué notas comparten una etiqueta o qué
archivos cambiaron durante un periodo. Los cuatro comandos consultan el mismo
inventario de rutas permitidas que el buscador principal. Todos devuelven JSON.

El lanzador verifica el paquete, el intérprete y el vault registrado en este
dispositivo. Desde otro directorio añade `--root "$VAULT"` después de
`query` para seleccionar la raíz física inscrita. Coloca
el alcance `--path` antes del comando; se puede repetir para unir ámbitos. Las
opciones `--config`, `--include-raw` y `--include-archive` amplían el alcance
solo cuando el encargo incluye esos datos.

```sh
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py skill-run core fast-finder query --path 06_Knowledge_Base content 'dual algebraico' --show count
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py skill-run core fast-finder query --path 06_Knowledge_Base content 'teorema[s]?' --regex --ignore-case --show hits --limit 5
```

`content` busca una cadena literal por defecto. Con `--regex` utiliza las
expresiones regulares de ripgrep. El recuento distingue archivos coincidentes,
líneas con coincidencias y apariciones; una línea con dos coincidencias aporta
dos apariciones. Usa `--show paths` para obtener solo los archivos que contienen
el patrón y `--show hits` para obtener las líneas. Las coincidencias se buscan
en todo el texto del archivo, incluido el frontmatter. Las apariciones de
longitud cero se omiten. El alcance de contenido
comprende los formatos de texto admitidos por el inventario y el límite de
tamaño anunciado por la herramienta. `--glob` y `--exclude` pueden repetirse
en cada comando. Un patrón sin barra compara nombres en cualquier nivel; con
barra, se interpreta desde la raíz y `**` abarca cero o más carpetas. El límite de salida afecta a lo que se
muestra; no convierte las primeras líneas en un total de todo el vault.

```sh
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py skill-run core fast-finder query --path 04_Research metadata --exists status --not-field status=archived --contains title=riesgo --group-by note_type
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py skill-run core fast-finder query --path 06_Knowledge_Base metadata --field tags=mathematics --missing source --limit 8
```

Combina predicados con AND. Para un campo de lista, la igualdad compara sus
elementos. `--contains` busca una subcadena en el valor; `--exists` y
`--missing` permiten preguntar por la presencia de datos. Al agrupar, el
recuento de una etiqueta responde cuántas notas pertenecen a ese grupo; si una
nota tiene varias etiquetas, puede contribuir a más de un grupo. El campo `missing_group` cuenta por separado las notas sin valor de agrupación.
Para interpretar los totales, el programa exige que la consulta termine y
que el frontmatter se pueda analizar en los primeros 16 KiB. Un error de
lectura, de sintaxis YAML o un encabezado demasiado largo se comunica como tal.

```sh
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py skill-run core fast-finder query --path 05_Projects paths --glob '*.md' --min-size 1024 --sort mtime --descending --limit 5
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py skill-run core fast-finder query --path 06_Knowledge_Base paths --since 2026-01-01 --until 2026-01-31 --sort size
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py skill-run core fast-finder query summary 07_AI_and_Agents/Reference/OpenAI_Codex_Docs/README.md --limit 1
```

`paths` filtra por nombre, tamaño en bytes y fecha de modificación. Incluso para un PDF, este modo solo necesita
su nombre y metadatos de archivo. Las fechas del ejemplo se interpretan en UTC e incluyen los días indicados. También se
admiten intervalos relativos como `7.days.ago`. `summary`
recupera los metadatos y un breve extracto del cuerpo de los archivos elegidos.
Para resumir una lista existente, usa `summary --stdin` con una ruta por línea.
La selección explícita pasa por las mismas restricciones del inventario.
`paths` incluye formatos documentales y de medios conocidos; los restantes
modos leen únicamente los formatos textuales permitidos. Los nombres ignorados
por Git, las categorías privadas y los repositorios anidados se excluyen
también en una búsqueda desde el directorio padre. Un nombre con más de un
enlace físico queda fuera porque puede referirse al mismo archivo que una
ruta restringida. Los nombres sensibles conocidos se filtran incluso cuando
contienen extensiones compuestas. Declara cualquier otra ruta confidencial en
las exclusiones del receptor. El sistema de archivos debe admitir apertura de
archivos por descriptor sin seguir enlaces y contar con `/dev/fd`.

Las rutas que la herramienta devuelve se interpretan desde la raíz del vault.
Una ausencia de coincidencias describe el alcance, formatos y filtros aplicados
en esa consulta.
