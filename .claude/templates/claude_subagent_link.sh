#!/usr/bin/env bash
# claude_subagent_link.sh — wire shared agents/skills/commands into a repo's
# .claude/ via read-only symlinks under _shared/.
#
# Usage:
#   claude_subagent_link.sh <repo_path>
#
# Effect:
#   <repo>/.claude/agents/_shared    → ~/GitHub/.claude/agents
#   <repo>/.claude/skills/_shared    → ~/GitHub/.claude/skills
#   <repo>/.claude/commands/_shared  → ~/GitHub/.claude/commands
#
# Idempotent: re-running is a no-op if links already point at the hub.

set -u

REPO="${1:-}"
[[ -z "$REPO" ]] && { echo "missing repo path" >&2; exit 2; }
[[ ! -d "$REPO/.claude" ]] && { echo "no .claude/ in $REPO" >&2; exit 2; }

HUB="${HOME}/GitHub/.claude"

link_one() {
  local target="$1"
  local source="$2"
  if [[ -L "$target" ]]; then
    local current
    current="$(readlink "$target")"
    if [[ "$current" == "$source" ]]; then
      echo "  - $target  (already linked)"
      return
    fi
    echo "  ! $target points to '$current' — leaving it alone" >&2
    return
  fi
  if [[ -e "$target" ]]; then
    echo "  ! $target exists and is not a symlink — leaving it alone" >&2
    return
  fi
  mkdir -p "$(dirname "$target")"
  ln -s "$source" "$target"
  echo "  + linked $target → $source"
}

echo "wiring shared constellation surfaces into $REPO/.claude/"
link_one "$REPO/.claude/agents/_shared"   "$HUB/agents"
link_one "$REPO/.claude/skills/_shared"   "$HUB/skills"
link_one "$REPO/.claude/commands/_shared" "$HUB/commands"

echo "done."
