#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/omarkhalil/OmarOS"
PLIST_SRC="/Users/omarkhalil/GitHub/Constellation/skills/omaros/codex-conversations-sync/launchd/com.omaros.codex-conversations-sync.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.omaros.codex-conversations-sync.plist"
RAW_DIR="${CODEXSYNC_RAW_DIR:-$HOME/OmarOS_RawData/codex-conversations-raw}"
GUI_DOMAIN="gui/$(id -u)"

mkdir -p "$HOME/Library/LaunchAgents" "$RAW_DIR"
chmod 700 "$RAW_DIR"

sed \
  -e "s|__REPO_ROOT__|$REPO_ROOT|g" \
  -e "s|__RAW_DIR__|$RAW_DIR|g" \
  "$PLIST_SRC" > "$PLIST_DST"
chmod 600 "$PLIST_DST"

launchctl bootout "$GUI_DOMAIN" "$PLIST_DST" 2>/dev/null || true
launchctl bootstrap "$GUI_DOMAIN" "$PLIST_DST"
launchctl kickstart -k "$GUI_DOMAIN/com.omaros.codex-conversations-sync"

echo "Loaded com.omaros.codex-conversations-sync"
echo "Plist:    $PLIST_DST"
echo "Raw:      $RAW_DIR"
echo "Rendered: $REPO_ROOT/09_Data_Sources/Codex_Conversations/rendered"
echo "Logs:     $REPO_ROOT/docs/codex_conversations_sync_daemon.log"
