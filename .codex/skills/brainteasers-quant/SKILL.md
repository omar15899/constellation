---
name: "brainteasers-quant"
description: "Diseña y produce las sesiones asíncronas de Brainteasers Quant para Hespérides a partir del currículo y los apuntes V12: Beamer y TikZ con diapositivas estáticas y autocontenidas, una página por frame y teleprompter de apoyo, 30–36 minutos por sesión y ciclos de compilación y revisión visual. Úsala al ajustar su syllabus o producir y revisar estas sesiones dentro del proyecto Brainteasers_Quant."
---

# Brainteasers Quant · Asíncronas Hespérides

Produce sesiones que hagan comprender la estructura del problema y que Omar
pueda enseñar usando solo la presentación, sin leer ni memorizar el teleprompter.
La unidad de producción es la **sesión completa de 30–36 minutos**, repartida
en vídeos según sus dependencias conceptuales. No impongas cuatro vídeos ni
conviertas cada vídeo en una clase de media hora.

## Regla permanente de autonomía docente

**La presentación de cada vídeo debe ser completamente autocontenida.** Un
docente con los prerrequisitos declarados debe poder abrirla, entender qué se
plantea y explicar el argumento completo a partir de lo visible. No debe tener
que conocer el guion, las notas del presentador, el banco de problemas ni la
historia de las revisiones para suplir información ausente.

En las diapositivas deben quedar, en una secuencia legible:

- El enunciado completo de cada problema trabajado: situación, datos, reglas,
  restricciones y pregunta exacta. Un título, un ID o un dibujo no lo sustituyen.
- Los objetos, las hipótesis y el significado de los símbolos antes de usarlos;
  las figuras llevan las etiquetas necesarias para interpretar sus relaciones.
- El desarrollo de los ejemplos y soluciones, con los pasos esenciales y la
  razón que permite pasar de uno a otro. Mostrar una fórmula final o nombrar
  un método no equivale a explicar por qué funciona.
- La conclusión interpretada en el problema y las condiciones de su validez.
  En práctica diferida, el enunciado y la tarea son completos; no se presenta
  como resuelto lo que se deja expresamente al alumno.

La autonomía se exige al recorrido de la presentación; no obliga a repetir
todo el enunciado o la prueba en cada página. Una continuación identifica el
problema y conserva los datos y relaciones necesarios para seguirla. Si se
recupera un caso de otro vídeo, repón su enunciado y el resultado o paso que se
utilizará. Nunca des un problema por conocido, explicado o resuelto porque
aparezca en el teleprompter, en otra versión o en una referencia externa. Al
retirar o sustituir material, revisa las dependencias y repara las remisiones
que hayan perdido su soporte.

El teleprompter sigue siendo un entregable sincronizado: aporta locución,
ritmo, pausas y ampliaciones opcionales. Su uso para impartir la clase es
opcional. Toda información necesaria para entender o justificar lo enseñado
debe aparecer también en las diapositivas. No copies párrafos de locución:
exprésala mediante prosa breve, fórmulas justificadas y figuras explicativas.

## Equilibrio entre texto, figura y explicación

**Autocontenida significa argumento completo y reconstruible, con una cantidad
intermedia de texto cuidadosamente elegido.** La autonomía y la legibilidad
se cumplen juntas: ni páginas de apuntes con toda la locución ni esquemas tan
escuetos que haya que adivinar el razonamiento.

Antes de maquetar, decide qué debe comprenderse en cada frame y redacta el texto
exacto que lo permite. Cada frase debe aportar una función concreta: plantear,
definir, justificar, orientar una tarea o concluir. Si solo parafrasea lo que
ya expresa con claridad una figura o fórmula, elimínala o intégrala como etiqueta
local. Conserva la frase que explica el paso difícil. El docente debe poder
reconstruir el argumento visible; la pantalla no necesita dictarle cada frase.

Busca una idea central reconocible, una figura o cuenta que haga trabajo real
y pocas frases breves conectadas. Ajusta esa composición al contenido; no
impongas el mismo bloque introductorio y conclusivo en todas las páginas ni una
cuota universal de palabras. La notación densa también consume atención: no
conviertas párrafos en una pared de fórmulas para aparentar concisión.

Si hay exceso, primero selecciona y reescribe; después redistribuye o separa
pasos con función propia. Conserva enunciados, hipótesis, razones esenciales y
problemas comprometidos, con tipografía legible y dentro del presupuesto de la
sesión. La locución desarrolla lo visible, aporta transiciones y ampliaciones
opcionales. No aloja en exclusiva una justificación necesaria.

**La sesión 05 revisada es el modelo principal aprobado por Omar** para
composición, cantidad de texto, integración de explicación y figuras, y acabado
de los TikZ. Conserva enunciados, contexto y razones esenciales mientras mejora
la figura. No reduzcas el texto a etiquetas ni lo aumentes para suplir un TikZ
débil. Sus PDF y versiones de calibración están en el
[contrato visual](references/visual_contract.md#calibrar-la-cantidad-de-texto).
La sesión 03 original, **Del árbol al objeto que contamos**, queda como apoyo
secundario. El vídeo 1 de la sesión 03 V12 no se usa como buen ejemplo.
La **paleta obligatoria es la de la sesión 02**, con los valores y funciones
fijados en ese contrato. Esta elección cromática prevalece sobre otras referencias.

## TikZ profesionales y revisión obligatoria

El texto autocontenido debe convivir con figuras que expliquen la estructura:
estados, masas, relaciones, transformaciones, decisiones o pruebas. Diseña el
TikZ como parte del argumento. Un grupo de párrafos encerrados en cajas o un
dibujo decorativo no satisface esta exigencia. La complejidad se justifica por
lo que permite comprender; portadas y enunciados no necesitan adornos.

Reutiliza la paleta y los estilos de la sesión 02. Compón figuras de acabado
profesional con geometría coherente, proporciones justificadas, conexiones
inequívocas, jerarquía tipográfica y espacio suficiente para leer y señalar.
Aplica los criterios de [acabado y revisión TikZ](references/visual_contract.md#acabado-profesional-y-revisión-de-cada-tikz)
a **cada figura del PDF real**, incluidas todas las que compartan página.

Compila, renderiza, inspecciona, corrige y vuelve a revisar hasta que no quede
ningún defecto conocido de geometría, legibilidad, paleta o significado
matemático. Registra evidencia concreta por figura dentro de su página y en
`checks.palette` y `checks.tikz_quality`; `accept` exige ambos controles.
Una compilación limpia no sustituye esa revisión. No declares una figura
perfecta por ausencia de avisos automáticos ni dejes pasar un defecto porque
la página, en conjunto, parezca aceptable.

## Apertura, numeración, cierre e identidad visual

Cada vídeo empieza con una **portada de título independiente de la primera
página de contenido**. La locución presenta el tema y su propósito; la primera
página de contenido sitúa la pregunta y su relación con lo aprendido. No mezcles
la portada con el enunciado ni con el desarrollo del problema.

Los enunciados se narran antes de resolverlos: presenta con voz natural la
situación, los datos, las reglas y la pregunta exacta mientras se ven completos
en pantalla. Un ID, una fórmula o «como veis» no sustituyen esa presentación.
Presupuesta la introducción y esa locución dentro de los 30–36 minutos.

Todas las diapositivas llevan numeración visible y consecutiva por vídeo,
incluida la portada como página 1; número visible, SLIDE del guion y página
física deben coincidir. La **última diapositiva de cada vídeo lleva un punto
rojo visible**, fijo desde el inicio, en una posición estable reservada al
cierre. No lo uses como indicador de final en páginas intermedias ni añadas
una página vacía solo para colocarlo.

Mantén exactamente la misma estética en todas las presentaciones: tema,
tipografías, tamaños por función, paleta, portada, títulos, márgenes, estilos
de figuras, numeración y señal de cierre. Reutiliza sus definiciones; no
rediseñes cada vídeo. Las composiciones se adaptan al argumento dentro de ese
sistema. Identifica en el README el archivo y la versión o huella de la
referencia y contrasta los PDF reales. La numeración y el punto rojo son
requisitos adicionales aunque falten en el PDF de referencia. El contrato
visual concreta cómo mantener esta identidad.

## Regla permanente de presentación estática

Una diapositiva es un frame y produce **una sola página física**. Todos sus
textos, fórmulas, figuras, colores y resaltados están visibles y fijos desde
que se abre. No uses overlays, animaciones, objetos que aparezcan o desaparezcan,
cambios de opacidad ni varias versiones de la misma diapositiva que simulen
revelados. La explicación avanza mediante el discurso y el señalamiento.

En Beamer usa `handout` y escribe el contenido nuevo sin `\only`, `\uncover`,
`\visible`, `\onslide`, `\pause` ni especificaciones de etapas. Al reparar
material, compón una versión estática completa: activar `handout` por sí solo
puede superponer variantes incompatibles. El guion cambia de página únicamente
al cambiar de diapositiva. Esta regla prevalece sobre plantillas y ejemplos
históricos del motor; solo una instrucción posterior explícita de Omar puede
cambiarla. El auditor exige una página por frame.

## Fuentes y ámbito

- Curso: `05_Projects/Brainteasers_Quant` desde la raíz de OmarOS. Las rutas curriculares y audiovisuales siguientes se leen desde esa carpeta.
- Entregas: siempre `asincronas/sesion-NN/video-MM-slug/`, con números de dos
  cifras. Por ejemplo, la sesión 03 se produce en `asincronas/sesion-03/`.
  **No crees ni uses `asincronas/v12/` como destino de producción o entrega.**
  V12 identifica el currículo, no un nivel de carpetas. `production_directory`
  debe coincidir con `asincronas/sesion-NN`; esta regla prevalece sobre rutas
  antiguas del plan, README o ejemplos. Al producir una sesión, corrige su
  entrada y sus enlaces dentro del encargo antes de generar los materiales.
  Si la carpeta ya existe, revisa y actualiza los vídeos correspondientes
  preservando trabajo previo; no abras otra raíz para evitar colisiones.
  Una actualización de esta skill no mueve ni borra entregas existentes.
- Motor compartido: `brainteasers-asincronas/_sistema`.
- Paleta obligatoria: sesión 02, especialmente
  `asincronas/sesion-02/video-04-problema-guiado/build/presentacion.pdf`;
  valores y usos precisos en el contrato visual.
- Modelo principal de composición, texto y TikZ: las tres presentaciones
  revisadas de `asincronas/sesion-05/`, con 11, 11 y 15 páginas. Sus rutas,
  huellas y páginas de calibración están en el contrato visual.
- Apoyo secundario: `asincronas/sesion-03/video-01-del-arbol-al-objeto-auxiliar/build/presentacion.pdf`
  y su `guion-teleprompter.md`; después, la sesión 01.
  Observa los PDF reales; estas referencias no cambian el currículo V12 ni
  autorizan copiar overlays o defectos históricos.

La referencia matemática vigente es **V12_Apuntes_Definitivos/**: manual,
cuaderno de 36 problemas y banco completo de 340 problemas. Para el orden y el
alcance audiovisual, lee la ficha AF2 correspondiente en
03_Syllabus_Asincronas_Definitivo.md (`ApuntesDefinitivos/03_Syllabus_Asincronas_Definitivo.md`)
y su entrada en
plan_sesiones_v12.json (`V12_Apuntes_Definitivos/programa/plan_sesiones_v12.json`).
El syllabus desarrolla el contrato docente; el plan conserva títulos, tiempos,
dependencias y fuentes para producirlo. Deben coincidir. AF2.n no significa
capítulo n; tampoco el prefijo del archivo TeX coincide siempre con su número
impreso. Comprueba título y etiqueta en las fuentes.

Lee después el README y los materiales reales de la sesión. Sus referencias a
V8, V10 o V11 documentan su procedencia; no desplazan el currículo V12. Las
sesiones 1, 2 y 4 conservan su contenido y su división actual en vídeos. La 3
se reformula según la ficha V12; las versiones anteriores sirven como recursos,
no como contrato vigente. Para las restantes, conserva lo que construya la
capacidad prevista y reordena lo que dependa de ideas aún no enseñadas. Una
nueva instrucción de Omar puede cambiar cualquiera de estas decisiones.

Distingue el encargo: actualizar el syllabus fija el recorrido y sus problemas;
producir una sesión genera sus presentaciones, guiones y justificaciones. No
marques vídeos como adaptados a V12 por haber cambiado una tabla o un README.
Si falta una elección temática, usa el contrato docente; pregunta solo si la
ambigüedad persiste y cambia materialmente lo que se enseñará.

Usa el perfil nativo de OmarOS para alcance, preflight Git, revisión y publicación.
Esta skill no activa cadenas históricas de agentes ni cambia modelos o hooks.
El motor externo y las sesiones de referencia se leen; una petición de producir
una sesión no autoriza cambios incidentales en todas las plantillas o sesiones.

## Continuidad y complementariedad entre vídeos

Antes de diseñar o mejorar un vídeo, revisa las presentaciones y guiones reales
de los vídeos anteriores y posteriores que conectan con él, como mínimo sus
vecinos inmediatos, también al cruzar de sesión. Si hay grabaciones disponibles,
revísalas para contrastar qué se explica efectivamente. Amplía la lectura a
los vídeos donde se introducen o utilizan sus conceptos y problemas; los títulos
del plan no bastan para conocer lo ya enseñado. Si el siguiente vídeo aún no
existe, usa su ficha y storyboard, y declara que esa continuidad es provisional.

Registra en el README un mapa breve por vídeo: qué recupera, qué capacidad nueva
construye, con qué problema o representación la desarrolla y qué deja preparado
para el siguiente. Cada vídeo debe aportar una dificultad, justificación,
conexión o transferencia reconocible. La riqueza procede de esas aportaciones
complementarias; no de repetir una solución con otras palabras ni de añadir
ejemplos sin función.

La apertura retoma el resultado preciso que se necesita; el cierre interpreta
lo conseguido y enlaza con la pregunta siguiente sin impartirla por adelantado.
En el último vídeo del curso, cierra el recorrido sin inventar un sucesor.
Mantén objetos, notación y vocabulario coherentes. Para conservar la autonomía,
repón brevemente el enunciado y resultado reutilizados, pero no repitas toda
la explicación anterior salvo que una nueva pregunta lo justifique. Distingue
en la justificación pedagógica esa recuperación de una duplicación prescindible.

Después de editar, recorre de nuevo anterior → actual → posterior y comprueba
que no hay repeticiones sustanciales, saltos de prerrequisitos, contradicciones
ni remisiones rotas. Registra los archivos y páginas o bloques contrastados,
la contribución propia y los enlaces de entrada y salida. Leer vídeos vecinos
no autoriza modificarlos fuera del encargo; documenta cualquier ajuste necesario
que quede fuera del alcance.

## Secuencia estable de producción

1. **Contrato de sesión.** En su README, concreta lo que el alumno podrá explicar
   y resolver, conocimientos previos, capítulos y secciones V12, IDs del banco
   o números del cuaderno, dependencias y presupuesto de 30–36 minutos. Separa
   el caso resuelto, la reconstrucción diferida y el intento sin pistas. En una mejora, conserva
   los objetivos válidos y diagnostica el material actual antes de reescribir.
   Aplica la revisión de continuidad anterior y posterior y fija el mapa de
   aportaciones y la referencia estética antes del storyboard.
2. **Arquitectura conceptual.** Empieza con una pregunta accesible y el objeto
   matemático general. Explicita qué son sus elementos, qué representan, cuándo
   dos casos cuentan como el mismo y qué estructura añaden las hipótesis. Desde
   ahí deriva el caso concreto, la prueba que explica el mecanismo y un problema
   de transferencia. Lee Scholar solo si necesitas desarrollar ese argumento;
   su enfoque ontológico es pertinente, pero el curso fija los prerrequisitos.
3. **Storyboard conjunto.** Diseña a la vez diapositivas completas y discurso.
   Cada frame responde a una pregunta; sus objetos permanecen fijos.
   Decide el texto exacto, qué relación explica la figura y qué desarrolla la
   locución. Comprueba que lo esencial queda visible sin duplicarlo entre título,
   cuerpo, etiquetas y cierre, y que el recorrido se entiende sin discurso.
   Decide qué se señala mientras se pronuncia cada frase. No escribas dos productos
   independientes para intentar sincronizarlos al final. Incluye portada
   independiente, introducción, enunciados narrados, números visibles y punto
   rojo final desde este diseño conjunto.
4. **Construcción.** Reutiliza la plantilla y el motor Hespérides. Lee el
   [contrato visual](references/visual_contract.md) para cualquier generación
   o cambio de geometría. Lee el [protocolo de producción](references/production_protocol.md)
   para comandos, formatos, controles y cierre. la entrada verificada `cli skill-run brainteasers-quant production init`
   crea los vídeos desde un plan; el contenido de plantilla aún debe escribirse.
5. **Verificación y reparación.** Ejecuta `audit` sobre la sesión completa.
   Repara errores de compilación, tiempos, estructura y presentación. Inspecciona
   **todas las páginas físicas** renderizadas, una por cada frame,
   a resolución suficiente para leer. Una hoja de contacto orienta; no sustituye
   esa lectura. Contrasta la estética exacta con la referencia aprobada,
   incluida la portada; verifica numeración y punto rojo final. Compara la
   paleta con la sesión 02 y revisa cada TikZ según el contrato de acabado.
6. **Revisión de comprensión y selección del texto.** Lee primero solo el PDF, en orden,
   como un docente que no conoce el teleprompter. Reconstruye cada enunciado y
   resuelve de nuevo los ejemplos usando lo visible: verifica hipótesis,
   notación, pasos justificados, conclusión y transiciones. No completes
   mentalmente los huecos con lo que recuerdas haber escrito. Registra por
   problema las páginas que contienen su planteamiento y su razonamiento.
   Después contrasta el guion: si contiene información esencial ausente del
   PDF, intégrala con redacción breve o representación explicativa, sin pegar
   el párrafo de locución. Haz también la revisión inversa: retira repeticiones
   y comprueba que cada frase conservada aporta algo necesario. Revisa a tamaño
   de exposición si se reconoce la idea central y se puede seguir el argumento
   sin leer varios párrafos mientras se escucha. Si una solución
   está en la misma diapositiva, trátala como visible desde el inicio; no finjas
   un intento ciego. Revisa de nuevo los enlaces con los vídeos anteriores y
   posteriores y registra las aportaciones propias y las repeticiones eliminadas.
7. **Cierre vigente.** Repite compilación, render y revisión tras las correcciones.
   Registra la revisión con `accept`: exige evidencia de cada página y rechaza
   una aprobación cuyo material haya cambiado. Una dependencia esencial del
   teleprompter o una página saturada de texto es un defecto pendiente e impide
   dar la revisión por superada, aunque no haya desbordamientos de LaTeX.
   También impiden cerrar una paleta distinta de la sesión 02, un TikZ con
   defectos pendientes, una estética distinta, una portada mezclada con
   contenido, la ausencia de números o punto rojo final, enunciados sin narrar
   y solapamientos o saltos conceptuales relevantes sin resolver.
   Documenta decisiones en la justificación pedagógica. Entrega PDFs, guiones
   y justificaciones; actualiza README, realiza commits y push conforme al
   flujo del proyecto.

## Criterio editorial y de enseñanza

Explicación general accesible → objetos y distinciones → mecanismo → caso
particular → prueba → variación que pone a prueba la comprensión. Es una lógica
del discurso, no siete rótulos obligatorios en cada vídeo. Evita formalismo que
no haga trabajo; no rebajes el rigor a una receta. Por ejemplo, antes de contar
«selecciones», identifica si son secuencias, subconjuntos o multiplicidades y
qué equivalencia permite pasar de un objeto al otro.

Cada sesión recupera una capacidad anterior y añade una dificultad reconocible.
Comprueba que los ejemplos se resuelven con lo ya construido; una remisión a
una ampliación no cubre un prerrequisito oculto. La práctica del cuaderno y el
banco se selecciona por mecanismo y dificultad, no por completar cuotas de IDs.
Consulta la auditoría V12 si un problema parece requerir teoría adicional;
lee su enunciado y solución actuales antes de asignarlo. Cobertura teórica no
significa rapidez ni dominio de un alumno.

Conserva el equilibrio entre comprender el formalismo y disponer de una vía
breve justificada. Ante un experimento confuso, vuelve a escribir el espacio
muestral, qué representa un resultado y qué ley le asigna pesos. Nombra y define
abstracción, representación, reencuadre y motor cuando ayuden a ordenar una
solución; no conviertas las etiquetas históricas M/R/E en un temario paralelo.

El teleprompter tiene voz humana: frases pronunciables, símbolos traducidos al
habla y referencias inequívocas a lo visible. Las pausas y la escritura consumen
tiempo real. No alcances la duración repitiendo ideas ni acelerando una prueba.
Conserva el formato y los modos que entiende el motor. A expone sobre una
página fija; C pausa la locución manteniéndola igual. Usa B solo cuando Omar
pida expresamente escritura manual; no convierte las figuras en una animación.
Anota diapositiva, página física y qué señalar. Si varios bloques usan la misma
diapo, indica mantenerla fija, sin volver a avanzar. No escondas respuestas
para introducir pausas; plantea una reconstrucción con solución visible o un
problema independiente en otra diapositiva completa.

Las figuras son parte del razonamiento: explican una relación, una construcción
o una distinción. El espacio libre tiene función. No rellenes una página para
que parezca compleja ni reduzcas toda la tipografía para encajar un diagrama.

## Qué automatizar y cuándo terminar

El script ejecuta mecánica repetible; el modelo decide y corrige contenido,
geometría y claridad. Mantén el modelo elegido por Omar. No exijas `max` ni
delegues por sistema. Trabaja primero sobre los fallos concretos, conserva lo
que ya funciona y vuelve a revisar el conjunto final.

Continúa hasta cerrar errores y observaciones relevantes. Si dos reparaciones
sucesivas no mejoran el mismo defecto, cambia la composición o la explicación;
no sigas escalando tamaño, complejidad o capacidad del modelo. Un impedimento
real se informa con su archivo y evidencia, conservando el trabajo recuperable.

`accept` certifica integridad y cobertura de una revisión declarada, no belleza
objetiva ni verdad matemática. Distingue «artefactos revisados» de «listo para
grabar»: este último requiere además las validaciones de entrega y un ensayo
oral real confirmado. Nunca marques una lectura en voz alta como realizada
por haber contado palabras o por haber leído silenciosamente el guion.

## Peticiones que debe resolver

- «Crea la sesión 03 a partir del syllabus V12»:
  produce la sesión y sus tres entregables por vídeo, no solo un esquema.
- «Mejora los TikZ y el ritmo de la sesión 02»: diagnostica, repara la sesión
  solicitada y revisa su duración total y todas las diapositivas afectadas.
- «Audita la sesión 01 sin modificarla»: analiza una copia temporal si necesitas
  recompilar; entrega hallazgos concretos y no cambia fuentes ni estados.
