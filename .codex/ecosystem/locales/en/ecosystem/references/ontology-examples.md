# Four examples of objects and representations

These developments apply the [ontology guidelines](ontology.md) to specific
difficulties. The choices and calculations are our own; each source supports
the indicated mathematical framework. They are not attributed to unavailable
manuscripts by the user.

<a id="configuraciones"></a>
## 1. A function can be a point of a space

Fix two labels \(I=\{1,2\}\) and the real line as the space of
positions. A collision-free configuration is an injective assignment:

\[
Q=\{q:I\to\mathbb R\mid q(1)\ne q(2)\}.
\]

Here \(q\) is simultaneously a function on \(I\) and an element of
\(Q\). Evaluation \(\operatorname{ev}_i:Q\to\mathbb R\) is another map:
\(\operatorname{ev}_i(q)=q(i)\) is the position of label \(i\), rather than
the entire configuration. The description of configurations of a finite set
through injective maps appears in
[Church, Ellenberg and Farb, *FI-modules*, §6.2, p. 40](https://www.math.uchicago.edu/~farb/papers/FImod.pdf).

The chosen order \((1,2)\) produces the bijection

\[
E:Q\to\mathbb R^2\setminus\Delta,\quad q\mapsto(q(1),q(2)),
\qquad \Delta=\{(a,a):a\in\mathbb R\}.
\]

Its inverse assigns to \((a,b)\) the function taking the value \(a\) at 1
and \(b\) at 2. Equip \(Q\) with the topology and smooth structure transported
by \(E\) from that open subset of \(\mathbb R^2\). It is this explicit
choice of structure that makes \(E\) a diffeomorphism; the bijection alone
was insufficient. Reversing the order swaps the coordinates without changing \(q\).

Forgetting the labels is a different operation. The group \(S_2\) acts
by \((\sigma\cdot q)(i)=q(\sigma^{-1}(i))\). Its quotient
\(Q/S_2\) contains orbits \([q]\), with projection
\(\pi:Q\to Q/S_2\). With the quotient topology, a subset
\(O\) is open exactly when \(\pi^{-1}(O)\) is open.

For \(F:Q\to\mathbb R\) to define a function \(\bar F\) on the
quotient satisfying \(F=\bar F\circ\pi\), it must be constant on every orbit.
The oriented separation \(F(q)=q(2)-q(1)\) changes sign under the swap
and is never zero; it therefore does not descend to the quotient. In contrast,
\(G(q)=|q(2)-q(1)|\) satisfies \(G(\sigma\cdot q)=G(q)\), so
\(\bar G([q])=G(q)\) is well defined. For example, the configurations
with coordinates \((1,4)\) and \((4,1)\) are distinct in \(Q\), equal
after projection to the quotient. For either configuration \(q\),
the image of its orbit is \(\bar G([q])=3\).
The magnitude of the separation survives forgetting the labels; its orientation
does not.

<a id="topologia"></a>
## 2. The underlying set does not determine its topology

A topology on a set \(X\) is a collection
\(\tau\subseteq\mathcal P(X)\) containing \(\varnothing,X\) and
closed under arbitrary unions and finite intersections. The space is
\((X,\tau)\). A basis \(\mathcal B\subseteq\mathcal P(X)\) covers
\(X\) and satisfies the following condition: for \(p\in B_1\cap B_2\),
with \(B_1,B_2\in\mathcal B\), there is \(B_3\in\mathcal B\) such that
\(p\in B_3\subseteq B_1\cap B_2\). Its unions generate the topology.
See Definitions 1.1 and 1.3 in
[May, *An Outline Summary of Basic Point Set Topology*](https://www.math.uchicago.edu/~may/MISC/Topology.pdf).

The refinement condition explains the construction: if \(p\) belongs to
two unions of basis elements, choose a basis element containing \(p\) from
each union; refinement provides a basis element inside their intersection.
Taking their union over all points shows that the intersection is also a union
of basis elements. Coverage gives \(X\), and the empty union gives
\(\varnothing\). This “basis” generates by unions of subsets; a linear basis
generates vectors through linear combinations and requires independence.
These are different definitions.

Take \(X=\{a,b\}\), \(a\ne b\). The collections

\[
\tau_d=\{\varnothing,\{a\},\{b\},X\},\qquad
\tau_i=\{\varnothing,X\}
\]

are the discrete and indiscrete topologies, generated respectively by
\(\{\{a\},\{b\}\}\) and \(\{X\}\). The identity map on sets,
viewed as \(j:(X,\tau_d)\to(X,\tau_i)\), is a continuous
bijection: the preimages of the only open sets in the codomain are
\(\varnothing\) and \(X\). Its inverse is not continuous, since the preimage
of \(\{a\}\in\tau_d\) is \(\{a\}\notin\tau_i\).

Thus even a continuous bijection can lose topological information.
A homeomorphism also requires continuity of the inverse
([May, Definition 2.9](https://www.math.uchicago.edu/~may/MISC/Topology.pdf)).
The counterexample uses the same underlying set and the same pointwise rule;
what changes is the structure that each direction of the map must respect.

<a id="geometria"></a>
## 3. From a chart to tangents, duals and tensors

Let \(M\) be a finite-dimensional smooth real manifold of dimension \(n\),
without boundary: its topology is Hausdorff and second countable, and it has
charts \(x:U\to x(U)\subseteq\mathbb R^n\) that are homeomorphisms
onto open sets, cover \(M\), and have smooth transitions. The smooth structure
is fixed by the compatible maximal atlas. A chart need not cover all of
\(M\). For these notions, see the
[MAT367 manifold notes, §§2.1–2.2](https://www.math.toronto.edu/mgualt/courses/18-367/docs/DiffGeomNotes-1.pdf).

Fix \(p\in M\) and consider smooth curves
\(\gamma:(-\varepsilon,\varepsilon)\to M\) with \(\gamma(0)=p\).
Define \(\gamma\sim\eta\) when their coordinate velocities in a chart
around \(p\) are equal. This condition is independent of the chart:
for another chart \(y\), the chain rule gives

\[
(y\circ\gamma)'(0)
=D(y\circ x^{-1})_{x(p)}(x\circ\gamma)'(0).
\]

The same factor acts on \(\eta\); the inverse transition also proves the
converse. The tangent space \(T_pM\) is the set of these equivalence classes
of curves. The map
\(J_x:T_pM\to\mathbb R^n\),
\(J_x([\gamma])=(x\circ\gamma)'(0)\), is injective by definition and
surjective: any \(a\in\mathbb R^n\) is obtained from the curve
\(t\mapsto x^{-1}(x(p)+ta)\) for sufficiently small \(t\).

Transport addition and scalar multiplication through \(J_x\). If we use
\(y\), the change \(J_yJ_x^{-1}=D(y\circ x^{-1})_{x(p)}\) is
invertible and linear, so it transports those same operations. This constructs
the vector space without identifying a particular curve with its class or a
particular tuple with the vector. The action on local functions,
\(v(f)=(f\circ\gamma)'(0)\), is also independent of the representative
by the chain rule. This approach is related to derivations in the
[tangent-space notes, §4.1](https://www.math.toronto.edu/mgualt/courses/18-367/docs/DiffGeomNotes-8.pdf).

The dual is \(T_p^*M=\operatorname{Hom}_{\mathbb R}(T_pM,\mathbb R)\).
The bases induced by the chart are
\(\partial_i|_p=J_x^{-1}(e_i)\) and \(dx^i|_p\), where
\(dx^i|_p(v)=v(x^i)\); they satisfy
\(dx^i|_p(\partial_j|_p)=\delta^i_j\). If
\(v=\sum_i v^i\partial_i|_p\) and
\(\alpha=\sum_i\alpha_i dx^i|_p\), then
\(\alpha(v)=\sum_i\alpha_i v^i\). The pairing is intrinsic;
the components and bases depend on the chart. The construction of the dual
and of forms appears in the
[differential-form notes, §§6.2–6.4](https://www.math.toronto.edu/mgualt/courses/18-367/docs/DiffGeomNotes-10.pdf).

Declare the convention: a tensor of type \((r,s)\) at \(p\) is an
element of \((T_pM)^{\otimes r}\otimes(T_p^*M)^{\otimes s}\), with
\(r,s\ge0\). In finite dimensions it is canonically interpreted as a
multilinear map with \(r\) covector arguments and \(s\) vector arguments:
a simple tensor acts through the product of the respective pairings.
For example, \((\alpha\otimes\beta)(v,w)=\alpha(v)\beta(w)\).
An alternating form of degree \(k\) at \(p\) belongs to
\(\Lambda^kT_p^*M\); alternating means that swapping two arguments
changes the sign.

A vector in \(T_pM\) belongs to a single fiber. A smooth vector field
is a section \(V:M\to TM\), with \(\pi\circ V=\mathrm{id}_M\),
of the bundle \(TM=\coprod_p T_pM\), equipped with its chart-induced
smooth trivializations. A tensor field is a smooth section of the corresponding
tensor bundle; a smooth differential \(k\)-form is a section of
\(\Lambda^kT^*M\). In particular, a 1-form is a field of covectors,
and its value at \(p\) is a covector. See the
[field notes, §5.1](https://www.math.toronto.edu/mgualt/courses/18-367/docs/DiffGeomNotes-9.pdf).

The circle gives an explicit check. Let
\(S^1=\{(u,v)\in\mathbb R^2:u^2+v^2=1\}\), with charts

\[
x(u,v)=\frac{v}{1-u}\quad\text{on }U=S^1\setminus\{(1,0)\},
\qquad
y(u,v)=\frac{v}{1+u}\quad\text{on }V=S^1\setminus\{(-1,0)\}.
\]

Both have image \(\mathbb R\): for example,
\(x^{-1}(a)=((a^2-1)/(a^2+1),2a/(a^2+1))\), and
\(y^{-1}(b)=((1-b^2)/(1+b^2),2b/(1+b^2))\).
On the intersection, \(xy=v^2/(1-u^2)=1\), hence
\(y\circ x^{-1}(a)=1/a\) for \(a\ne0\). At
\(p=(3/5,4/5)\), \(x(p)=2\), \(y(p)=1/2\). The chain rule
and its dual give

\[
\partial_x|_p=-\tfrac14\partial_y|_p,\qquad
dx|_p=-4\,dy|_p,\qquad
dx|_p\otimes dx|_p=16\,dy|_p\otimes dy|_p.
\]

Indeed, \(dy/dx=-1/x^2=-1/4\) and \(dx/dy=-1/y^2=-4\).
Therefore \(dx|_p(\partial_x|_p)=(-4)(-1/4)=1\), and the tensor
\(dx|_p\otimes dx|_p\) evaluated on two copies of
\(\partial_x|_p\) still has value \(16(-1/4)^2=1\).
The inverse transformation of dual bases preserves evaluation; a tensor is
not a table of components without a transformation law.

The cited notes are hosted in
[Marco Gualtieri's MAT367 course, Toronto, 2018](https://www.math.toronto.edu/mgualt/courses/18-367/),
whose page states that they are based on a book in preparation by E. Meinrenken
and G. Gross. The specific calculation on \(S^1\) above is our own.

<a id="calculo"></a>
## 4. Differential, gradient and quadratic variation

Let \(E,F\) be real normed spaces, \(U\subseteq E\) open, and
\(f:U\to F\). The Fréchet derivative at \(x\in U\), if it exists,
is a **bounded linear** operator \(Df(x):E\to F\) such that

\[
f(x+h)=f(x)+Df(x)[h]+r_x(h),\qquad
\frac{\|r_x(h)\|_F}{\|h\|_E}\longrightarrow0\quad(h\to0,\ h\ne0).
\]

The limit uses all sufficiently small increments with \(x+h\in U\), rather
than a single fixed direction. Completeness is unnecessary for this definition.
Two candidate operators \(A,B\) must coincide: fix \(h\), apply both
expansions to the increment \(th\), subtract, divide by \(|t|\), and
let \(t\to0\); this gives \((A-B)h=0\). See
[Bell, *Fréchet derivatives and Gâteaux derivatives*, §3](https://jordanbell.info/LaTeX/mathematics/frechetderivatives/).
The derivative is a linear map; \(Df(x)[h]\) is its value on an increment.

If \(E=H\) is a real Hilbert space and \(F=\mathbb R\), the Riesz
theorem represents that continuous functional through a unique vector:

\[
Df(x)[h]=\langle h,\operatorname{grad}f(x)\rangle_H
\quad\text{for every }h\in H.
\]

The differential belongs to \(H^*\); the gradient belongs to \(H\), and
the inner product provides the identification. Riesz is developed in the
[MIT 18.102 notes, Spring 2021, Theorem 184](https://ocw.mit.edu/courses/18-102-introduction-to-functional-analysis-spring-2021/8fb8d5c170f1613151aca71de21027bc_MIT18_102s21_full_lec.pdf).
On a Riemannian manifold, the same relation applies fiber by fiber;
see [Boumal, §3.8, Definition 3.58](https://www.nicolasboumal.net/book/IntroOptimManifolds_Boumal_2022.pdf).

Now fix \(f(x)=\frac12\langle x,x\rangle_H\). The identity
\(f(x+h)-f(x)=\langle x,h\rangle_H+\frac12\|h\|_H^2\) proves
\(Df(x)[h]=\langle x,h\rangle_H\) and
\(\operatorname{grad}f(x)=x\). If we change the inner product to
\(\langle u,v\rangle_c=c\langle u,v\rangle_H\), \(c>0\),
**keeping the function** \(f\) **fixed**, the norms are equivalent and the
differential remains the same functional. Its representative is now
\(\operatorname{grad}_c f(x)=x/c\), because
\(\langle h,x/c\rangle_c=\langle h,x\rangle_H\).
Changing the metric changes this gradient; changing coordinates with the metric
fixed changes only its description.

Stochastic change of variables also requires specifying the type of paths
and the integral. On a filtered probability space
\((\Omega,\mathcal F,(\mathcal F_t),\mathbb P)\) satisfying the usual
conditions (completeness and right continuity), let \(W\) be a real Brownian
motion with respect to that filtration, with \(W_0=0\). Let \(X_0\)
be real, finite and \(\mathcal F_0\)-measurable, and let \(b,\sigma\)
be real progressively measurable processes such that, for every \(T<\infty\),
\(\int_0^T(|b_s|+\sigma_s^2)\,ds<\infty\) almost surely.
Define the continuous Itô process

\[
X_t=X_0+\int_0^t b_s\,ds+\int_0^t\sigma_s\,dW_s,
\]

where the second integral is the Itô integral, localized when necessary.
For \(f\in C^{1,2}([0,T]\times\mathbb R)\)—one continuous time
 derivative and two continuous spatial derivatives—the integral Itô formula
states, almost surely for every \(t\le T\),

\[
\begin{aligned}
f(t,X_t)-f(0,X_0)
={}&\int_0^t\left(\partial_t f(s,X_s)
 +b_s\partial_x f(s,X_s)
 +\tfrac12\sigma_s^2\partial_{xx}f(s,X_s)\right)ds\\
&+\int_0^t\sigma_s\partial_x f(s,X_s)\,dW_s.
\end{aligned}
\]

This is a change-of-variables theorem for semimartingales; the second-order
term is integrated against their quadratic variation. The spatial version
and its proof appear in
[Baudoin, Lecture 21, Itô's formula I](https://fabricebaudoin.blog/2012/09/19/lecture-21-itos-formula/);
the time-dependent version, with the stronger sufficient hypothesis \(C^2\),
and the definition of an Itô process appear in
[Ryzhik, *Math 227 notes*, Definition 2.11 and Theorem 2.12, p. 18](https://math.stanford.edu/~ryzhik/STANFORD/STANF227-13/notes227-13.pdf).
The regularity \(C^{1,2}\) is also stated explicitly in
[MIT 18.642, Lecture 19.1, slides 15 and 20](https://ocw.mit.edu/courses/18-642-topics-in-mathematics-with-applications-in-finance-fall-2024/mit18_642_f24_lec19_1.pdf).
Time regularity \(C^1\) suffices: time increments have finite variation,
their contribution follows from the fundamental theorem of calculus, and only
the spatial variable needs the quadratic term.

The case \(f(t,x)=x^2\), \(X=W\), shows exactly what that term produces.
For a deterministic partition \(\Pi\) of \([0,t]\), write
\(\Delta W_i=W_{t_{i+1}}-W_{t_i}\) and
\(|\Pi|=\max_i(t_{i+1}-t_i)\). The telescoping algebraic identity is

\[
W_t^2=2\sum_i W_{t_i}\Delta W_i+\sum_i(\Delta W_i)^2.
\]

The increments are independent Gaussian variables with variance \(\Delta t_i\).
If \(Q_\Pi=\sum_i(\Delta W_i)^2\), their moments give

\[
\mathbb E Q_\Pi=t,\qquad
\mathbb E[(Q_\Pi-t)^2]=2\sum_i(\Delta t_i)^2
\le 2t|\Pi|\longrightarrow0.
\]

Thus \(Q_\Pi\to t\) in \(L^2\) for sequences of deterministic
partitions whose mesh tends to zero. The left-point sums also converge in
\(L^2\) to \(\int_0^t W_s\,dW_s\): by the Itô isometry, their
mean-square error is
\(\sum_i\int_{t_i}^{t_{i+1}}\mathbb E|W_s-W_{t_i}|^2ds
=\frac12\sum_i(\Delta t_i)^2\to0\). Taking the limit gives

\[
W_t^2=2\int_0^tW_s\,dW_s+t.
\]

The equality holds almost surely for each \(t\), and continuous versions
allow us to choose a single event of probability one on which it holds for all
times, using rational times first. This does not assert almost-sure convergence
of the quadratic sums simultaneously for every choice of partitions.
The Brownian calculation can be checked against
[Ryzhik, pp. 14–18](https://math.stanford.edu/~ryzhik/STANFORD/STANF227-13/notes227-13.pdf).

For a continuous real path \(z\) of finite total variation on
\([0,t]\), in contrast,
\(\sum_i(\Delta z_i)^2\le\max_i|\Delta z_i|\,
\operatorname{Var}_{[0,t]}(z)\to0\), by uniform continuity.
The Taylor expansion remains a deterministic relation about the function;
what changes when it is summed along a Brownian path is which terms survive
the limit. The notation \((dW)^2=dt\) summarizes that quadratic variation:
it is not an equality between ordinary infinitesimals.
