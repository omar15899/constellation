# Functional Analysis — Banach Spaces

## Definition

A **Banach space** is a complete normed vector space $(X, \|\cdot\|)$.
Completeness means every Cauchy sequence converges in $X$.

## Key Theorems

### Hahn–Banach

If $p : X \to \mathbb{R}$ is a sublinear functional and $f : Y \to \mathbb{R}$
is a linear functional on a subspace $Y \subseteq X$ with $f(y) \leq p(y)$ for
all $y \in Y$, then there exists a linear extension $F : X \to \mathbb{R}$ such
that $F|_Y = f$ and $F(x) \leq p(x)$ for all $x \in X$.

### Open Mapping Theorem

Let $T : X \to Y$ be a bounded surjective linear operator between Banach spaces.
Then $T$ is an open map, i.e., $T(U)$ is open in $Y$ for every open $U \subseteq X$.

**Corollary.** If $T$ is also injective then $T^{-1} : Y \to X$ is bounded.

### Closed Graph Theorem

A linear operator $T : X \to Y$ with closed graph
$$\Gamma(T) = \{(x, Tx) : x \in X\} \subseteq X \times Y$$
is bounded.

## Dual Space

The **dual space** $X^*$ of a Banach space $X$ consists of all bounded linear
functionals $f : X \to \mathbb{R}$ (or $\mathbb{C}$), equipped with the norm:

$$\|f\|_{X^*} = \sup_{\|x\| \leq 1} |f(x)|$$

The **canonical embedding** $J : X \hookrightarrow X^{**}$ defined by
$J(x)(f) = f(x)$ is an isometric isomorphism onto a closed subspace of $X^{**}$.
$X$ is **reflexive** iff $J$ is surjective.

## Examples

| Space | Norm | Dual |
|-------|------|------|
| $\ell^p$, $1 < p < \infty$ | $\left(\sum |x_n|^p\right)^{1/p}$ | $\ell^q$, $1/p + 1/q = 1$ |
| $L^p(\mu)$, $1 < p < \infty$ | $\left(\int |f|^p\, d\mu\right)^{1/p}$ | $L^q(\mu)$ |
| $c_0$ | $\sup_n |x_n|$ | $\ell^1$ |
| $\ell^1$ | $\sum |x_n|$ | $\ell^\infty$ |
