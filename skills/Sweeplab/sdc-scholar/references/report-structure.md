# SweepLab Scholar — Section Content Reference

Canonical structure derived from:
- `review/2026/04/11/american_iv_research_2026-04-11_19-41-47/discussion.md` (740 lines — master reference)
- `review/2026/04/10/american_put_analysis/analysis.md` (459 lines — focused reference)

Read both documents before using this reference. The rules below describe what the sections contain — not what to copy, but what depth and structure each section must reach.

---

## §1. Introduction

**Length:** 15–25 lines. No prose preamble.

**Required content:**
- One paragraph: what was solved, the method (FEM + SDC + VI/penalty), spatial domain and resolution, time integration parameters.
- A bullet list of central quantitative results — all numbers at four significant figures. Minimum: price(s), CRR reference(s), relative error(s), EEP, any convergence rate measured, invariant status.
- One paragraph: what this run establishes (e.g. "demonstrates that the FEM-VI-SDC pipeline achieves machine-precision agreement with the binomial reference at standard grid resolution").
- One sentence on what the remainder of the document covers.

**Example bullet block (from master reference):**
```
- American put: V=6.0901, CRR 6.0900, rel err 1.77×10⁻⁵
- American call: V=10.4506, CRR 10.4496, rel err 9.58×10⁻⁵
- EEP (put): 0.5166 (9.3% of V_Eu=5.5735)
- EEP (call): 1.37×10⁻⁶ ≈ 0, confirming Merton's theorem
- Penalty convergence: O(ε) rate measured 1.02 (theory: 1.0)
- All 10 numerical invariants pass
```

---

## §2. Mathematical Framework

**Length:** 60–100 lines. Four subsections covering the four theoretical pillars.

### 2.1 American Options as Optimal Stopping
- Snell envelope: `V(S,t) = sup_{τ∈[t,T]} E_t^Q[e^{−r(τ−t)}Φ(S_τ)]`
- Define continuation region C and stopping region E with set notation
- State S*(t) as the free boundary; note it is part of the solution, not given a priori
- For the put: S*(t) ∈ (0, K), approaches K as t→T, approaches S*_∞=Kr/b for large T
- For the call (b=r): S*(t)=+∞ (Merton, §2.1 preview)

### 2.2 The Obstacle Problem (Variational Inequality)
- Write the complementarity system in full, all three conditions
- Define L_BS explicitly: `L_BS V = ½σ²S²∂²V/∂S² + bS∂V/∂S − rV`
- State Lions–Stampacchia existence/uniqueness; name the Bochner space `L²(0,T;H¹₀(Ω))∩H¹(0,T;H⁻¹(Ω))`
- Write the weak form with bilinear form `a(u,w) = ∫[½σ²S²∂u/∂S·∂w/∂S − bSu·∂w/∂S + ru·w]dS`
- State the FE space used (CG2, n_elem, DOFs, h)

### 2.3 Penalty Regularisation (include if penalty method used)
- Source term: `(1/ε)max(Φ−V_ε, 0)`
- State Jaillet–Lamberton–Lapeyre (1990): `‖V_ε − V‖_{L²(Q_T)} = O(ε)` — name the theorem
- Explain why non-differentiability at Φ−V=0 requires backtracking linesearch (bt)
- Give the condition number estimate O(1/ε) for the penalised Jacobian

### 2.4 SDC Time Integration
- State the collocation representation: u_M(t) = Σ_{j=1}^M u_j L_j(t)
- Write the sweep: u^{(k+1)} = u^{(k)} − Q_Δ^{-1} F_coll(u^{(k)})
- State accuracy: K sweeps with Q_Δ = backward-Euler → O(Δt^{K+1}) up to collocation order 2M−1
- State the VI compatibility: constraints enforced inside each node solve

---

## §3. Numerical Setup

**Length:** 15–25 lines. Two parts: a table and one explanatory paragraph.

**Parameter table (mandatory):**
| Parameter | Symbol | Value |
|-----------|--------|------:|
| Domain | [0, S_max] | [0, 400] |
| Mesh elements | n_elem | 500 |
| FE space | — | CG2 |
| DOFs | — | 1001 |
| Mesh spacing | h | 0.4 |
| Time step | dt | 0.01 |
| Time steps | N | 100 |
| SDC nodes | M | 3 (Radau-right) |
| SDC sweeps | K | 3 |
| Solver | snes_type | vinewtonrsls |
| Tolerances | rtol / atol | 1e-8 / 1e-10 |
| Max Newton its | snes_max_it | 500 |
| Reference | CRR | N=2000 |

**Explanatory paragraph:** justify the non-obvious choices — S_max=4K (far-field truncation error <10⁻⁶), CG2 over CG1 (second derivatives for Greeks), dt=0.01 (empirical stability at snes_max_it=500), M=3 Radau-right (balances accuracy and conditioning).

**Appendix:** always include a full solver configuration block (SNES settings verbatim).

---

## §4. Price Surfaces and Time Evolution

Embed `price_surface.png` (or equivalent).

**Required analysis (4+ sentences):**
- Geometric character: convexity in S (Γ>0), monotone in τ, convergence to payoff as τ→0
- Where slices of V(S,·) at different τ concentrate near the payoff — physical meaning
- Why the call lies strictly above its payoff everywhere (Merton) and the put touches the payoff for S < S*(τ)
- What changes in the surface shape near ATM as τ varies (the smile/skew of Γ)

---

## §5. Early Exercise Premium: Structure and Magnitude

Embed EEP figure (two panels: EEP(τ) at S₀=K, and EEP(S,τ) spatial profile).

**Required content:**
- Quantify EEP at S₀=K: absolute value, fraction of V_Eu, what this represents in dollars
- Explain growth rate of EEP for small τ: relates to discounting of strike r·K·τ
- Spatial structure of EEP(S,τ): plateau in stopping region where EEP ≈ K(1−e^{−rτ}), drop near S*(τ), near-zero in C
- For the call: EEP ≈ 0 to machine precision — Merton's theorem confirmed numerically

---

## §6. Greeks Surfaces: Δ, Γ, Θ

Embed Greeks figure (three panels).

**Required per Greek:**
- Visual description: curve shape, dependence on τ
- Physical meaning: what risk this Greek hedges, which market participant is exposed
- Key feature: the kink in Δ at S*(τ), the Gamma spike, the Theta sign
- Quantitative reference: ATM value for this run

**Specific callouts:**
- Δ discontinuity across S*(τ): V' is continuous from above but jumps across the free boundary in the limit
- Γ spike at S*(τ): Γ→+∞ as S→S*(τ)⁺ in the continuous limit; FEM regularises this to a sharp peak
- Θ sign: Θ>0 for American put (time value increases with τ) — derive from the PDE perspective (−∂V/∂t = L_BS V in C)

---

## §7. Gamma Diagnostics and Free Boundary Detection

Embed four-panel Gamma diagnostics figure. This is the most technically rich section — give it 30+ lines.

**Four panels:**
1. **Raw Γ:** zero in the stopping region (V=Φ is linear in S → V''=0 exactly, not numerically), peak at S*(τ), smooth decay in C. The zero-Gamma region is an exact analytical statement.
2. **Smoothed Γ (Gaussian, σ=N/50):** why regularisation reveals true peak shape vs mesh noise; what the regularisation parameter σ means geometrically (spans ~20 mesh widths)
3. **|∂Γ/∂S| on log scale:** the derivative of Γ is a free boundary detector because Γ is not smooth across S* — the contrast between S* and the rest of the domain is orders of magnitude
4. **|ΔΓ| jump metric on log scale:** the jump in Γ at S* is the cleanest numerical signature of the free boundary; connection to the smooth-fit condition (V'(S*)=Φ'(S*) holds, but V''(S*) does not)

**Report:** detected S*(τ=T) with units and method. Compare to theoretical S*_∞=Kr/b.

---

## §8. Call Free Boundary: Merton's Theorem

Embed call free boundary figure (price contour in (S,τ) plane).

**Required content:**
- Why S*(τ)=S_max for the call with b=r — state Merton (1973) by name
- The contour plot shows every point in C (no stopping region exists) — this is a visual proof
- What changes if b < r (e.g. dividend yield > risk-free rate): stopping region re-emerges, state the critical ratio
- Compare to the put free boundary visible in §7

---

## §9. Vega and Rho: Sensitivity to Market Parameters

Embed Vega/Rho figure (two panels: ν(S,τ) and ρ(S,τ)).

**Per Greek:**
- Visual shape (Vega: bell near ATM; Rho: sigmoid for call, negative sigmoid for put)
- Dependence on τ: Vega decreases as τ→0 (less time for volatility to matter); Rho increases (greater interest rate sensitivity over longer horizon)
- ATM values from this run, comparison with BS closed-form formula
- Which market participant is primarily exposed (vol desk for Vega, rate desk for Rho)

---

## §10. Greeks at S₀: Full Numerical Report

**One complete table with all Greeks for both put and call:**

| Greek | Put | Call | Reference (BS/CRR) | Rel. Error |
|-------|-----|------|-------------------|------------|
| Price V | | | CRR N=2000 | |
| Delta Δ | | | BS formula | |
| Gamma Γ | | | BS formula | |
| Theta Θ | | | BS formula | |
| Vega ν | | | BS formula | |
| Rho ρ | | | BS formula | |
| European V_Eu | | | BS formula | |
| EEP | | | — | — |

**BS theta identity verification (mandatory):**
For each option type, compute LHS = ½σ²S₀²Γ + bS₀Δ − rV and compare to |Θ|. Report:
- Put: LHS=__, |Θ|=__, discrepancy=__%, [PASS/FAIL]
- Call: LHS=__, |Θ|=__, discrepancy=__%, [PASS/FAIL]

Note: the identity holds exactly in C; discrepancy at S₀≈S* reflects proximity to the stopping region.

---

## §11. Epsilon Convergence Study

Embed three-panel epsilon figure: solution profiles, Gamma sharpening, L² error (log-log).

**Convergence table:**
| ε | L² error | Measured order |
|---|----------|----------------|

**Required analysis:**
- Left panel: systematic deviation near S* for large ε; the penalty solution holds V_ε slightly above Φ
- Middle panel: Gamma sharpening as ε→0; the convergence of Gamma profile is convergence in W^{1,p}
- Right panel: log-log regression slope vs theoretical O(ε); report slope ± confidence interval

**Practical recommendation:** when is penalty adequate (λ≤10⁴, rel err <10⁻³) vs when is VI required (research quality, max constraint violation <10⁻⁶)?

---

## §12. Method Comparison: VI, Penalty, Projection

Embed method comparison figure for the put (three panels: price, Gamma, deviation).

**Three-panel analysis:**
- Price panel: visual indistinguishability at plotting resolution — what this hides about the constraint-region error
- Gamma panel: where methods diverge (near S*) and why — different constraint enforcement → different Gamma profiles at the kink
- Deviation panel (log scale): quantify peak deviation for each method pair, spatial localisation near S*

**Call panel (if present):** all methods agree to ~10⁻⁴ — no active constraint, deviations are pure discretisation noise.

**Recommendation table:**
| Method | Accuracy | Cost | When to use |
|--------|----------|------|-------------|
| VI (vinewtonrsls) | best | highest | thesis/research |
| Penalty λ=10⁴ | good | medium | preliminary |
| Projection | adequate | lowest | rough estimates |

---

## §13. Dividend Stress Test

Embed six-panel dividend figure.

**Six panels — one paragraph each:**
1. Price profiles at τ=T for different q: where dividend curves separate from no-dividend baseline
2. ΔV = V_div − V_nodiv: spatial structure of price impact; non-monotone sign from drop-and-reset
3. Γ at τ=T: free boundary shift changes Gamma peak location and height
4. S*(τ) with and without dividend: smooth no-dividend curve, and the discontinuous jump in S*(τ) at τ_D; **state the jump condition V(S,τ_D+) = V(S+D,τ_D−) from the dividend drop-and-reset mechanism**
5. Γ near τ_D: Gamma spike migrating as dividend is processed
6. EEP at S₀ vs τ: EEP larger with dividend (faster approach to K−S); kink in curve at τ_D

---

## §14. Convergence Analysis

**Two subsections: spatial and temporal.**

### Spatial Convergence
Table: n_elem | h | price error | EOC
Measured EOC vs theoretical O(h²) for CG2 in L² norm (or O(h) for energy norm).

### Temporal Convergence (SDC sweep order)
Table: K sweeps | dt | error | EOC
Measured EOC for K=1,2,3 vs theoretical O(Δt^{K+1}).

Explain saturation at collocation order 2M−1: once K≥2M−1, additional sweeps do not improve order. For M=3 Radau-right, saturation at K=5 (order 5).

---

## §15. Numerical Invariant Verification

**Full 10-point invariant table:**

| # | Invariant | Computed | Reference | Status |
|---|-----------|----------|-----------|--------|
| 1 | V_Am_call ≈ V_Eu_call (no dividends) | | BS formula | |
| 2 | V_Am_put > V_Eu_put | | — | |
| 3 | Δ_put < 0 | | — | |
| 4 | Δ_call ∈ (0,1) | | — | |
| 5 | Γ > 0 (both) | | — | |
| 6 | Put monotone in S | | — | |
| 7 | SDC convergence order ≥ K | | O(Δt^{K+1}) | |
| 8 | CRR consistency (rel err <5×10⁻²) | | CRR N=2000 | |
| 9 | Constraint satisfaction (max(Φ−V) <10⁻⁶) | | 0 | |
| 10 | BS theta identity (discrepancy <5%) | | exact in C | |

For each PASS with substantial margin: note what the margin implies for grid convergence or solver quality.
For any FAIL: identify the likely cause and what further investigation is needed.

---

## §16. Conclusions and Outlook

**Length:** 20–30 lines. Five substantive points — never a summary.

Required points:
1. What this run establishes about the FEM-VI-SDC pipeline (be specific: which regime, which parameter range, which accuracy claim)
2. What the convergence study establishes (if run)
3. What the method comparison establishes about practical solver choice (with specific thresholds)
4. Two or three follow-up experiments with scientific motivation (not generic "future work")
5. One genuinely open mathematical question raised by the results

**Practical recommendations section** (always present):
```
For research-quality results: use vinewtonrsls (VI), snes_max_it≥500, dt≤0.02.
For preliminary diagnostics: penalty with λ=10⁴, snes_linesearch_type=bt.
```

---

## Style invariants

- **Tense:** present for mathematical facts, past for what the computation did.
- **Numbers:** four significant figures. Never "approximately 6.1" — write 6.090.
- **Theorems:** named. Never "it can be shown that".
- **No:** "as shown in the figure", "as mentioned above", "it is clear that", "trivially", "obviously", "in conclusion".
- **Language:** output language = language of the user's prompt. LaTeX math in both languages.
- **Figure captions:** descriptive ("Fig 7: Four-panel Gamma diagnostics at τ=1 year"), not generic ("Fig 7: Gamma").
