# `~/GitHub/.claude/templates/`

Bootstrap material used by `scripts/bootstrap_repo.sh` and the
`repo-bootstrap` skill.

| File                          | Purpose                                                                  |
| ----------------------------- | ------------------------------------------------------------------------ |
| `CLAUDE.md.template`          | Starting `CLAUDE.md` for any new repo, with perimeter/tier placeholders. |
| `importlinter.template`       | Standard tier-discipline contract for a QuantOS lab.                     |
| `lint.yml.template`           | Standard GitHub Actions lint workflow.                                   |
| `claude_subagent_link.sh`     | Symlink the hub's `agents/skills/commands` into a repo's `.claude/_shared/`. |

## Conventions

- All `.template` files use angle-bracket placeholders (`<LAB_NAME>`,
  `<TIER>`, …). The bootstrap script does NOT auto-substitute — it
  copies verbatim and surfaces the placeholders for the user to fill.
- Templates are intentionally small. If a template grows beyond ~80
  lines, it probably wants to be a proper directory with its own
  scaffolding script.
- Never include secrets or credentials in templates.
