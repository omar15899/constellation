# Cuatro ejemplos de objetos y representaciones

Estos desarrollos aplican la [pauta de ontología](ontology.md) a dificultades
concretas. Las elecciones y cálculos son propios; cada fuente respalda el marco
matemático indicado. No se atribuyen a manuscritos del usuario que no estén
disponibles.

<a id="configuraciones"></a>
## 1. Una función puede ser un punto de un espacio

Fijemos dos etiquetas \(I=\{1,2\}\) y la recta real como espacio de
posiciones. Una configuración sin colisiones es una asignación inyectiva:

\[
Q=\{q:I\to\mathbb R\mid q(1)\ne q(2)\}.
\]

Aquí \(q\) es simultáneamente una función sobre \(I\) y un elemento de
\(Q\). La evaluación \(\operatorname{ev}_i:Q\to\mathbb R\) es otro mapa:
\(\operatorname{ev}_i(q)=q(i)\) es la posición de la etiqueta \(i\), no
la configuración completa. La descripción de configuraciones de un conjunto
finito mediante aplicaciones inyectivas está en
[Church, Ellenberg y Farb, *FI-modules*, §6.2, p. 40](https://www.math.uchicago.edu/~farb/papers/FImod.pdf).

El orden elegido \((1,2)\) produce la biyección

\[
E:Q\to\mathbb R^2\setminus\Delta,\quad q\mapsto(q(1),q(2)),
\qquad \Delta=\{(a,a):a\in\mathbb R\}.
\]

Su inversa asigna a \((a,b)\) la función que vale \(a\) en 1 y \(b\)
en 2. Equipamos \(Q\) con la topología y estructura suave transportadas por
\(E\) desde ese abierto de \(\mathbb R^2\). Es esa elección explícita
de estructura la que hace de \(E\) un difeomorfismo; la biyección aislada
no bastaba. Invertir el orden intercambia las coordenadas, sin cambiar \(q\).

Olvidar las etiquetas es una operación distinta. El grupo \(S_2\) actúa
mediante \((\sigma\cdot q)(i)=q(\sigma^{-1}(i))\). Su cociente
\(Q/S_2\) contiene órbitas \([q]\), con proyección
\(\pi:Q\to Q/S_2\). Si se usa su topología cociente, un subconjunto
\(O\) es abierto exactamente cuando \(\pi^{-1}(O)\) lo es.

Para que \(F:Q\to\mathbb R\) defina una función \(\bar F\) sobre el
cociente con \(F=\bar F\circ\pi\), debe ser constante en cada órbita.
La separación orientada \(F(q)=q(2)-q(1)\) cambia de signo bajo el
intercambio y nunca vale cero; por tanto no desciende. En cambio,
\(G(q)=|q(2)-q(1)|\) satisface \(G(\sigma\cdot q)=G(q)\), así que
\(\bar G([q])=G(q)\) está bien definida. Por ejemplo, las configuraciones
con coordenadas \((1,4)\) y \((4,1)\) son distintas en \(Q\), iguales
tras proyectarlas al cociente y dan el mismo valor \(\bar G=3\).
La magnitud de la separación sobrevive al olvido de etiquetas; su orientación
no lo hace.

<a id="topologia"></a>
## 2. El portador no determina su topología

Una topología sobre un conjunto \(X\) es una colección
\(\tau\subseteq\mathcal P(X)\) que contiene \(\varnothing,X\) y es
cerrada bajo uniones arbitrarias e intersecciones finitas. El espacio es
\((X,\tau)\). Una base \(\mathcal B\subseteq\mathcal P(X)\) cubre
\(X\) y cumple: para \(p\in B_1\cap B_2\), con
\(B_1,B_2\in\mathcal B\), existe \(B_3\in\mathcal B\) tal que
\(p\in B_3\subseteq B_1\cap B_2\). Sus uniones generan la topología.
Véanse las definiciones 1.1 y 1.3 de
[May, *An Outline Summary of Basic Point Set Topology*](https://www.math.uchicago.edu/~may/MISC/Topology.pdf).

La condición de refinamiento explica la construcción: si \(p\) pertenece a
dos uniones de básicos, elige un básico de cada una que contenga a \(p\);
el refinamiento proporciona un básico dentro de la intersección. Reuniéndolos
para todos sus puntos, esa intersección también es una unión de básicos. La
cobertura da \(X\), y la unión vacía da \(\varnothing\). Esta «base»
genera por uniones de subconjuntos; una base lineal genera vectores por
combinaciones lineales y exige independencia. Son definiciones diferentes.

Tomemos \(X=\{a,b\}\), \(a\ne b\). Las colecciones

\[
\tau_d=\{\varnothing,\{a\},\{b\},X\},\qquad
\tau_i=\{\varnothing,X\}
\]

son las topologías discreta e indiscreta, generadas respectivamente por
\(\{\{a\},\{b\}\}\) y \(\{X\}\). La identidad de conjuntos,
considerada como \(j:(X,\tau_d)\to(X,\tau_i)\), es una biyección
continua: las preimágenes de los únicos abiertos del codominio son
\(\varnothing\) y \(X\). Su inversa no es continua, pues la preimagen
de \(\{a\}\in\tau_d\) es \(\{a\}\notin\tau_i\).

Así, incluso una biyección continua puede perder información topológica.
Un homeomorfismo exige también continuidad de la inversa
([May, definición 2.9](https://www.math.uchicago.edu/~may/MISC/Topology.pdf)).
El contraejemplo usa el mismo portador y la misma regla puntual; lo que cambia
es la estructura que cada dirección del mapa debe respetar.

<a id="geometria"></a>
## 3. De una carta a tangentes, duales y tensores

Sea \(M\) una variedad real suave de dimensión finita \(n\), sin borde:
su topología es Hausdorff y tiene una base numerable, y dispone de cartas
\(x:U\to x(U)\subseteq\mathbb R^n\) que son homeomorfismos sobre
abiertos, cubren \(M\) y tienen transiciones suaves. La estructura suave
se fija mediante el atlas maximal compatible. Una carta no tiene por qué
cubrir todo \(M\). Para estas nociones, véanse las
[notas MAT367 de variedades, §§2.1–2.2](https://www.math.toronto.edu/mgualt/courses/18-367/docs/DiffGeomNotes-1.pdf).

Fijado \(p\in M\), consideremos curvas suaves
\(\gamma:(-\varepsilon,\varepsilon)\to M\) con \(\gamma(0)=p\).
Definimos \(\gamma\sim\eta\) cuando sus velocidades coordenadas en una
carta alrededor de \(p\) son iguales. Esta condición es independiente de
la carta: para otra carta \(y\), la regla de la cadena da

\[
(y\circ\gamma)'(0)
=D(y\circ x^{-1})_{x(p)}(x\circ\gamma)'(0).
\]

El mismo factor actúa sobre \(\eta\); la transición inversa demuestra
también el recíproco. El espacio tangente \(T_pM\) es el conjunto de
estas clases de curvas. El mapa
\(J_x:T_pM\to\mathbb R^n\),
\(J_x([\gamma])=(x\circ\gamma)'(0)\), es inyectivo por definición y
sobreyectivo: cualquier \(a\in\mathbb R^n\) se obtiene con la curva
\(t\mapsto x^{-1}(x(p)+ta)\) para \(t\) suficientemente pequeño.

Transportamos suma y multiplicación escalar mediante \(J_x\). Si usamos
\(y\), el cambio \(J_yJ_x^{-1}=D(y\circ x^{-1})_{x(p)}\) es lineal
invertible, así que transporta esas mismas operaciones. Esto construye el
espacio vectorial sin identificar una curva particular con su clase ni una
tupla particular con el vector. La acción sobre funciones locales,
\(v(f)=(f\circ\gamma)'(0)\), también es independiente del representante
por la regla de la cadena. Este enfoque se relaciona con las derivaciones en
las [notas de espacios tangentes, §4.1](https://www.math.toronto.edu/mgualt/courses/18-367/docs/DiffGeomNotes-8.pdf).

El dual es \(T_p^*M=\operatorname{Hom}_{\mathbb R}(T_pM,\mathbb R)\).
Las bases inducidas por la carta son
\(\partial_i|_p=J_x^{-1}(e_i)\) y \(dx^i|_p\), donde
\(dx^i|_p(v)=v(x^i)\); satisfacen
\(dx^i|_p(\partial_j|_p)=\delta^i_j\). Si
\(v=\sum_i v^i\partial_i|_p\) y
\(\alpha=\sum_i\alpha_i dx^i|_p\), entonces
\(\alpha(v)=\sum_i\alpha_i v^i\). El emparejamiento es intrínseco;
las componentes y las bases dependen de la carta. La construcción del dual
y de las formas está en las
[notas de formas diferenciales, §§6.2–6.4](https://www.math.toronto.edu/mgualt/courses/18-367/docs/DiffGeomNotes-10.pdf).

Declaramos la convención: un tensor de tipo \((r,s)\) en \(p\) es un
elemento de \((T_pM)^{\otimes r}\otimes(T_p^*M)^{\otimes s}\), con
\(r,s\ge0\). En dimensión finita se interpreta canónicamente como una
aplicación multilineal con \(r\) entradas covectoriales y \(s\) vectoriales:
un tensor simple actúa por el producto de los emparejamientos respectivos.
Por ejemplo, \((\alpha\otimes\beta)(v,w)=\alpha(v)\beta(w)\).
Una forma alternante de grado \(k\) en \(p\) pertenece a
\(\Lambda^kT_p^*M\); alternante significa que intercambiar dos entradas
cambia el signo.

Un vector en \(T_pM\) pertenece a una sola fibra. Un campo vectorial suave
es una sección \(V:M\to TM\), con \(\pi\circ V=\mathrm{id}_M\),
del fibrado \(TM=\coprod_p T_pM\), equipado con sus trivializaciones
suaves inducidas por las cartas. Un campo tensorial es una sección suave del
fibrado tensorial correspondiente; una \(k\)-forma diferencial suave es
una sección de \(\Lambda^kT^*M\). En particular, una 1-forma es un campo
de covectores, y su valor en \(p\) es un covector. Véanse las
[notas de campos, §5.1](https://www.math.toronto.edu/mgualt/courses/18-367/docs/DiffGeomNotes-9.pdf).

La circunferencia da una comprobación explícita. Sea
\(S^1=\{(u,v)\in\mathbb R^2:u^2+v^2=1\}\), con cartas

\[
x(u,v)=\frac{v}{1-u}\quad\text{en }U=S^1\setminus\{(1,0)\},
\qquad
y(u,v)=\frac{v}{1+u}\quad\text{en }V=S^1\setminus\{(-1,0)\}.
\]

Ambas tienen imagen \(\mathbb R\): por ejemplo,
\(x^{-1}(a)=((a^2-1)/(a^2+1),2a/(a^2+1))\), y
\(y^{-1}(b)=((1-b^2)/(1+b^2),2b/(1+b^2))\).
En la intersección, \(xy=v^2/(1-u^2)=1\), luego
\(y\circ x^{-1}(a)=1/a\) para \(a\ne0\). En
\(p=(3/5,4/5)\), \(x(p)=2\), \(y(p)=1/2\). La regla de la cadena
y su dual dan

\[
\partial_x|_p=-\tfrac14\partial_y|_p,\qquad
dx|_p=-4\,dy|_p,\qquad
dx|_p\otimes dx|_p=16\,dy|_p\otimes dy|_p.
\]

En efecto, \(dy/dx=-1/x^2=-1/4\) y \(dx/dy=-1/y^2=-4\).
Por tanto \(dx|_p(\partial_x|_p)=(-4)(-1/4)=1\), y el tensor
\(dx|_p\otimes dx|_p\) evaluado sobre dos copias de
\(\partial_x|_p\) sigue valiendo \(16(-1/4)^2=1\).
La transformación inversa de bases duales conserva la evaluación; un tensor
no es una tabla de componentes sin ley de transformación.

Las notas citadas están alojadas en el curso
[MAT367 de Marco Gualtieri, Toronto, 2018](https://www.math.toronto.edu/mgualt/courses/18-367/),
cuya página indica que se basan en un libro en preparación de E. Meinrenken
y G. Gross. El cálculo concreto de \(S^1\) anterior es propio.

<a id="calculo"></a>
## 4. Diferencial, gradiente y variación cuadrática

Sean \(E,F\) espacios normados reales, \(U\subseteq E\) abierto y
\(f:U\to F\). La derivada de Fréchet en \(x\in U\), si existe, es
un operador **lineal acotado** \(Df(x):E\to F\) tal que

\[
f(x+h)=f(x)+Df(x)[h]+r_x(h),\qquad
\frac{\|r_x(h)\|_F}{\|h\|_E}\longrightarrow0\quad(h\to0,\ h\ne0).
\]

El límite usa todos los incrementos pequeños con \(x+h\in U\), no sólo
una dirección fijada. No hace falta completitud para esta definición. Dos
operadores candidatos \(A,B\) deben coincidir: fijado \(h\), aplica
ambas expansiones al incremento \(th\), resta, divide por \(|t|\) y
haz \(t\to0\); resulta \((A-B)h=0\). Véase
[Bell, *Fréchet derivatives and Gâteaux derivatives*, §3](https://jordanbell.info/LaTeX/mathematics/frechetderivatives/).
La derivada es un mapa lineal; \(Df(x)[h]\) es su valor sobre un incremento.

Si \(E=H\) es un Hilbert real y \(F=\mathbb R\), el teorema de Riesz
representa ese funcional continuo mediante un único vector:

\[
Df(x)[h]=\langle h,\operatorname{grad}f(x)\rangle_H
\quad\text{para todo }h\in H.
\]

El diferencial pertenece a \(H^*\); el gradiente pertenece a \(H\), y el
producto interno proporciona la identificación. Riesz se desarrolla en las
[notas MIT 18.102, primavera de 2021, teorema 184](https://ocw.mit.edu/courses/18-102-introduction-to-functional-analysis-spring-2021/8fb8d5c170f1613151aca71de21027bc_MIT18_102s21_full_lec.pdf).
En una variedad riemanniana, la misma relación se aplica fibra a fibra;
véase [Boumal, §3.8, definición 3.58](https://www.nicolasboumal.net/book/IntroOptimManifolds_Boumal_2022.pdf).

Fijemos ahora \(f(x)=\frac12\langle x,x\rangle_H\). La identidad
\(f(x+h)-f(x)=\langle x,h\rangle_H+\frac12\|h\|_H^2\) prueba
\(Df(x)[h]=\langle x,h\rangle_H\) y
\(\operatorname{grad}f(x)=x\). Si cambiamos el producto interno a
\(\langle u,v\rangle_c=c\langle u,v\rangle_H\), \(c>0\),
**manteniendo fija la función** \(f\), las normas son equivalentes y el
diferencial sigue siendo el mismo funcional. Ahora su representante es
\(\operatorname{grad}_c f(x)=x/c\), porque
\(\langle h,x/c\rangle_c=\langle h,x\rangle_H\).
Cambiar la métrica cambia este gradiente; cambiar coordenadas con la métrica
fija cambia sólo su descripción.

El cambio de variable estocástico requiere además especificar el tipo de
trayectorias y la integral. En un espacio de probabilidad filtrado
\((\Omega,\mathcal F,(\mathcal F_t),\mathbb P)\) con las condiciones
usuales (completitud y continuidad por la derecha), sea \(W\) un movimiento
browniano real respecto de esa filtración, con \(W_0=0\). Sean \(X_0\)
real, finito y \(\mathcal F_0\)-medible, y \(b,\sigma\) procesos
reales progresivamente medibles tales que, para todo \(T<\infty\),
\(\int_0^T(|b_s|+\sigma_s^2)\,ds<\infty\) casi seguramente.
Definimos el proceso de Itô continuo

\[
X_t=X_0+\int_0^t b_s\,ds+\int_0^t\sigma_s\,dW_s,
\]

donde la segunda integral es la integral de Itô, localizada cuando haga falta.
Para \(f\in C^{1,2}([0,T]\times\mathbb R)\) —una derivada temporal y
dos espaciales continuas—, la fórmula integral de Itô afirma, casi seguramente
para todo \(t\le T\),

\[
\begin{aligned}
f(t,X_t)-f(0,X_0)
={}&\int_0^t\left(\partial_t f(s,X_s)
 +b_s\partial_x f(s,X_s)
 +\tfrac12\sigma_s^2\partial_{xx}f(s,X_s)\right)ds\\
&+\int_0^t\sigma_s\partial_x f(s,X_s)\,dW_s.
\end{aligned}
\]

Es un teorema de cambio de variable para semimartingalas; el término de segundo
orden se integra contra su variación cuadrática. La versión espacial y su
demostración están en
[Baudoin, lección 21, fórmula de Itô I](https://fabricebaudoin.blog/2012/09/19/lecture-21-itos-formula/);
la versión temporal, con la hipótesis suficiente más fuerte \(C^2\), y la
definición de proceso de Itô están en
[Ryzhik, *Math 227 notes*, definición 2.11 y teorema 2.12, p. 18](https://math.stanford.edu/~ryzhik/STANFORD/STANF227-13/notes227-13.pdf).
La regularidad \(C^{1,2}\) se explicita también en
[MIT 18.642, lección 19.1, diapositivas 15 y 20](https://ocw.mit.edu/courses/18-642-topics-in-mathematics-with-applications-in-finance-fall-2024/mit18_642_f24_lec19_1.pdf).
La regularidad temporal \(C^1\) basta: los incrementos de tiempo son de
variación finita, su contribución se obtiene por el teorema fundamental del
cálculo y sólo la variable espacial necesita el término cuadrático.

El caso \(f(t,x)=x^2\), \(X=W\), muestra exactamente qué produce ese
término. Para una partición determinista \(\Pi\) de \([0,t]\), escribamos
\(\Delta W_i=W_{t_{i+1}}-W_{t_i}\) y
\(|\Pi|=\max_i(t_{i+1}-t_i)\). La identidad algebraica telescópica es

\[
W_t^2=2\sum_i W_{t_i}\Delta W_i+\sum_i(\Delta W_i)^2.
\]

Los incrementos son gaussianos independientes, con varianza \(\Delta t_i\).
Si \(Q_\Pi=\sum_i(\Delta W_i)^2\), sus momentos dan

\[
\mathbb E Q_\Pi=t,\qquad
\mathbb E[(Q_\Pi-t)^2]=2\sum_i(\Delta t_i)^2
\le 2t|\Pi|\longrightarrow0.
\]

Así \(Q_\Pi\to t\) en \(L^2\) para sucesiones de particiones
deterministas cuya malla tienda a cero. También las sumas por la izquierda
convergen en \(L^2\) a \(\int_0^t W_s\,dW_s\): por la isometría
de Itô, su error cuadrático medio es
\(\sum_i\int_{t_i}^{t_{i+1}}\mathbb E|W_s-W_{t_i}|^2ds
=\frac12\sum_i(\Delta t_i)^2\to0\). Al pasar al límite obtenemos

\[
W_t^2=2\int_0^tW_s\,dW_s+t.
\]

La igualdad vale casi seguramente para cada \(t\), y las versiones continuas
permiten elegir un único suceso de probabilidad uno donde vale para todos los
tiempos, usando primero los racionales. Esto no afirma convergencia casi segura
de las sumas cuadráticas simultáneamente para cualquier elección de particiones.
El cálculo browniano puede contrastarse con
[Ryzhik, pp. 14–18](https://math.stanford.edu/~ryzhik/STANFORD/STANF227-13/notes227-13.pdf).

Para una trayectoria real continua \(z\) de variación total finita en
\([0,t]\), en cambio,
\(\sum_i(\Delta z_i)^2\le\max_i|\Delta z_i|\,
\operatorname{Var}_{[0,t]}(z)\to0\), por continuidad uniforme.
La expansión de Taylor sigue siendo una relación determinista sobre la función;
lo que cambia al sumarla a lo largo de una trayectoria browniana es qué términos
sobreviven al límite. La escritura \((dW)^2=dt\) resume esa variación
cuadrática: no es una igualdad entre infinitesimales ordinarios.
