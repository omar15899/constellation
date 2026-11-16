---
name: project
description: Launch a real background Claude Code session for any GitHub project, fully integrated with Agent View. The background session loads the project's own CLAUDE.md and skills from disk — not injected context. Usage — /project <name> [task]. <name> is case-insensitive and partial-match (e.g. "sweep", "execution", "scilux", "pricing"). Use whenever the user says "vamos a trabajar en X", "trabaja en X", "abre el proyecto X", "switch to X", "work on X project", "context switch to X", "abre X en background", "/project X task". After launch, tell the user to press the left arrow key or run `claude agents` to see the Agent View. Do NOT use for OmarOS-internal work (no project switch needed).
license: Proprietary. OmarOS internal.
sk_protected: false
mobile_safe: false
---

# Project — Background Agent Launcher

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

Launches a true background `claude --bg` session from the target project's directory.
The session loads that project's own CLAUDE.md and skills from disk — exactly as if the
user had opened a terminal, `cd`'d into the project, and run `claude --bg`.

All sessions appear in **Agent View**: press `←` (left arrow) from any session, or run
`claude agents` from a new terminal.

**Args:** `$args`

First word = project name (case-insensitive, partial-match).
Everything after = initial task for the background session. If empty, the session opens
interactively (no task sent — the user attaches via Agent View).

---

## Execution steps

### Step 1 — Resolve the project path

Run the following Python snippet via the Bash tool:

```python
import os, sys

raw_args = """$args""".strip()
parts = raw_args.split(None, 1)
name_query = parts[0].lower() if parts else ""
task = parts[1] if len(parts) > 1 else ""

search_bases = [
    "/Users/omarkhalil/GitHub",
    "/Users/omarkhalil/Downloads",
    "/Users/omarkhalil/VisualStudioLocal",
]

candidates = []
for base in search_bases:
    if not os.path.isdir(base):
        continue
    for d in os.listdir(base):
        full = os.path.join(base, d)
        if os.path.isdir(full) and not d.startswith("."):
            candidates.append((d, full))

exact   = [(n, p) for n, p in candidates if n.lower() == name_query]
prefix  = [(n, p) for n, p in candidates if n.lower().startswith(name_query)]
partial = [(n, p) for n, p in candidates if name_query in n.lower()]
# Also match if query is a prefix of any word in the name (e.g. "backtester" → "BacktestLab")
word    = [(n, p) for n, p in candidates if any(
              w.startswith(name_query) for w in n.lower().replace('-','_').replace(' ','_').split('_')
           )]
chosen  = (exact or prefix or partial or word or [None])[0]

if not chosen:
    print("ERROR: no match")
    print("Available:", ", ".join(n for n, _ in sorted(candidates)))
    sys.exit(1)

name, path = chosen
print(f"NAME={name}")
print(f"PATH={path}")
print(f"TASK={task}")
```

If no match, list all available projects and stop. Ask the user to retry with a clearer name.

If args are completely empty, list all projects with their skill counts:

```bash
for d in /Users/omarkhalil/GitHub/*/; do
    name=$(basename "$d")
    skills=$(ls "$d/.claude/skills/" 2>/dev/null | wc -l | tr -d ' ')
    has_claude=$([ -f "$d/CLAUDE.md" ] && echo "✓" || echo "—")
    echo "$name  (CLAUDE.md: $has_claude, skills: $skills)"
done
```

Then ask which project to open and wait.

---

### Step 2 — Launch the background session

Use the Bash tool to run:

```bash
cd "<PATH>" && claude --bg --dangerously-skip-permissions "<TASK>"
```

- If TASK is empty (no task given), omit the task argument entirely:
  ```bash
  cd "<PATH>" && claude --bg --dangerously-skip-permissions
  ```
  This opens an interactive background session the user can attach to.

- `--dangerously-skip-permissions` mirrors OmarOS's `bypassPermissions` default so the
  background session has the same autonomy as the foreground one.

- The session launches from `<PATH>`, so it automatically loads:
  - `<PATH>/CLAUDE.md` (project constitution)
  - `<PATH>/.claude/skills/` (project skills)
  - `<PATH>/.claude/settings.json` (project settings, if any)
  - `~/.claude/settings.json` and `~/CLAUDE.md` (user-level, always)

---

### Step 3 — Confirm and instruct

After the Bash command returns, tell the user:

```
Background session launched for <NAME> at <PATH>.

To open Agent View:
  • Press ← (left arrow) from this session, or
  • Run `claude agents` in a new terminal tab.

The session will appear in the list. Press Enter to attach to it.
```

If a task was given, also say:
```
Task sent: "<TASK>"
The session is working on it. Check Agent View for progress.
```

---

## Error cases

| Condition | Action |
|-----------|--------|
| No name match | List all projects, ask to retry |
| Empty args | List all projects with skill counts, ask which to open |
| `claude --bg` fails | Show the error output; likely a permissions or PATH issue |
| Project has no CLAUDE.md | Launch anyway — note the absence to the user |
