---
name: pde-intake
description: Classify and formulate a PDE problem for Sweeplab, identifying its data, constraints, regularity, stiffness and compatibility with available numerical methods before implementation.
---
# PDE intake

Read the [Sweeplab profile](../../../profiles/sweeplab.md), the applicable owner instructions and the current `src/specs.py`, `src/mesh.py` and `src/sdc_gate.py` contracts. Resolve project paths against `/Users/omarkhalil/GitHub/Sweeplab`. Find related implementations under the current `labs/` tree; the former top-level `cases/` tree is not an entry point.

Produce the analysis needed for the requested decision. An explanation can remain in conversation; recording a formulation requires an authorized output path. Do not create a run or choose implementation parameters merely because a PDE was supplied.

## Establish the mathematical problem

- State the unknowns, independent variables, domain, time interval and parameter regime. Distinguish the continuous problem from its discretization and computed fields.
- Specify the operator, coefficients, source terms, initial data and each boundary condition. Identify degeneracy, discontinuities, boundary layers and data compatibility.
- Classify order, linearity and elliptic/parabolic/hyperbolic or mixed structure under explicit hypotheses. Explain the expected regularity and appropriate function spaces rather than assigning smoothness from the equation's name.
- Distinguish an obstacle/variational inequality, complementarity condition, free boundary, optimal-control constraint and algebraic constraint. State the feasible set, bounds and whether it changes with time.
- For a proposed weak formulation, give trial/test spaces, integration-by-parts terms, essential/natural boundary treatment and the assumptions supporting existence or uniqueness. Mark unresolved proof obligations.
- Identify stiffness and relevant nondimensional ratios. For Black–Scholes-type problems, address degeneracy, domain truncation, payoff regularity and dividend/event treatment.

## Assess numerical choices

Compare methods against the actual problem and project capabilities: spatial discretization, conservation or monotonicity needs, constraint treatment, nonlinear solver, temporal method and expected failure modes. Retain the SDC-first policy: justify compatibility from the implemented mass/operator/constraint interface, or explain the concrete obstruction and an alternative. Do not infer compatibility solely from a PDE label or promise an order without its regularity, stability and quadrature assumptions.

Reuse existing lab backends and shared operators before proposing a new implementation. Spatial FE derivatives use FE operators; an ordering of DOFs is not a spatial finite-difference grid. Preserve the project's primal/sensitivity event cursor and the limits of frozen-active-set or frozen-policy sensitivities.

Finish with the recommended formulation, evidence for it, reusable components and unresolved choices that affect correctness. Keep mathematical analysis before dependent implementation; use the native roles for these responsibilities rather than retired specialist selectors.

## Evidence and scope

Separate assumptions, analytic statements and observations from existing runs. Name missing data explicitly. Any numerical experiment or test needs its own authorization and scope; do not create, change or run tests without Omar's explicit request. A static formulation review does not establish convergence or runtime behavior.
