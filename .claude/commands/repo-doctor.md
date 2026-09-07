---
name: repo-doctor
description: Inspect hub or repository health, or audit whether its AI workflows and hooks actually work. Use for control-plane health, broken configuration, stale projections or review of skills, agents and hook behavior; read-only unless repairs are requested.
---

# Repository doctor and workflow audit

Run the read-only diagnostic from the hub:

```bash
python3 .claude/scripts/doctor.py
python3 .claude/scripts/doctor.py --repo <target> --json
```

It composes registry, lever and settings validators; checks hook wiring, Codex
configuration and projection drift; and reports git state. With `--repo`, it
also profiles conflicts, project tooling, raw-data hygiene and oversized staged
blobs. Read findings, not just exit status: PASS/WARN exit 0, FAIL exits 1.
A missing validator is not-run, not a successful check.

For a workflow audit, go beyond structural health:

1. Compare requested behavior with actual sources, helper arguments and authority.
   Look for duplicate skills, conflicting rules, broken references, unsupported
   options and roles that add dispatch without independent responsibility.
2. Select relevant fixture tests from [tests](../tests/) for observed risks.
   For Codex projection/hooks, use test_codex_sync.py,
   test_codex_projection_safety.py, test_codex_workflow.py and test_hook_safety.py.
   Test meaningful refusal cases and false positives; do not use real secrets.
3. Check that retired managed outputs disappear, modified local files survive,
   and unchanged regeneration produces no writes. Review configuration and source
   diffs. Syntax validation alone is not behavioral proof.
4. Distinguish configured, tested and loaded/trusted. Consult
   [Codex parity](../docs/codex_parity.md) for runtime verification and native
   hook review. The doctor cannot establish approval in this running session.

Report evidence-backed gaps and their effects. Apply repairs when requested,
then recheck changed behavior; an audit-only request stays read-only. Do not
create a permanent report or run every suite unless the task warrants it.
