# Category Theory Notes

## Functors and Natural Transformations

Let $\mathcal{C}$ and $\mathcal{D}$ be categories. A **functor**
$F : \mathcal{C} \to \mathcal{D}$ assigns to each object $X \in \mathcal{C}$
an object $F(X) \in \mathcal{D}$.

### Morphism composition

Given morphisms $f, g$ in $\mathcal{C}$, composition satisfies:

$$
F(g \circ_\mathcal{C} f) = F(g) \circ_\mathcal{D} F(f)
$$

### Hom-functor

The hom-functor $\mathbf{Py}_\mathcal{C}(X, -)$ sends each object $Y$ to the
set of morphisms $\mathcal{C}(X, Y)$.

More generally, for any two functors $F, G : \mathcal{C} \to \mathcal{D}$:

$$
\text{Nat}(F, G) = \int_{c \in \mathcal{C}} \mathbf{Hom}_\mathcal{D}(F(c), G(c))
$$

### Example with subscripts on mathbf

Let $v \in \mathbf{R}^n_\mathbf{e}$ denote a vector in the standard basis, and
$A_\mathrm{sym}$ the symmetric part of matrix $A$.

The adjoint operator satisfies $T^\mathrm{ad} = T^*$.
