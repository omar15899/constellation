---
name: refute
description: Adversarial self-review. Do not defend the current solution — try to falsify it. Lists failure modes, runs at least one cheap test, and downgrades the claim if evidence is weak.
---

# /refute <claim>

Do **not** defend the current solution. Try to falsify it.

**Produce:**

| possible failure | why plausible | cheap test | result | consequence |
|---|---|---|---|---|

Rules:

- At least **five** possible failures.
- At least **one** cheap test must actually be run, unless impossible.
- If no test is run, explain why.
- If the evidence is weak, **downgrade the claim** — say "unverified" or
  "partial", not "done".

Quant-specific failure modes worth checking (when relevant): stale artifact,
silent fallback to a default, NaN / null / empty metric, lookahead leakage,
survivorship bias, alpha mistaken for beta exposure, costs/turnover ignored,
sample too small. For research validity use `/quant-loop`.
