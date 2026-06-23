---
name: evidence
description: Audit every numerical or completion claim in the current answer / report / diff against hard evidence. No artifact or source means the claim is unsupported.
---

# /evidence <report or claim>

Audit all claims in the current answer / report / diff. For every numerical or
completion claim, identify the hard evidence behind it.

**Use:**

| claim | artifact / source | command / check | verified? | caveat |
|---|---|---|---|---|

**Hard evidence** includes: passing tests, metrics files, report files,
generated artifacts, command output, commit hashes. **No artifact / source
means the claim is unsupported** — say so.

To scan files automatically for unsupported claims:

```bash
python3 ~/GitHub/.claude/hooks/evidence_audit.py <path-or-dir>        # advisory
python3 ~/GitHub/.claude/hooks/evidence_audit.py --strict <path>      # exit 1 if unsupported
```

The audit flags a metric/completion claim only when no artifact reference sits
within a few lines of it (false positives kept low). A flagged line is not
necessarily wrong — it means the evidence is not adjacent and must be added or
linked.
