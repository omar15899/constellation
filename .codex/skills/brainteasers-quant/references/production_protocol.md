# Producción, auditoría y revisión vigente

## Archivos y fuentes

Cada vídeo conserva tres entregables: `presentacion/main.tex` y sus inputs;
`guion-teleprompter.md`; `justificacion-pedagogica.md`. Los PDF, PNG, logs y QA
son derivados bajo `build/`. Los frames van en `presentacion/frames/` y los TikZ
en `presentacion/figures/`. La carpeta de entrega es siempre
`asincronas/sesion-NN/`, con vídeos `video-MM-slug/`; por ejemplo,
`asincronas/sesion-03/video-01-del-arbol-al-objeto-auxiliar/`.
`production_directory` debe señalar esa carpeta canónica. Si el plan o un README
conserva `asincronas/v12/`, corrige la entrada y los enlaces de la sesión del
encargo; nunca reproduzcas esa jerarquía al generar entregables. V12 sigue siendo
la referencia curricular. El README de sesión explica objetivos, fuentes,
orden, dependencias y presupuesto. No añade un cuarto informe pedagógico
paralelo: las decisiones de revisión pertenecen a la justificación existente.
La presentación cumple la [autonomía docente](../SKILL.md#regla-permanente-de-autonomía-docente):
se puede impartir completa sin leer ni memorizar el guion. Este se entrega
sincronizado como apoyo; no es el único soporte de ningún contenido esencial.
Antes de construir cada frame, aplica el [equilibrio editorial](../SKILL.md#equilibrio-entre-texto-figura-y-explicación):
elige su pregunta, el texto exacto y la relación que explica la figura. Reparte
las funciones entre lo visible y su desarrollo oral; no añadas sistemáticamente
un párrafo arriba y otro abajo para acreditar que la página está completa.

Antes del storyboard, aplica la
[revisión de continuidad](../SKILL.md#continuidad-y-complementariedad-entre-vídeos):
lee las presentaciones y guiones anteriores y posteriores pertinentes, incluidas
las transiciones entre sesiones; contrasta las grabaciones si existen. Registra
en el README los materiales y versiones consultados y el mapa de aportaciones.
Si un vecino solo está planificado, distingue esa comprobación provisional de
una revisión de materiales producidos. Identifica también el PDF principal
aprobado por Omar y su versión o huella; no uses la sesión 03 V12 como modelo.
Declara la sesión 05 revisada como modelo principal de composición, cantidad
de texto y TikZ, y la sesión 02 como autoridad de paleta, con los archivos y
versiones del contrato visual. La sesión 03 original es apoyo secundario.

Lee `_sistema/convenciones.md`, la plantilla y sus scripts. Para problemas,
verifica enunciado y solución en la edición elegida. `resolver_problema.py`
resuelve identificadores V8; no lo apliques a V12 suponiendo equivalencia.
En V12, busca el ID en `problemas/enunciados/` y `problemas/soluciones/`, y
contrástalo con sus tres manifiestos. Consulta `revision_editorial/correcciones_banco_v12.json`
si reutilizas un pasaje de una edición anterior. Los números del cuaderno
identifican otra colección: problema07 del cuaderno no es M1-007 del banco.
La guía `_sistema/referencias/evidencia-educativa.md` aporta decisiones docentes;
consulta su evidencia cuando una justificación dependa de una afirmación empírica.

En borradores, modifica el vídeo autorizado. Si consta `estado: aprobado`,
preserva esa versión y sigue las convenciones de versionado del proyecto;
el scaffolder rechaza sobreescrituras. El auditor admite una carpeta de versión
que contenga `presentacion/main.tex`, pero los validadores heredados pueden
rechazar su nombre: registra ese resultado, no alteres su salida para aprobar.

## Inicio automático

Usa el lanzador del dispositivo, que verifica la distribución y ejecuta con
el intérprete registrado. `CURSO` es la carpeta
del proyecto Brainteasers_Quant y `SISTEMA_CURSO` la carpeta conocida
`brainteasers-asincronas/_sistema` en su repositorio de software. Esta última
contiene los scripts que se ejecutarán; confirma su procedencia en el proyecto.
Los insumos de una sesión se preparan en una zona temporal para invocar el
compilador y el motor de curso. Elige sus ejecutables y fuentes conforme al
contrato del curso. Una salida enlazada a otra ruta o a otro archivo impide la
publicación de los resultados.

La producción usa un entorno POSIX con Bash, PyYAML, PyMuPDF, Pillow, `latexmk`,
`lualatex` y `pdftoppm` en PATH. Para consultar opciones, añade `--help` a la invocación de `production`.

`--system` señala la copia local del motor docente que quieres ejecutar.
La versión de Constellation distribuye el [inventario aprobado](course-engine.json):
para esta entrega corresponde al árbol Git `a2e630c37c730f3a2c6f73f252382e339eebf37d`.
El validador compara los nombres, modos, tamaños y huellas de los archivos que
copiará a la zona temporal. Solo debe usarse código e insumos procedentes de un
repositorio y una revisión en los que confíes.

Para adoptar otra versión, verifica su procedencia y revisa el árbol publicado
que deseas aprobar. La siguiente consulta genera un inventario candidato a
partir del identificador completo de **ese árbol Git**:

```sh
"${CODEX_HOME:-$HOME/.codex}/constellation/run" cli skill-run brainteasers-quant engine inventory --repository "$REPO_MOTOR" --tree "$ARBOL_REVISADO"
```

Si decides aprobar este candidato, consérvalo como
`${CODEX_HOME:-$HOME/.codex}/brainteasers-engine.json` en esa instalación. El
archivo debe pertenecer al usuario, tener modo 0600 y un solo enlace físico.
Si ya hay una autorización, comprueba su procedencia antes de sustituirla. En
otro dispositivo, verifica el mismo árbol o usa su inventario aprobado. Sin
una autorización específica del dispositivo se utiliza la incluida en el paquete.

Para crear vídeos que aún no existen, prepara el objeto de sesión en un JSON
temporal y comprueba antes las carpetas de destino. Desde la raíz del vault:

```sh
mkdir -p "$CURSO/asincronas"
"${CODEX_HOME:-$HOME/.codex}/constellation/run" cli skill-run brainteasers-quant production init /tmp/plan_sesion.json --output "$CURSO/asincronas" --system "$SISTEMA_CURSO"
```

El destino de producción es la raíz `asincronas/` del curso; `init` añade
`sesion-NN/video-MM-slug/`. No pases una carpeta de sesión como `--output`,
pues duplicaría ese nivel.

Extrae la sesión elegida de
`05_Projects/Brainteasers_Quant/V12_Apuntes_Definitivos/programa/plan_sesiones_v12.json`.
`init` recibe un objeto de sesión, no el catálogo completo. Conserva los campos
`session` y `videos` de esa entrada; los vídeos contienen `number`, `slug`,
`title` y `seconds`. Lee también sus dependencias y fuentes antes de escribir.
Para la sesión 03, el destino es `asincronas/sesion-03/`, igual que para las
demás sesiones. Si un vídeo ya existe, trabaja sobre él sin ejecutar `init`
encima. Conserva versiones aprobadas conforme al versionado del proyecto;
una colisión no justifica producir en otra raíz. La corrección de esta guía
no traslada ni sobrescribe por sí sola materiales históricos.
El siguiente es solo un ejemplo de formato, no el temario vigente de AF2.3.
El presupuesto total debe estar entre 1.800 y 2.160 segundos:

```json
{
  "session": 3,
  "videos": [
    {"number": 1, "slug": "objeto-y-pregunta", "title": "El objeto y la pregunta", "seconds": 450},
    {"number": 2, "slug": "construccion", "title": "Construir la respuesta", "seconds": 500},
    {"number": 3, "slug": "prueba", "title": "Por qué funciona", "seconds": 500},
    {"number": 4, "slug": "transferencia", "title": "Resolver una variación", "seconds": 530}
  ]
}
```

`init` valida todo el plan y las colisiones antes de llamar al scaffolder
compartido. No inventa contenido ni considera terminado el ejemplo de plantilla.
El inicializador fija `handout` en cada `main.tex` creado, sin modificar el
motor externo. Escribe después contenido estático, guion, figuras y justificación conforme al
contrato. Actualiza el README completo: el scaffolder heredado solo anota el
primer vídeo. `--output` permite una raíz temporal fuera del curso para ensayos
o auditorías sin modificar originales; esas copias no son entregas. Para
producción usa la raíz canónica `asincronas/`, sin subcarpeta curricular.
Antes de cerrar, comprueba que los vídeos, PDF y guiones entregados, el README
y `production_directory` apuntan a `asincronas/sesion-NN/`; una entrega bajo
`asincronas/v12/` no cumple el contrato.

## Guion, tiempo y cambios de página

Reserva SLIDE 01 a la portada independiente. Su locución presenta el tema y el
propósito; el contenido comienza en la página siguiente. Narra cada enunciado
antes de calcular, con situación, datos, restricciones y pregunta completos.
Incorpora estos tiempos al presupuesto. El cierre interpreta la aportación del
vídeo y enlaza con la pregunta siguiente, sin duplicar su desarrollo.

Conserva encabezados `## [00:00–00:15] SLIDE 01 · MODO A · Título` y etiquetas
del parser compartido. Varias entradas del mismo SLIDE pueden segmentar el
habla, pero mantienen la misma página completa y fija. A = exposición estática;
C = pausa sobre esa página; B = escritura manual solo si Omar la ha pedido
expresamente. No uses B para reemplazar revelados automáticos. El bloque siguiente empieza donde acaba el anterior; el primero
empieza en cero. Cada vídeo declara objetivo y estimación; los bloques deben
cuadrar con esta última. La suma de las estimaciones, incluidas pausas y
escritura, debe quedar entre 30 y 36 minutos.

Solo `DECIR` cuenta como texto hablado. El motor ya contrasta palabras/minuto,
presupuestos, modos, cobertura y metadatos. Son estimaciones: símbolos, atención
a una figura y escritura hacen insuficiente una simple división palabras/tiempo.
En cada acción indica «diapositiva 03, página 3; señalar …». Avanza solo al
empezar otra diapositiva; en bloques sucesivos del mismo SLIDE indica mantener
la página. Verifica esos números contra `main.nav` tras compilar y contra la
numeración visible en cada página: todas, incluida la portada, se numeran de
1 a N sin saltos por vídeo. La página N lleva el punto rojo final definido en
el contrato visual; anota en el guion que esa señal indica el fin del vídeo.
El punto está fijo desde la apertura de la página, no aparece al acabar de hablar.
No se numeran
etapas: todo está visible. El auditor rechaza cualquier frame con más de una
página física. Al leer materiales históricos, los campos técnicos `overlay`
y `overlays` del informe se conservan para diagnosticar el mapa; una entrega
estática válida solo contiene el valor 1.

## Auditoría y reparación

```sh
"${CODEX_HOME:-$HOME/.codex}/constellation/run" cli skill-run brainteasers-quant production audit RUTA_SESION --system "$SISTEMA_CURSO"
```

También admite un solo vídeo para reparar rápido; el cierre requiere auditoría
de la sesión completa. `--system` permite localizar una instalación existente
del motor; no sustituye la plantilla por otra estética. No modifica fuentes.
Las ejecuciones sobre la misma sesión o vídeo se coordinan con bloqueos; cada
nueva auditoría invalida el estado de aceptación anterior antes de compilar.
En una auditoría solicitada sin escrituras, usa una copia temporal.

Por vídeo ejecuta el build y render compartidos, captura sus logs y ejecuta las
cuatro fases del validador heredado. Si falla la compilación, no inspecciona un
PDF antiguo como si fuera el resultado nuevo. Comprueba además continuidad
temporal, formato 16:9 y correspondencia de una página por frame; señala recortes de texto,
tamaños reducidos y desbordamientos verticales. Esos controles no detectan
todas las colisiones de trazos TikZ ni prueban claridad visual.

Resultados: `build/production/qa.json`, `review-template.json` y hojas de
contacto; por vídeo permanecen PDF, PNG y logs en su `build/`. La salida enumera
errores mecánicos, advertencias y códigos de cada fase heredada por separado.
Separa duración declarada de duración verificada: si un guion no se puede
interpretar, no presenta la suma parcial como duración real de la sesión.
Exit 1 significa que hay controles sin superar; no borres esos resultados.
Un validador V8 incompatible con una fuente V12 o un ensayo oral pendiente se
explican con su causa. El criterio heredado no se declara superado por omisión.

Repara primero los errores duros. Después revisa todas las páginas, corrige
densidad, geometría y secuencia, vuelve a auditar y revisa la versión definitiva.
Haz la revisión de comprensión primero con el PDF y sin consultar el guion:
localiza el enunciado completo de cada problema, sus hipótesis y notación,
reconstruye los pasos y justificaciones visibles, e interpreta la conclusión.
Comprueba también las dependencias entre páginas y vídeos; una referencia a
material retirado o a un caso no expuesto no cuenta como explicación.
Después lee el teleprompter y compara: integra el contenido esencial ausente
mediante redacción breve, una fórmula justificada o una figura explicativa;
no copies el párrafo hablado. Revisa también el exceso: localiza información
repetida entre texto y figura, conserva su expresión más clara y comprueba que
la idea central sigue siendo reconocible a tamaño de exposición. Usa la
[calibración visual](visual_contract.md#calibrar-la-cantidad-de-texto) para decidir.
Repite la lectura del PDF corregido sin apoyarte en el guion. Tanto una laguna
esencial como la saturación de texto son defectos pendientes, aunque la
compilación y los controles mecánicos pasen. El recuento de palabras puede
orientar un diagnóstico; no sustituye esta revisión ni impone un umbral universal.
El presupuesto de tiempo y la correspondencia con guion se comprueban de nuevo
cuando cambia la división en frames o vídeos. Una compilación correcta no
equivale a una presentación revisada.

## Registrar la revisión real

Copia `review-template.json` fuera del árbol de fuentes, completa su contenido
después de leer los artefactos y pásalo a:

```sh
"${CODEX_HOME:-$HOME/.codex}/constellation/run" cli skill-run brainteasers-quant production accept RUTA_SESION/build/production/qa.json /tmp/revision_sesion.json
```

El formato exige `audit_fingerprint`, `pages` (identificador de cada página →
observación concreta), `checks` (matemática, comprensión, sincronización,
identidad visual, paleta y calidad TikZ → evidencia), `unresolved` (lista) y `oral_rehearsal` (por vídeo,
confirmación y evidencia del ensayo real, si existe). El template está vacío
deliberadamente: **no se rellena automáticamente con «OK»**. La evidencia de
identidad visual debe identificar el PDF principal y las páginas realmente
contrastadas, y acreditar la estética exacta, portada independiente, numeración
completa y punto rojo solo en la última página. En sincronización, registra los
bloques que presentan el vídeo y narran los enunciados antes de resolverlos.
Estos requisitos se verifican visual y editorialmente; no afirmes que el auditor
los detecta automáticamente. Justifica las advertencias tipográficas o corrígelas.

`checks.palette` identifica los PDF y páginas de sesión 02 realmente comparados,
la correspondencia con los valores y funciones de la paleta fija y las diferencias
corregidas. `checks.tikz_quality` recoge la revisión de acabado profesional:
función, fidelidad matemática, geometría, conexiones, lectura e integración con
el texto. En `pages`, nombra cada figura (archivo o identificador y página) y su
evidencia concreta, también cuando varias comparten página. Una portada sin
figura matemática se identifica como tal, sin añadir un dibujo decorativo.
No basta repetir «TikZ profesional»: aplica los criterios del contrato visual,
repara lo encontrado y comprueba el PDF final. `accept` rechaza la ausencia de
cualquiera de los seis controles; no deduce calidad a partir de una declaración.

En `checks.understanding` registra la lectura realizada sin guion, con evidencia
por problema: páginas del enunciado y las hipótesis, del desarrollo justificado
y de la conclusión; si es práctica diferida, identifica la tarea y ese estado.
Explica qué paso esencial se pudo reconstruir y qué lagunas se corrigieron,
si las hubo. En `pages`, concreta el aporte visible de cada página y su
legibilidad, incluida la densidad del texto; en la justificación pedagógica
conserva las decisiones relevantes de selección: qué se condensó o por qué se
mantuvo una explicación. No hace falta una tabla editorial por cada frase.
En `checks.understanding` registra también los materiales anteriores y posteriores
consultados, con páginas o bloques: qué se recupera, qué se aporta y qué se
prepara; justifica las recapitulaciones y señala repeticiones eliminadas o
prerrequisitos reparados. Conserva las decisiones en la justificación pedagógica.
Una declaración genérica de «autocontenida» o «hay continuidad» no sustituye
esta evidencia. Una desviación estética, apertura incompleta, enunciado sin
narrar, numeración o punto rojo ausentes, o un solapamiento o salto conceptual
relevante se registra en `unresolved` y se corrige antes de solicitar `accept`. Si
queda contenido esencial solo en el teleprompter o una página saturada,
decláralo en `unresolved` y corrígelo antes de solicitar `accept`.

`accept` verifica cobertura, ausencia de pendientes y huella actual de fuentes,
dependencias de LaTeX, motor, PDF y PNG. Una modificación invalida la revisión;
hay que auditar y revisar otra vez. Escribe `acceptance.json` con dos estados:

- `artifacts_reviewed`: controles mecánicos superados y revisión declarada
  completa sobre los artefactos actuales.
- `recording_ready`: además, sesión completa, todas las fases heredadas
  superadas y ensayo oral confirmado para cada vídeo.

Los estados son evidencia del flujo, no una garantía de verdad o perfección.
El script comprueba la presencia de evidencia, no deduce la autonomía docente
del PDF: corresponde al revisor aplicar la lectura sin guion y registrar sus
hallazgos con honestidad.
No inventes ensayos ni uses una aceptación antigua para afirmar que la versión
actual está revisada. Si el usuario solo pide generar materiales, entrega los
artefactos y distingue el ensayo pendiente; no dejes de trabajar en ellos por
una actividad vocal que el modelo no puede realizar por sí mismo.

El PDF de grabación es estático, una página por diapositiva. No se generan
versiones con overlays ni páginas duplicadas con distintas fases de un mismo
dibujo. El mismo PDF sirve para lectura. Si ya existe un PDF de lectura
adicional, no lo conviertas en motivo para recuperar animaciones.
Antes del cierre revisa diffs, conserva trabajo ajeno, publica solo los archivos
del encargo y verifica commit/push mediante el flujo nativo de OmarOS.
