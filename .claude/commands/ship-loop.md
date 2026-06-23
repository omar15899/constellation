---
name: ship-loop
description: Final verified-success gate before finalising or committing — git status, diff inspection, syntax checks, focused tests, secret scan, evidence audit, refutation audit, artifact and report confirmation. Commits only if explicitly requested.
---

# /ship-loop

Before finalising or committing, run the gate in order:

1. `git status --short` (skip cleanly if not in a git repo — e.g. `~/GitHub/`).
2. Inspect changed files.
3. Run cheap syntax checks:
   - `bash -n` on changed shell scripts;
   - `python3 -m py_compile` on changed Python.
4. Run the relevant **focused** tests (not the whole suite unless asked).
5. Run the secret scan:
   `bash ~/GitHub/.claude/hooks/secret_scan.sh` (or rely on the staged-diff path).
6. Run the evidence audit:
   `python3 ~/GitHub/.claude/hooks/evidence_audit.py --strict <report paths>`.
7. Run the refutation audit (`/refute`).
8. Confirm the expected artifacts exist on disk.
9. Confirm reports / logs are updated.
10. Confirm no `.env` or secret-like file is staged.
11. **Commit only if explicitly requested** by the user. Natural commit
    message, no AI attribution, no `Co-authored-by` (per `~/CLAUDE.md`). One
    commit per repo (constellation git policy).

**Final answer (required):**

| claim | artifact / source | check performed | result | residual caveat |
|---|---|---|---|---|

The `Stop` hook [`loop_guard.py`](../hooks/loop_guard.py) backs this gate
deterministically: it blocks on staged secrets and on TODO/FIXME markers left
in `.claude/`, and (with `LOOP_GUARD_STRICT=1`) on completion claims that carry
no hard-evidence token.
