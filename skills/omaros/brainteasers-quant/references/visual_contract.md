# Contrato visual Hespérides

Los materiales de referencia se localizan en el proyecto del curso, desde su raíz.

La **sesión 05 revisada es la referencia principal aprobada por Omar** para
composición, cantidad de texto, integración de explicación y figuras, y acabado
de los TikZ. La **paleta obligatoria** procede de la sesión 02. La sesión 03
original,
Del árbol al objeto que contamos (`asincronas/sesion-03/video-01-del-arbol-al-objeto-auxiliar/build/presentacion.pdf`),
con su guion (`asincronas/sesion-03/video-01-del-arbol-al-objeto-auxiliar/guion-teleprompter.md`),
queda como apoyo secundario; después, la sesión 01. Cada referencia gobierna
su función: la sesión 03 no desplaza a la 05 ni cambia la paleta de la 02.
Usa el motor compartido `_sistema`.
Mantén exactamente esta estética entre presentaciones: no importes estilos de
Reflexiones a LaTeX, plantillas genéricas ni una estética nueva. La selección
de este ejemplo no sustituye las fuentes matemáticas ni el orden del currículo V12.

La referencia principal tiene 37 páginas repartidas en tres vídeos de 11, 11
y 15 páginas. Cada vídeo tiene portada propia, numeración y punto rojo final;
su guion narra los enunciados antes del cálculo. La sesión 03 secundaria tiene
11 páginas y no muestra número ni punto rojo: no copies esas ausencias.

## Elementos estables

| Elemento | Contrato observado |
|---|---|
| Soporte | Beamer, 10 pt, 16:9, compilación LuaLaTeX |
| Tema | `HesperidesQFBeamer` + `estilos/asincronas.sty` + `estilos/notacion.tex` |
| Tipografía | Open Sans para texto; matemática Palatino/Pazo definida por el tema |
| Fondo | Blanco; composición tranquila y márgenes visibles |
| Portada | Página propia anterior al contenido; banda horizontal amarilla `FFCD00`, título negro, subtítulo, autor e institución |
| Interior | Título negro arriba a la izquierda; figuras explicativas y texto conciso suficiente para enseñar |
| Autor | Omar Khalil Abuali; Universidad de las Hespérides |
| Cabeceras | Sin logos ni navegación añadidos; mismo título y posición que la referencia |
| Numeración | Visible en todas las páginas, consecutiva desde 1 por vídeo, incluida la portada; esquina inferior derecha y posición constante |
| Cierre | Punto rojo sólido a la izquierda del número, solo en la última página de cada vídeo; visible desde que se abre |
| Visibilidad | Una página por frame; todo visible y fijo, sin cambios de opacidad |

Mantén las importaciones del `main.tex` de plantilla y una ruta real del motor.
No copies ni alteres el vendor Hespérides para reparar un problema local.
Fija una única definición de numeración y marcador final para los vídeos del
encargo, respetando el área de contenido. Mantén su tamaño, separación y posición
idénticos. El punto de cierre ocupa una zona distinta de los dibujos: el rojo
sigue disponible dentro de ellos para errores y contraejemplos.
No cambies fuentes, tamaños por función, paleta, títulos, márgenes, bordes,
rellenos o estilos de flechas entre vídeos. Si el contenido no cabe, reescribe
la composición o separa pasos; no alteres la identidad para hacerlo caber.
La composición cumple la [autonomía docente](../SKILL.md#regla-permanente-de-autonomía-docente):
el enunciado, las hipótesis y los pasos esenciales tienen espacio visible y
legible. No se relegan al teleprompter para conseguir una página más despejada.
La selección del texto sigue el [equilibrio editorial](../SKILL.md#equilibrio-entre-texto-figura-y-explicación):
la información esencial puede expresarse mediante texto, notación y figuras
que se complementan; no necesita aparecer por triplicado.

## Paleta fija de la sesión 02

Se verificó en las fuentes y los PDF reales: árboles de decisión (`asincronas/sesion-02/video-01-arboles-de-decision/build/presentacion.pdf`),
pp. 1, 3 y 6, SHA-256 `af3dc68f60fd1691b28c30dd6f473f84c37384d89a532e9c9bb37efd00d8965a`;
y problema guiado (`asincronas/sesion-02/video-04-problema-guiado/build/presentacion.pdf`),
pp. 1, 3 y 6, SHA-256 `a906da17d592864372b6668e075e8bfdf5d3959a5f8cdf111c9660a65bef9303`.
La retícula y su recorrido ámbar están en `fig02_reticula.tex`; los colores se
definen en `_sistema/estilos/asincronas.sty` y el amarillo institucional en
`_sistema/hesperides/HesperidesQFBeamer.sty`. Reutiliza esas definiciones.

| Función | Nombre | Hexadecimal |
|---|---|---|
| Datos y estructura principal | `cDato` / `qbtBlue` | `#1F3A93` |
| Estructura secundaria, nodos y ramas de apoyo | `qbtBlueSoft` | `#4A6FA5` |
| Resultado y conclusión | `cResultado` / `qbtGreen` | `#2E7D5B` |
| Error, exclusión o contraejemplo | `cError` / `qbtRed` | `#A33A3A` |
| Recorrido o relación destacada | `cAcento` / `qbtAccent` | `#B97A2A` |
| Portada y énfasis institucional puntual | `cDestacado` / `HesperidesYellow` | `#FFCD00` |
| Glosas y contexto | `cSecundario` / `qbtMuted` | `#6B6B6B` |
| Fondo frío | `qbtBgCool` | `#F1F4FA` |
| Fondo cálido | `qbtBgWarm` | `#FBF6EE` |
| Texto principal y fondo general | `HesperidesBlack`, `HesperidesWhite` | `#000000`, `#FFFFFF` |

No elijas una paleta nueva por vídeo ni sustituyas estos colores por tonos
parecidos. Conserva los rellenos y mezclas con blanco de los estilos del motor
(`caja`, `cajadato`, `cajacalida`, `cajaresultado`, `cajaerror`, `cajafoco`);
si una figura necesita un matiz, derívalo de esta paleta y conserva su función.
Las mezclas de color son fijas desde el inicio; no son revelados por opacidad.
Usa el ámbar y el fondo cálido como en los recorridos de la sesión 02, y el
amarillo de forma puntual, sin convertir toda figura en paneles amarillos.

Los fondos suaves `qbtBgCool` y `qbtBgWarm` separan grupos sin crear paneles
pesados. El color tiene el mismo significado entre vídeos. No dependas solo
del color para distinguir casos: añade posición, etiqueta o forma.

## Calibrar la cantidad de texto

**Usa la sesión 05 revisada como patrón principal de texto, composición y TikZ.**
La versión aprobada consta de estos tres PDF:

- Normalizar y condicionar (`asincronas/sesion-05/video-01-normalizar-y-condicionar/build/presentacion.pdf`),
  11 páginas, SHA-256 `aae78e3c17cd1a8f6544bc4ab629162c670df52d6582f6d88261f3062445ebc5`.
  Calibración: p. 1, portada; pp. 3 y 4, barras y normalización; pp. 5 y 6,
  regiones y prueba con texto suficiente; p. 10, transporte de masas con flechas.
- Contar estados y respetar pesos (`asincronas/sesion-05/video-02-contar-estados-y-respetar-pesos/build/presentacion.pdf`),
  11 páginas, SHA-256 `9878f1db81c364684d147a062388f68274dc307888bb123ac31bbf1df8f36c58`.
  Calibración: pp. 3 y 4, cuadrículas; p. 6, enunciado y cubo 3D; pp. 7 y 8,
  superficies y multiplicidades que justifican una cuenta.
- Dos sobres y retos de información (`asincronas/sesion-05/video-03-dos-sobres-y-retos-de-informacion/build/presentacion.pdf`),
  15 páginas, SHA-256 `44c3b3e39669c8187656b1874c6d5addb4911544eb72f47b82255a4fe5324a59`.
  Calibración: pp. 3 a 6, árboles y masa ganadora; pp. 9 a 14, tres parejas de
  enunciado y solución visual; p. 15, cierre y transferencia.

Sus guiones están junto a cada PDF, en la carpeta del vídeo. La referencia es
un patrón de acabado; cada producción nueva exige su propia revisión.
Mantén el enunciado, el contexto y la razón del paso difícil, combinados con
una figura que haga visible el mecanismo. No recortes esas razones para
agrandar el dibujo ni añadas párrafos para compensar una figura insuficiente.
No conviertas esta calibración en una cuota uniforme de palabras o líneas.

Como apoyo secundario, abre el PDF original de sesión 03 y su guion cuando
resuelva una decisión de composición. Usa estas páginas para observar funciones
editoriales concretas, sin convertir sus ejemplos en el temario de cada vídeo:

- Página 1: portada exclusiva de título, subtítulo y autoría; la locución abre
  con la pregunta que guía el vídeo.
- Página 2: situación narrada en prosa, pregunta explícita, empates permitidos y
  distinción entre el orden de aparición y ordenar después. El universo y el
  evento se formalizan una vez explicado qué representan.
- Páginas 3–5: miniatura que puede enumerarse completa, pérdida de información
  del histograma y correspondencia reversible al restringir el dominio. Las
  figuras muestran la relación y las frases explican qué se conserva y por qué.
- Páginas 6–9: regreso explícito al problema original, mismo ejemplo al cambiar
  de representación, existencia y unicidad, cuenta y probabilidad interpretadas.
- Páginas 10–11: variación de una sola condición y cierre que pide reconstruir
  el mecanismo. El guion enlaza con la formalización del vídeo siguiente.

El vídeo 1 de la sesión 03 V12 queda retirado como ejemplo de buena presentación.
Conserva la cantidad intermedia de texto: enunciado íntegro, contexto local y
razón esencial, con figuras que hagan trabajo explicativo. El guion narra los
enunciados y desarrolla las relaciones visibles; no se limita a leer títulos
ni aloja en exclusiva las justificaciones. La misma estética no exige repetir
la distribución de cajas ni las frases de una página: cada composición debe
servir a su pregunta con los mismos estilos, tamaños y márgenes.

## Componer TikZ sin deteriorar la página

Usa estilos `caja`, sus variantes semánticas y `glosa`. Prefiere anclajes,
coordenadas compartidas y espaciado explícito. Alinea centros, filas, columnas y
ejes cuando representen relaciones comparables. Las flechas deben terminar en
el objeto correcto, sin cruzar etiquetas. Deja holgura alrededor de fórmulas,
entre ramas y respecto al título.

El texto explicativo de cajas ronda 9 pt y las glosas 7 pt en las composiciones
más legibles de las referencias. Son objetivos de lectura, no límites ciegos:
un subíndice puede ser menor. El auditor señala texto por debajo de 6 pt para
inspección; una etiqueta esencial ilegible se corrige aunque no haya aviso de
LaTeX. Evita `\tiny`, escalado global y glosas microscópicas como remedio al
exceso de contenido.

Ante saturación, en este orden: elimina redundancia y reescribe con precisión
sin perder información esencial; redistribuye espacio; reparte el argumento entre preguntas o subpasos
con función propia, cada uno en una diapositiva completa. Conserva el contexto
necesario para seguir la secuencia.
En un árbol grande, deja visibles la regla local y el conjunto completo, y
recórrelos con el señalamiento; no exijas descifrar veinte hojas para entender
qué se está contando.

Compón una página estática por diapositiva y fija su caja envolvente. Todo el
contenido se muestra desde el inicio. No uses comandos de overlays, revelados,
resaltados cambiantes ni opacidades temporales. No fabriques varios frames casi
idénticos para simular apariciones sucesivas. Si no cabe, redistribuye o condensa
la redacción conservando enunciados, condiciones y justificaciones; separa
diapositivas por su función en el argumento, con una composición completa para
cada una. Al convertir material antiguo, resuelve las variantes
incompatibles y elige resaltados permanentes antes de compilar en `handout`.

## Acabado profesional y revisión de cada TikZ

Antes de dibujar, formula qué debe permitir explicar la figura y qué representan
sus elementos. Diseña después su geometría. Las figuras pueden ser ricas cuando
el argumento lo necesita; el acabado profesional depende de la precisión y la
claridad, no del número de objetos o de efectos. Una tabla puede ser la mejor
comparación, pero no sustituye todas las construcciones por párrafos en cajas.

Revisa cada figura en el PDF renderizado, a tamaño de exposición y con ampliación
para comprobar detalles. Si una página contiene varias, identifica y revisa
cada una. Aplica estos criterios:

| Criterio | Evidencia exigida para cerrar |
|---|---|
| Función matemática | Se puede explicar qué relación muestra y qué paso justifica; no es decoración. |
| Fidelidad | Estados, masas, escalas, multiplicidades, ejes y restricciones corresponden al modelo. Una ilustración de un caso no se presenta como dato observado. |
| Geometría | Alineaciones, tamaños, distancias y proporciones son coherentes; no hay recortes, tangencias accidentales, solapes ni etiquetas atravesadas. |
| Conexiones | Cada flecha sale y llega al objeto correcto, con dirección y punta legibles; ramas, llaves y rótulos tienen referente inequívoco. |
| Lectura | Texto y notación se leen al tamaño de exposición; el contraste es suficiente y los rótulos están junto a sus objetos. No se reduce toda la figura para encajar. |
| Integración | Texto, fórmula y TikZ se complementan; la idea central se reconoce y el argumento se reconstruye sin el teleprompter. |
| Identidad | Paleta exacta de sesión 02, estilos del motor y jerarquía visual consistente con las referencias. |

Para cada figura registra su página y archivo o identificador, la relación que
explica y observaciones concretas sobre estos criterios. Escribe las reparaciones
efectuadas y cualquier pendiente. Corrige y vuelve a renderizar hasta que no quede
un defecto conocido; una página fallida no se compensa con otras mejores. Si dos
ajustes no resuelven el mismo defecto, cambia la composición o la representación.

Un PDF que compila, un resultado automático sin avisos o un «todo perfecto»
genérico no acreditan esta revisión. La skill exige inspección real y evidencia;
la aceptación verifica su cobertura y vigencia, no demuestra belleza ni verdad
matemática por sí sola. No imites overlays o letra diminuta de una fuente
histórica de sesión 02: la referencia cromática no anula las reglas actuales.

## Inspección visual exigida

Abre la hoja de contacto para detectar cambios de escala y densidad entre
vídeos. Después abre cada página a tamaño legible y registra su observación:
jerarquía, recortes, intersecciones, contraste, equilibrio, legibilidad y sentido
matemático de las conexiones. Antes de consultar el guion, lee la secuencia y
comprueba que se puede explicar cada problema y justificar su solución con lo
visible. Una página limpia que requiere adivinar el enunciado o suplir un paso
esencial falla la revisión. También falla una página que contiene todo pero
obliga a leer párrafos y explicaciones repetidas sin una idea central clara.
Revisa el texto en títulos, cajas, etiquetas y glosas como un conjunto: distingue
recordatorios necesarios de duplicaciones que no aportan nada. El blanco libre
no compensa una concentración de texto difícil de seguir. Comprueba después que el número de páginas coincide
con el de frames y que cada cambio del guion corresponde a una diapositiva distinta.

Contrasta la paleta con los PDF de sesión 02 indicados arriba. Contrasta además
una portada, una definición, una construcción completa y un problema guiado con
las páginas pertinentes de la sesión 05, a igual escala. Usa la sesión 03 solo
como apoyo secundario. Comprueba tipografía,
tamaños por función, paleta, márgenes, títulos, cajas y flechas; registra páginas
comparadas y diferencias corregidas. Verifica en todas las páginas la numeración
visible contra el PDF y el guion, y la presencia del punto rojo solo al final.
La portada debe ocupar una página propia anterior al contenido. Contrasta
apertura y enunciados con los bloques de locución, y los enlaces conceptuales
con los vídeos anteriores y posteriores conforme a la skill. No asignes una puntuación media
que oculte una página fallida: toda observación pendiente se resuelve o se
declara explícitamente como impedimento. Registra la comparación cromática en
`checks.palette` y el acabado de las figuras en `checks.tikz_quality`; conserva
en `pages` la evidencia de cada figura de cada página. Ambos controles son
obligatorios para `accept`, además de comprensión, sincronización y matemática.
