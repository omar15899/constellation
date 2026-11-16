# Objetos, estructura y representaciones

Esta referencia orienta la explicación y la revisión matemática: el lector debe
poder reconstruir qué objetos intervienen, qué relaciones los conectan y por qué
una conclusión sobre sus representaciones dice algo sobre ellos. Úsala donde
una distinción sostenga el argumento; no conviertas cada respuesta en un
inventario formal. Los [cuatro ejemplos desarrollados](ontology-examples.md)
permiten profundizar sin cargar la pauta general.

## Elegir la generalidad que explica

Parte de la pregunta y de la clase de objeto que puede responderla. Presenta el
marco general pertinente antes de particularizarlo, cuando ese orden permita
comprender la construcción. Si el encargo pide primero un ejemplo o un cálculo,
respeta ese orden y sitúalo después en el marco que lo justifica. La generalidad
útil permite recuperar los casos pedidos; no exige remontarse a fundamentos
que no intervengan en el argumento.

Haz visibles las dependencias: construir un objeto, añadir estructura, imponer
una propiedad, elegir una representación y perder información son operaciones
distintas. Explica qué habilita cada transición y qué conserva. Un ejemplo
pequeño puede acompañar ese recorrido, pero no reemplazar la definición general
por sus particularidades finitas, euclídeas o matriciales.

## Establecer el objeto antes de operar

Introduce el conjunto o espacio ambiente, el tipo de sus elementos y la
estructura necesaria para la pregunta. Un elemento puede ser un número, una
función, una clase de equivalencia o una transformación. Decir que algo es un
«punto» sólo afirma su pertenencia a un espacio; no lo convierte en una tupla
de números ni impone que ese espacio sea geométrico.

Diferentes papeles no implican objetos distintos: una misma función puede ser
un elemento de un espacio de funciones. Decide la identidad por las definiciones,
no por los nombres de sus papeles. Evaluar y representar son operaciones que
hay que precisar; un valor puede ser otra función si el codominio lo permite.
Distingue también el índice temporal o la etiqueta de un sensor de la
configuración o lectura que selecciona.

Separa el portador de su estructura: un conjunto con operaciones lineales, una
topología, una norma, un producto interno o una medida determina problemas
distintos. Añade únicamente las estructuras que vayas a usar. Una norma permite
hablar de continuidad y aproximación; no identifica en general un espacio con
su dual continuo. Si \(H\) tiene producto interno, para la norma inducida el mapa
\(J:H\to H^*\), \(J(v)(u)=\langle u,v\rangle\), es inyectivo; \(H^*\)
denota aquí los funcionales lineales continuos. Con el producto interno lineal
en la primera entrada, \(J\) es lineal en el caso real y conjugado-lineal en el
complejo. Si \(H\) es completo para esa norma (un espacio de Hilbert), Riesz
garantiza además la sobreyectividad; en un espacio incompleto puede haber
funcionales continuos sin representante.
Una estructura suave permite diferenciar; una métrica riemanniana es un dato
adicional.

Introduce cada mapa con dominio y codominio, y comprueba que las composiciones
tienen sentido. Para una restricción, un cociente o una construcción local,
explicita dónde está definida y por qué su valor no depende de elecciones que
el resultado pretende olvidar. «Bien definido» es una obligación demostrable.

| Distinción | Qué debe quedar determinado |
| --- | --- |
| Objeto / nombre | El símbolo designa algo definido; renombrarlo no cambia ese objeto. |
| Elemento / coordenadas | Si \(v\in V\), especifica el mapa que produce su tupla y qué elección requiere. |
| Función / valor | \(f:X\to Y\), \(x\in X\) y \(f(x)\in Y\) tienen papeles distintos; \(f\) puede ser a su vez un elemento de un espacio de funciones. |
| Clase / representante | \([x]\in X/{\sim}\) contiene representantes; una fórmula en \(x\) define una función de \([x]\) sólo si es constante en cada clase. |
| Igualdad / isomorfismo | \(X=Y\) afirma igualdad; un isomorfismo es un mapa invertible que preserva la estructura pertinente, también en la dirección inversa. |
| Isomorfismo / identificación elegida | Si escribes un objeto como otro, declara el isomorfismo usado y las elecciones de las que depende. |
| Intrínseco / representación | Explicita qué propiedad pertenece al objeto estructurado y cómo se transforma su descripción al cambiar de representación. |

Una biyección sólo garantiza correspondencia de elementos. Para espacios
topológicos, la equivalencia pertinente exige un homeomorfismo; para espacios
vectoriales, un isomorfismo lineal; para espacios métricos, preservar distancias
es una exigencia adicional. Una biyección continua puede tener inversa
discontinua: el [ejemplo de dos topologías](ontology-examples.md#topologia)
impide identificar equivalencia de conjuntos con equivalencia geométrica.

## Hacer visible la representación

Una representación debe venir con su mapa, las operaciones que respeta y su
alcance. No presupongas coordenadas globales en una variedad. Una carta es local;
un atlas y sus transiciones permiten comparar descripciones en las intersecciones.
Dos cartas compatibles describen la misma estructura suave; cambiar esa
estructura sería otra operación. Lo intrínseco siempre es relativo a los datos
declarados: un gradiente es independiente de las coordenadas una vez fijada la
métrica, pero depende de esa métrica.

El caso lineal fija la disciplina. Sean \(V,W\) espacios vectoriales sobre
\(\mathbb K\in\{\mathbb R,\mathbb C\}\), de dimensiones finitas \(n,m\),
y \(L:V\to W\) lineal. Bases ordenadas \(B=(b_i)\), \(C=(c_j)\)
definen isomorfismos de reconstrucción

\[
e_B:\mathbb K^n\to V,\quad (a_i)\mapsto\sum_i a_i b_i,
\qquad e_C:\mathbb K^m\to W.
\]

Las coordenadas son \([v]_B=e_B^{-1}(v)\). La matriz \(A\) representa,
en las bases estándar de los espacios de coordenadas, el mapa
\(e_C^{-1}\circ L\circ e_B\). Así,

\[
[L(v)]_C=A[v]_B,\qquad L(e_B(a))=e_C(Aa).
\]

La segunda igualdad expresa la compatibilidad que hace útil a la matriz: calcular
y después reconstruir da lo mismo que aplicar \(L\) al objeto. El concepto de
matriz de un mapa respecto de dos bases aparece en
[Axler, *Linear Algebra Done Right*, 4.ª ed., §3C](https://linear.axler.net/LADR4e.pdf).
La siguiente comparación se obtiene directamente de esa composición.

Sean \(B',C'\) otras bases ordenadas de \(V,W\), respectivamente. Las matrices
de cambio \(P\in GL_n(\mathbb K)\), \(Q\in GL_m(\mathbb K)\) se definen por

\[
e_{B'}(a')=e_B(Pa'),\qquad e_{C'}(b')=e_C(Qb')
\]

para todo \(a'\in\mathbb K^n\), \(b'\in\mathbb K^m\). Si \(A'\) representa
a \(L\) en las bases \(B',C'\), entonces

\[
[v]_{B'}=P^{-1}[v]_B,\qquad A'=Q^{-1}AP.
\]

El rango sigue siendo \(\dim\operatorname{im}L\), porque componer con
isomorfismos no cambia la dimensión de la imagen. La semejanza
\(A'=P^{-1}AP\) corresponde al caso \(V=W\) con la misma base en entrada
y salida. Supongamos ahora \(\mathbb K=\mathbb R\). Una forma bilineal
\(\beta:V\times V\to\mathbb R\) es otro tipo de objeto: si
\(\beta(e_B(a),e_B(b))=a^{\mathsf T}Gb\), sustituir \(a=Pa'\),
\(b=Pb'\) da \(G'=P^{\mathsf T}GP\), una congruencia. No traslades
una ley de transformación a otra por la mera apariencia de sus matrices.

## Construir el argumento

Introduce notación cuando aclare una relación o comprima estructura que el
argumento necesita, con nombres estables y sin convertir la prosa en un código
por descifrar. Cuando uses una fórmula, explica qué relación expresa, escríbela
con sus tipos e hipótesis y desarrolla su consecuencia. Define un término antes
de usarlo como premisa. Introduce una construcción abstracta cuando resuelva
una ambigüedad o revele una dependencia real.

Distingue los siguientes compromisos sin exigir etiquetas en cada frase:

- Una **definición** fija un significado o una convención; declara las
  convenciones variables, como el orden de los índices de un tensor.
- Los **axiomas** fijan la clase de estructuras; los **supuestos de modelización**
  vinculan una estructura con el sistema estudiado. Deducir consecuencias dentro
  del modelo no demuestra que ese vínculo describa el sistema.
- Una **hipótesis** restringe los casos considerados. Debe estar presente antes
  del paso que la usa, con sus cuantificadores y alcance local o global.
- Una **consecuencia** requiere un argumento o un teorema cuyas hipótesis se
  hayan comprobado. Justifica los pasos de los que depende la conclusión.
- Una **aproximación** requiere régimen y error: norma, escala, límite o modo
  de convergencia. Un símbolo diferencial no sustituye esa información.
- La **evidencia** numérica o empírica informa sobre los casos observados;
  no demuestra por sí sola una afirmación universal. Una conjetura o inferencia
  debe conservar ese estatus.

Si la pregunta exige probabilidades o esperanzas, establece primero el modelo
probabilístico, el objeto aleatorio y la realización observada; conserva esos
papeles al operar. La insesgadez pertenece al estimador bajo una ley y respecto
de un objetivo declarados, no al número que devuelve una observación aislada.
No añadas estructura estadística cuando no contribuya a la pregunta.

Busca un caso que rompa la afirmación al retirar una hipótesis importante.
Comprueba además el cambio de representación: el mismo vector debe producir el
mismo valor al aplicarle el mismo covector, aunque cambien ambas listas de
componentes. Para una construcción en un cociente, prueba con dos representantes
de la misma clase. Para un límite aleatorio, distingue la variable aleatoria,
el proceso y una trayectoria fijada; declara si la convergencia es en
probabilidad, en media cuadrática o casi segura, y sobre qué particiones.

Estas preguntas se transfieren a otros dominios sin imponerles geometría:

1. ¿Qué clase de objeto es cada entrada y cada resultado? ¿Qué datos forman
   parte de él y cuáles pertenecen a su presentación?
2. ¿Qué relaciones o mapas están permitidos y qué estructura preservan?
3. ¿Qué equivalencia importa para esta pregunta? ¿La construcción respeta esa
   equivalencia o necesita un representante elegido?
4. ¿Qué observación permanece igual al cambiar una representación admisible,
   y qué cálculo demuestra esa invariancia?
5. ¿Qué hipótesis hace válido el paso crucial, y qué caso lo refutaría al
   retirarla? ¿Qué evidencia falta para cerrar la afirmación?
6. ¿Puede el lector obtener el caso concreto desde el marco general y reconstruir
   el paso decisivo sin aportar mentalmente una premisa o identificación ausente?

## Consultar ejemplos y fuentes

Lee sólo el ejemplo que resuelva la dificultad actual: las
[configuraciones](ontology-examples.md#configuraciones) distinguen función,
elemento y cociente; la [topología](ontology-examples.md#topologia) distingue
portador, estructura y generadores; la
[geometría local](ontology-examples.md#geometria) construye tangentes, duales,
tensores y campos; el [cálculo](ontology-examples.md#calculo) distingue
diferencial, gradiente y cambio de variable estocástico. Los cálculos propios
se presentan como tales; las fuentes enlazadas respaldan definiciones y
teoremas concretos. Una referencia no reemplaza la justificación esencial.

Si el usuario menciona un referente, localízalo primero en el contexto y las
fuentes autorizadas del encargo. No solicites una ruta que ya puedas determinar;
pregunta solo si queda una ambigüedad material o falta acceso necesario. Un
título no permite atribuir contenido no leído: mientras falte el original,
distingue tus ejemplos y fuentes de lo que todavía no has comprobado. Registra
procedencia y, cuando el ciclo elegido lo requiera, los archivos como `inputs`
con su hash. Leer un material para adaptar el criterio de explicación y
redistribuirlo son autorizaciones distintas: conserva los materiales privados
fuera del paquete publicable salvo consentimiento específico. No uses
conversaciones, transcripciones ni archivos privados encontrados incidentalmente
para suplir una fuente ausente.
