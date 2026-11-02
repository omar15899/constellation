# Criterio editorial y calibración

## Qué aprender de las referencias

Las rutas siguientes se expresan desde la raíz de OmarOS. Lee los fragmentos
relevantes al empezar el trabajo editorial; después trabaja sobre el destino
vigente. Estas referencias calibran voz y arquitectura, no certifican ausencia
de errores ni obligan a copiar su materia.

- `05_Projects/Brainteasers_Quant/V12_Apuntes_Definitivos/latex/curso/01_metodo.tex`:
  voz directa, distinción entre modelo, representación y motor; los dados
  muestran cómo una pregunta determina el resultado completo que hay que describir.
- `05_Projects/Brainteasers_Quant/V12_Apuntes_Definitivos/latex/curso/02_contar_construyendo.tex`:
  árbol, hojas, listas y conjuntos; la suma nace de grupos disjuntos y el producto
  de un número constante de continuaciones. Conserva esa explicación verbal
  junto a las fórmulas. La independencia probabilística todavía no interviene.
- `05_Projects/Brainteasers_Quant/V12_Apuntes_Definitivos/latex/curso/03_contar_transformando.tex`:
  subconjuntos, restricciones y corrección de repeticiones. Es también un caso
  que Omar encuentra insuficientemente motivado: examina la apertura con especial
  atención, sin asumir que la frase «incluir o excluir» resuelve esa objeción.
- `06_Knowledge_Base/Mathematics/Finance/Matematicas_Financieras.MD`:
  lee «Pregunta rectora», «Mapa maestro», «La misma call a lo largo de todo el
  libro» y «Cómo está construido este libro». La cualidad transferible es el
  recorrido causal: se construye cada objeto, se precisa qué añade cada estructura
  y el mismo ejemplo revela varias capas. No importes su nivel técnico financiero
  como prerrequisito del taller.

El alumno del taller puede llegar con un vocabulario menos desarrollado que Omar.
Obtén el nivel inicial del programa y del material previo; si no está declarado,
haz explícita una suposición razonable y construye los términos necesarios.
El destino conceptual puede ser profundo sin exigir que el lector ya domine
el lenguaje con que lo vamos a expresar.

## Una explicación completa tiene una razón para existir

Antes de escribir, concreta para ti la pregunta, la dificultad que la vuelve
interesante, lo que ya sabemos y lo que falta. Eso determina el orden, no un
molde de encabezados. La apertura orienta al lector dentro del problema general
y le permite anticipar para qué necesitaremos la construcción.

Presenta la estructura general que realmente reúne los casos: qué objetos
admite, cuáles son sus elementos y qué cuenta como el mismo objeto. Desciende
al ejemplo pequeño sin perder esa estructura. Después recupera la generalidad
con las hipótesis precisas. Si empiezas por el ejemplo porque revela la pregunta,
sitúalo pronto en su universo; no prolongues una receta sin significado.

La cadena de razones debe quedar escrita. «Ahora veremos subconjuntos» anuncia
un cambio; explicar qué permite aislar ese laboratorio y qué dificultad prepara
es lo que lo justifica. La última frase de un bloque puede abrir la necesidad
del siguiente sin anticipar toda su solución.

### Calibración del inicio del tema 3

Verifica primero si Omar se refiere al capítulo impreso o al tema audiovisual.
Si el encargo es el capítulo de conteo con restricciones, una motivación útil
conecta lo ya aprendido —construir y contar hojas— con tres dificultades nuevas:
filtrar construcciones, cambiar de descripción y corregir múltiples conteos.

Los subconjuntos proporcionan un laboratorio sencillo para separar esas
operaciones. Sobre un conjunto finito $S$, una selección sin orden ni repeticiones
es un subconjunto $A\subseteq S$. Cada elemento de $S$ plantea una decisión
de pertenencia. Su función indicadora $\mathbf 1_A:S\to\{0,1\}$ registra todas
esas decisiones; el mapa que envía $A$ a $\mathbf 1_A$ tiene inversa, pues una
función binaria recupera el subconjunto donde vale uno. Elegir una enumeración
de $S$ permite escribir la función como una palabra; la palabra es una
representación que depende de esa enumeración, no el propio subconjunto.

Con tres elementos se ven las ocho selecciones. Con $n=|S|$, la biyección y el
producto permiten contarlas como $2^n$. Fijar su tamaño es una restricción;
agrupar por tamaños explica una cuenta por suma; cambiar una condición sobre
las selecciones puede hacer útil una biyección o un complemento. Antes de
prometer que una figura o método preparará una sección posterior, comprueba
esa sección real. No añadas material ajeno para justificar retrospectivamente
una apertura mal escogida.

Este ejemplo orienta una reparación posible. Crear esta skill no autoriza
reescribir ahora el capítulo; en un encargo de redacción, adapta la motivación
a su contenido efectivo y comprueba qué estaba ya explicado antes.

## Ontología que hace trabajo

Introduce distinciones allí donde cambian una conclusión. En conteo: objeto,
descripción, secuencia, subconjunto y multiplicidad. En probabilidad: experimento,
resultado completo, suceso, observable y ley. En procesos: historia, estado,
información y decisión. No conviertas estos nombres en un catecismo paralelo.

Si contamos descripciones de objetos, explicita el mapa y comprueba qué alcanza.
Para dividir por un número, demuestra que todas las fibras pertinentes tienen
ese tamaño; una fibra es el conjunto de descripciones que producen un objeto
fijado. Si los tamaños varían, la división uniforme falla. Explica esa dificultad
con un ejemplo pequeño o un contraejemplo cuando haga falta.

Si interviene una relación de equivalencia, desarrolla lo necesario para que
el lector no tenga que aportar la teoría:

1. Declara el conjunto de descripciones $X$ y el criterio de identificación.
2. Explica y comprueba reflexividad, simetría y transitividad. No basta decir
   que «agrupamos cosas parecidas»: un criterio que falle transitividad no
   produce las clases que estamos usando.
3. Define $[x]=\{y\in X:y\sim x\}$ y muestra por qué dos clases son iguales
   o disjuntas; así forman una partición. Distingue $x$, $[x]$ y $X/{\sim}$.
4. Si se da una fórmula sobre clases mediante un representante, verifica que
   no cambia al escoger otro representante. Justifica qué tiene que ver ese
   cociente con los objetos originales; no presupongas una biyección.

El grado de detalle depende del uso: una referencia explícita a una construcción
ya demostrada puede evitar repetir su prueba entera, pero repón la definición,
las hipótesis y el paso necesario para entender el pasaje actual.

## Voz, densidad y consulta

Escribe español natural, como alguien que entiende la materia y quiere que
otro también la entienda. Preguntas de orientación, «pensemos», «la dificultad
está en…» o «esto permite…» sirven cuando guían un paso real; no los repitas
como muletillas. Conserva terminología estable, verbos concretos y frases que
se puedan leer en voz alta. No copies la informalidad de una conversación al
registro del libro.

Introduce la fórmula después de decir qué expresa y explica después lo que
permite concluir. No traduzcas mecánicamente cada símbolo si ya está fijado.
Desarrolla el paso difícil; comprime el álgebra rutinaria que el público pueda
reconstruir. Evita «obviamente», «trivialmente» o «se ve» donde falta la razón.
Una afirmación universal lleva hipótesis y alcance; una aproximación, el motivo
y la condición bajo la que es útil.

Usa títulos para preguntas o resultados identificables, no para fragmentar
cada párrafo. Un recuadro destaca algo que merece consulta, no otra repetición
de la página. Las definiciones, etiquetas y referencias deben permitir volver
al resultado y sus condiciones. Un ejemplo recurrente da continuidad; otro
ejemplo se justifica si revela una estructura, una frontera o una transferencia
que el primero no muestra.

Autocontención no significa repetir el libro dentro de cada sección. Un capítulo
declara sus prerrequisitos y repone el contenido indispensable para seguirlo;
el desarrollo local no puede depender de una solución ausente, una nota privada,
un futuro capítulo o conocimientos que el curso todavía no ha construido.

## Revisión adversarial útil

Revisa desde tres perspectivas y deja hallazgos concretos en la evidencia del
encargo, sin forzar al texto del alumno a exhibir la auditoría:

- **Alumno:** ¿puedo decir qué buscamos antes de la primera cuenta? ¿Entiendo
  por qué aparece cada concepto? ¿Qué frase me obliga a adivinar algo?
- **Matemático:** ¿qué supuesto autoriza cada paso? ¿Es la construcción bien
  definida? ¿Puedo romper la afirmación con un caso frontera o retirando una
  hipótesis? Comprueba al menos las fronteras que afectan al argumento.
- **Editor:** ¿qué aporta aquí respecto de lo anterior? ¿El ejemplo progresa?
  ¿Una definición o prueba está repetida sin función? ¿Las remisiones siguen
  siendo verdaderas después del cambio?

Resuelve de nuevo el ejemplo o contrástalo con una enumeración pequeña, una
prueba alternativa o un contraejemplo pertinente. Elige verificaciones capaces
de detectar un error; no añadas tests que copien la fórmula que se verifica.
Una prueba externa citada lleva sus hipótesis y una fuente verificable. Consulta
fuentes primarias cuando un hecho especializado sea incierto; no hagas búsqueda
web de cada definición elemental ni inventes citas.

Reescribe y vuelve a leer los pasajes afectados y sus conexiones hasta resolver
los defectos relevantes. Si dos intentos no mejoran el mismo paso, cambia el
ejemplo o la arquitectura; no sigas alargando su paráfrasis. No prometas ausencia
universal de lagunas: informa qué se comprobó y cualquier límite pendiente.
