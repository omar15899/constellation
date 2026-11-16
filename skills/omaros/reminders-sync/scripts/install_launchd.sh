#!/usr/bin/env bash
# Install (or reinstall) the reminders-sync LaunchAgent in daemon mode.
#
# Replaces the old daily-cron plist (StartCalendarInterval @ 07:00) with a
# KeepAlive daemon that polls Reminders.app every INTERVAL_SECONDS (default 5).
# Idempotent: safe to re-run.

set -euo pipefail

LABEL="com.omaros.reminders-sync"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC_PLIST="$SKILL_DIR/launchd/$LABEL.plist"
DEST_PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [[ ! -f "$SRC_PLIST" ]]; then
    echo "source plist missing: $SRC_PLIST" >&2
    exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"

# Unload any prior version (old cron-based or older daemon) before overwriting.
if [[ -f "$DEST_PLIST" ]]; then
    launchctl unload "$DEST_PLIST" 2>/dev/null || true
fi

cp "$SRC_PLIST" "$DEST_PLIST"
launchctl load "$DEST_PLIST"

echo "installed: $DEST_PLIST"
echo "interval:  $(/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:INTERVAL_SECONDS' "$DEST_PLIST") s"
echo
echo "logs:"
echo "  /Users/omarkhalil/OmarOS/docs/reminders_sync_daemon.log"
echo "  /Users/omarkhalil/OmarOS/docs/reminders_sync_daemon.err"
echo
echo "to unload: launchctl unload $DEST_PLIST"
