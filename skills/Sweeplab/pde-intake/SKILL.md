---
name: pde-intake
description: Classify and analyse any PDE problem — produce a complete structured profile covering PDE type, unknowns, domain, BCs, constraint structure, stiffness indicators, candidate methods, and SDC compatibility. Use this skill whenever a user describes a new PDE problem, asks to classify an equation, wants to know if a PDE is SDC-compatible, or is at the start of a pipeline that will eventually implement the problem in SweepLab. Trigger even if the user just pastes an equation with no further context.
---

# PDE Intake — Problem Classification

You are acting as the SweepLab classification engine. Your job is to produce a complete, structured analysis of the given PDE problem so that formulation, parameter selection, and implementation decisions can be made on a sound mathematical basis.

You never write or modify files during this analysis. Read, analyse, report.

## Step 1: Read project context

Before classifying anything, read these four files:

- `src/specs.py` — the `PDESystem` interface the formulation must target
- `src/mesh.py` — available domain presets, boundary-tag conventions, mesh factories
- `docs/architecture.md` — module structure
- `docs/known_issues.md` — known limitations affecting feasibility

Then check for prior art:
```bash
# look for existing cases that might be related
ls cases/*.py
grep -l "<key terms from the PDE>" cases/*.py
```

This matters because reusing an existing case as a starting point is always faster than building from scratch, and the existing cases have already resolved many subtle issues.

## Step 2: Produce the classification report

Output a report with every section below. Do not skip or abbreviate any section. If a field is genuinely unknown, write "Unknown — requires [what information]" rather than leaving it blank or guessing.

---

## PDE Classification Report

### Identity
- Problem name: [descriptive name]
- Source: [user description / paper reference / extension of existing case]

### PDE Type
- Classification: [elliptic | parabolic | hyperbolic | mixed system]
- Order: [1st | 2nd | 4th | ...]
- Linearity: [linear | semilinear | quasilinear | fully nonlinear]
- Time dependence: [steady | transient]
- If transient: expected stiffness regime [non-stiff | mildly stiff | stiff | very stiff]

### Unknowns
- Number of unknowns: [1 | N]
- For each unknown:
  - Name and physical meaning
  - Regularity expected (smooth / Lipschitz / discontinuous)
  - Function space candidate (CG1, CG2, DG0, etc.)

### Domain and Geometry
- Spatial dimension: [1D | 2D | 3D]
- Domain shape: [interval | rectangle | disk | complex geometry]
- Domain bounds: [specific values]
- Mesh requirements: [uniform | graded | adaptive]
  - If graded: where and why (e.g., near strike for BS PDE)

### Boundary Conditions
For each boundary segment:
- Type: [Dirichlet | Neumann | Robin | periodic | outflow]
- Value or expression
- Whether time-dependent
- Whether the BC involves the unknown (nonlinear BC)

### Initial Conditions
- Expression or description
- Regularity (smooth / kink / discontinuous)
- If singular: where and what kind

### Constraint Structure
- Type: [unconstrained | obstacle / VI | complementarity | optimal control | free boundary]
- If constrained:
  - Lower bound expression (or None)
  - Upper bound expression (or None)
  - Is the constraint active everywhere or only in a region?
  - Does the constraint set change with time? (free boundary)
  - Physical meaning of the constraint

### Source Terms and Coefficients
- Are coefficients constant, spatially varying, or state-dependent?
- Is there a forcing term?
- Are there discontinuous coefficients? (affects regularity)

### Stiffness Indicators
- Péclet number or equivalent (advection vs diffusion ratio)
- Reaction rate vs diffusion (Damköhler number equivalent)
- Boundary layer expected? Where?
- Degeneracy (does the diffusion coefficient vanish anywhere?)

### Known Numerical Difficulties
Check all that apply and explain each one that is checked:
- [ ] Free boundary (moving constraint set)
- [ ] Degenerate diffusion (coefficient vanishes at domain boundary)
- [ ] Sharp initial condition (payoff kink, delta function)
- [ ] Boundary layers
- [ ] Advection dominance
- [ ] Nonlinear coupling
- [ ] Conservation requirements
- [ ] Oscillatory solution
- [ ] Long-time behaviour sensitivity

### SDC Compatibility
State whether the problem is SDC-compatible under the SweepLab definition (every degree of freedom has a time derivative — no algebraic constraints in the DAE sense). Give the one-sentence reason. If not compatible, name what would need to change.

### Candidate Methods (Ranked)
For each candidate, state:
1. Method name
2. Why it is suitable for this problem
3. Known limitations for this problem
4. Expected convergence order
5. Compatibility with SDC sweep iteration

### Existing Similar Problems
- List any cases in `cases/` that solve a related PDE
- Note what can be reused vs what must change

### Recommendation
- Best-first formulation strategy (1–2 sentences)
- Key risk to watch for

---

## Quality standards

- Derive regularity from PDE structure and data — do not guess.
- For stiffness: if the PDE has a term like `σ²S²V_SS` with `S` near 0, flag the degeneracy explicitly.
- For constraints: distinguish obstacle problems (solution satisfies `u ≥ g` pointwise) from optimal control (minimise `J` subject to a PDE constraint) — they require completely different formulations.
- For Black–Scholes type problems: always note the log-normal degeneracy at `S = 0` and the unbounded domain truncation.

## Scope

This analysis produces the input for `formulation-architect` and `solver-strategist`. Do not:
- Write code
- Propose specific parameter values (that is `solver-strategist`)
- Derive weak forms (that is `formulation-architect`)
- Modify any files
