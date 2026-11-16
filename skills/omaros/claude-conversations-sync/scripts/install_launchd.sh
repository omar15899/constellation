#!/usr/bin/env bash
# Install the claude-conversations-sync launchd agent (mirrors calendar-sync).
set -euo pipefail

REPO_ROOT="/Users/omarkhalil/OmarOS"
PLIST_SRC="/Users/omarkhalil/GitHub/Constellation/skills/omaros/claude-conversations-sync/launchd/com.omaros.claude-conversations-sync.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.omaros.claude-conversations-sync.plist"

mkdir -p "$HOME/Library/LaunchAgents"

# Render REPO_ROOT into the plist (template uses __REPO_ROOT__ placeholder).
sed "s|__REPO_ROOT__|$REPO_ROOT|g" "$PLIST_SRC" > "$PLIST_DST"

# Reload: unload if present, then load.
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo "Loaded com.omaros.claude-conversations-sync"
echo "Plist: $PLIST_DST"
echo "Logs:  $REPO_ROOT/docs/claude_conversations_sync_daemon.log"
echo
echo "To enable continuous auto-commit of rendered transcripts, add to the plist"
echo "EnvironmentVariables:  CCSYNC_COMMIT = 1   (then reload)."
